'use client';
import Link from 'next/link';
import {ArrowUpRight,BrainCircuit,Cable,ChevronRight,Sparkles} from 'lucide-react';
import {useBeastSession} from './beast-session';
import PixelBeast from './pixel-beast';
import UniverseRoomNav from './universe-room-nav';
import {useUniverseMotion} from './use-universe-motion';
import {beastIdentity,shownName} from '../lib/companion/session.mjs';
import BeastTalkPanel from './beast-talk-panel';
import {visualStateFromBeast} from '../lib/companion/creature-visual-state.mjs';
import styles from './brain-bay-workshop.module.css';


export default function BrainBayWorkshop(){
 const {session}=useBeastSession();
 const motion=useUniverseMotion();
 const beast=session?.beast,name=shownName(beast);
 const identity=beastIdentity(beast),visual=visualStateFromBeast(beast);
 const emote=visual==='sleeping'?'sleep':visual==='celebrating'?'happy':'watch';

 return <main className={styles.room} data-reduced-motion={motion.reduced}>
  <UniverseRoomNav current="/brain-bay"/>
  <section className={styles.intro}>
   <p className={styles.eyebrow}><Cable size={14} aria-hidden="true"/> THE BRAIN WORKSHOP</p>
   <h1>Swap the brain.<br/><em>Keep the Beast.</em></h1>
   <p>One creature. One story. Pick the model that gives your Beast its voice, see exactly which one is connected, and talk to it right here.</p>
  </section>
  <div className={styles.workshop}>
   <section className={styles.creatureCard} aria-label="Your canonical Beast">
    <div className={styles.cardTop}><span>YOUR BEAST</span><span>{beast?'SAME IDENTITY':'PREVIEW'}</span></div>
    <div className={styles.stage} data-beast-state={visual} data-motion={motion.reduced?'reduced':'full'}>
     <div className={styles.orbit} aria-hidden="true"/>
     {beast?.genome?<div className={styles.pixel}><PixelBeast genome={beast.genome} publicSpark={Boolean(beast.qbeast)} stage={beast.qbeast?beast.nativeStage||1:beast.stage||1} emote={emote} reduced={motion.reduced} label={`${name}, your selected Beast`}/></div>:<div className={styles.preview}><Sparkles size={80} strokeWidth={1} aria-hidden="true"/><p>A place for your Beast</p><small>Zeref is answering until you meet your own Beast</small></div>}
     <span className={styles.stageNote}>{beast?`LOCAL STATE · ${String(visual).toUpperCase()}`:'MEET YOUR FIRST BEAST'}</span>
    </div>
    <div className={styles.identity}>
     <h2>{beast?name:'Your story starts here'}</h2>
     {beast?<><code title={identity||''}>{identity}</code><dl className={styles.metrics}><div><dt>XP</dt><dd>{beast.xp}</dd></div><div><dt>Bond</dt><dd>{beast.bond}</dd></div><div><dt>Pattern steps</dt><dd>{session.mind?.steps||0}</dd></div></dl><p>Changing the brain keeps this identity, genome and growth. Verified replies add to its chat and bond.</p></>:<><p>Choose a Beast in My Beast, then bring it into the workshop.</p><a className={styles.meet} href="/spark/index.html">Meet a Beast <ChevronRight size={16} aria-hidden="true"/></a></>}
    </div>
   </section>
   <div className={styles.talkColumn}>
    <div className={styles.sectionLabel}><span>CHOOSE A BRAIN · TALK</span><BrainCircuit size={21} aria-hidden="true"/></div>
    <BeastTalkPanel title={beast?`Talk to ${name}`:undefined}/>
   </div>
  </div>
  <footer className={styles.footer}><p>Your Beast&apos;s story stays in this browser. A model only receives the message you send, framed by your Beast&apos;s name and personality.</p><Link href="/beast-cage/talk">Full Talk to Beast room <ArrowUpRight size={14} aria-hidden="true"/></Link><Link href="/workspace#brain-bay">Open owner workstation <ArrowUpRight size={14} aria-hidden="true"/></Link><Link href="/research">Read the Lab receipts <ArrowUpRight size={14} aria-hidden="true"/></Link></footer>
 </main>;
}
