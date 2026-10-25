// Per-user PRIVATE storage of the consent record + the latest derived numbers (never media). Revoke erases the record.
// `store` = {get(name)->text|null, put(name,text), del(name)}; the route supplies the Azure-backed one. userKey is the signed-in
// account id (40 hex) or 'owner'; a guest has no identity, so nothing is ever stored for a guest.
import {validateEnvironment,ENV_LABELS} from './environment-link.mjs';
export const ENV_PREFIX='environment/v1/';
export const CONSENT_SCHEMA='beastbox-environment-consent-v1';
const okKey=k=>k==='owner'||/^[a-f0-9]{40}$/.test(k||'');
const name=k=>ENV_PREFIX+k+'.json';
export async function saveEnvironment(store,userKey,raw,nowMs){
 if(!okKey(userKey))return {status:401,body:{ok:false,error:'Sign in to keep a private record. Without it, your numbers stay on this device and nothing is stored.'}};
 const v=validateEnvironment(raw);
 if(!v.ok)return {status:400,body:{ok:false,error:'Not stored: '+v.errors.slice(0,3).join('; '),stored:false}};
 const rec={schema:CONSENT_SCHEMA,consent:true,updated_at_ms:nowMs,numbers:v.numbers,labels:ENV_LABELS,raw_media_stored:false};
 await store.put(name(userKey),JSON.stringify(rec));
 return {status:200,body:{ok:true,stored:true,updated_at_ms:nowMs,raw_media_stored:false}};
}
export async function readEnvironment(store,userKey,nowMs){
 if(!okKey(userKey))return {status:401,body:{ok:false,consent:false,error:'Sign in to keep a private per-user record.'}};
 const t=await store.get(name(userKey));if(!t)return {status:200,body:{ok:true,consent:false,found:false}};
 let rec;try{rec=JSON.parse(t);}catch{return {status:200,body:{ok:true,consent:false,found:false}};}
 const v=validateEnvironment(rec&&rec.numbers?Object.fromEntries(Object.entries(rec.numbers).filter(([k])=>k!=='schema')):null);
 if(rec?.consent!==true||!v.ok)return {status:200,body:{ok:true,consent:false,found:false}};
 return {status:200,body:{ok:true,consent:true,found:true,age_s:Math.max(0,Math.round((nowMs-rec.updated_at_ms)/1000)),numbers:v.numbers,labels:ENV_LABELS}};
}
export async function revokeEnvironment(store,userKey){
 if(!okKey(userKey))return {status:401,body:{ok:false,error:'Sign in to keep a private record.'}};
 await store.del(name(userKey));
 return {status:200,body:{ok:true,consent:false,erased:true}};
}
