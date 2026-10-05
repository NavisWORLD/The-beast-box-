'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import CosmicCompanion3D,{type CreatureLook} from '@/components/cosmic-companion-3d';
import {useCompanion} from '@/components/companion-provider';
import styles from './turntable.module.css';

const ANGLES=[0,90,180,270] as const;
export default function CreatureTurntable(){
 const {profile}=useCompanion();
 const [look,setLook]=useState<CreatureLook>(profile?.baseLook??'nebula');
 const [spin,setSpin]=useState(true),[angle,setAngle]=useState<number>(0);
 const [showProcess,setShowProcess]=useState(false);
 useEffect(()=>{if(profile)setLook(profile.baseLook);},[profile?.id,profile?.baseLook]);
 return <main className={styles.page}>
  <header className={styles.header}><Link href="/beast-cage">← BEAST CAGE</Link><span>CORY DAVIS / NAVISWORLD</span><Link href="/beast-cage/talk">TALK TO THE BEAST ↗</Link></header>
  <section className={styles.intro}>
   <span>DEV DAY SIDE QUEST // ORIGINAL PROCEDURAL MESH</span>
   <h1>Meet {profile?.name||'the Beast'} <em>in 3D.</em></h1>
   <p>The active browser Beast now drives this real Three.js rig: its saved hue, glow, fin pattern, halo pattern and constellation seed carry into the mesh instead of falling back to one generic creature.</p>
  </section>
  <div className={styles.stage} data-stage="real-3d-turntable" data-view-angle={spin?'spinning':angle} aria-label="Actual rotating Three.js cosmic creature">
    <span className={styles.star} aria-hidden="true">✧</span>
    <CosmicCompanion3D profile={profile} look={look} state="idle" turntable={spin} turntableAngle={spin?null:angle} quality="auto" className={styles.model} label={spin?'Real 3D rotating '+(profile?.name||'cosmic companion'):'Real 3D '+(profile?.name||'companion')+' at '+angle+' degrees'}/>
    <div className={styles.stageLabel}>{spin?'LIVE GEOMETRY • FULL 360° ROTATION':'LIVE GEOMETRY • '+angle+'° VIEW'}</div>
  </div>
  <section className={styles.controls} aria-label="3D turntable camera controls">
    <div className={styles.buttons}>
      <button className={spin?styles.active:''} aria-pressed={spin} onClick={()=>setSpin(true)}>↻ Rotate 360°</button>
      {ANGLES.map(a=><button key={a} className={!spin&&angle===a?styles.active:''} aria-pressed={!spin&&angle===a} onClick={()=>{setAngle(a);setSpin(false)}}>{a}° {a===0?'front':a===90?'side':a===180?'back':'side'}</button>)}
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
    <p className={styles.note}>Visual companion, not model consciousness or live neuronal activity. No owner credentials, private memory or synthetic model replies appear in this public turntable.</p>
  </section>
 </main>;
}