import { bridgeConfigured, isOwner, safeJson } from '@/lib/security';
export const runtime='nodejs';
const GET_ALLOW=new Set(['orbit','memory','trace','provider','conversation','storage','context','connections','bio','chat-job','observations','models','model-inventory']);
const POST_ALLOW=new Set(['chat','chat-start','context','connections','bio','observations','models','azure-read']);
type RouteContext={params:Promise<{endpoint:string}>};
async function forward(request:Request, method:'GET'|'POST', {params}:RouteContext) {
  if (!await isOwner()) return safeJson(401,{error:'Owner authentication required'});
  const {endpoint}=await params;
  if (!(method==='GET'?GET_ALLOW:POST_ALLOW).has(endpoint)) return safeJson(404,{error:'Route not exposed by the cloud bridge'});
  const incoming=new URL(request.url);
  if(endpoint==='chat-job'&&method==='GET'){
    if([...incoming.searchParams.keys()].length!==1||!incoming.searchParams.has('id')||
       !/^[A-Za-z0-9_-]{32}$/.test(incoming.searchParams.get('id')||''))
      return safeJson(400,{error:'Invalid chat job ID'});
  }else if(incoming.search) return safeJson(400,{error:'Unexpected query parameters'});

  if (!bridgeConfigured()) return safeJson(503,{error:'A durable HTTPS Beast Box bridge has not been provisioned. No model call was performed.'});
  let body: string|undefined;
  if (method==='POST') {
    if (endpoint==='connections'||endpoint==='bio'||endpoint==='chat-start'||endpoint==='observations'||endpoint==='models'||endpoint==='azure-read') {
      // Cross-site forms must not edit credentials or submit sensitive bio readings.
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
    if(endpoint==='azure-read') {
      if(Object.keys(input).sort().join(',')!=='blob_name,read_confirmed'||
         input.read_confirmed!==true||typeof input.blob_name!=='string'||
         !/^[A-Za-z0-9][A-Za-z0-9._/-]{0,179}$/.test(input.blob_name)||
         input.blob_name.split('/').some(s=>!s||s==='.'||s==='..')||
         !/\.(txt|md|json|csv)$/i.test(input.blob_name))
         return safeJson(400,{error:'Confirm one exact Azure text blob name; no automatic retrieval'});
    }
    if(endpoint==='models'){
      const keys=Object.keys(input).sort().join(',');
      const choice=input.choice;
      if(choice==='local'){
        if(keys!=='choice')return safeJson(400,{error:'Local model selection accepts only choice'});
      }else if(choice==='huggingface'||choice==='ollama_cloud'){
        const selectedModel=choice==='ollama_cloud'&&typeof input.model==='string';
        if(keys!==(selectedModel?'choice,model,spend_approved':'choice,spend_approved')||
           input.spend_approved!==true||
           (selectedModel&&(!/^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,179}$/.test(input.model as string)||
                            (input.model as string).endsWith('-cloud'))))
          return safeJson(400,{error:'Remote model activation requires explicit usage approval and a valid model ID'});
      }else return safeJson(400,{error:'Unknown model selection'});
    }
    if (endpoint==='observations') {
      if(body.length>4000||Object.keys(input).sort().join(',')!=='consent,observations,persist_confirmed'||
         input.consent!==true||input.persist_confirmed!==true||!Array.isArray(input.observations)||
         input.observations.length<1||input.observations.length>8)
        return safeJson(400,{error:'Owner consent and bounded observation batch required'});
      for(const item of input.observations){
        if(!item||typeof item!=='object'||Array.isArray(item))return safeJson(400,{error:'Invalid observation'});
        const entry=item as Record<string,unknown>;
        const keys=Object.keys(entry).sort().join(',');
        const camera=entry.source==='camera_classifier';
        if(!['camera_classifier','browser_speech'].includes(String(entry.source))||
           keys!==(camera?'confidence,source,text,timestamp':'source,text,timestamp')||
           typeof entry.text!=='string'||entry.text.length<1||
           entry.text.length>(camera?96:240)||
           typeof entry.timestamp!=='string'||entry.timestamp.length>35||
           (camera&&(typeof entry.confidence!=='number'||!Number.isFinite(entry.confidence)||
                    entry.confidence<0.32||entry.confidence>1)))
          return safeJson(400,{error:'Only bounded text labels and transcripts are accepted'});
      }
    }
    if (endpoint==='bio') {
      const allowed=['heart_rate_bpm','hrv_rmssd_ms','respiration_rate_bpm','skin_temperature_c',
        'spo2_pct','eda_microsiemens','accelerometer_rms_g','eeg_alpha_relative',
        'eeg_beta_relative','eeg_theta_relative','eeg_delta_relative','eeg_gamma_relative'];
      const base=['action','source','consent','readings'];
      const action=input.action;
      const keys=Object.keys(input).sort();
      const validKeys=action==='preview'?base:action==='persist'
        ?[...base,'persist_confirmed',...(input.remote_share_confirmed===true?['remote_share_confirmed']:[])]
        :[];
      if(!validKeys.length||keys.join(',')!==validKeys.sort().join(',')||input.consent!==true||
         !['manual','wearable_export','browser_sensor'].includes(String(input.source))||
         !input.readings||typeof input.readings!=='object'||Array.isArray(input.readings)||
         (action==='persist'&&input.persist_confirmed!==true)||body.length>2_048)
        return safeJson(400,{error:'Invalid or unconsented bio submission'});
      const readings=input.readings as Record<string,unknown>;
      const channels=Object.keys(readings);
      if(channels.length<1||channels.length>12||
         channels.some(k=>!allowed.includes(k)||typeof readings[k]!=='number'||!Number.isFinite(readings[k])))
        return safeJson(400,{error:'Bio readings must be bounded numeric channels'});
    }
    if (endpoint==='chat'||endpoint==='chat-start') {
      if(endpoint==='chat-start'&&(
         typeof input.request_id!=='string'||
         !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(input.request_id)||
         !Array.isArray(input.context_ids)))return safeJson(400,{error:'Invalid async chat ID or context selection'});

      if (Object.keys(input).some(k=>!['text','context_ids',...(endpoint==='chat-start'?['request_id']:[])].includes(k))) return safeJson(400,{error:'Cloud chat only accepts text, context IDs and a request ID'});
      const text=input.text;
      if (typeof text!=='string'||text.trim().length<1||text.length>8192) return safeJson(400,{error:'Chat text must be 1..8192 characters'});
      if (input.context_ids!==undefined && (!Array.isArray(input.context_ids)||input.context_ids.length>20||input.context_ids.some(x=>!Number.isSafeInteger(x)||x<0))) return safeJson(400,{error:'Invalid context IDs'});
    }
    if (endpoint==='connections') {
      const allowed=['action','provider','config','secret','spend_approved','model'];
      if (Object.keys(input).some(k=>!allowed.includes(k))||typeof input.action!=='string'||typeof input.provider!=='string') return safeJson(400,{error:'Invalid connection operation'});
      if (!['save','remove','activate','test','update_model'].includes(input.action)) return safeJson(400,{error:'Unsupported connection operation'});
      if (input.action==='save' && (Object.keys(input).sort().join(',')!=='action,config,provider,secret'||typeof input.secret!=='string'||input.secret.length>4096||!input.config||typeof input.config!=='object'||Array.isArray(input.config)))return safeJson(400,{error:'Invalid provider credentials'});
      if (input.action==='activate' && (Object.keys(input).sort().join(',')!=='action,provider,spend_approved'||input.spend_approved!==true)) return safeJson(400,{error:'Explicit model-spending approval required'});
      if (input.action==='update_model'&&(
        Object.keys(input).sort().join(',')!=='action,model,provider'||
        !['ollama_cloud','huggingface'].includes(input.provider as string)||
        typeof input.model!=='string'||input.model.length<1||input.model.length>180||
        !/^[A-Za-z0-9_.:/-]+$/.test(input.model)
      )) return safeJson(400,{error:'Invalid model update; no credential was changed'});
      if (!['save','activate','update_model'].includes(input.action as string) && Object.keys(input).sort().join(',')!=='action,provider') return safeJson(400,{error:'Invalid provider action'});
    }
    if (endpoint==='context' && (Object.keys(input).sort().join(',')!=='name,scope,text'||input.scope!=='temporary_attachment'||typeof input.name!=='string'||typeof input.text!=='string'||input.name.length>255||input.text.length>16000)) return safeJson(400,{error:'Only bounded temporary attachment context is accepted'});
  }
  const root=process.env.BEASTBOX_CLOUD_BRIDGE_URL!;
  const url=new URL('/api/'+endpoint, root.endsWith('/')?root:root+'/');
  if(endpoint==='chat-job') url.searchParams.set('id',incoming.searchParams.get('id')!);
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
