'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
type Me={signedIn:boolean;workshop:boolean;workshopReason:string;accountsReady:boolean;emailReady:boolean};
export default function AccountPanel({verified}:{verified?:string}){
 const [me,setMe]=useState<Me|null>(null),[email,setEmail]=useState(''),[pw,setPw]=useState(''),[msg,setMsg]=useState(''),[busy,setBusy]=useState(false);
 const load=()=>fetch('/api/account',{cache:'no-store'}).then(r=>r.json()).then(setMe).catch(()=>setMe(null));
 useEffect(()=>{void load();},[]);
 async function go(action:'signup'|'signin'|'signout'){
  setBusy(true);setMsg('');
  try{const r=await fetch('/api/account',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,email,password:pw})});const j=await r.json().catch(()=>({}));
   if(!r.ok)setMsg(j.error||'Something went wrong.');
   else if(action==='signup')setMsg(j.emailSent?'Account made! Check your email to verify it.':'Account made! Verification email could not be sent yet; you can still play.');
   else if(action==='signin')setMsg(j.verified?'Signed in.':'Signed in. Please verify your email from the link we sent.');
   else setMsg('Signed out. Guest mode is always available.');
   setPw('');await load();
  }finally{setBusy(false);}
 }
 return <main data-account-page className="login-screen"><div className="login-stars" aria-hidden="true"/><Link href="/" className="back-home">← BACK TO THE COSMOS</Link><section className="login-card" style={{display:'grid',gap:12}}>
  <span className="eyebrow">BEAST BOX / ACCOUNT</span>
  <h1>Your Beast Box <em>account</em></h1>
  {verified==='yes'?<p data-verified>Email verified 💚</p>:verified?<p>That verification link didn&apos;t work. Try signing in again.</p>:null}
  <p>An account is optional. <Link href="/">Continue as a guest</Link> to experience everything except the Workshop.</p>
  {me?.signedIn?<>
   <p data-signed-in>You&apos;re signed in.{me.workshop?' You have Workshop access.':' Workshop access is granted by Cory — message him to ask.'}</p>
   <button disabled={busy} onClick={()=>go('signout')}>Sign out</button>
  </>:<form onSubmit={e=>{e.preventDefault();void go('signup');}} style={{display:'grid',gap:10}}>
   <label>EMAIL<input type="email" required autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)}/></label>
   <label>PASSWORD<input type="password" required minLength={8} autoComplete="new-password" value={pw} onChange={e=>setPw(e.target.value)}/></label>
   <button type="submit" disabled={busy}>Create account</button>
   <button type="button" className="outline-action" disabled={busy} onClick={()=>go('signin')}>Sign in</button>
  </form>}
  {me&&!me.accountsReady?<small>Accounts are still being set up. Guest mode works now.</small>:null}
  {msg?<p role="status">{msg}</p>:null}
 </section></main>;
}
