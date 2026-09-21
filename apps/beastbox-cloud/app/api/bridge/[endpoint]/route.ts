import { bridgeConfigured, isOwner, safeJson } from '@/lib/security';
export const runtime='nodejs';
const GET_ALLOW=new Set(['orbit','memory','trace','provider','conversation','storage','context','connections','bio']);
const POST_ALLOW=new Set(['chat','context','connections','bio']);
type RouteContext={params:Promise<{endpoint:string}>};
async function forward(request:Request, method:'GET'|'POST', {params}:RouteContext) {
  if (!await isOwner()) return safeJson(401,{error:'Owner authentication required'});
  const {endpoint}=await params;
  if (!(method==='GET'?GET_ALLOW:POST_ALLOW).has(endpoint)) return safeJson(404,{error:'Route not exposed by the cloud bridge'});
  if (!bridgeConfigured()) return safeJson(503,{error:'A durable HTTPS Beast Box bridge has not been provisioned. No model call was performed.'});
  let body: string|undefined;
  if (method==='POST') {
    if (endpoint==='connections' || endpoint==='bio') {
      // A cross-site form or redirect must never set credentials or upload bio measurements.
      const origin=request.headers.get('origin');
      if (!origin || origin!==new URL(request.url).origin) return safeJson(403,{error:'Same-origin owner action required'});
      if (!request.headers.get('content-type')?.toLowerCase().startsWith('application/json')) return safeJson(415,{error:'JSON required'});
    }
    if (Number(request.headers.get('content-length') || 0)>256_000) return safeJson(413,{error:'Request too large'});
    body=await request.text();
    if (body.length>256_000) return safeJson(413,{error:'Request too large'});
    let parsed:unknown;try{parsed=JSON.parse(body);}catch{return safeJson(400,{error:'Invalid JSON'});}
    if (!parsed || typeof parsed!=='object' || Array.isArray(parsed)) return safeJson(400,{error:'Invalid request'});
    const input=parsed as Record<string,unknown>;
    if (endpoint==='chat') {
      if (Object.keys(input).some(k=>!['text','context_ids'].includes(k))) return safeJson(400,{error:'Cloud chat only accepts text and selected context IDs'});
      const text=input.text;
      if (typeof text!=='string'||text.trim().length<1||text.length>8192) return safeJson(400,{error:'Chat text must be 1..8192 characters'});
      if (input.context_ids!==undefined && (!Array.isArray(input.context_ids)||input.context_ids.length>20||input.context_ids.some(x=>!Number.isSafeInteger(x)||x<0))) return safeJson(400,{error:'Invalid context IDs'});
    }
    if (endpoint==='connections') {
      const allowed=['action','provider','config','secret','spend_approved'];
      if (Object.keys(input).some(k=>!allowed.includes(k))||typeof input.action!=='string'||typeof input.provider!=='string') return safeJson(400,{error:'Invalid connection operation'});
      if (!['save','remove','activate','test'].includes(input.action)) return safeJson(400,{error:'Unsupported connection operation'});
      if (input.action==='save' && (Object.keys(input).sort().join(',')!=='action,config,provider,secret'||typeof input.secret!=='string'||input.secret.length>4096||!input.config||typeof input.config!=='object'||Array.isArray(input.config)))return safeJson(400,{error:'Invalid provider credentials'});
      if (input.action==='activate' && (Object.keys(input).sort().join(',')!=='action,provider,spend_approved'||input.spend_approved!==true)) return safeJson(400,{error:'Explicit model-spending approval required'});
      if (!['save','activate'].includes(input.action as string) && Object.keys(input).sort().join(',')!=='action,provider') return safeJson(400,{error:'Invalid provider action'});
    }
    if (endpoint==='bio') {
      const required=['captured_at','consent','persist','share_remote','signals','source'];
      if (Object.keys(input).sort().join(',')!==required.join(',') || input.consent!==true ||
          typeof input.persist!=='boolean' || typeof input.share_remote!=='boolean')
        return safeJson(400,{error:'Explicit bio consent and persistence/remote-sharing choices required'});
      if (!['manual','wearable_summary','research_sensor'].includes(String(input.source)))
        return safeJson(400,{error:'Unsupported bio source'});
      if (typeof input.captured_at!=='number' || !Number.isFinite(input.captured_at))
        return safeJson(400,{error:'Invalid bio timestamp'});
      const bounds:Record<string,[number,number]>={
        heart_rate_bpm:[20,260], hrv_rmssd_ms:[0,500], respiration_bpm:[2,90],
        skin_temperature_c:[15,50], eda_microsiemens:[0,150], movement_index:[0,1],
      };
      const signals=input.signals;
      if (!signals || typeof signals!=='object' || Array.isArray(signals))
        return safeJson(400,{error:'Bio input requires bounded numeric summaries'});
      const entries=Object.entries(signals);
      if (entries.length<1 || entries.length>6 || entries.some(([name,value])=>
        !Object.prototype.hasOwnProperty.call(bounds,name) || typeof value!=='number' ||
        !Number.isFinite(value) || value<bounds[name][0] || value>bounds[name][1]))
        return safeJson(400,{error:'Invalid physiological summary values'});
    }
    if (endpoint==='context' && (Object.keys(input).sort().join(',')!=='name,scope,text'||input.scope!=='temporary_attachment'||typeof input.name!=='string'||typeof input.text!=='string'||input.name.length>255||input.text.length>16000)) return safeJson(400,{error:'Only bounded temporary attachment context is accepted'});
  }
  const root=process.env.BEASTBOX_CLOUD_BRIDGE_URL!;
  const url=new URL('/api/'+endpoint, root.endsWith('/')?root:root+'/');
  try {
    const upstream=await fetch(url, {method, body, cache:'no-store',redirect:'error',
      headers:{Authorization:'Bearer '+process.env.BEASTBOX_CLOUD_BRIDGE_TOKEN!,
        ...(method==='POST'?{'Content-Type':'application/json'}:{})},signal:AbortSignal.timeout(45_000)});
    const raw=await upstream.text();
    if (raw.length>1_000_000) return safeJson(502,{error:'Backend response too large'});
    let data:unknown;try{data=JSON.parse(raw);}catch{return safeJson(502,{error:'Invalid backend response'});}
    if (!upstream.ok) return safeJson(upstream.status>=500?502:upstream.status,{error:(data&&typeof data==='object'&&'error' in data&&typeof data.error==='string')?data.error:'Backend rejected request'});
    return safeJson(200,data);
  } catch {return safeJson(502,{error:'Durable Beast Box service unavailable; no substitute provider was used'});}
}
export async function GET(request:Request,context:RouteContext){return forward(request,'GET',context);}
export async function POST(request:Request,context:RouteContext){return forward(request,'POST',context);}
