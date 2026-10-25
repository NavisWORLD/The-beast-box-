import {isOwner,safeJson} from '@/lib/security';
import * as blob from '@/lib/cosmos/azure-blob.mjs';
import {azureAdapter} from '@/lib/library/store.mjs';

/** Owner-only guard shared by every library route. Visitors never reach storage. */
export async function ownerGuard(request:Request,{write=false}:{write?:boolean}={}):Promise<Response|null>{
 if(!await isOwner())return safeJson(401,{error:'Owner session required. The library is private to the owner.'});
 if(write){
  const origin=request.headers.get('origin');
  if(origin!==new URL(request.url).origin)return safeJson(403,{error:'Same-origin request required'});
  if(!request.headers.get('content-type')?.toLowerCase().startsWith('application/json'))return safeJson(415,{error:'JSON required'});
  if(Number(request.headers.get('content-length')||0)>2_000_000)return safeJson(413,{error:'Request too large'});
 }
 return null;
}

/** null when the site has no Azure storage configured (no new paid service is added). */
export function libraryStore(){
 const cfg=blob.storageConfig();
 return cfg?azureAdapter(cfg,blob):null;
}

export function errorResponse(e:any){
 const status=Number.isInteger(e?.status)&&e.status>=400&&e.status<600?e.status:500;
 if(e?.publicMessage)return safeJson(status,{error:e.publicMessage});
 // Never echo storage URLs, SAS tokens or provider bodies.
 return safeJson(status===500?502:status,{error:'Library storage error: '+String(e?.message||'unknown').replace(/https?:\/\/\S+/g,'[url]').slice(0,120)});
}

export async function readJson(request:Request):Promise<Record<string,unknown>|null>{
 try{const raw=await request.text();if(raw.length>2_000_000)return null;const v=JSON.parse(raw);return v&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:null;}catch{return null;}
}
