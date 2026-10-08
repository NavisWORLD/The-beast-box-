'use client';
import {useState} from 'react';
import CosmicCompanion3D from './cosmic-companion-3d';
import {useCompanion} from './companion-provider';
import {useBeastSession} from './beast-session';
import {shownName} from '../lib/companion/session.mjs';
/** Original real geometric hero, sharing the selected PUBLIC game genome. */
export default function HomepageCreature(){
 const {profile}=useCompanion();
 const {session}=useBeastSession();
 // A QBEAST's recorded genome outranks a decorative 3D preview. Do not invent
 // a new 3D body for a creature whose authoritative art is the native sprite.
 const savedBeast=session?.beast?.qbeast?.profile?.id?session.beast:null;
 const genome=savedBeast?.genome?.seed?savedBeast.genome:null;
 const [spin,setSpin]=useState(false),[angle,setAngle]=useState<number|null>(null);
 return <div className="cosmos-home-hero" aria-label="Interactive cosmic companion observatory">
  <CosmicCompanion3D quality="low" profile={profile}
   preferSprite={Boolean(genome)} spriteGenome={genome} spriteStage={savedBeast?.nativeStage||savedBeast?.stage||1} spriteName={savedBeast?shownName(savedBeast):''} spriteId={savedBeast?.qbeast?.profile?.id||''}
   look={profile?.baseLook??'nebula'}
   label={savedBeast?`${shownName(savedBeast)} · QBEAST ${savedBeast.qbeast.profile.id}`:"Procedural 3D preview dragon with a golden orbiting star"}
   turntable={spin} turntableAngle={angle}/>
  {genome?<p className="cosmos-home-qbeast" role="status">✦ {shownName(savedBeast)} · {savedBeast.qbeast.profile.id} · same recorded-sprite identity</p>:null}
  {!genome?<div className="cosmos-home-controls" aria-label="Real 3D rotation controls">
   <button type="button" aria-pressed={spin} onClick={()=>{setSpin(x=>!x);setAngle(null);}}>Rotate 360°</button>
   <button type="button" onClick={()=>{setSpin(false);setAngle(0);}}>Front</button>
   <button type="button" onClick={()=>{setSpin(false);setAngle(90);}}>Side</button>
   <button type="button" onClick={()=>{setSpin(false);setAngle(180);}}>Back</button>
  </div>:null}
 </div>;
}
