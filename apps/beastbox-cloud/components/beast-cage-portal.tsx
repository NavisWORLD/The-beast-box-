'use client';
import {useCallback,useEffect,useState} from 'react';
import Link from 'next/link';
import {ArrowRight,BrainCircuit,DatabaseZap,LockKeyhole,Orbit,ShieldCheck,SlidersHorizontal,Sparkles,Volume2} from 'lucide-react';
import SparkBeastCompanion from './spark-beast-companion';
import SparkBeastArena from './spark-beast-arena';
import CagePocketDimension from './cage-pocket-dimension';
import GenesisForge from './genesis-forge';
import BeastCareDeck from './beast-care-deck';
import CreatureHabitat from './creature-habitat';
import {visualStateFromBeast} from '../lib/companion/creature-visual-state.mjs';
import {useUniverseMotion} from './use-universe-motion';
import QbeastMenagerie from './qbeast-menagerie';
import {useBeastSession} from './beast-session';
import {shownName} from '../lib/companion/session.mjs';
import {useCompanion} from './companion-provider';
import {generateCreature,type BaseLook,type AmbientAction} from '../lib/creature-profile';
const LOOKS:{id:BaseLook;label:string;detail:string;accent:string}[]=[
 {id:'nebula',label:'Nebby',detail:'A curious little pocket galaxy',accent:'violet'},
 {id:'aurora',label:'Lumen',detail:'The quiet glow of cosmic dawn',accent:'cyan'},
 {id:'starlight',label:'Orion',detail:'A whimsical celestial explorer',accent:'rose'}
];
const WORLDS=[
 {name:'The Beast Cage',description:'Meet your companion and configure its appearance.',icon:Sparkles,tag:'COSMIC HABITAT',href:'/beast-cage'},
 {name:'Brain Bay',description:'Real models, deliberate selection and transparent readiness.',icon:BrainCircuit,tag:'REPLACEABLE INFERENCE',href:'/brain-bay'},
 {name:'Memory Nebula',description:'Your records remain outside the model you select.',icon:DatabaseZap,tag:'AUTHORIZED PERSISTENCE',href:'/workspace#memory-nebula'},
 {name:'Sensorium',description:'Permissioned browser sensing, not imagined perception.',icon:Volume2,tag:'LOCAL SENSORS',href:'/workspace#sensorium'},
 {name:'Synapse Observatory',description:'Recorded events and genuine state receipts.',icon:Orbit,tag:'MEASURED SOFTWARE',href:'/workspace#synapse-observatory'},
 {name:'Connector Dock',description:'Inspect supported integrations and authorization boundaries.',icon:ShieldCheck,tag:'EXPLICIT CONTROL',href:'/workspace#connector-dock'}
];
const STORAGE='beastbox-cage-appearance-v1';
export default function BeastCagePortal(){
 const [look,setLook]=useState<BaseLook>('nebula');
 const [saved,setSaved]=useState(false);
 const {reduced:prefersReduced}=useUniverseMotion();
 const [expanded,setExpanded]=useState(false);
 const [pocketReady,setPocketReady]=useState(false);
 const onPocketActive=useCallback((active:boolean)=>setPocketReady(active),[]);
 const {profile:creature,selectProfile,clearProfile}=useCompanion();
 const [ambient,setAmbient]=useState<AmbientAction>('hover');
 const {session}=useBeastSession();
 const sameSpark=!!creature&&!!session?.beast?.qbeast&&session.beast.qbeast.profile.id===creature.id;
 const creatureName=sameSpark?shownName(session.beast):creature?.name;
 useEffect(()=>{if(creature)setLook(creature.baseLook);},[creature?.id,creature?.baseLook]);
 useEffect(()=>{
  try{const item=window.localStorage.getItem(STORAGE);if(item&&LOOKS.some(x=>x.id===item)){setLook(item as BaseLook);setSaved(true);}}
  catch{/* private browsing/storage unavailable: visual preview remains usable */}
 },[]);
 function save(){
  try{window.localStorage.setItem(STORAGE,look);window.dispatchEvent(new Event('beastbox:cage-look-changed'));setSaved(true);}
  catch{setSaved(false);}
 }
 function clear(){
  try{window.localStorage.removeItem(STORAGE);window.dispatchEvent(new Event('beastbox:cage-look-changed'));}catch{/* state still resets */ }
  clearProfile();setLook('nebula');setSaved(false);
 }
 const current=LOOKS.find(x=>x.id===look)||LOOKS[0];
 return <main className="cage-universe" data-reduced-motion={prefersReduced}>
  <div className="cage-sky" aria-hidden="true"/>
  <header className="cage-topbar"><Link href="/" aria-label="Beast Box homepage" className="cage-brand"><span>✺</span><span>BEAST BOX<small>NAVISWORLD / COSMOS</small></span></Link>
   <nav aria-label="Beast Box journey">
    <Link href="/">Home</Link>
    <Link href="/spark/index.html">My Beast</Link>
    <Link href="/beast-cage" aria-current="page">Beast Cage</Link>
    <Link href="/sol-game">Lost COSMOS</Link>
    <Link href="/brain-bay">Brain Bay</Link>
    <Link href="/research">Lab</Link>
    <Link className="cage-nav-cta" href="/settings">Settings <ArrowRight size={15}/></Link>
   </nav>
  </header>
  <section className="cage-hero" id="habitat" aria-labelledby="cage-title">
   <div className="cage-headline">
    <span className="cage-eyebrow"><Sparkles size={13}/> WELCOME TO THE BEAST CAGE</span>
    <h1 id="cage-title">A small companion.<br/><em>An entire universe.</em></h1>
    <p>For dreamers, idlers, players, builders and anyone with a strange little idea: this is the place to live with your Beast. Care for it, talk to it, shape its look, then take the same identity into LOST COSMOS.</p>
    <div className="cage-hero-actions"><Link className="cage-primary" href="/beast-cage/talk">Talk to My Beast <ArrowRight size={17}/></Link><a className="cage-secondary" href="#customize">Customize</a><Link className="cage-secondary" href="/sol-game">Enter LOST COSMOS 🎮</Link></div>
    <p className="cage-quiet"><LockKeyhole size={13}/><span>One Beast stays at the center. More ways to explore: <Link href="/beast-cage/turntable">3D model</Link> · <Link href="/beast-cage/play">Adventure</Link> · <Link href="/beast-cage/guest">Game lab</Link> · <a href="/spark/index.html">Open Public Beast Generator</a> · <Link href="/workspace">Owner deck</Link>.</span></p>
   </div>
   <div className={'cage-habitat-visual'+(pocketReady?' cage-pocket-active':'')} role="group" aria-label="Circular dimensional world behind the original Spark Beast; drag or pinch to explore, or focus and use arrow keys and plus/minus to move the view" tabIndex={0}>
    <div className="cage-orbit cage-orbit-one" aria-hidden="true"/><div className="cage-orbit cage-orbit-two" aria-hidden="true"/>
    <CagePocketDimension
     seed={sameSpark?session.beast.genome?.seed||session.beast.seed:null}
     qbeastId={sameSpark?session.beast.qbeast.profile.id:null}
     stage={sameSpark?(session.beast.nativeStage||1):1}
     behaviorPosition={sameSpark?session.beast.behavior?.position||null:null}
     state={sameSpark?visualStateFromBeast(session.beast):ambient}
     reduced={prefersReduced} onActiveChange={onPocketActive}/>
    <SparkBeastArena profile={creature} fallbackLook={look}
     state={sameSpark?visualStateFromBeast(session.beast):ambient==='rest'?'sleeping':ambient==='orbit'?'celebrating':ambient==='perch'?'observing':'idle'}
     label="Active Spark Beast companion"/>
    <span className="cage-habitat-caption">✧ YOUR OWN POCKET UNIVERSE</span>
   </div>
  </section>
  {!sameSpark?<GenesisForge value={creature} onChange={next=>{selectProfile(next);setLook(next.baseLook);}}
   onAmbient={setAmbient}/>:<div className="cage-generated-status"><span>{creatureName} · same recorded genome and QBEAST</span><Link href="/sol-game">Play this Beast in LOST COSMOS 🎮</Link></div>}
  {creature?<div className="cage-generated-status" role="status">
   ✧ {creatureName} · {creature.family} · {ambient} (classical seeded visual behavior)
   <Link href="/beast-cage/guest">Take this creature to the GBA Game Lab ↗</Link>
  </div>:null}
  <CreatureHabitat />
  <BeastCareDeck />
  <QbeastMenagerie />
  <section className="cage-invariants"><span>MODEL ≠ MEMORY</span><span>MODEL ≠ IDENTITY</span><span>MODEL ≠ AUTHORITY</span></section>
  <section className="cage-customize" id="customize" aria-labelledby="customize-title">
   <div className="cage-section-heading"><span className="cage-eyebrow"><SlidersHorizontal size={13}/> A LOOK THAT FEELS LIKE YOURS</span>
    <h2 id="customize-title">Meet the first<br/><em>little constellations.</em></h2>
    <p>Customize the same Beast that roams the site, uses the shared care deck, and crosses into Lost COSMOS. Stage controls are previews; earned cartridge evolution still comes from gameplay. The public generator can draw from the expanded recorded-seed pool.</p><a className="cage-secondary" href="/spark/index.html">Generate from the public IBM seed archive ↗</a></div>
   <SparkBeastCompanion profile={creature} fallbackLook={look}
    state={sameSpark?visualStateFromBeast(session.beast):ambient==='rest'?'sleeping':ambient==='orbit'?'celebrating':ambient==='perch'?'observing':'idle'}
    controls label="Customizable Spark Beast preview"/>
   {!sameSpark?<div className="cage-look-grid">{LOOKS.map(item=><button type="button" className={'cage-look-card '+item.accent+(look===item.id?' selected':'')} key={item.id} aria-pressed={look===item.id} onClick={()=>{
    const starter=generateCreature('beastbox-starter-'+item.id,item.id);
    setLook(item.id);selectProfile(starter);setSaved(false);
   }}>
    <span className="cage-look-art" aria-hidden="true">✦</span>
    <strong>{item.label}</strong><small>{item.detail}</small><span className="cage-select-label">{look===item.id?'✓ Active family':'Choose starter'} →</span>
   </button>)}</div>:<p className="cage-quiet">This Beast’s palette and body belong to its recorded genome. Preview its forms above, or name and care for it in the shared deck.</p>}
   <div className="cage-save-panel"><p><strong>{creatureName||current.label} is ready to explore.</strong><br/>The active game profile is browser-local. Real memory, model choice and permissions remain in COSMOS.</p><div><button type="button" className="cage-primary" onClick={save}>Save visual family</button><button type="button" className="cage-secondary" onClick={clear}>Clear active Beast</button></div><span role="status" className="cage-save-status">{saved?'Visual family saved locally. The active Beast profile is also retained locally.':'Generate or choose a starter to keep one Beast across the site.'}</span></div>
  </section>
  <section className="cage-worlds" id="worlds" aria-labelledby="world-title">
   <div className="cage-section-heading"><span className="cage-eyebrow">GO DEEPER WHEN YOU WANT</span><h2 id="world-title">The machinery lives<br/><em>under the magic.</em></h2><p>Brain Bay, memory, sensors, evidence and connectors stay available for people who want the deeper system. You never need them just to enjoy your Beast.</p></div>
   <div className="cage-world-grid">{WORLDS.map(world=><Link key={world.name} href={world.href} className="cage-world-card">
    <span className="cage-world-decoration" aria-hidden="true"><world.icon size={52} strokeWidth={1.05}/></span><span className="cage-world-tag">{world.tag}</span><strong>{world.name}</strong><span>{world.description}</span><ArrowRight size={15} aria-hidden="true" className="cage-world-go"/>
   </Link>)}</div>
  </section>
  <section className="cage-continuity"><div className="cage-continuity-art" aria-hidden="true"><img src="/cosmic-creature.svg" alt=""/></div><div><span className="cage-eyebrow">THE STORY LIVES OUTSIDE THE MODEL</span><h2>Different brain.<br/><em>Your chosen continuity.</em></h2><p>In the real owner workstation, deliberate provider changes can preserve authorized external substrate memory. A visual look isn't an AI checkpoint, and preview cards do not run model inference.</p><Link href="/brain-bay" className="cage-secondary">Open Brain Bay ↗</Link></div></section>
  <footer className="cage-footer"><span>✺ BEAST BOX · CORY DAVIS / NAVISWORLD</span><span>Ambient animation ≠ model understanding</span><button onClick={()=>setExpanded(x=>!x)} type="button" aria-expanded={expanded}>{expanded?'Hide':'Show'} accessibility notes</button>
   {expanded?<p>The active companion uses the local Spark pixel renderer and recorded game-seed distributions. Reduced motion disables roaming transforms. Sound starts only after your tap. It never records sensor media or starts model inference on this public page.</p>:null}
  </footer>
 </main>;
}
