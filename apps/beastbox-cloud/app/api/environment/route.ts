// Consent-based environment numbers (light, sound level, motion, heartbeat numbers) for the signed-in user's OWN pocket universe.
// Per user (account id or owner), private storage, numbers only. POST stores, GET reads own record, DELETE revokes and erases.
// A guest has no identity: 401 with a plain message (the page still uses the numbers on-device, nothing is stored).
import {isOwner,safeJson} from '@/lib/security';
import {currentAccountId} from '@/lib/accounts';
import * as blob from '@/lib/cosmos/azure-blob.mjs';
import {saveEnvironment,readEnvironment,revokeEnvironment} from '@/lib/environment/consent-store.mjs';
export const runtime='nodejs';
export const dynamic='force-dynamic';
const MAX_BODY=2000;
async function who(){return (await isOwner())?'owner':(await currentAccountId())||'';}
function store(){
 const cfg=blob.storageConfig();if(!cfg)return null;
 return {get:async(n:string)=>(await blob.getBlob(cfg,n))?.text??null,put:(n:string,t:string)=>blob.putBlob(cfg,n,t),
  del:async(n:string)=>{const b=await blob.getBlob(cfg,n);if(b?.etag)await blob.deleteBlob(cfg,n,{ifMatch:b.etag});}};
}
const fail=(e:unknown)=>safeJson(502,{ok:false,error:'Storage error: '+String((e as Error)?.message||'unknown').replace(/https?:\/\/\S+/g,'[url]').slice(0,100)});
function sameOrigin(request:Request){const o=request.headers.get('origin');return !!o&&o===new URL(request.url).origin;}
export async function POST(request:Request){
 if(!sameOrigin(request))return safeJson(403,{ok:false,error:'Same-origin request required'});
 if(!request.headers.get('content-type')?.toLowerCase().startsWith('application/json'))return safeJson(415,{ok:false,error:'JSON required'});
 const text=await request.text();if(text.length>MAX_BODY)return safeJson(413,{ok:false,error:'Request too large'});
 let parsed:unknown;try{parsed=JSON.parse(text);}catch{return safeJson(400,{ok:false,error:'Invalid JSON'});}
 const user=await who();if(!user)return safeJson(401,{ok:false,error:'Sign in to keep a private record. Without it, your numbers stay on this device and nothing is stored.'});
 const s=store();if(!s)return safeJson(503,{ok:false,error:'Private storage is not configured on this site.'});
 try{const r=await saveEnvironment(s,user,parsed,Date.now());return safeJson(r.status,r.body);}catch(e){return fail(e);}
}
export async function GET(){
 const user=await who();if(!user)return safeJson(401,{ok:false,consent:false,error:'Sign in to keep a private per-user record.'});
 const s=store();if(!s)return safeJson(503,{ok:false,error:'Private storage is not configured on this site.'});
 try{const r=await readEnvironment(s,user,Date.now());return safeJson(r.status,r.body);}catch(e){return fail(e);}
}
export async function DELETE(request:Request){
 if(!sameOrigin(request))return safeJson(403,{ok:false,error:'Same-origin request required'});
 const user=await who();if(!user)return safeJson(401,{ok:false,error:'Sign in to keep a private record.'});
 const s=store();if(!s)return safeJson(503,{ok:false,error:'Private storage is not configured on this site.'});
 try{const r=await revokeEnvironment(s,user);return safeJson(r.status,r.body);}catch(e){return fail(e);}
}
