/** Server-only, signed private-guest capabilities. Never accepts a browser user ID. */
import {createHmac,randomBytes,timingSafeEqual} from 'node:crypto';
export const CREDENTIAL_AGE=7*24*60*60;
export const PRIVATE_COOKIE='beastbox-private-cosmos';
export const validSubject=value=>typeof value==='string'&&/^u_[0-9a-f]{32}$/.test(value);
const time=()=>Math.floor(Date.now()/1000);
const mac=(secret,payload)=>createHmac('sha256',secret).update('beastbox-private-owner/v1\0'+payload).digest('hex');
function configured(secret){return typeof secret==='string'&&secret.length>=32;}
export function issueCredential(secret,{subject,now=time(),age=CREDENTIAL_AGE,kind='guest'}={}){
 if(!configured(secret))throw Error('Private memory signing is unconfigured.');
 const id=subject||'u_'+randomBytes(16).toString('hex');if(!validSubject(id)||!['guest','pair'].includes(kind)||!Number.isInteger(now))throw Error('Invalid private credential request.');
 const expiry=now+Math.min(CREDENTIAL_AGE,Math.max(1,Math.floor(age))),nonce=randomBytes(16).toString('hex'),payload=[kind,id,expiry,nonce].join('.');
 return {subject:id,expiry,token:payload+'.'+mac(secret,payload)};
}
export function verifyCredential(secret,token,{now=time(),kind='guest'}={}){
 if(!configured(secret)||typeof token!=='string'||token.length>240)return null;
 const parts=token.split('.');if(parts.length!==5)return null;const [type,subject,expiry,nonce,signature]=parts;
 if(type!==kind||!validSubject(subject)||!/^\d{1,12}$/.test(expiry)||!Number.isInteger(now)||!/^[0-9a-f]{32}$/.test(nonce)||!/^[0-9a-f]{64}$/.test(signature))return null;
 const age=kind==='pair'?300:CREDENTIAL_AGE;
 if(Number(expiry)<=now||Number(expiry)>now+age)return null;
 const expected=mac(secret,parts.slice(0,4).join('.'));if(!timingSafeEqual(Buffer.from(signature),Buffer.from(expected)))return null;
 return {subject,expiry:Number(expiry),nonce};
}
