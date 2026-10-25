'use client';
import {WORLD_SCENE_BG} from '@/lib/world-scene';
import {useActiveBeastName} from '@/components/use-active-beast-name';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import JourneyLinks from '@/components/journey-links';
import CosmicCompanion3D,{type CreatureLook,type CreatureState} from '@/components/cosmic-companion-3d';
import dynamic from 'next/dynamic';
import type {ZerefMood} from '@/components/zeref-glb-3d';
const ZerefGlb3D=dynamic(()=>import('@/components/zeref-glb-3d'),{ssr:false});
import FamilyExplain from '@/components/family-explain';
import {useCompanion} from '@/components/companion-provider';
import {MOONWRAITH_DISPLAY_ID,SAVED_ZEREF_ID,dimensionalAttribution} from '@/lib/creature-dimensional.mjs';
import {lookSubjectLabels} from '@/lib/look-closer-subjects.mjs';
import LOOK_LABELS from '@/lib/look-closer-labels.json';
import {ZEREF_RECORDED_SOURCE} from '@/lib/zeref/zeref-mind.mjs';
import heartSound from '../../../public/spark/ibm-zeref-heart-sound-20261010.json';
import styles from './turntable.module.css';

const ANGLES=[0,90,180,270] as const;
const POSES:CreatureState[]=['idle','listening','observing','sleeping','celebrating'];
type Subject='workshop'|'moonwraith'|'dragonling';
const MOODS:ZerefMood[]=['calm','happy','curious','scared','sleepy','angry','walk'];
const heartRun=heartSound.runs[0];
export default function CreatureTurntable(){
 const {profile}=useCompanion();const activeName=useActiveBeastName();
 const [look,setLook]=useState<CreatureLook>(profile?.baseLook??'nebula');
 const [spin,setSpin]=useState(true),[angle,setAngle]=useState<number>(0);
 const [showProcess,setShowProcess]=useState(false);
 const [subject,setSubject]=useState<Subject>('workshop');
 useEffect(()=>{try{if(new URLSearchParams(location.search).get('with')==='zeref')setSubject('moonwraith');}catch{}},[]);
 const [pose,setPose]=useState<CreatureState>('idle');
 const [speaking,setSpeaking]=useState(false);
 useEffect(()=>{if(profile)setLook(profile.baseLook);},[profile?.id,profile?.baseLook]);
 // Preview flag: ?glb=1 shows the sculpted, rigged Zeref GLB (CST spring bones) while it is reviewed.
 const [glb,setGlb]=useState(false),[mood,setMood]=useState<ZerefMood>('calm');
 useEffect(()=>{setGlb(new URLSearchParams(window.location.search).get('glb')==='1');},[]);
 const dimensionalId=subject==='moonwraith'?MOONWRAITH_DISPLAY_ID:subject==='dragonling'?SAVED_ZEREF_ID:null;
 const attribution=dimensionalId?dimensionalAttribution(subject==='moonwraith'?'moonwraith-artistic':'dragonling-artistic'):null;
 const LB=lookSubjectLabels(subject,{activeName:activeName||'',profileName:profile?.name||"",labels:LOOK_LABELS}),LBm=lookSubjectLabels('moonwraith',{labels:LOOK_LABELS}),LBd=lookSubjectLabels('dragonling',{labels:LOOK_LABELS}),LBw=lookSubjectLabels('workshop',{activeName:activeName||'',profileName:profile?.name||"",labels:LOOK_LABELS});
 const explain=subject==='moonwraith'?{
  id:MOONWRAITH_DISPLAY_ID,name:LB.explainName,nextAction:'talk' as const,
  genome:{quantum:{source_class:'RECORDED_IBM_HARDWARE',backend:ZEREF_RECORDED_SOURCE.backend,job_id:ZEREF_RECORDED_SOURCE.job_id}},
  behavior:{lastAction:'idle',energy:90,curiosity:70},
 }:{
  id:SAVED_ZEREF_ID,name:LB.explainName,nextAction:'play' as const,
  genome:{quantum:{source_class:heartSound.source_class,backend:heartRun.b,job_id:heartRun.j}},
  behavior:{lastAction:'idle',energy:63,curiosity:52},
 };
 return <main className={styles.page}>
  <header className={styles.header}><Link href="/beast-cage">← BEAST CAGE</Link><span>CORY DAVIS / NAVISWORLD</span><Link href="/beast-cage/talk">TALK TO THE BEAST ↗</Link></header>
  <div className="room-strip"><JourneyLinks current="cage" label="Beast Box rooms"/></div>
  <section className={styles.intro}>
   <span>LOOK CLOSER // 360° VIEW</span>
   <h1>Look Closer at {LB.headingName} <em>in 3D.</em></h1>
   <p>{LB.caption?LB.caption:'The active browser Beast drives the original procedural Three.js rig: saved hue, glow, fin pattern, halo pattern and constellation seed.'}</p>
  </section>
  {/* Cosmo's tap-to-inspect art (select ring, pedestal, info card) mounts here: data-look-closer-hook */}
  <div className={styles.stage} style={{background:WORLD_SCENE_BG,border:0,borderRadius:0,boxShadow:'none'}} data-look-closer-hook data-stage="real-3d-turntable" data-subject={subject} data-view-angle={spin?'spinning':angle} aria-label="Actual rotating Three.js creature">
    <span className={styles.star} aria-hidden="true">✧</span>
    {/* Cosmo's Look Closer pedestal set (lookcloser v1): contact shadow, mossy stone pedestal, animated select ring */}
    <div aria-hidden="true" data-look-pedestal className={styles.pedestal}><i className={styles.pedShadow}/><i className={styles.pedStone}/><i className={styles.pedRing}/></div>
    {glb?<ZerefGlb3D spin={spin} angle={angle} mood={mood}/>:<><CosmicCompanion3D profile={subject==='workshop'?profile:null} dimensionalId={dimensionalId} look={look} state={pose} speaking={speaking&&pose==='listening'} turntable={spin} turntableAngle={spin?null:angle} quality="auto" className={styles.model} label={(LB.caption?LB.caption:'Real 3D '+LB.stageName)+(spin?' · rotating':' · '+angle+' degrees')}/></>}
    <div className={styles.stageLabel}>{spin?'LIVE GEOMETRY • FULL 360° ROTATION':'LIVE GEOMETRY • '+angle+'° VIEW'}</div>
  </div>
  <section className={styles.controls} aria-label="3D turntable camera controls">
    <div className={styles.buttons} role="group" aria-label="Choose which creature is on the turntable">
      <button type="button" className={subject==='moonwraith'?styles.active:''} aria-pressed={subject==='moonwraith'} onClick={()=>setSubject('moonwraith')}>{LBm.button}</button>
      <button type="button" className={subject==='dragonling'?styles.active:''} aria-pressed={subject==='dragonling'} onClick={()=>setSubject('dragonling')}>{LBd.button}</button>
      <button type="button" className={subject==='workshop'?styles.active:''} aria-pressed={subject==='workshop'} onClick={()=>setSubject('workshop')}>{LBw.button}</button>
    </div>
    <div className={styles.buttons}>
      <button className={spin?styles.active:''} aria-pressed={spin} onClick={()=>setSpin(true)}>↻ Rotate 360°</button>
      {ANGLES.map(a=><button key={a} className={!spin&&angle===a?styles.active:''} aria-pressed={!spin&&angle===a} onClick={()=>{setAngle(a);setSpin(false)}}>{a}° {a===0?'front':a===90?'side':a===180?'back':'side'}</button>)}
    </div>
    {glb?<div className={styles.buttons} role="group" aria-label="Zeref GLB mood (drives CST motion + expressions)">
      {MOODS.map(m=><button key={m} type="button" className={mood===m?styles.active:''} aria-pressed={mood===m} onClick={()=>setMood(m)}>{m}</button>)}
    </div>:null}
    <div className={styles.buttons} role="group" aria-label="Animation pose">
      {POSES.map(item=><button key={item} type="button" className={pose===item?styles.active:''} aria-pressed={pose===item} onClick={()=>setPose(item)}>{item}</button>)}
      <button type="button" className={speaking?styles.active:''} aria-pressed={speaking} onClick={()=>setSpeaking(value=>!value)}>Speaking</button>
    </div>
    <div className={styles.looks} aria-label="Choose palette">
      <button onClick={()=>setLook('nebula')} aria-pressed={look==='nebula'}>NEBULA</button>
      <button onClick={()=>setLook('aurora')} aria-pressed={look==='aurora'}>AURORA</button>
      <button onClick={()=>setLook('starlight')} aria-pressed={look==='starlight'}>STARLIGHT</button>
    </div>
  </section>
  <section className={styles.process}>
    <h2>The actual creation process</h2>
    <p>Original character concept → source-editable vector reference → Three.js procedural geometry → textured galaxy material, 11 extruded fins, 3D star eyes and golden orbital star → browser-tested rotating model.</p>
    <button type="button" onClick={()=>setShowProcess(v=>!v)} aria-expanded={showProcess}>{showProcess?'Hide':'Show'} source prompt / process</button>
    {showProcess?<div className={styles.source}>
      <p><strong>Creation brief:</strong> Build an original, fully rotatable, lightweight WebGL cosmic companion from the supplied galaxy-creature reference. Preserve recognizable shape, translucent/iridescent fins, expressive shining eyes and orbiting gold star. Generate geometry and texture procedurally; avoid a 2D sprite pretending to rotate. Use real lighting, deterministic decorative stars, explicit reduced-motion fallback and no sensor permissions.</p>
      <p><strong>Implementation:</strong> Three.js SphereGeometry, ExtrudeGeometry, MeshPhysicalMaterial, deterministic CanvasTexture, lights, torus halo and requestAnimationFrame. Four camera-facing yaw presets and a continuous 360-degree model turntable reuse exactly the same source mesh as the Beast Cage interface.</p>
      <a href="https://github.com/NavisWORLD/The-beast-box-/blob/feature/beast-cage-live-sidequest-20261001/apps/beastbox-cloud/components/cosmic-companion-3d.tsx" target="_blank" rel="noreferrer">View the real model source ↗</a>
    </div>:null}
    <p className={styles.note}>Visual companion, not model consciousness or live neuronal activity. No owner credentials, private memory or synthetic model replies appear in this public turntable. The Moonwraith and saved-Zeref models are artistic geometry. They do not share a body.</p>
  </section>
  {subject==='workshop'?null:<FamilyExplain input={explain}/>}
 </main>;
}