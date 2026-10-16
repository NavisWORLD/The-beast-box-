// Visitor accounts (Cory, 2026-10-16): email sign-up with verification email,
// guest mode untouched, Workshop access only for owner or allowlisted accounts.
// Accounts are stored in the existing Azure container; passwords are scrypt-hashed.
import {createHash,createHmac,randomBytes,scryptSync,timingSafeEqual} from 'node:crypto';
import {cookies} from 'next/headers';
import {storageConfig,getBlob,putBlob} from '@/lib/cosmos/azure-blob.mjs';
import {isOwner} from '@/lib/security';
const COOKIE='beastbox-account',AGE=60*60*24*30,PREFIX='accounts/v1/';
export const EMAIL_RE=/^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,180}\.[A-Za-z]{2,24}$/;
export type Account={schema:'beastbox-account-v1';email:string;salt:string;hash:string;verified:boolean;verify_hash:string|null;created_at:string;verified_at:string|null};
export const normEmail=(v:unknown)=>typeof v==='string'?v.trim().toLowerCase().slice(0,254):'';
export const emailId=(email:string)=>createHash('sha256').update('acct:'+email).digest('hex').slice(0,40);
const secret=()=>{const s=process.env.BEASTBOX_CLOUD_AUTH_SECRET||'';return s.length>=32?s:'';};
export function accountsConfigured(){return {storage:!!storageConfig(),signing:!!secret()};}
export function emailConfigured(){return !!(process.env.RESEND_API_KEY&&process.env.BEASTBOX_EMAIL_FROM);}
export function hashPassword(pw:string,salt=randomBytes(16).toString('hex')){return {salt,hash:scryptSync(pw,salt,32).toString('hex')};}
export function checkPassword(pw:string,a:Pick<Account,'salt'|'hash'>){const h=scryptSync(pw,a.salt,32);const want=Buffer.from(a.hash,'hex');return want.length===h.length&&timingSafeEqual(h,want);}
export const tokenHash=(t:string)=>createHash('sha256').update('verify:'+t).digest('hex');
export async function loadAccount(email:string){const cfg=storageConfig();if(!cfg)return null;const b=await getBlob(cfg,PREFIX+emailId(email)+'.json').catch(()=>null);if(!b)return null;try{return {account:JSON.parse(b.text) as Account,etag:b.etag as string|undefined};}catch{return null;}}
export async function saveAccount(a:Account,{create=false,etag}:{create?:boolean;etag?:string}={}){const cfg=storageConfig();if(!cfg)return false;return !!(await putBlob(cfg,PREFIX+emailId(a.email)+'.json',JSON.stringify(a),create?{ifNoneMatch:'*'}:etag?{ifMatch:etag}:{}).catch(()=>null));}
function sign(p:string){return createHmac('sha256',secret()).update('acct-session:'+p).digest('hex');}
export function newAccountSession(email:string){const p=emailId(email)+'.'+(Math.floor(Date.now()/1000)+AGE);return p+'.'+sign(p);}
export function readAccountSession(token:string|undefined){
 if(!secret()||!token||token.length>200)return null;
 const [id,exp,mac,extra]=token.split('.');
 if(extra||!/^[a-f0-9]{40}$/.test(id||'')||!/^\d{10}$/.test(exp||'')||!/^[a-f0-9]{64}$/.test(mac||''))return null;
 if(Number(exp)<Date.now()/1000)return null;
 const want=Buffer.from(sign(id+'.'+exp)),got=Buffer.from(mac);
 return want.length===got.length&&timingSafeEqual(want,got)?id:null;
}
export const accountCookie=()=>COOKIE;
export const accountCookieOptions=()=>({httpOnly:true,secure:process.env.NODE_ENV==='production',sameSite:'lax' as const,path:'/',maxAge:AGE});
export async function currentAccountId(){return readAccountSession((await cookies()).get(COOKIE)?.value);}
/** Allowlist entries are emails (comma/space separated) in BEASTBOX_WORKSHOP_ALLOWLIST. Names only are ever reported. */
export function workshopAllowlist(){return (process.env.BEASTBOX_WORKSHOP_ALLOWLIST||'').split(/[\s,;]+/).map(normEmail).filter(e=>EMAIL_RE.test(e));}
export async function workshopAccess(){
 if(await isOwner())return {allowed:true,reason:'owner'};
 const id=await currentAccountId();if(!id)return {allowed:false,reason:'guest'};
 const email=workshopAllowlist().find(e=>emailId(e)===id);if(!email)return {allowed:false,reason:'not-granted'};
 const rec=await loadAccount(email);return rec?.account.verified?{allowed:true,reason:'allowlist'}:{allowed:false,reason:'unverified'};
}
/** Sends via Resend only when RESEND_API_KEY and BEASTBOX_EMAIL_FROM are configured. */
export async function sendEmail(to:string,subject:string,text:string){
 if(!emailConfigured())return {sent:false,reason:'email-not-configured'};
 try{const r=await fetch('https://api.resend.com/emails',{method:'POST',headers:{Authorization:'Bearer '+process.env.RESEND_API_KEY,'Content-Type':'application/json'},body:JSON.stringify({from:process.env.BEASTBOX_EMAIL_FROM,to:[to],subject,text}),signal:AbortSignal.timeout(10000)});return {sent:r.ok,reason:r.ok?'sent':'provider-error-'+r.status};}
 catch{return {sent:false,reason:'provider-unreachable'};}
}
