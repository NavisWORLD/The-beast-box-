'use client';
import {useEffect,useRef,useState,type FormEvent} from 'react';
import Link from 'next/link';
import {ArrowUpRight,BrainCircuit,Cable,ChevronRight,Cpu,Sparkles} from 'lucide-react';
import {useBeastSession} from './beast-session';
import PixelBeast from './pixel-beast';
import UniverseRoomNav from './universe-room-nav';
import {useUniverseMotion} from './use-universe-motion';
import {rememberExchange} from '../lib/companion/adventure.mjs';
import {beastIdentity,shownName} from '../lib/companion/session.mjs';
import {publicBrainProvider,runPublicBrain,setPublicBrain} from '../lib/companion/public-brain-bay.mjs';
import {visualStateFromBeast} from '../lib/companion/creature-visual-state.mjs';
import styles from './brain-bay-workshop.module.css';

const names:Record<string,string>={'local-mind':'On-device pattern','guest-rawrphos':'RAWRPHØS guest','loopback-ollama':'Local Ollama'};
type Answer={reply:string;source:string;label:string;fallback:boolean;moduleReady:boolean;failure:string};

export default function BrainBayWorkshop(){
 const {ready,session,change}=useBeastSession();
 const motion=useUniverseMotion();
 const beast=session?.beast,provider=publicBrainProvider(session),name=shownName(beast);
 const [message,setMessage]=useState(''),[ollamaModel,setOllamaModel]=useState('');
 const [answer,setAnswer]=useState<Answer|null>(null),[busy,setBusy]=useState(false),[notice,setNotice]=useState('');
 const [saving,setSaving]=useState(false);
 const request=useRef<AbortController|null>(null);
 const sessionRef=useRef(session);sessionRef.current=session;
 useEffect(()=>()=>{request.current?.abort();request.current=null;},[]);
 const identity=beastIdentity(beast),visual=visualStateFromBeast(beast);
 const emote=visual==='sleeping'?'sleep':visual==='celebrating'?'happy':'watch';
 const unavailable=Boolean(answer&&!answer.moduleReady);

 async function choose(next:string){
  if(!ready||!beast||busy||saving)return;
  setAnswer(null);setNotice('');setSaving(true);
  try{
   const saved=await change(draft=>{setPublicBrain(draft,next);});
   if(saved&&!saved.ok)setNotice(saved.reason||'The brain preference could not be saved.');
  }catch{setNotice('The brain preference could not be saved.');}
  finally{setSaving(false);}
 }
 async function send(event:FormEvent<HTMLFormElement>){
  event.preventDefault();const saying=message.trim();
  if(!ready||!beast||!saying||busy||saving)return;
  const current=sessionRef.current,id=beastIdentity(current.beast),controller=new AbortController();
  request.current=controller;setBusy(true);setNotice('');setAnswer(null);
  const timeout=window.setTimeout(()=>controller.abort(),60000);
  try{
   const result=await runPublicBrain(current,saying,{ollamaModel,signal:controller.signal});
   if(request.current!==controller)return;
   if(beastIdentity(sessionRef.current?.beast)!==id){setNotice('Your selected Beast changed. Send again for the current Beast.');return;}
   if(!result.ok||!result.reply){setNotice(('reason' in result&&result.reason)||'Enter a short message.');return;}
   const recorded:Answer={reply:result.reply,source:result.source||'local-mind',label:result.label||'',fallback:result.fallback||false,moduleReady:result.moduleReady!==false,failure:result.failure||''};
   const saved=await change(draft=>{if(beastIdentity(draft.beast)===id)rememberExchange(draft,saying,recorded.reply,{learnReply:recorded.source!=='local-mind'});});
   if(saved&&!saved.ok)setNotice(saved.reason||'This answer completed, but the exchange could not be saved.');
   setAnswer(recorded);setMessage('');
  }catch{
   if(request.current===controller)setNotice('The exchange could not be saved. Try sending again.');
  }finally{
   window.clearTimeout(timeout);
   if(request.current===controller){request.current=null;setBusy(false);}
  }
 }

 return <main className={styles.room} data-reduced-motion={motion.reduced}>
  <UniverseRoomNav current="/brain-bay"/>
  <section className={styles.intro}>
   <p className={styles.eyebrow}><Cable size={14} aria-hidden="true"/> THE BRAIN WORKSHOP</p>
   <h1>Swap the brain.<br/><em>Keep the Beast.</em></h1>
   <p>One creature. One local story. Choose the socket that answers your next message.</p>
  </section>
  <div className={styles.workshop}>
   <section className={styles.creatureCard} aria-label="Your canonical Beast">
    <div className={styles.cardTop}><span>YOUR BEAST</span><span>{beast?'SAME IDENTITY':'PREVIEW'}</span></div>
    <div className={styles.stage} data-beast-state={visual} data-motion={motion.reduced?'reduced':'full'}>
     <div className={styles.orbit} aria-hidden="true"/>
     {beast?.genome?<div className={styles.pixel}><PixelBeast genome={beast.genome} publicSpark={Boolean(beast.qbeast)} stage={beast.qbeast?beast.nativeStage||1:beast.stage||1} emote={emote} reduced={motion.reduced} label={`${name}, your selected Beast`}/></div>:<div className={styles.preview}><Sparkles size={80} strokeWidth={1} aria-hidden="true"/><p>A place for your Beast</p><small>Labeled preview · no creature selected</small></div>}
     <span className={styles.stageNote}>{beast?`LOCAL STATE · ${String(visual).toUpperCase()}`:'MEET YOUR FIRST BEAST'}</span>
    </div>
    <div className={styles.identity}>
     <h2>{beast?name:'Your story starts here'}</h2>
     {beast?<><code title={identity||''}>{identity}</code><dl className={styles.metrics}><div><dt>XP</dt><dd>{beast.xp}</dd></div><div><dt>Bond</dt><dd>{beast.bond}</dd></div><div><dt>Pattern steps</dt><dd>{session.mind?.steps||0}</dd></div></dl><p>Brain selection keeps this identity, genome and local growth.</p></>:<><p>Choose a Beast in My Beast, then bring it into the workshop.</p><Link className={styles.meet} href="/spark/index.html">Meet a Beast <ChevronRight size={16} aria-hidden="true"/></Link></>}
    </div>
   </section>
   <section className={styles.socketCard} aria-labelledby="socket-title">
    <div className={styles.sectionLabel}><span>01 / CHOOSE A SOCKET</span><BrainCircuit size={21} aria-hidden="true"/></div>
    <h2 id="socket-title">A brain is a module.</h2>
    <p className={styles.description}>Choosing a socket saves your preference. A model request starts when you press Send.</p>
    <div className={styles.choices}>
     <button type="button" aria-pressed={provider==='local-mind'} disabled={!ready||!beast||busy||saving} onClick={()=>void choose('local-mind')} className={styles.choice}><Cpu size={23} aria-hidden="true"/><span><strong>On-device pattern</strong><small>Deterministic word links · available offline</small></span><b>LOCAL</b></button>
     <button type="button" aria-pressed={provider==='guest-rawrphos'} disabled={!ready||!beast||busy||saving} onClick={()=>void choose('guest-rawrphos')} className={styles.choice}><BrainCircuit size={23} aria-hidden="true"/><span><strong>RAWRPHØS guest</strong><small>Native 14K host · stateless message only</small></span><b>HOST</b></button>
    </div>
    <details className={styles.local}>
     <summary>Connect an installed local model <span>OPTIONAL</span></summary>
     <p>Ollama must already run on your computer. Your browser may block the connection or require local-network permission. Only the typed message goes to fixed loopback; no probing starts here.</p>
     <label htmlFor="ollama-model">Installed Ollama model tag</label>
     <input id="ollama-model" value={ollamaModel} onChange={event=>setOllamaModel(event.target.value)} maxLength={80} placeholder="e.g. qwen2.5:0.5b" autoComplete="off" disabled={busy}/>
     <button type="button" className={styles.localButton} aria-pressed={provider==='loopback-ollama'} disabled={!ready||!beast||busy||saving} onClick={()=>void choose('loopback-ollama')}>Select local Ollama <Cable size={15} aria-hidden="true"/></button>
    </details>
    <div className={`${styles.module} ${unavailable?styles.unavailable:''}`} data-module-status={unavailable?'unavailable':busy?'working':answer?'answered':'selected'}>
     <div className={styles.moduleIcon}><BrainCircuit size={30} aria-hidden="true"/></div>
     <div><span>SELECTED BRAIN</span><strong>{names[provider]}</strong><small>{saving?'Saving preference':unavailable?'Unavailable · pattern fallback below':busy?'Request in progress':answer?answer.source==='local-mind'?'Pattern reply completed':'Verified model reply completed':'Selected · waiting for a message'}</small></div>
     <i aria-hidden="true"/>
    </div>
    <form onSubmit={send} className={styles.form}>
     <label htmlFor="brain-message">Say something to {beast?name:'your Beast'}</label>
     <textarea id="brain-message" value={message} onChange={event=>setMessage(event.target.value)} rows={3} maxLength={400} placeholder="Try a pair of words: quiet star" disabled={!ready||!beast||busy||saving}/>
     <div className={styles.sendRow}><small>Text only · 400 characters</small><button type="submit" disabled={!ready||!beast||!message.trim()||busy||saving}>{busy?'Waiting…':'Send message'} <ArrowUpRight size={16} aria-hidden="true"/></button></div>
    </form>
   </section>
  </div>
  <section className={styles.response} aria-live="polite" aria-atomic="true" data-answer-source={answer?.source||'none'}>
   <div className={styles.sectionLabel}><span>02 / THE RESPONSE</span><Sparkles size={17} aria-hidden="true"/></div>
   {answer?<><strong className={answer.fallback?styles.fallback:styles.answerLabel}>{answer.label}</strong>{answer.failure&&<p className={styles.failure}>{answer.failure}</p>}<p className={styles.answer}>{answer.reply}</p><small>Accepted exchanges update the existing local pattern and game growth. Model weights stay unchanged. The shared chat keeps up to 400 characters per line.</small></>:<p className={styles.empty}>Your next exchange appears here, with its actual source.</p>}
   {notice&&<p role="status" className={styles.failure}>{notice}</p>}
  </section>
  <footer className={styles.footer}><p>Local story stays in this browser. Guest and Ollama receive only the message you send.</p><Link href="/workspace#brain-bay">Open owner workstation <ArrowUpRight size={14} aria-hidden="true"/></Link><Link href="/research">Read the Lab receipts <ArrowUpRight size={14} aria-hidden="true"/></Link></footer>
 </main>;
}
