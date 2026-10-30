'use client';
import Details from './details-toggle';
import CageCreatureSwitch from './cage-creature-switch';
import {beastDisplayName} from '../lib/companion/beast-name.mjs';
import {useCallback,useEffect,useMemo,useState} from 'react';
import Link from 'next/link';
import TalkBeastLabel from './talk-beast-label'; // Talk to My Beast fallback
import {ArrowRight,BrainCircuit,DatabaseZap,LockKeyhole,Orbit,ShieldCheck,SlidersHorizontal,Sparkles,Volume2} from 'lucide-react';
import SparkBeastCompanion from './spark-beast-companion';
import dynamic from 'next/dynamic';
import {isSoftwareGL} from '../lib/three/soft-gl';
import SparkBeastArena from './spark-beast-arena';
// Code-split the heavy WebGL/animation scenes so the Beast Cage paints fast on phones.
const LivingWorld=dynamic(()=>import('./living-world'),{ssr:false});
const CagePocketDimension=dynamic(()=>import('./cage-pocket-dimension'),{ssr:false,loading:()=><div style={{minHeight:320}} aria-busy="true"/>});
import GenesisForge from './genesis-forge'; // stays in the first bundle: tests and users type a seed into it right after load
import BeastCareDeck from './beast-care-deck';
import CreatureHabitat from './creature-habitat';
import {visualStateFromBeast} from '../lib/companion/creature-visual-state.mjs';
import {recordedQvmStimulusPath} from '../lib/companion/recorded-qvm-stimulus.mjs';
import {useOwnQvmCounts} from './use-own-qvm-counts';
import {useUniverseMotion} from './use-universe-motion';
const QbeastMenagerie=dynamic(()=>import('./qbeast-menagerie')); // E3: below-the-fold, split out of the first Cage bundle
const CreatureDashboard=dynamic(()=>import('./creature-dashboard')); // E3: below-the-fold, split out of the first Cage bundle
import {useBeastSession} from './beast-session';
import {shownName} from '../lib/companion/session.mjs';
import {publicProfileFromBeast,publicProfileFromCreature,type CosmosProfile} from '../public/spark/cosmos-profile.mjs';
import {useCompanion} from './companion-provider';
import {generateCreature,type BaseLook,type AmbientAction} from '../lib/creature-profile';
import BrandCrest from '@/components/brand-crest';
import {useActiveBeastName} from './use-active-beast-name';
const ZerefDiaryPanel=dynamic(()=>import('./zeref-diary-panel')); // E3: below-the-fold, split out of the first Cage bundle
const MetaMusePanel=dynamic(()=>import('./meta-muse-panel')); // E3: below-the-fold, split out of the first Cage bundle
import {ZEREF_PROFILE} from '../lib/zeref/zeref-mind.mjs';
import {creatureVisual} from '../public/spark/creature-assets.mjs';
import {POCKET_3D_CAMERA_RESET} from '../lib/companion/pocket-3d-settings.mjs';
import GeyserControls from './geyser-controls';
import WorldMenu,{type MenuHosts} from './world-menu';
import useWorldView from './use-world-view';
import {overlayFor} from '../lib/world/world-options.mjs';
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
 {name:'Synapse Observatory',description:'Logged events and genuine state receipts.',icon:Orbit,tag:'SOFTWARE LOGS',href:'/workspace#synapse-observatory'},
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
 const {session,ready:sessionReady}=useBeastSession();
 const activeName=useActiveBeastName();
 const sameSpark=!!session?.beast?.qbeast;
 const qvmCounts=useOwnQvmCounts(session?.beast?.qbeast?.profile?.id?recordedQvmStimulusPath(session.beast):null);
 const creatureName=sameSpark?shownName(session.beast):creature?.name;
 // The model/persona and the companion starter profile do not override the verified saved QBEAST.
 const savedVisual=sameSpark?creatureVisual({id:session.beast.qbeast.profile.id,genome:session.beast.genome}):null;
 // Default view: the ZEREF rig exploring the dimensional pocket. The original pixel sprite stays one tap away.
 // Tapping the Beast (or Zeref) in the pocket offers Look Closer; other creatures just get the camera focus.
 const [lookId,setLookId]=useState<string|null>(null);
 /* E2 fallback: on CPU-rendered WebGL the 3D tap pick is unreliable, so a fixed Look Closer tap target stays on screen there. */
  const [softTap,setSoftTap]=useState(false);useEffect(()=>{setSoftTap(isSoftwareGL());},[]);
  useEffect(()=>{let t=0;const on=(e:Event)=>{const id=(e as CustomEvent).detail?.id;const ok=id==='beast'||id==='zeref';setLookId(ok?id:null);if(ok){/* E2: a tap on your creature opens Look Closer */window.location.assign('/beast-cage/look'+(id==='zeref'?'?with=zeref':''));}clearTimeout(t);t=window.setTimeout(()=>setLookId(null),7000);};window.addEventListener('beastbox:look-closer',on);return()=>{window.removeEventListener('beastbox:look-closer',on);clearTimeout(t);};},[]);
 // ONE shared view state (Living world / Pocket explorer / Classic pixel sprite): same saved choice as the home pocket and the menu.
 const {view,setView}=useWorldView(sameSpark);const [worldFull,setWorldFull]=useState(false);
 const [hosts,setHosts]=useState<MenuHosts>({place:null,tools:null,about:null});
 const [cageMode,setCageMode]=useState<'friendly'|'advanced'>('friendly');
 useEffect(()=>{try{if(window.localStorage.getItem('beastbox-cage-mode-v1')==='advanced'||/^#(menagerie)/.test(window.location.hash))setCageMode('advanced');}catch{}},[]);
 const chooseMode=(next:'friendly'|'advanced')=>{setCageMode(next);try{window.localStorage.setItem('beastbox-cage-mode-v1',next);}catch{}};
 // Until the saved session has loaded, never show the seeded starter's name (it flashed 'Look Closer at <starter>' before the real beast appeared): use the active beast's name from storage, else a neutral phrase.
 const pocketName=sessionReady?(creatureName||'Zeref'):(activeName||'your beast');
 const cosmosProfile=useMemo<CosmosProfile|null>(()=>{
  if(sameSpark)return publicProfileFromBeast(session.beast,{name:creatureName});
  if(!creature)return {schema:'cosmos-beast-public/v1',id:ZEREF_PROFILE.id,name:'Zeref',provenance:{kind:'recorded-quantum-genome',backend:'ibm_marrakesh'},traits:{}};
  return publicProfileFromCreature(creature);
  // eslint-disable-next-line react-hooks/exhaustive-deps
 },[creature?.id,sameSpark,creatureName,session?.beast]);
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
 // Cory Oct 25: the 2D sprite is never drawn over the 3D scene by default (those creatures already live in the world as 3D); only the explicit Classic view or the 3D rig draws here.
 const overlay=overlayFor(view,{rigAvailable:!savedVisual||savedVisual.renderer==='moonwraith-rig'});
 return <main className="cage-universe" data-reduced-motion={prefersReduced} data-cage-mode={cageMode}>
  <div className="cage-mode-toggle" role="group" aria-label="Cage view mode">
   <button type="button" aria-pressed={cageMode==='friendly'} onClick={()=>chooseMode('friendly')}>✦ Friendly</button>
   <button type="button" aria-pressed={cageMode==='advanced'} onClick={()=>chooseMode('advanced')}>⚙ Advanced</button>
  </div>
  <div className="cage-sky" aria-hidden="true"/>
  <header className="cage-topbar"><Link href="/" aria-label="Beast Box homepage" className="cage-brand"><BrandCrest className="cage-brand-crest" size={40} decorative/><span>BEAST BOX<small>NAVISWORLD / COSMOS</small></span></Link>
   <nav aria-label="Beast Box journey">
    <Link href="/">Home</Link>
    <a href="/spark/index.html">My Beast</a>
    <Link href="/beast-cage" aria-current="page">Beast Cage</Link>
    <Link href="/sol-game">Lost COSMOS</Link>
    <Link href="/beast-cage/field">Lost COSMOS Field</Link>
    <Link href="/brain-bay">Brain Bay</Link>
    <Link href="/research">Research Lab</Link>
    <Link href="/workspace">Workshop</Link>
    <Link className="cage-nav-cta" href="/settings">Settings <ArrowRight size={15}/></Link>
   </nav>
  </header>
  <section className="cage-hero" id="habitat" aria-labelledby="cage-title">
   <div className="cage-headline">
    <span className="cage-eyebrow"><Sparkles size={13}/> WELCOME TO THE BEAST CAGE</span>
    <h1 id="cage-title">A small companion.<br/><em>An entire universe.</em></h1>
    <p>For dreamers, idlers, players, builders and anyone with a strange little idea: this is the place to live with your Beast. Care for it, talk to it, shape its look, then take the same identity into LOST COSMOS.</p>
    <div className="cage-hero-actions"><Link className="cage-primary" href="/beast-cage/talk"><TalkBeastLabel/> <ArrowRight size={17}/></Link><a className="cage-secondary" href="#customize">Customize</a><Link className="cage-secondary" href="/sol-game">Enter LOST COSMOS 🎮</Link></div>
    <p className="cage-quiet"><LockKeyhole size={13}/><span>One Beast stays at the center. More ways to explore: <Link href="/beast-cage/world">Tiny World</Link> · <Link href="/beast-cage/look">Look Closer</Link> · <Link href="/beast-cage/play">Adventure walk</Link> · <Link href="/beast-cage/field">📷 Lost COSMOS Field</Link> · <Link href="/beast-cage/guest">Catch a Star</Link> · <a href="/spark/index.html">Open Public Beast Generator</a> · <Link href="/workspace?owner=1" data-workshop-link>Workshop</Link>.</span></p>
   </div>
   <div data-cage-view={view} data-creature-id={sameSpark?session.beast.qbeast.profile.id:undefined} className={'cage-habitat-visual'+(pocketReady?' cage-pocket-active':'')} role="group" aria-label="Circular dimensional world behind your beast; drag or pinch to explore, or focus and use arrow keys and plus/minus to move the view" tabIndex={0}>
    <div className="cage-orbit cage-orbit-one" aria-hidden="true"/><div className="cage-orbit cage-orbit-two" aria-hidden="true"/>
    <GeyserControls/>
    <WorldMenu context="cage" view={view} onView={setView} hasBeast={sameSpark} beastName={pocketName} onHosts={setHosts}/>
    {/* Oct 25: 'Look Closer' lives in the menu now so nothing sits on top of the creatures. */}
    <CagePocketDimension
     seed={sameSpark?session.beast.genome?.seed||session.beast.seed:null}
     qbeastId={sameSpark?session.beast.qbeast.profile.id:null}
     stage={sameSpark?(session.beast.nativeStage||1):1}
     behaviorPosition={sameSpark?session.beast.behavior?.position||null:null}
     state={sameSpark?visualStateFromBeast(session.beast):ambient}
     reduced={prefersReduced} onActiveChange={onPocketActive}
     qvmCounts={qvmCounts} menuHost={hosts.tools}/>
    {overlay!=='none'?<SparkBeastArena profile={creature} fallbackLook={look}
     state={sameSpark?visualStateFromBeast(session.beast):ambient==='rest'?'sleeping':ambient==='orbit'?'celebrating':ambient==='perch'?'observing':'idle'}
     label="Active beast companion" preferSavedBeast={sameSpark}
     rig={overlay==='rig'}/>:null}
    {view==='world'&&sameSpark&&!worldFull?<LivingWorld embedded menuHost={hosts.place} infoHost={hosts.about} genome={session.beast.genome||null} beastKey={session.beast.qbeast.profile.id} beastName={beastDisplayName(session.beast)} onExpand={()=>setWorldFull(true)}/>:null}
    {worldFull&&sameSpark?<LivingWorld genome={session.beast.genome||null} beastKey={session.beast.qbeast.profile.id} beastName={beastDisplayName(session.beast)} onClose={()=>setWorldFull(false)}/>:null}
    <span className="cage-habitat-caption">✧ YOUR OWN POCKET UNIVERSE</span>
   </div>
   <div className="cage-details-row"><CageCreatureSwitch context="cage"/></div>
   <p className="cage-view-status" data-cage-view-status aria-live="polite"><span>{view==='world'?'🌍 Living world':view==='classic'?'▦ Classic pixel sprite':'✦ Pocket explorer'}</span> · change the view, reset the camera or open the diary in the <strong>☰ Habitat</strong> (top right of the scene).</p>
  </section>
  {sameSpark?<CreatureDashboard beast={session.beast} cosmosProfile={cosmosProfile}/>:null}
  <ZerefDiaryPanel journalId={sameSpark?session.beast.qbeast.profile.id:creature?creature.id:ZEREF_PROFILE.id} beastName={pocketName} cosmosProfile={cosmosProfile} showGrow={!sameSpark}/>
  <MetaMuseCageEntry/>
  {!sameSpark?<GenesisForge value={creature} onChange={next=>{selectProfile(next);setLook(next.baseLook);}}
   onAmbient={setAmbient}/>:<div className="cage-generated-status"><span>{creatureName} · same recorded genome and QBEAST</span><Link href="/sol-game">Play this Beast in LOST COSMOS 🎮</Link></div>}
  {creature?<div className="cage-generated-status" role="status">
   ✧ {creatureName} · {creature.family} · {ambient} (classical seeded visual behavior)
   <Link href="/beast-cage/guest">Take {creatureName} to the game lab ↗</Link>
  </div>:null}
  <CreatureHabitat />
  <BeastCareDeck />
  <div data-advanced-only><QbeastMenagerie />
  <Details><section className="cage-invariants"><span>MODEL ≠ MEMORY</span><span>MODEL ≠ IDENTITY</span><span>MODEL ≠ AUTHORITY</span></section></Details></div>
  <section className="cage-customize" id="customize" aria-labelledby="customize-title">
   <div className="cage-section-heading"><span className="cage-eyebrow"><SlidersHorizontal size={13}/> A LOOK THAT FEELS LIKE YOURS</span>
    <h2 id="customize-title">Meet the first<br/><em>little constellations.</em></h2>
    <p>Customize the same Beast that roams the site, uses the shared care deck, and crosses into Lost COSMOS. Stage controls are previews; earned cartridge evolution still comes from gameplay. The public generator can draw from the expanded recorded-seed pool.</p><a className="cage-secondary" href="/spark/index.html">Generate from the public IBM seed archive ↗</a></div>
   <SparkBeastCompanion profile={creature} fallbackLook={look}
    state={sameSpark?visualStateFromBeast(session.beast):ambient==='rest'?'sleeping':ambient==='orbit'?'celebrating':ambient==='perch'?'observing':'idle'}
    controls label="Customizable beast preview" preferSavedBeast={sameSpark}/>
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
  <section className="cage-continuity"><div className="cage-continuity-art" aria-hidden="true"><img src="/cosmic-creature.svg" alt=""/></div><div><span className="cage-eyebrow">THE STORY LIVES OUTSIDE THE MODEL</span><h2>Different brain.<br/><em>Your chosen continuity.</em></h2><p>In the real owner Workshop, deliberate provider changes can preserve authorized external substrate memory. A visual look isn't an AI checkpoint, and preview cards do not run model inference.</p><Link href="/brain-bay" className="cage-secondary">Open Brain Bay ↗</Link></div></section>
  <footer className="cage-footer"><span><BrandCrest size={14} decorative style={{verticalAlign:'-2px',marginRight:6}}/>BEAST BOX · CORY DAVIS / NAVISWORLD</span><span>Ambient animation ≠ model understanding</span><button onClick={()=>setExpanded(x=>!x)} type="button" aria-expanded={expanded}>{expanded?'Hide':'Show'} accessibility notes</button>
   {expanded?<p>The active companion uses the local Spark pixel renderer and recorded game-seed distributions. Reduced motion disables roaming transforms. Sound starts only after your tap. It never records sensor media or starts model inference on this public page.</p>:null}
  </footer>
 </main>;
}

/** Pair with Meta Muse on the Beast Cage. The panel mounts only after the guest opens it,
 * so its browser-only connector URL never differs between server and client render. */
function MetaMuseCageEntry(){
 const [open,setOpen]=useState(false);
 return <details id="meta-muse" data-meta-muse-entry="beast-cage" className="cage-meta-muse" onToggle={event=>setOpen((event.currentTarget as HTMLDetailsElement).open)}>
  <summary>Pair with Meta Muse</summary>{open?<MetaMusePanel/>:null}
 </details>;
}
