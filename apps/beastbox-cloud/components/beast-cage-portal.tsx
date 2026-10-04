'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {ArrowRight,BrainCircuit,DatabaseZap,LockKeyhole,Orbit,ShieldCheck,SlidersHorizontal,Sparkles,Volume2} from 'lucide-react';
import SparkBeastCompanion from './spark-beast-companion';
import GenesisForge from './genesis-forge';
import BeastCareDeck from './beast-care-deck';
import {useCompanion} from './companion-provider';
import {generateCreature,type BaseLook,type AmbientAction} from '../lib/creature-profile';
const LOOKS:{id:BaseLook;label:string;detail:string;accent:string}[]=[
 {id:'nebula',label:'Nebula',detail:'Purple cosmic glow',accent:'violet'},
 {id:'aurora',label:'Aurora',detail:'Cool cyan starlight',accent:'cyan'},
 {id:'starlight',label:'Starlight',detail:'Warm celestial shimmer',accent:'rose'}
];
const WORLDS=[
 {name:'The Beast Cage',description:'Meet your companion and configure its appearance.',icon:Sparkles,tag:'COSMIC HABITAT',href:'/beast-cage'},
 {name:'Brain Bay',description:'Real models, deliberate selection and transparent readiness.',icon:BrainCircuit,tag:'REPLACEABLE INFERENCE',href:'/workspace#brain-bay'},
 {name:'Memory Nebula',description:'Your records remain outside the model you select.',icon:DatabaseZap,tag:'AUTHORIZED PERSISTENCE',href:'/workspace#memory-nebula'},
 {name:'Sensorium',description:'Permissioned browser sensing, not imagined perception.',icon:Volume2,tag:'LOCAL SENSORS',href:'/workspace#sensorium'},
 {name:'Synapse Observatory',description:'Recorded events and genuine state receipts.',icon:Orbit,tag:'MEASURED SOFTWARE',href:'/workspace#synapse-observatory'},
 {name:'Connector Dock',description:'Inspect supported integrations and authorization boundaries.',icon:ShieldCheck,tag:'EXPLICIT CONTROL',href:'/workspace#connector-dock'}
];
const STORAGE='beastbox-cage-appearance-v1';
export default function BeastCagePortal(){
 const [look,setLook]=useState<BaseLook>('nebula');
 const [saved,setSaved]=useState(false),[prefersReduced,setPrefersReduced]=useState(false);
 const [expanded,setExpanded]=useState(false);
 const {profile:creature,selectProfile,clearProfile}=useCompanion();
 const [ambient,setAmbient]=useState<AmbientAction>('hover');
 useEffect(()=>{if(creature)setLook(creature.baseLook);},[creature?.id,creature?.baseLook]);
 useEffect(()=>{
  const media=window.matchMedia('(prefers-reduced-motion: reduce)');
  const onChange=()=>setPrefersReduced(media.matches);
  onChange();media.addEventListener('change',onChange);
  try{const item=window.localStorage.getItem(STORAGE);if(item&&LOOKS.some(x=>x.id===item)){setLook(item as BaseLook);setSaved(true);}}
  catch{/* private browsing/storage unavailable: visual preview remains usable */}
  return()=>media.removeEventListener('change',onChange);
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
   <nav aria-label="Beast Cage navigation"><a href="#habitat">Meet</a><Link href="/beast-cage/go">Play</Link><Link href="/beast-cage/talk">Talk</Link><a href="#customize">Look</a><Link className="cage-nav-cta" href="/workspace">Owner <ArrowRight size={15}/></Link></nav>
  </header>
  <section className="cage-hero" id="habitat" aria-labelledby="cage-title">
   <div className="cage-headline">
    <span className="cage-eyebrow"><Sparkles size={13}/> WELCOME TO THE BEAST CAGE</span>
    <h1 id="cage-title">A small companion.<br/><em>An entire universe.</em></h1>
    <p>Pick one Beast and keep the same name, look, care state and game identity everywhere.</p>
    <div className="cage-hero-actions"><Link className="cage-primary" href="/beast-cage/go">Play Lost COSMOS <ArrowRight size={17}/></Link><Link className="cage-secondary" href="/beast-cage/talk">Talk</Link><a className="cage-secondary" href="#customize">Change its look</a></div>
    <p className="cage-quiet"><LockKeyhole size={13}/> One browser-local game profile drives the visible Beast. Model choice, COSMOS memory and authority stay separate.</p>
   </div>
   <div className="cage-habitat-visual" role="img" aria-label="Original cosmic observatory with a floating galaxy companion">
    <div className="cage-orbit cage-orbit-one" aria-hidden="true"/><div className="cage-orbit cage-orbit-two" aria-hidden="true"/>
    <SparkBeastCompanion profile={creature} fallbackLook={look}
     state={ambient==='rest'?'sleeping':ambient==='orbit'?'celebrating':ambient==='perch'?'observing':'idle'}
     label="Active Spark Beast companion"/>
    <span className="cage-habitat-caption">✧ YOUR OWN POCKET UNIVERSE</span>
   </div>
  </section>
  <GenesisForge value={creature} onChange={next=>{selectProfile(next);setLook(next.baseLook);}}
   onAmbient={setAmbient}/>
  {creature?<div className="cage-generated-status" role="status">
   ✧ {creature.name} · {creature.family} · {ambient} (classical seeded visual behavior)
   <Link href="/beast-cage/guest">Play with this Beast in Lost COSMOS →</Link>
  </div>:null}
  <BeastCareDeck />
  <section className="cage-invariants"><span>MODEL ≠ MEMORY</span><span>MODEL ≠ IDENTITY</span><span>MODEL ≠ AUTHORITY</span></section>
  <section className="cage-customize" id="customize" aria-labelledby="customize-title">
   <div className="cage-section-heading"><span className="cage-eyebrow"><SlidersHorizontal size={13}/> CHANGE THE LOOK</span>
    <h2 id="customize-title">Same Beast.<br/><em>Different style.</em></h2>
    <p>These are appearance choices, not different identities. Your generated Beast keeps its own name and game history.</p></div>
   <SparkBeastCompanion profile={creature} fallbackLook={look}
    state={ambient==='rest'?'sleeping':ambient==='orbit'?'celebrating':ambient==='perch'?'observing':'idle'}
    controls label="Customizable Spark Beast preview"/>
   <div className="cage-look-grid">{LOOKS.map(item=><button type="button" className={'cage-look-card '+item.accent+(look===item.id?' selected':'')} key={item.id} aria-pressed={look===item.id} onClick={()=>{
    const starter=generateCreature('beastbox-starter-'+item.id,item.id);
    setLook(item.id);selectProfile(starter);setSaved(false);
   }}>
    <span className="cage-look-art" aria-hidden="true"><SparkBeastCompanion profile={generateCreature('beastbox-starter-'+item.id,item.id)} fallbackLook={item.id} compact state="idle" /></span>
    <strong>{item.label}</strong><small>{item.detail}</small><span className="cage-select-label">{look===item.id?'✓ Active look':'Use this look'} →</span>
   </button>)}</div>
   <div className="cage-save-panel"><p><strong>{creature?.name||current.label} is ready to explore.</strong><br/>The active game profile is browser-local. Real memory, model choice and permissions remain in COSMOS.</p><div><button type="button" className="cage-primary" onClick={save}>Save look</button><button type="button" className="cage-secondary" onClick={clear}>Reset Beast</button></div><span role="status" className="cage-save-status">{saved?'Visual family saved locally. The active Beast profile is also retained locally.':'Generate or choose a starter to keep one Beast across the site.'}</span></div>
  </section>
  <details className="cage-advanced"><summary>More things you can do</summary><div className="cage-advanced-links"><Link href="/beast-cage/play">Care & Adventure</Link><Link href="/beast-cage/guest">Game exports</Link><Link href="/beast-cage/turntable">3D model</Link><a href="/spark/index.html">Open Public Beast Generator</a><Link href="/workspace">Owner COSMOS tools</Link></div><section className="cage-worlds" id="worlds" aria-labelledby="world-title">
   <div className="cage-section-heading"><span className="cage-eyebrow">ONE COSMOS. MANY PLACES TO EXPLORE.</span><h2 id="world-title">Your workstation,<br/><em>with a sense of wonder.</em></h2><p>Every operational state and measurement comes from the authenticated runtime; ambient art stays illustrative.</p></div>
   <div className="cage-world-grid">{WORLDS.map(world=><Link key={world.name} href={world.href} className="cage-world-card">
    <span className="cage-world-decoration" aria-hidden="true"><world.icon size={52} strokeWidth={1.05}/></span><span className="cage-world-tag">{world.tag}</span><strong>{world.name}</strong><span>{world.description}</span><ArrowRight size={15} aria-hidden="true" className="cage-world-go"/>
   </Link>)}</div>
  </section></details>
  <section className="cage-continuity"><div className="cage-continuity-art" aria-hidden="true"><img src="/cosmic-creature.svg" alt=""/></div><div><span className="cage-eyebrow">THE STORY LIVES OUTSIDE THE MODEL</span><h2>Different brain.<br/><em>Your chosen continuity.</em></h2><p>In the real owner workstation, deliberate provider changes can preserve authorized external substrate memory. A visual look isn't an AI checkpoint, and preview cards do not run model inference.</p><Link href="/workspace" className="cage-secondary">Open Brain Bay in the workstation ↗</Link></div></section>
  <footer className="cage-footer"><span>✺ BEAST BOX · CORY DAVIS / NAVISWORLD</span><span>Ambient animation ≠ model understanding</span><button onClick={()=>setExpanded(x=>!x)} type="button" aria-expanded={expanded}>{expanded?'Hide':'Show'} accessibility notes</button>
   {expanded?<p>The active companion uses the local Spark pixel renderer and recorded game-seed distributions. Reduced motion disables roaming transforms. Sound starts only after your tap. It never records sensor media or starts model inference on this public page.</p>:null}
  </footer>
 </main>;
}
