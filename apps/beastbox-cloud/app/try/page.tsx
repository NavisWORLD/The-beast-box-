'use client';
import {useState,type FormEvent} from 'react';
import Link from 'next/link';
import {ArrowLeft,ArrowRight,BrainCircuit,Globe,ShieldCheck,KeyRound} from 'lucide-react';
type Provider='rawrphos-local'|'huggingface-byok';
type Reply={provider?:Provider;model?:string;step?:number;reply?:string;guest_stateless?:boolean;charged_to?:string;error?:string};
export default function TryBeastBox(){
 const [provider,setProvider]=useState<Provider>('rawrphos-local');
 const [text,setText]=useState(''),[hfKey,setHfKey]=useState(''),[model,setModel]=useState('openai/gpt-oss-20b:fastest');
 const [confirm,setConfirm]=useState(false),[busy,setBusy]=useState(false);
 const [reply,setReply]=useState<Reply|null>(null),[error,setError]=useState('');
 async function submit(e:FormEvent<HTMLFormElement>){
  e.preventDefault();if(busy||text.trim().length<1||text.length>700)return;
  if(provider==='huggingface-byok'&&(!hfKey||!confirm))return;
  const data=provider==='rawrphos-local'?{provider,text:text.trim()}:
   {provider,text:text.trim(),hf_key:hfKey,model,spend_confirmed:confirm};
  setBusy(true);setReply(null);setError('');setHfKey('');setConfirm(false);
  try{
   const response=await fetch('/api/guest',{method:'POST',cache:'no-store',credentials:'same-origin',
    headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
   const result:Reply=await response.json();
   if(!response.ok)throw new Error(typeof result.error==='string'?result.error:'Model unavailable');
   if(result.guest_stateless!==true||typeof result.reply!=='string'||!result.reply.trim())
    throw new Error('Guest response could not be confirmed');
   setReply(result);
  }catch(e){setError(e instanceof Error?e.message:'Guest inference unavailable');}
  finally{setBusy(false);}
 }
 return <main className="guest-page">
  <header className="guest-top"><Link href="/"><ArrowLeft size={17}/> Back to COSMOS</Link><span>✺ BEAST BOX · PUBLIC GUEST LAB</span><Link href="/workspace">Owner login <ArrowRight size={16}/></Link></header>
  <section className="guest-hero"><p className="eyebrow">CORY DAVIS / NAVISWORLD</p><h1>Meet the <em>Beast.</em></h1>
   <p>Try the pinned local RAWRPHØS model on Cory&apos;s backend, or connect your own Hugging Face account. This guest conversation is stateless: it does not read or write Cory&apos;s COSMOS memory or grant tools.</p>
  </section>
  <form className="guest-panel" onSubmit={e=>void submit(e)}>
   <h2>Choose your brain</h2>
   <div className="guest-options" role="group" aria-label="Guest model provider">
    <label className={provider==='rawrphos-local'?'selected':''}><input type="radio" name="guest-provider" checked={provider==='rawrphos-local'} onChange={()=>{setProvider('rawrphos-local');setReply(null);setError('');setHfKey('');setConfirm(false);}} disabled={busy}/>
     <BrainCircuit size={26}/><strong>RAWRPHØS · Local CPU</strong><small>Cory&apos;s hosted stable 14K checkpoint. Limited public trial and queue; no Hugging Face key required.</small></label>
    <label className={provider==='huggingface-byok'?'selected':''}><input type="radio" name="guest-provider" checked={provider==='huggingface-byok'} onChange={()=>{setProvider('huggingface-byok');setReply(null);setError('');setHfKey('');setConfirm(false);}} disabled={busy}/>
     <Globe size={26}/><strong>Hugging Face · Your key</strong><small>Uses your account and its quotas/billing, never Cory&apos;s HF key. The selected HF model is not RAWRPHØS.</small></label>
   </div>
   {provider==='huggingface-byok'?<div className="guest-credentials">
    <label htmlFor="guest-hf-key"><KeyRound size={15}/> Your Hugging Face API token</label>
    <input id="guest-hf-key" type="password" autoComplete="off" value={hfKey} onChange={e=>setHfKey(e.target.value)} minLength={20} maxLength={300} required disabled={busy} placeholder="hf_..." />
    <label htmlFor="guest-hf-model">Your HF Inference Providers model ID</label>
    <input id="guest-hf-model" value={model} onChange={e=>setModel(e.target.value)} maxLength={150} required disabled={busy} placeholder="namespace/model:provider" />
    <label className="guest-consent"><input type="checkbox" checked={confirm} disabled={busy} onChange={e=>setConfirm(e.target.checked)}/> I approve sending my message and key through this website to Hugging Face. My HF account may incur charges. The website does not intentionally save the token or use Cory&apos;s token for this request.</label>
    <p>Key is cleared from this form after submission. It is sent server-side to the fixed Hugging Face router; never put a key into your message. No fallback to Cory&apos;s account.</p>
   </div>:<p className="guest-note"><ShieldCheck size={17}/> Guest requests use a separate inference route, not the owner workstation. 30-day trial; bounded daily and total usage. Your prompt is sent to Cory&apos;s hosted model for inference, not saved to COSMOS memory.</p>}
   <label htmlFor="guest-input">Your message</label>
   <textarea id="guest-input" maxLength={700} rows={4} required value={text} onChange={e=>setText(e.target.value)} disabled={busy} placeholder="Say hi to the Beast..."/>
   <div className="guest-submit"><small>{text.length}/700 characters · no persistent guest chat</small>
    <button type="submit" disabled={busy||!text.trim()||(provider==='huggingface-byok'&&(!hfKey||!confirm))}>{busy?'Generating…':'Send to model'} <ArrowRight size={16}/></button>
   </div>
   {error?<p role="alert" className="guest-error">{error}</p>:null}
   {reply?<section className="guest-reply" role="status"><strong>{reply.provider==='rawrphos-local'?'RAWRPHØS · stable 14K':reply.model||'Hugging Face model'}</strong><p>{reply.reply}</p><small>Real model response · stateless guest session · answers may be wrong</small></section>:null}
  </form>
  <footer className="guest-bottom">✺ BEAST BOX COSMOS · MODEL ≠ MEMORY ≠ AUTHORITY <Link href="https://github.com/NavisWORLD/The-beast-box-" target="_blank" rel="noopener noreferrer">Open source ↗</Link></footer>
 </main>;
}
