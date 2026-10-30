'use client';
import {beastDisplayName} from '../lib/companion/beast-name.mjs';
import CagePocketDimension from './cage-pocket-dimension';
import {useBeastSession} from './beast-session';
import {useUniverseMotion} from './use-universe-motion';
import {visualStateFromBeast} from '../lib/companion/creature-visual-state.mjs';
import {recordedQvmStimulusPath} from '../lib/companion/recorded-qvm-stimulus.mjs';
import {useOwnQvmCounts} from './use-own-qvm-counts';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {createPortal} from 'react-dom';
import EnvironmentConsent from './environment-consent';
import FluidSwirlLayer from './fluid-swirl-layer';
import {stormChaos} from '../lib/companion/fluid-swirl.mjs';
import {deriveEmotions} from '../lib/companion/emotion.mjs';
import {useChshGame} from './use-chsh-game';
import dynamic from 'next/dynamic';
import {isSoftwareGL} from '../lib/three/soft-gl';
import WorldMenu,{type MenuHosts} from './world-menu';
import useWorldView from './use-world-view';
import {VIEW_EVENT} from '../lib/world/world-options.mjs';
import {guestPickedPocket} from '../lib/world/home-guest-view.mjs';
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
 // The same shared view state as the Cage (Living world / Pocket explorer). Home has no pixel overlay, so a saved Classic choice shows as the pocket here.
 const {view:sharedView,setView:chooseHomeView}=useWorldView(!!own,{pixelSync:false});const homeView:'world'|'pocket'=sharedView==='world'?'world':'pocket';
 // Oct 30 (Cory: the home tiny universe is the same place as the world): a guest also sees the embedded living world, the same land,
 // one sun (lib/universe/one-sun.mjs) and residents as /beast-cage/world, unless they picked the pocket explorer on this device.
 const [guestPocket,setGuestPocket]=useState(false);useEffect(()=>{const read=()=>setGuestPocket(guestPickedPocket());read();window.addEventListener(VIEW_EVENT,read);return()=>window.removeEventListener(VIEW_EVENT,read);},[]);
 const guestWorld=!own&&!guestPocket;
 const [hosts,setHosts]=useState<MenuHosts>({place:null,tools:null,about:null});
 useEffect(()=>{if(own||zeref)return;let live=true;fetch(ZEREF_HOME_DEFAULT.src).then(r=>r.ok?r.json():null).then(d=>{const b=d?.beast;if(live&&b?.qbeast?.profile?.id===ZEREF_HOME_DEFAULT.id)setZeref(b);}).catch(()=>{});return()=>{live=false;};},[own,zeref]);
 const beast=own||zeref;const [world,setWorld]=useState(false);const [envOpen,setEnvOpen]=useState(false);
 // Software GL (CI SwiftShader, GPU-less VMs): the living world's shaders take tens of seconds to link there and freeze the page,
 // so the home view keeps the classic Cage pocket; real GPUs (incl. phones) get the embedded world. The full world still opens on demand.
 const [softHome,setSoftHome]=useState(false);useEffect(()=>{setSoftHome(isSoftwareGL());},[]);
 // Tapping your creature in the home pocket opens Look Closer, like the Cage does (the 3D pick fires beastbox:look-closer; nothing listened on Home).
 const lookHref=own?'/beast-cage/look':'/beast-cage/look?with=zeref';
 useEffect(()=>{const on=(e:Event)=>{const id=(e as CustomEvent).detail?.id;if(id==='beast'||id==='zeref')window.location.assign(lookHref);};window.addEventListener('beastbox:look-closer',on);return()=>window.removeEventListener('beastbox:look-closer',on);},[lookHref]);
 const game=useChshGame();const sc=stormChaos(deriveEmotions(beast),game);
 const qvmCounts=useOwnQvmCounts(beast?recordedQvmStimulusPath(beast):null);
 const chat=Array.isArray(session?.chat)?session.chat:[];const lastYou=[...chat].reverse().find((m:any)=>m?.role==='you')?.text||null;
 // Oct 16: the same cage look Cory loves; living-core Zeref + life layer live inside it. The ⋯ button tucks sound/game/help on phones.
 return <><div className="home-pocket-layer is-roamer" data-home-pocket={own?'saved-beast':zeref?'zeref-bb-deada969':'guide'}>
  {((own&&homeView==='world')||guestWorld)&&!world&&!softHome?<LivingWorld embedded menuHost={hosts.place} infoHost={hosts.about} genome={own?.genome||null} beastKey={own?.qbeast?.profile?.id||null} beastName={own?beastDisplayName(own):null} onExpand={()=>setWorld(true)}/>:<CagePocketDimension seed={beast?beast.genome?.seed||beast.seed:null} qbeastId={beast?beast.qbeast.profile.id:null}
   stage={beast?(beast.nativeStage||1):1} behaviorPosition={beast?beast.behavior?.position||null:null}
   state={beast?visualStateFromBeast(beast):'idle'} reduced={reduced} onActiveChange={noop} qvmCounts={qvmCounts} autoOrbit chatLine={lastYou} menuHost={hosts.tools} ignorePixel/>}
  {world&&typeof document!=='undefined'?createPortal(<LivingWorld genome={own?.genome||null} beastKey={own?.qbeast?.profile?.id||null} beastName={own?(beastDisplayName(own)):null} onClose={()=>setWorld(false)}/>,document.body):null}
  {envOpen&&typeof document!=='undefined'?createPortal(<EnvironmentConsent onClose={()=>setEnvOpen(false)} beastName={beastDisplayName(beast)}/>,document.body):null}
  {reduced?null:<FluidSwirlLayer storm={sc.storm} chaos={sc.chaos} count={60}/>}
 </div>
 {/* Oct 25: ONE menu replaces the three buttons that used to sit on the scene. It sits in its own layer above the 3D sprite so it is always tappable. */}
 <div className="home-menu-layer">
  <WorldMenu context="home" view={homeView} onView={chooseHomeView} hasBeast={!!own} beastName={beast?beastDisplayName(beast):null} onHosts={setHosts} hideViews={['classic']}
   extra={[{label:'Enter the tiny world',icon:'🌍',onClick:()=>setWorld(true),attr:'data-open-living-world'},{label:'Share my world\u2019s signals',icon:'🌱',onClick:()=>setEnvOpen(true),attr:'data-open-environment'},{label:'Sound, game & help controls',icon:'🔊',onClick:()=>document.body.classList.toggle('lc-tools-open'),attr:'data-home-tools'}]}/>
 </div></>;
}
