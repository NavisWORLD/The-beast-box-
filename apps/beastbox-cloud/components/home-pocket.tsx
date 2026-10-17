'use client';
import CagePocketDimension from './cage-pocket-dimension';
import {useBeastSession} from './beast-session';
import {useUniverseMotion} from './use-universe-motion';
import {visualStateFromBeast} from '../lib/companion/creature-visual-state.mjs';
import {recordedQvmStimulusPath} from '../lib/companion/recorded-qvm-stimulus.mjs';
import {useOwnQvmCounts} from './use-own-qvm-counts';
import {useEffect,useState} from 'react';
import FluidSwirlLayer from './fluid-swirl-layer';
import {stormChaos} from '../lib/companion/fluid-swirl.mjs';
import {deriveEmotions} from '../lib/companion/emotion.mjs';
import {useChshGame} from './use-chsh-game';
import LivingCoreRoamer from './living-core-roamer';
import {baseMood} from '../lib/living-core/roam-brain.mjs';
/** Guest default: Zeref bb-deada969's own recorded session record (display only; never adopted, never merged with the Moonwraith display guide). */
export const ZEREF_HOME_DEFAULT={id:'bb-deada969',src:'/spark/zeref-live-20261010/unsigned-session.json'};
/** Home shows the same dimensional pocket as the Cage, view-only (explore it in the Cage).
 * Driven by the saved Beast's real state/behavior; no new identity or seed is created. */
const noop=()=>{};
export default function HomePocket(){
 const {session}=useBeastSession();const {reduced}=useUniverseMotion();
 const own=session?.beast?.qbeast?.profile?.id?session.beast:null;
 const [zeref,setZeref]=useState<any>(null);
 useEffect(()=>{if(own||zeref)return;let live=true;fetch(ZEREF_HOME_DEFAULT.src).then(r=>r.ok?r.json():null).then(d=>{const b=d?.beast;if(live&&b?.qbeast?.profile?.id===ZEREF_HOME_DEFAULT.id)setZeref(b);}).catch(()=>{});return()=>{live=false;};},[own,zeref]);
 const beast=own||zeref;
 const game=useChshGame();const sc=stormChaos(deriveEmotions(beast),game);
 const qvmCounts=useOwnQvmCounts(beast?recordedQvmStimulusPath(beast):null);
 const chat=Array.isArray(session?.chat)?session.chat:[];const lastYou=[...chat].reverse().find((m:any)=>m?.role==='you')?.text||null;
 // Oct 16: guests (and Zeref) get the living-core 3D Zeref roaming a bigger pocket; a saved QBEAST keeps its own genome render.
 if(!own)return <div className="home-pocket-layer is-roamer" data-home-pocket={zeref?'zeref-bb-deada969':'guide'}>
  <LivingCoreRoamer creature="zeref" beastId={ZEREF_HOME_DEFAULT.id} mood={baseMood(deriveEmotions(beast),beast?visualStateFromBeast(beast):'idle')} chatText={lastYou} chatCount={chat.length} game={game} reduced={reduced}/>
 </div>;
 return <div className="home-pocket-layer" aria-hidden="true" data-home-pocket="saved-beast">
  <CagePocketDimension seed={beast.genome?.seed||beast.seed} qbeastId={beast.qbeast.profile.id}
   stage={beast.nativeStage||1} behaviorPosition={beast.behavior?.position||null}
   state={visualStateFromBeast(beast)} reduced={reduced} onActiveChange={noop} qvmCounts={qvmCounts} autoOrbit/>
  {reduced?null:<FluidSwirlLayer storm={sc.storm} chaos={sc.chaos} count={60}/>}
 </div>;
}
