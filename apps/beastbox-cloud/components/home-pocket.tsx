'use client';
import CagePocketDimension from './cage-pocket-dimension';
import {useBeastSession} from './beast-session';
import {useUniverseMotion} from './use-universe-motion';
import {visualStateFromBeast} from '../lib/companion/creature-visual-state.mjs';
import {recordedQvmStimulusPath} from '../lib/companion/recorded-qvm-stimulus.mjs';
import {useOwnQvmCounts} from './use-own-qvm-counts';
import {useEffect,useState} from 'react';
import {createPortal} from 'react-dom';
import FluidSwirlLayer from './fluid-swirl-layer';
import {stormChaos} from '../lib/companion/fluid-swirl.mjs';
import {deriveEmotions} from '../lib/companion/emotion.mjs';
import {useChshGame} from './use-chsh-game';
import dynamic from 'next/dynamic';
import {isSoftwareGL} from '../lib/three/soft-gl';
const LivingWorld=dynamic(()=>import('./living-world'),{ssr:false});
/** Guest default: Zeref bb-deada969's own recorded session record (display only; never adopted, never merged with the Moonwraith display guide). */
export const ZEREF_HOME_DEFAULT={id:'bb-deada969',src:'/spark/zeref-live-20261010/unsigned-session.json'};
/** Home shows the same dimensional pocket as the Cage, view-only (explore it in the Cage).
 * Driven by the saved Beast's real state/behavior; no new identity or seed is created. */
const noop=()=>{};
export default function HomePocket(){
 const {session}=useBeastSession();const {reduced}=useUniverseMotion();
 const own=session?.beast?.qbeast?.profile?.id?session.beast:null;
 const [zeref,setZeref]=useState<any>(null);
 const [homeView,setHomeView]=useState<'world'|'pocket'>('world');const chooseHomeView=(v:'world'|'pocket')=>setHomeView(v);
 useEffect(()=>{if(own||zeref)return;let live=true;fetch(ZEREF_HOME_DEFAULT.src).then(r=>r.ok?r.json():null).then(d=>{const b=d?.beast;if(live&&b?.qbeast?.profile?.id===ZEREF_HOME_DEFAULT.id)setZeref(b);}).catch(()=>{});return()=>{live=false;};},[own,zeref]);
 const beast=own||zeref;const [world,setWorld]=useState(false);
 // Software GL (CI SwiftShader, GPU-less VMs): the living world's shaders take tens of seconds to link there and freeze the page,
 // so the home view keeps the classic Cage pocket; real GPUs (incl. phones) get the embedded world. The full world still opens on demand.
 const [softHome,setSoftHome]=useState(false);useEffect(()=>{setSoftHome(isSoftwareGL());},[]);
 const game=useChshGame();const sc=stormChaos(deriveEmotions(beast),game);
 const qvmCounts=useOwnQvmCounts(beast?recordedQvmStimulusPath(beast):null);
 const chat=Array.isArray(session?.chat)?session.chat:[];const lastYou=[...chat].reverse().find((m:any)=>m?.role==='you')?.text||null;
 // Oct 16: the same cage look Cory loves; living-core Zeref + life layer live inside it. The ⋯ button tucks sound/game/help on phones.
 return <div className="home-pocket-layer is-roamer" data-home-pocket={own?'saved-beast':zeref?'zeref-bb-deada969':'guide'}>
  {own&&homeView==='world'&&!world&&!softHome?<LivingWorld embedded genome={own.genome||null} beastKey={own.qbeast?.profile?.id||null} beastName={own.displayName||own.genome?.names?.[String(own.stage)]||null} onExpand={()=>setWorld(true)}/>:<CagePocketDimension seed={beast?beast.genome?.seed||beast.seed:null} qbeastId={beast?beast.qbeast.profile.id:null}
   stage={beast?(beast.nativeStage||1):1} behaviorPosition={beast?beast.behavior?.position||null:null}
   state={beast?visualStateFromBeast(beast):'idle'} reduced={reduced} onActiveChange={noop} qvmCounts={qvmCounts} autoOrbit chatLine={lastYou}/>}
  {own?<button type="button" className="lc-living-world-open" data-home-view-toggle onClick={()=>chooseHomeView(homeView==='world'?'pocket':'world')} style={{position:'absolute',left:10,top:48,zIndex:5,background:'rgba(20,14,50,.85)',color:'#fff',border:0,borderRadius:10,padding:'6px 10px',font:'12px system-ui'}}>{homeView==='world'?'✦ Pocket view':'🌍 Living world'}</button>:null}
  <button type="button" className="lc-roamer-tools" aria-label="Show sound, game and help controls" onClick={()=>document.body.classList.toggle('lc-tools-open')}>⋯</button>
  <button type="button" className="lc-living-world-open" data-open-living-world onClick={()=>setWorld(true)} style={{position:'absolute',left:10,top:10,zIndex:5,background:'rgba(107,70,193,.9)',color:'#fff',border:0,borderRadius:10,padding:'8px 12px',fontWeight:600}}>🌍 Enter the tiny world</button>
  {world&&typeof document!=='undefined'?createPortal(<LivingWorld genome={own?.genome||null} beastKey={own?.qbeast?.profile?.id||null} beastName={own?(own.displayName||own.genome?.names?.[String(own.stage)]||null):null} onClose={()=>setWorld(false)}/>,document.body):null}
  {reduced?null:<FluidSwirlLayer storm={sc.storm} chaos={sc.chaos} count={60}/>}
 </div>;
}
