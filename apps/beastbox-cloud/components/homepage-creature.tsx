'use client';
import {useState} from 'react';
import Link from 'next/link';
import CosmicCompanion3D from './cosmic-companion-3d';
import {useCompanion} from './companion-provider';
import {useBeastSession} from './beast-session';
import {shownName} from '../lib/companion/session.mjs';
import {visualStateFromBeast} from '../lib/companion/creature-visual-state.mjs';
import styles from './homepage-creature.module.css';

/**
 * The workshop guide is a preview, not a second QBEAST. Once a player has a
 * verified QBEAST the actual saved genome/ID/mood replace that preview.
 */
export default function HomepageCreature(){
 const {profile}=useCompanion();
 const {session}=useBeastSession();
 const savedBeast=session?.beast?.qbeast?.profile?.id?session.beast:null;
 const genome=savedBeast?.genome?.seed?savedBeast.genome:null;
 const [spin,setSpin]=useState(false),[angle,setAngle]=useState<number|null>(null);
 const [waved,setWaved]=useState(false);
 const activeName=savedBeast?shownName(savedBeast):'';
 const waveMood=waved?'observing':'idle';
 return <div className="cosmos-home-hero" aria-label="Interactive cosmic companion observatory">
  <CosmicCompanion3D quality="low" profile={profile}
   preferSprite={Boolean(genome)} spriteGenome={genome}
   spriteStage={savedBeast?.nativeStage||savedBeast?.stage||1}
   spriteName={activeName}
   state={genome?visualStateFromBeast(savedBeast):waveMood}
   spriteId={savedBeast?.qbeast?.profile?.id||''}
   look={profile?.baseLook??'nebula'}
   label={genome?activeName+' · QBEAST '+savedBeast.qbeast.profile.id:'Original procedural cosmic dragon workshop guide'}
   turntable={spin} turntableAngle={angle}/>
  <div className={styles.bubble} role="status" aria-live="polite">
   {genome?<><strong>✦ YOUR BEAST IS HERE</strong>
    <p>{activeName} · the same QBEAST you saved on this device.</p>
    <small>QBEAST {savedBeast.qbeast.profile.id}</small>
    <p className={styles.stats}>XP {Number(savedBeast.xp)||0} · Bond {Number(savedBeast.bond)||0} · Energy {Number(savedBeast.energy)||0}</p>
    <Link href="/beast-cage#habitat">Visit {activeName} →</Link>
   </>:<><strong>✦ HELLO FROM THE WORKSHOP</strong>
    <p>{waved?'Oh! A visitor waved. Want to meet a creature of your own?':'That little dragon noticed you. Curious what lives in here?'}</p>
    <div className={styles.actions}>
     <button type="button" aria-pressed={waved} onClick={()=>setWaved(value=>!value)}>{waved?'Wave again ✦':'Wave hello ✦'}</button>
     <Link href="/spark/index.html">Meet your Beast →</Link>
    </div>
    <small>Guide reaction is visual only. Your own Beast begins when you create one.</small>
   </>}
  </div>
  {!genome?<div className="cosmos-home-controls" aria-label="Real 3D rotation controls">
   <button type="button" aria-pressed={spin} onClick={()=>{setSpin(x=>!x);setAngle(null);}}>Rotate 360°</button>
   <button type="button" onClick={()=>{setSpin(false);setAngle(0);}}>Front</button>
   <button type="button" onClick={()=>{setSpin(false);setAngle(90);}}>Side</button>
   <button type="button" onClick={()=>{setSpin(false);setAngle(180);}}>Back</button>
  </div>:null}
 </div>;
}
