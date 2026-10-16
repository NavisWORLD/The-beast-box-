import {timingSafeEqual} from 'node:crypto';
import {normEmail,EMAIL_RE,loadAccount,saveAccount,tokenHash} from '@/lib/accounts';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export async function GET(req:Request){
 const u=new URL(req.url),email=normEmail(u.searchParams.get('e')),t=u.searchParams.get('t')||'';
 const back=(s:string)=>Response.redirect(new URL('/account?verified='+s,req.url),303);
 if(!EMAIL_RE.test(email)||!/^[a-f0-9]{48}$/.test(t))return back('invalid');
 const rec=await loadAccount(email);if(!rec)return back('invalid');
 if(rec.account.verified)return back('yes');
 const a=Buffer.from(rec.account.verify_hash||''),b=Buffer.from(tokenHash(t));
 if(a.length!==b.length||!timingSafeEqual(a,b))return back('invalid');
 const ok=await saveAccount({...rec.account,verified:true,verify_hash:null,verified_at:new Date().toISOString()},{etag:rec.etag});
 return back(ok?'yes':'retry');
}
