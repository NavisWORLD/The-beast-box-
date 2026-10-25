// Real IBM Bio Connection. OWNER ONLY. The GitHub token lives in the server environment and never reaches the browser.
// POST: validate the numbers-only packet and dispatch the real-IBM workflow (which holds the IBM secret inside GitHub Actions).
// GET ?sha=<12 hex>: status of that run. Raw video and audio are never accepted here (the packet schema forbids them).
import {isOwner,safeJson} from '@/lib/security';
import {dispatchBio,bioStatus,BIO_LIMITS} from '@/lib/bio/dispatch.mjs';
export const runtime='nodejs';
export const dynamic='force-dynamic';
const tokenFromEnv=()=>(process.env.BEASTBOX_GITHUB_DISPATCH_TOKEN||'').trim()||undefined;
export async function POST(request:Request){
 if(!await isOwner())return safeJson(401,{ok:false,error:'Owner session required'});
 const origin=request.headers.get('origin');
 if(!origin||origin!==new URL(request.url).origin)return safeJson(403,{ok:false,error:'Same-origin owner action required'});
 if(!request.headers.get('content-type')?.toLowerCase().startsWith('application/json'))return safeJson(415,{ok:false,error:'JSON required'});
 const text=await request.text();
 if(text.length>BIO_LIMITS.max_body_bytes)return safeJson(413,{ok:false,error:'Request too large'});
 let parsed:unknown;try{parsed=JSON.parse(text);}catch{return safeJson(400,{ok:false,error:'Invalid JSON'});}
 if(!parsed||typeof parsed!=='object'||Array.isArray(parsed)||Object.keys(parsed as object).join()!=='packet')return safeJson(400,{ok:false,error:'Send only {packet}'});
 const r=await dispatchBio((parsed as {packet:unknown}).packet,{fetch,token:tokenFromEnv(),nowMs:Date.now(),sleep:ms=>new Promise(res=>setTimeout(res,ms))});
 return safeJson(r.status,r.body);
}
export async function GET(request:Request){
 if(!await isOwner())return safeJson(401,{ok:false,error:'Owner session required'});
 const sha=new URL(request.url).searchParams.get('sha')||'';
 const r=await bioStatus(sha,{fetch,token:tokenFromEnv()});
 return safeJson(r.status,r.body);
}
