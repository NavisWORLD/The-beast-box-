'use client';
import {useState} from 'react';
import CosmicCompanion3D from './cosmic-companion-3d';
import {useCompanion} from './companion-provider';
/** Original real geometric hero, sharing the selected PUBLIC game genome. */
export default function HomepageCreature(){
 const {profile}=useCompanion();
 const [spin,setSpin]=useState(false),[angle,setAngle]=useState<number|null>(null);
 return <div className="cosmos-home-hero" aria-label="Interactive cosmic companion observatory">
  <CosmicCompanion3D quality="low" profile={profile}
   look={profile?.baseLook??'nebula'}
   label="Genuine procedural 3D cosmic creature with a golden orbiting star"
   turntable={spin} turntableAngle={angle}/>
  <div className="cosmos-home-controls" aria-label="Real 3D rotation controls">
   <button type="button" aria-pressed={spin} onClick={()=>{setSpin(x=>!x);setAngle(null);}}>Rotate 360°</button>
   <button type="button" onClick={()=>{setSpin(false);setAngle(0);}}>Front</button>
   <button type="button" onClick={()=>{setSpin(false);setAngle(90);}}>Side</button>
   <button type="button" onClick={()=>{setSpin(false);setAngle(180);}}>Back</button>
  </div>
 </div>;
}
