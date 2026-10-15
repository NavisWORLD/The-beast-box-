'use client';
import {useCallback,useEffect,useState} from 'react';
import Link from 'next/link';
import CosmicCompanion3D,{type CreatureState} from './cosmic-companion-3d';
import BeastCareDeck from './beast-care-deck';
import SparkWanderer from './spark-wanderer';
import BeastTalkPanel,{type TalkState} from './beast-talk-panel';
import ZerefMoonwraith from './zeref-moonwraith';
import ZerefSprite3D from './zeref-sprite-3d';
import {useCompanion} from './companion-provider';
import {MOONWRAITH_DISPLAY_ID,SAVED_ZEREF_ID} from '../lib/creature-dimensional.mjs';
import {useBeastSession} from './beast-session';
import styles from './beast-cage-talk.module.css';

const CREATURE:Record<TalkState,CreatureState>={idle:'idle',thinking:'thinking',listening:'listening',speaking:'celebrating',replied:'observing',offline:'idle'};
const CAPTION:Record<TalkState,string>={idle:'WAITING FOR YOUR MESSAGE',thinking:'MODEL REQUEST PENDING',listening:'LISTENING',speaking:'READING THE REPLY ALOUD',replied:'REPLY VERIFIED',offline:'MODEL OFFLINE · NO REPLY INVENTED'};

/** Talk to Beast page: the animated habitat reacts to the real request state of the shared talk panel. */
export default function BeastCageTalk(){
 const {profile}=useCompanion();
 const {session}=useBeastSession();
 const zeref=!session?.beast&&!profile;
 const savedId=session?.beast?.qbeast?.profile?.id||'';
 const canSolid=zeref||savedId===SAVED_ZEREF_ID||savedId===MOONWRAITH_DISPLAY_ID;
 const [solid,setSolid]=useState(false);
 const dimensionalId=solid?(zeref?MOONWRAITH_DISPLAY_ID:savedId===SAVED_ZEREF_ID?SAVED_ZEREF_ID:savedId===MOONWRAITH_DISPLAY_ID?MOONWRAITH_DISPLAY_ID:null):null;
 const [talk,setTalk]=useState<TalkState>('idle'),[greet,setGreet]=useState(0);
 useEffect(()=>{if(talk==='replied')setGreet(g=>g+1);},[talk]);
 const [motion,setMotion]=useState(true),[reduced,setReduced]=useState(false);
 useEffect(()=>{const media=window.matchMedia('(prefers-reduced-motion: reduce)');const change=()=>setReduced(media.matches);change();media.addEventListener('change',change);return()=>media.removeEventListener('change',change)},[]);
 const onState=useCallback((next:TalkState)=>setTalk(next),[]);
 return <div className={styles.shell}>
  <section className={styles.hero} aria-labelledby="talk-title">
   <span className={styles.eyebrow}>BEAST BOX // REAL MODEL CONVERSATION</span>
   <h1 id="talk-title">Talk to <em>your Beast.</em></h1>
   <p>Your Beast keeps its own name, personality and memories. Pick a brain to give it a voice: the free RAWRPHØS guest model, a model on your own computer, or your own key. Every reply comes from that model, and if it is offline you will see that instead of a made-up answer.</p>
  </section>
  <div className={styles.main}>
   <section className={styles.scene} aria-label="Animated cosmic companion">
    <div className={styles.orbit} aria-hidden="true"/>
    {zeref&&solid?<div className={styles.zeref}><ZerefSprite3D greet={greet}/></div>:zeref&&!solid?<div className={styles.zeref}><ZerefMoonwraith greet={greet} showCaption={false}/></div>:
     <CosmicCompanion3D state={motion&&!reduced?CREATURE[talk]:'idle'} speaking={talk==='speaking'} look="nebula" profile={dimensionalId?null:profile} dimensionalId={dimensionalId} preferSprite={!dimensionalId&&Boolean(session?.beast?.genome?.seed)} spriteGenome={session?.beast?.genome?.seed?session.beast.genome:null} spriteStage={session?.beast?.nativeStage||session?.beast?.stage||1} className={styles.creature} label={(dimensionalId?'Artistic 3D '+dimensionalId+' · ':'Your creature: ')+CREATURE[talk]}/>}
    <div className={styles.caption}>✧ {CAPTION[talk]}</div>
    <button className={styles.motion} type="button" aria-pressed={motion} onClick={()=>setMotion(v=>!v)}>{motion?'Pause':'Enable'} reactive animation</button>
    {canSolid?<button className={styles.motion+" "+styles.formToggle} type="button" aria-pressed={solid} onClick={()=>setSolid(v=>!v)}>{solid?'Flat art':'3D form'}</button>:null}
   </section>
   <div className={styles.panel}>
    <div className={styles.yard}><SparkWanderer profile={profile} pulse={talk==='replied'?'reply':''} thinking={talk==='thinking'}/></div>
    <BeastTalkPanel onState={onState}/>
    <div className={styles.foot}><Link href="/beast-cage/go">Lost Cosmos field ↗</Link><Link href="/brain-bay">Brain Bay ↗</Link><Link href="/beast-cage">Beast Cage ↗</Link><Link href="/sol-game">Lost COSMOS ↗</Link><Link href="/try">Other guest options ↗</Link></div>
   </div>
  </div>
  <BeastCareDeck />
  <p className={styles.disclaimer}>The animation shows what the page is doing (waiting, thinking, replied), not model emotions or awareness. The Beast is a game companion; the model is the voice it borrows.</p>
 </div>
}
