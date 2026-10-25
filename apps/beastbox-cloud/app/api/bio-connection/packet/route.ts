// Owner-only: keep the numbers-only bio packet in the owner's PRIVATE storage so the real-IBM run can be started from the box.
// POST {packet}: strict re-validation + hash check, then store. GET: numbers-only status of the latest saved packet. No raw media, ever.
import {isOwner,safeJson} from '@/lib/security';
import * as blob from '@/lib/cosmos/azure-blob.mjs';
import {savePacket,latestStatus} from '@/lib/bio/packet-store.mjs';
import {BIO_LIMITS} from '@/lib/bio/dispatch.mjs';
export const runtime='nodejs';
export const dynamic='force-dynamic';
function store(){
 const cfg=blob.storageConfig();if(!cfg)return null;
 return {put:(name:string,text:string)=>blob.putBlob(cfg,name,text),get:async(name:string)=>(await blob.getBlob(cfg,name))?.text??null};
}
export async function POST(request:Request){
 if(!await isOwner())return safeJson(401,{ok:false,error:'Owner session required'});
 const origin=request.headers.get('origin');
 if(!origin||origin!==new URL(request.url).origin)return safeJson(403,{ok:false,error:'Same-origin owner action required'});
 if(!request.headers.get('content-type')?.toLowerCase().startsWith('application/json'))return safeJson(415,{ok:false,error:'JSON required'});
 const text=await request.text();
 if(text.length>BIO_LIMITS.max_body_bytes)return safeJson(413,{ok:false,error:'Request too large'});
 let parsed:unknown;try{parsed=JSON.parse(text);}catch{return safeJson(400,{ok:false,error:'Invalid JSON'});}
 if(!parsed||typeof parsed!=='object'||Array.isArray(parsed)||Object.keys(parsed as object).join()!=='packet')return safeJson(400,{ok:false,error:'Send only {packet}'});
 const s=store();if(!s)return safeJson(503,{ok:false,error:'Owner storage is not configured on this site.'});
 try{const r=await savePacket(s,(parsed as {packet:unknown}).packet,Date.now());return safeJson(r.status,r.body);}
 catch(e){return safeJson(502,{ok:false,error:'Owner storage error: '+String((e as Error)?.message||'unknown').replace(/https?:\/\/\S+/g,'[url]').slice(0,120)});}
}
export async function GET(){
 if(!await isOwner())return safeJson(401,{ok:false,error:'Owner session required'});
 const s=store();if(!s)return safeJson(503,{ok:false,error:'Owner storage is not configured on this site.'});
 try{const r=await latestStatus(s,Date.now());return safeJson(r.status,r.body);}
 catch{return safeJson(502,{ok:false,error:'Owner storage error'});}
}
