import {randomBytes,createHash} from 'node:crypto';
import {cookies} from 'next/headers';
import {safeJson} from '@/lib/security';
import {EMAIL_RE,normEmail,hashPassword,checkPassword,tokenHash,loadAccount,saveAccount,newAccountSession,accountCookie,accountCookieOptions,currentAccountId,accountsConfigured,emailConfigured,sendEmail,workshopAccess,type Account} from '@/lib/accounts';
export const runtime='nodejs';
export const dynamic='force-dynamic';
const hits=new Map<string,number[]>();
function limited(req:Request,max=8){const ip=(req.headers.get('x-forwarded-for')||'').split(',')[0].trim();const k=createHash('sha256').update('acct:'+ip).digest('hex');const now=Date.now(),r=(hits.get(k)||[]).filter(t=>now-t<3_600_000);if(r.length>=max)return true;r.push(now);hits.set(k,r);if(hits.size>5000)hits.clear();return false;}
function missing(){const c=accountsConfigured();return [...(!c.storage?['AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_CONTAINER_SAS_URL']:[]),...(!c.signing?['BEASTBOX_CLOUD_AUTH_SECRET (32+ chars)']:[])];}
export async function GET(){
 const id=await currentAccountId(),ws=await workshopAccess();
 return safeJson(200,{signedIn:!!id,workshop:ws.allowed,workshopReason:ws.reason,accountsReady:missing().length===0,emailReady:emailConfigured(),missing:[...missing(),...(emailConfigured()?[]:['RESEND_API_KEY','BEASTBOX_EMAIL_FROM'])]});
}
export async function POST(req:Request){
 if(req.headers.get('origin')!==new URL(req.url).origin)return safeJson(403,{error:'Same-origin request required'});
 const raw=await req.text();if(raw.length>2048)return safeJson(413,{error:'Too large'});
 let b:Record<string,unknown>;try{b=JSON.parse(raw);if(!b||typeof b!=='object')throw 0;}catch{return safeJson(400,{error:'Invalid JSON'});}
 const action=b.action;
 if(action==='signout'){(await cookies()).set(accountCookie(),'',{...accountCookieOptions(),maxAge:0});return safeJson(200,{signedIn:false});}
 if(missing().length)return safeJson(503,{error:'Accounts are not set up on this server yet. Guest mode still works.'});
 const email=normEmail(b.email),pw=typeof b.password==='string'?b.password:'';
 if(!EMAIL_RE.test(email))return safeJson(400,{error:'Enter a valid email.'});
 if(pw.length<8||pw.length>200)return safeJson(400,{error:'Password must be 8–200 characters.'});
 if(limited(req))return safeJson(429,{error:'Too many tries. Please wait a bit.'});
 if(action==='signup'){
  const token=randomBytes(24).toString('hex'),{salt,hash}=hashPassword(pw);
  const a:Account={schema:'beastbox-account-v1',email,salt,hash,verified:false,verify_hash:tokenHash(token),created_at:new Date().toISOString(),verified_at:null};
  if(!(await saveAccount(a,{create:true})))return safeJson(409,{error:'That email may already have an account. Try signing in.'});
  const link=new URL('/api/account/verify?e='+encodeURIComponent(email)+'&t='+token,req.url).toString();
  const mail=await sendEmail(email,'Welcome to Beast Box — verify your email',`Welcome to Beast Box!\n\nTap to verify your email:\n${link}\n\nYou can keep playing as a guest anytime. Workshop access is granted by Cory on request.\n\nIf you didn't sign up, ignore this email.`);
  (await cookies()).set(accountCookie(),newAccountSession(email),accountCookieOptions());
  return safeJson(201,{signedIn:true,verified:false,emailSent:mail.sent,emailStatus:mail.reason});
 }
 if(action==='signin'){
  const rec=await loadAccount(email);
  if(!rec||!checkPassword(pw,rec.account))return safeJson(401,{error:'Email or password is wrong.'});
  (await cookies()).set(accountCookie(),newAccountSession(email),accountCookieOptions());
  return safeJson(200,{signedIn:true,verified:rec.account.verified});
 }
 return safeJson(400,{error:'Unknown action'});
}
