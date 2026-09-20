import { bridgeConfigured, isOwner, safeJson } from '@/lib/security';
export const runtime='nodejs';
const GET_ALLOW=new Set(['orbit','memory','trace','provider','conversation','storage','context']);
const POST_ALLOW=new Set(['chat','context']);
type RouteContext={params:Promise<{endpoint:string}>};
async function forward(request:Request, method:'GET'|'POST', {params}:RouteContext) {
  if (!await isOwner()) return safeJson(401,{error:'Owner authentication required'});
  const {endpoint}=await params;
  if (!(method==='GET'?GET_ALLOW:POST_ALLOW).has(endpoint)) return safeJson(404,{error:'Route not exposed by the cloud bridge'});
  if (!bridgeConfigured()) return safeJson(503,{error:'A durable HTTPS Beast Box bridge has not been provisioned. No model call was performed.'});
  let body: string|undefined;
  if (method==='POST') {
    if (Number(request.headers.get('content-length') || 0)>256_000) return safeJson(413,{error:'Request too large'});
    body=await request.text();
    if (body.length>256_000) return safeJson(413,{error:'Request too large'});
    let parsed:unknown;try{parsed=JSON.parse(body);}catch{return safeJson(400,{error:'Invalid JSON'});}
    if (!parsed || typeof parsed!=='object' || Array.isArray(parsed)) return safeJson(400,{error:'Invalid request'});
    if (endpoint==='chat') {
      const text=(parsed as {text?:unknown}).text;
      if (typeof text!=='string'||text.trim().length<1||text.length>8192) return safeJson(400,{error:'Chat text must be 1..8192 characters'});
    }
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
