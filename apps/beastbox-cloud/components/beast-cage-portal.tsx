'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {ArrowRight,BrainCircuit,DatabaseZap,LockKeyhole,Orbit,ShieldCheck,SlidersHorizontal,Sparkles,Volume2} from 'lucide-react';
import CosmicCompanion3D,{type CreatureLook} from './cosmic-companion-3d';
const LOOKS:{id:CreatureLook;label:string;detail:string;accent:string}[]=[
 {id:'nebula',label:'Nebby',detail:'A curious little pocket galaxy',accent:'violet'},
 {id:'aurora',label:'Lumen',detail:'The quiet glow of cosmic dawn',accent:'cyan'},
 {id:'starlight',label:'Orion',detail:'A whimsical celestial explorer',accent:'rose'}
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
 const [look,setLook]=useState<CreatureLook>('nebula');
 const [saved,setSaved]=useState(false),[prefersReduced,setPrefersReduced]=useState(false);
 const [expanded,setExpanded]=useState(false);
 useEffect(()=>{
  const media=window.matchMedia('(prefers-reduced-motion: reduce)');
  const onChange=()=>setPrefersReduced(media.matches);
  onChange();media.addEventListener('change',onChange);
  try{const item=window.localStorage.getItem(STORAGE);if(item&&LOOKS.some(x=>x.id===item)){setLook(item as CreatureLook);setSaved(true);}}
  catch{/* private browsing/storage unavailable: visual preview remains usable */}
  return()=>media.removeEventListener('change',onChange);
 },[]);
 function save(){
  try{window.localStorage.setItem(STORAGE,look);window.dispatchEvent(new Event('beastbox:cage-look-changed'));setSaved(true);}
  catch{setSaved(false);}
 }
 function clear(){
  try{window.localStorage.removeItem(STORAGE);window.dispatchEvent(new Event('beastbox:cage-look-changed'));}catch{/* state still resets */ }
  setLook('nebula');setSaved(false);
 }
 const current=LOOKS.find(x=>x.id===look)||LOOKS[0];
 return <main className="cage-universe" data-reduced-motion={prefersReduced}>
  <div className="cage-sky" aria-hidden="true"/>
  <header className="cage-topbar"><Link href="/" aria-label="Beast Box homepage" className="cage-brand"><span>✺</span><span>BEAST BOX<small>NAVISWORLD / COSMOS</small></span></Link>
   <nav aria-label="Beast Cage navigation"><a href="#habitat">Habitat</a><a href="#worlds">Explore</a><Link href="/beast-cage/talk">Talk</Link><Link className="cage-nav-cta" href="/workspace">Owner deck <ArrowRight size={15}/></Link></nav>
  </header>
  <section className="cage-hero" id="habitat" aria-labelledby="cage-title">
   <div className="cage-headline">
    <span className="cage-eyebrow"><Sparkles size={13}/> WELCOME TO THE BEAST CAGE</span>
    <h1 id="cage-title">A small companion.<br/><em>An entire universe.</em></h1>
    <p>Give your ideas a little cosmic troublemaker. Keep the story in COSMOS, choose your compatible brain in the owner workstation, and let real signals inspire its motion.</p>
    <div className="cage-hero-actions"><Link className="cage-primary" href="/beast-cage/talk">Talk to the real Beast <ArrowRight size={17}/></Link><a className="cage-secondary" href="#customize">Customize your companion</a><Link className="cage-secondary" href="/workspace">Open real workstation ↗</Link></div>
    <p className="cage-quiet"><LockKeyhole size={13}/> Customization below is a browser-only visual preview, not an additional COSMOS identity or memory store.</p>
   </div>
   <div className="cage-habitat-visual" role="img" aria-label="Original cosmic observatory with a floating galaxy companion">
    <div className="cage-orbit cage-orbit-one" aria-hidden="true"/><div className="cage-orbit cage-orbit-two" aria-hidden="true"/>
    <CosmicCompanion3D look={look} quality="auto" className="cage-hero-creature" label="Interactive three-dimensional cosmic companion"/>
    <span className="cage-habitat-caption">✧ YOUR OWN POCKET UNIVERSE</span>
   </div>
  </section>
  <section className="cage-invariants"><span>MODEL ≠ MEMORY</span><span>MODEL ≠ IDENTITY</span><span>MODEL ≠ AUTHORITY</span></section>
  <section className="cage-customize" id="customize" aria-labelledby="customize-title">
   <div className="cage-section-heading"><span className="cage-eyebrow"><SlidersHorizontal size={13}/> A LOOK THAT FEELS LIKE YOURS</span>
    <h2 id="customize-title">Meet the first<br/><em>little constellations.</em></h2>
    <p>Preview an original companion look. Save only the visual preference to this device, or clear it whenever you like.</p></div>
   <div className="cage-look-grid">{LOOKS.map(item=><button type="button" className={'cage-look-card '+item.accent+(look===item.id?' selected':'')} key={item.id} aria-pressed={look===item.id} onClick={()=>{setLook(item.id);setSaved(false);}}>
    <span className="cage-look-art"><img src="/cosmic-creature.svg" alt="" aria-hidden="true"/></span>
    <strong>{item.label}</strong><small>{item.detail}</small><span className="cage-select-label">{look===item.id?'✓ Selected':'Choose this look'} →</span>
   </button>)}</div>
   <div className="cage-save-panel"><p><strong>{current.label} is ready to explore.</strong><br/>This changes appearance only. Real memory, model choice and permissions remain in COSMOS.</p><div><button type="button" className="cage-primary" onClick={save}>Save look on this device</button><button type="button" className="cage-secondary" onClick={clear}>Clear saved look</button></div><span role="status" className="cage-save-status">{saved?'Visual look saved locally. No private COSMOS data copied.':'Look is a temporary preview until you save it.'}</span></div>
  </section>
  <section className="cage-worlds" id="worlds" aria-labelledby="world-title">
   <div className="cage-section-heading"><span className="cage-eyebrow">ONE COSMOS. MANY PLACES TO EXPLORE.</span><h2 id="world-title">Your workstation,<br/><em>with a sense of wonder.</em></h2><p>Every operational state and measurement comes from the authenticated runtime; ambient art stays illustrative.</p></div>
   <div className="cage-world-grid">{WORLDS.map(world=><Link key={world.name} href={world.href} className="cage-world-card">
    <span className="cage-world-decoration" aria-hidden="true"><world.icon size={52} strokeWidth={1.05}/></span><span className="cage-world-tag">{world.tag}</span><strong>{world.name}</strong><span>{world.description}</span><ArrowRight size={15} aria-hidden="true" className="cage-world-go"/>
   </Link>)}</div>
  </section>
  <section className="cage-continuity"><div className="cage-continuity-art" aria-hidden="true"><img src="/cosmic-creature.svg" alt=""/></div><div><span className="cage-eyebrow">THE STORY LIVES OUTSIDE THE MODEL</span><h2>Different brain.<br/><em>Your chosen continuity.</em></h2><p>In the real owner workstation, deliberate provider changes can preserve authorized external substrate memory. A visual look isn't an AI checkpoint, and preview cards do not run model inference.</p><Link href="/workspace" className="cage-secondary">Open Brain Bay in the workstation ↗</Link></div></section>
  <footer className="cage-footer"><span>✺ BEAST BOX · CORY DAVIS / NAVISWORLD</span><span>Ambient animation ≠ model understanding</span><button onClick={()=>setExpanded(x=>!x)} type="button" aria-expanded={expanded}>{expanded?'Hide':'Show'} accessibility notes</button>
   {expanded?<p>Animated companion uses a WebGL procedural mesh if supported. Reduced motion uses its static original illustration. It never records sensor data or starts inference on this public page.</p>:null}
  </footer>
 </main>;
}
