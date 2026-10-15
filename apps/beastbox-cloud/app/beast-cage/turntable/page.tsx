'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import JourneyLinks from '@/components/journey-links';
import CosmicCompanion3D,{type CreatureLook,type CreatureState} from '@/components/cosmic-companion-3d';
import Creature3DCanvas from '@/components/creature-3d-canvas';
import FamilyExplain from '@/components/family-explain';
import {useCompanion} from '@/components/companion-provider';
import {MOONWRAITH_DISPLAY_ID,SAVED_ZEREF_ID,dimensionalAttribution} from '@/lib/creature-dimensional.mjs';
import {CATALOG_BODIES,catalogRowToGenome} from '@/lib/creature-catalog-3d.mjs';
import {deriveEmotions} from '@/lib/companion/emotion.mjs';
import {ZEREF_RECORDED_SOURCE} from '@/lib/zeref/zeref-mind.mjs';
import heartSound from '../../../public/spark/ibm-zeref-heart-sound-20261010.json';
import catalogIndex from '../../../public/spark/catalog-index.json';
import styles from './turntable.module.css';

const ANGLES=[0,90,180,270] as const;
const POSES:CreatureState[]=['idle','listening','observing','sleeping','celebrating'];
type Subject='workshop'|'moonwraith'|'dragonling'|'catalog';
const heartRun=heartSound.runs[0];
const bodyCol=(catalogIndex as any).traits.indexOf('body');
export default function CreatureTurntable(){
 const {profile}=useCompanion();
 const [look,setLook]=useState<CreatureLook>(profile?.baseLook??'nebula');
 const [spin,setSpin]=useState(true),[angle,setAngle]=useState<number>(0);
 const [showProcess,setShowProcess]=useState(false);
 const [subject,setSubject]=useState<Subject>('workshop');
 const [catalogBody,setCatalogBody]=useState<string>('fox');
 const [pose,setPose]=useState<CreatureState>('idle');
 const [speaking,setSpeaking]=useState(false);
 useEffect(()=>{if(profile)setLook(profile.baseLook);},[profile?.id,profile?.baseLook]);
 const dimensionalId=subject==='moonwraith'?MOONWRAITH_DISPLAY_ID:subject==='dragonling'?SAVED_ZEREF_ID:null;
 const attribution=dimensionalId?dimensionalAttribution(subject==='moonwraith'?'moonwraith-artistic':'dragonling-artistic'):null;
 const catalogGenome=(()=>{
  const bIdx=(catalogIndex as any).values.body.indexOf(catalogBody);
  const row=(catalogIndex as any).rows.find((r:any[])=>r[4+bodyCol]===bIdx)||(catalogIndex as any).rows[0];
  return catalogRowToGenome(catalogIndex,row);
 })();
 const catalogEmotion=deriveEmotions({genome:catalogGenome});
 const explain=subject==='moonwraith'?{
  id:MOONWRAITH_DISPLAY_ID,name:'Zeref',nextAction:'talk' as const,
  genome:{quantum:{source_class:'RECORDED_IBM_HARDWARE',backend:ZEREF_RECORDED_SOURCE.backend,job_id:ZEREF_RECORDED_SOURCE.job_id}},
  behavior:{lastAction:'idle',energy:90,curiosity:70},
 }:{
  id:SAVED_ZEREF_ID,name:'Zeref',nextAction:'play' as const,
  genome:{quantum:{source_class:heartSound.source_class,backend:heartRun.b,job_id:heartRun.j}},
  behavior:{lastAction:'idle',energy:63,curiosity:52},
 };
 return <main className={styles.page}>
  <header className={styles.header}><Link href="/beast-cage">← BEAST CAGE</Link><span>CORY DAVIS / NAVISWORLD</span><Link href="/beast-cage/talk">TALK TO THE BEAST ↗</Link></header>
  <div className="room-strip"><JourneyLinks current="cage" label="Beast Box rooms"/></div>
  <section className={styles.intro}>
   <span>DEV DAY SIDE QUEST // ORIGINAL PROCEDURAL MESH</span>
   <h1>Meet {subject==='workshop'?(profile?.name||'the Beast'):subject==='catalog'?(catalogGenome?.names?.[1]||catalogBody):'Zeref'} <em>in 3D.</em></h1>
   <p>{attribution?attribution.label:subject==='catalog'?`Faithful 3D catalogue creature (${catalogBody} · ${catalogGenome?.island||'Eridoria Prime'} · ${catalogGenome?.element||'verdant'} fluid particles · Verlet tail/ears/wings).`:'The active browser Beast drives the original procedural Three.js rig: saved hue, glow, fin pattern, halo pattern and constellation seed.'}</p>
  </section>
  <div className={styles.stage} data-stage="real-3d-turntable" data-subject={subject} data-catalog-body={subject==='catalog'?catalogBody:undefined} data-view-angle={spin?'spinning':angle} aria-label="Actual rotating Three.js creature">
    <span className={styles.star} aria-hidden="true">✧</span>
    {subject==='catalog'?<Creature3DCanvas genome={catalogGenome} stage={2} emotion={catalogEmotion} turntable={spin} turntableAngle={spin?null:angle} speaking={speaking} className={styles.model} label={`3D ${catalogBody} (${catalogGenome?.names?.[1]||catalogBody})`}/>:<CosmicCompanion3D profile={subject==='workshop'?profile:null} dimensionalId={dimensionalId} look={look} state={pose} speaking={speaking&&pose==='listening'} turntable={spin} turntableAngle={spin?null:angle} quality="auto" className={styles.model} label={(attribution?attribution.label:'Real 3D '+(profile?.name||'companion'))+(spin?' · rotating':' · '+angle+' degrees')}/>}
    <div className={styles.stageLabel}>{spin?'LIVE GEOMETRY • FULL 360° ROTATION':'LIVE GEOMETRY • '+angle+'° VIEW'}</div>
  </div>
  <section className={styles.controls} aria-label="3D turntable camera controls">
    <div className={styles.buttons} role="group" aria-label="Choose which creature is on the turntable">
      <button type="button" className={subject==='moonwraith'?styles.active:''} aria-pressed={subject==='moonwraith'} onClick={()=>setSubject('moonwraith')}>Moonwraith 3D</button>
      <button type="button" className={subject==='dragonling'?styles.active:''} aria-pressed={subject==='dragonling'} onClick={()=>setSubject('dragonling')}>Saved Zeref 3D</button>
      <button type="button" className={subject==='catalog'?styles.active:''} aria-pressed={subject==='catalog'} onClick={()=>setSubject('catalog')}>Catalogue 3D (11 bodies)</button>
      <button type="button" className={subject==='workshop'?styles.active:''} aria-pressed={subject==='workshop'} onClick={()=>setSubject('workshop')}>Workshop mesh</button>
    </div>
    {subject==='catalog'?<div className={styles.buttons} role="group" aria-label="Choose catalogue creature body plan">
      {CATALOG_BODIES.map(b=><button key={b} type="button" data-catalog-body-btn={b} className={catalogBody===b?styles.active:''} aria-pressed={catalogBody===b} onClick={()=>setCatalogBody(b)}>{b}</button>)}
    </div>:null}
    <div className={styles.buttons}>
      <button className={spin?styles.active:''} aria-pressed={spin} onClick={()=>setSpin(true)}>↻ Rotate 360°</button>
      {ANGLES.map(a=><button key={a} className={!spin&&angle===a?styles.active:''} aria-pressed={!spin&&angle===a} onClick={()=>{setAngle(a);setSpin(false)}}>{a}° {a===0?'front':a===90?'side':a===180?'back':'side'}</button>)}
    </div>
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
    <p className={styles.note}>Visual companion, not model consciousness or live neuronal activity. No owner credentials, private memory or synthetic model replies appear in this public turntable. The Moonwraith and saved-Zeref meshes are artistic geometry bound to bb-7f9c2a03 and bb-deada969. They do not share a body.</p>
  </section>
  {subject==='workshop'||subject==='catalog'?null:<FamilyExplain input={explain}/>}
 </main>;
}
