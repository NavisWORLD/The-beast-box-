'use client';
import CagePocketDimension from './cage-pocket-dimension';
import {useBeastSession} from './beast-session';
import {useUniverseMotion} from './use-universe-motion';
import {visualStateFromBeast} from '../lib/companion/creature-visual-state.mjs';
/** Home shows the same dimensional pocket as the Cage, view-only (explore it in the Cage).
 * Driven by the saved Beast's real state/behavior; no new identity or seed is created. */
const noop=()=>{};
export default function HomePocket(){
 const {session}=useBeastSession();const {reduced}=useUniverseMotion();
 const beast=session?.beast?.qbeast?.profile?.id?session.beast:null;
 return <div className="home-pocket-layer" aria-hidden="true" data-home-pocket={beast?'saved-beast':'guide'}>
  <CagePocketDimension seed={beast?beast.genome?.seed||beast.seed:null} qbeastId={beast?beast.qbeast.profile.id:null}
   stage={beast?(beast.nativeStage||1):1} behaviorPosition={beast?beast.behavior?.position||null:null}
   state={beast?visualStateFromBeast(beast):'idle'} reduced={reduced} onActiveChange={noop}/>
 </div>;
}
