'use client';
import {useCallback,useEffect,useRef,useState,type FormEvent} from 'react';
import Link from 'next/link';
import CosmicCompanion3D,{type CreatureState} from './cosmic-companion-3d';
import styles from './beast-cage-talk.module.css';

type Reply={provider?:string;model?:string;step?:number;reply?:string;guest_stateless?:boolean;error?:string};
type SpeechResult={results:ArrayLike<{0:{transcript:string}}>};
type Recognition={lang:string;interimResults:boolean;onresult:((event:SpeechResult)=>void)|null;onerror:(()=>void)|null;onend:(()=>void)|null;start:()=>void;stop:()=>void};
type BrowserSpeech=Window&{SpeechRecognition?:new()=>Recognition;webkitSpeechRecognition?:new()=>Recognition};

export default function BeastCageTalk(){
 const [text,setText]=useState(''),[reply,setReply]=useState(''),[error,setError]=useState('');
 const [busy,setBusy]=useState(false),[listening,setListening]=useState(false),[speaking,setSpeaking]=useState(false);
 const [motion,setMotion]=useState(true),[hasReply,setHasReply]=useState(false);
 const speech=useRef<Recognition|null>(null),pending=useRef<AbortController|null>(null);
 const [reduced,setReduced]=useState(false);
 useEffect(()=>{const media=window.matchMedia('(prefers-reduced-motion: reduce)');const change=()=>setReduced(media.matches);change();media.addEventListener('change',change);return()=>media.removeEventListener('change',change)},[]);
 useEffect(()=>()=>{speech.current?.stop();pending.current?.abort();window.speechSynthesis?.cancel()},[]);
 const stopMic=useCallback(()=>{speech.current?.stop();speech.current=null;setListening(false)},[]);
 function listen(){
  if(listening){stopMic();return;}
  const ctor=(window as BrowserSpeech).SpeechRecognition||(window as BrowserSpeech).webkitSpeechRecognition;
  if(!ctor){setError('Speech transcription is not supported in this browser. You can type instead.');return;}
  try{
   const instance=new ctor(); instance.lang='en-US';instance.interimResults=false;
   instance.onresult=e=>{const transcript=e.results[0]?.[0]?.transcript||'';setText(t=>(t+' '+transcript).trim().slice(0,700));setListening(false)};
   instance.onerror=()=>{setError('Speech transcription failed or microphone permission was denied.');setListening(false)};
   instance.onend=()=>{setListening(false);speech.current=null};
   instance.start();speech.current=instance;setListening(true);setError('');
  }catch{setError('Microphone unavailable. Try typing.');setListening(false)}
 }
 async function send(event:FormEvent<HTMLFormElement>){
  event.preventDefault();
  if(busy||!text.trim()||text.length>700)return;
  stopMic();window.speechSynthesis?.cancel();setSpeaking(false);setReply('');setHasReply(false);setError('');setBusy(true);
  const controller=new AbortController();pending.current=controller;
  const timeout=window.setTimeout(()=>controller.abort(),65000);
  try{
   const response=await fetch('/api/guest',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',cache:'no-store',signal:controller.signal,body:JSON.stringify({provider:'rawrphos-local',text:text.trim()})});
   const result:Reply=await response.json();
   if(!response.ok)throw new Error(typeof result.error==='string'?result.error:'Guest model unavailable');
   if(result.provider!=='rawrphos-local'||result.model!=='rawrphos-native'||result.step!==14000||result.guest_stateless!==true||typeof result.reply!=='string'||!result.reply.trim())
    throw new Error('Could not verify the guest model response.');
   setReply(result.reply);setHasReply(true);setText('');
  }catch(e){setError(controller.signal.aborted?'Request cancelled or timed out. No reply was confirmed.':e instanceof Error?e.message:'Model did not confirm a reply.')}
  finally{window.clearTimeout(timeout);if(pending.current===controller)pending.current=null;setBusy(false)}
 }
 function speak(){
  if(speaking){window.speechSynthesis?.cancel();setSpeaking(false);return}
  if(!hasReply||!reply||!('speechSynthesis'in window)){setError('Read aloud is unavailable.');return}
  const utterance=new SpeechSynthesisUtterance(reply.slice(0,650));utterance.lang='en-US';
  utterance.onend=()=>setSpeaking(false);utterance.onerror=()=>setSpeaking(false);
  try{window.speechSynthesis.cancel();window.speechSynthesis.speak(utterance);setSpeaking(true)}catch{setError('Browser voice playback was unavailable.')}
 }
 const state:CreatureState=busy?'thinking':listening?'listening':speaking?'celebrating':hasReply?'observing':'idle';
 return <div className={styles.shell}>
  <section className={styles.hero} aria-labelledby="talk-title">
   <span className={styles.eyebrow}>NAVISWORLD // REAL GUEST INFERENCE</span>
   <h1 id="talk-title">Talk to the <em>little Beast.</em></h1>
   <p>An original galaxy companion representing actual app events. Your message goes to the existing guest RAWRPHØS route; this creature is the interface, not another model.</p>
  </section>
  <div className={styles.main}>
   <section className={styles.scene} aria-label="Animated cosmic companion">
    <div className={styles.orbit} aria-hidden="true"/>
    <CosmicCompanion3D state={motion&&!reduced?state:'idle'} look="nebula" className={styles.creature} label={'Galaxy creature: '+state}/>
    <div className={styles.caption}>✧ {busy?'MODEL REQUEST PENDING':listening?'LOCAL SPEECH TRANSCRIPTION':speaking?'BROWSER VOICE':hasReply?'REPLY CONFIRMED':'WAITING FOR YOUR MESSAGE'}</div>
    <button className={styles.motion} type="button" aria-pressed={motion} onClick={()=>setMotion(v=>!v)}>{motion?'Pause':'Enable'} reactive animation</button>
   </section>
   <section className={styles.panel} aria-label="Real RAWRPHØS guest chat">
    <div className={styles.tag}><span className={styles.dot}/>RAWRPHØS • LOCAL GUEST • STABLE 14K</div>
    <p className={styles.intro}>Guest mode is stateless: no access to Cory&apos;s private memories, tools or owner controls. The live model may be slow, unavailable, or produce imperfect text.</p>
    <div className={styles.response} role="status" aria-live="polite">
     {busy?<><strong>Contacting the real model…</strong><p>Waiting for a verified guest response. This is not a canned transcript.</p></>:
       hasReply?<><strong>Verified API reply • RAWRPHØS 14K</strong><p>{reply}</p><button type="button" className={styles.secondary} onClick={speak}>{speaking?'Stop voice':'▶ Read actual reply aloud'}</button></>:
       <><strong>{error?'Model status':'Your companion is ready'}</strong><p>{error||'Choose a message below, or ask your own question.'}</p></>}
    </div>
    <form onSubmit={send} className={styles.form}>
     <label htmlFor="beast-speech-input">Say something to the Beast</label>
     <textarea id="beast-speech-input" value={text} onChange={e=>setText(e.target.value)} maxLength={700} rows={3} disabled={busy} placeholder="Hey Beast, introduce yourself…" required />
     <div className={styles.actions}>
      <button className={styles.secondary} type="button" disabled={busy} aria-pressed={listening} onClick={listen}>{listening?'Stop listening':'🎙 Dictate (optional)'}</button>
      <button className={styles.primary} type="submit" disabled={busy||!text.trim()}>{busy?'Waiting…':'Send to real model ↗'}</button>
     </div>
     <small>{text.length}/700 characters. Speech transcription may use your browser&apos;s speech service. You review text before sending.</small>
    </form>
    <div className={styles.foot}><Link href="/beast-cage/guest">Visual guest + GBA download ↗</Link><Link href="/try">Other guest options ↗</Link><Link href="/workspace">Owner memory demo ↗</Link></div>
   </section>
  </div>
  <p className={styles.disclaimer}>The animation shows frontend states, not model emotions, awareness, cognition or hardware measurements. Model failures remain visible; no invented replies.</p>
 </div>
}
