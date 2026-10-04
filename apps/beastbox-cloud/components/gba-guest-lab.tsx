'use client';
import {useEffect,useRef,useState} from 'react';
import Link from 'next/link';
import {ArrowLeft,ArrowRight,Download,ShieldCheck,Gamepad2,Sparkles} from 'lucide-react';
import SparkBeastCompanion from './spark-beast-companion';
import {makeGbaZip,spritePreview,type Look,type Mood} from '../lib/gba-companion';
import styles from './gba-guest-lab.module.css';
import GenesisForge from './genesis-forge';
import {type CreatureProfile,type AmbientAction} from '../lib/creature-profile';
import {profilePreview} from '../lib/gba-companion';
import {createCreatureGlb} from '../lib/creature-glb';
import {useCompanion} from './companion-provider';

const LOOKS:{value:Look;name:string}[]=[{value:'nebula',name:'Nebby'},{value:'aurora',name:'Lumen'},{value:'starlight',name:'Orion'}];
const STATES:{value:Mood;name:string;description:string}[]=[
 {value:'idle',name:'Explore',description:'Float through a little imagined universe.'},
 {value:'listening',name:'Listen',description:'Illustrative listening pose; no microphone requested.'},
 {value:'thinking',name:'Process',description:'Illustrative signal activity; no model call.'},
 {value:'celebrating',name:'Celebrate',description:'A little victory dance!'}
];
const STORAGE='beastbox-cage-appearance-v1';
export default function GuestGbaLab(){
 const [look,setLook]=useState<Look>('nebula'),[mood,setMood]=useState<Mood>('idle');
 const [busy,setBusy]=useState(false),[modelBusy,setModelBusy]=useState(false),[error,setError]=useState(''),[done,setDone]=useState(false);
 const [creature,setCreature]=useState<CreatureProfile|null>(null),[ambient,setAmbient]=useState<AmbientAction>('hover');
 const {profile:sharedProfile,selectProfile,clearProfile}=useCompanion();
 useEffect(()=>{if(sharedProfile){setCreature(sharedProfile);setLook(sharedProfile.baseLook);}},[sharedProfile]);
 const preview=useRef<HTMLCanvasElement>(null);
 useEffect(()=>{
  try{
   const previous=window.localStorage.getItem(STORAGE);
   if(previous==='nebula'||previous==='aurora'||previous==='starlight')setLook(previous);
  }catch{/* optional visual choice only */}
 },[]);
 useEffect(()=>{
  if(preview.current){if(creature)profilePreview(creature,mood,preview.current);else spritePreview(look,mood,preview.current);}
 },[look,mood,creature]);
 function chooseLook(next:Look){
  setLook(next);setCreature(null);clearProfile();setDone(false);
  try{
   window.localStorage.setItem(STORAGE,next);
   window.dispatchEvent(new Event('beastbox:cage-look-changed'));
  }catch{/* guest still works without storage */}
 }
 async function exportModel(){
  if(modelBusy)return;
  setModelBusy(true);setError('');
  try{
   const glb=await createCreatureGlb(creature,look);
   const url=URL.createObjectURL(new Blob([Uint8Array.from(glb)],{type:'model/gltf-binary'}));
   const anchor=document.createElement('a');
   anchor.href=url;anchor.download='beast-cage-'+(creature?creature.id:look)+'-original-3d.glb';
   document.body.appendChild(anchor);anchor.click();anchor.remove();
   window.setTimeout(()=>URL.revokeObjectURL(url),8000);
  }catch(e){setError(e instanceof Error?e.message:'The original 3D source could not be exported.');}
  finally{setModelBusy(false);}
 }
 async function exportPack(){
  if(busy)return;
  setBusy(true);setError('');setDone(false);
  try{
   // Deliberately NULL: public guests do not read owner routes or memory.
   const zip=creature?await makeGbaZip(look,null,creature):await makeGbaZip(look,null);
   const blob=new Blob([Uint8Array.from(zip)],{type:'application/zip'});
   const url=URL.createObjectURL(blob),anchor=document.createElement('a');
   anchor.href=url;anchor.download='beast-cage-'+(creature?creature.id:look)+'-gba-module.zip';
   document.body.appendChild(anchor);anchor.click();anchor.remove();
   window.setTimeout(()=>URL.revokeObjectURL(url),5000);
   setDone(true);
  }catch(e){setError(e instanceof Error?e.message:'Companion pack was not available.');}
  finally{setBusy(false);}
 }
 const label=STATES.find(s=>s.value===mood)??STATES[0];
 return <main className={styles.page}>
  <header className={styles.header}>
   <Link href="/beast-cage"><ArrowLeft size={16}/> Beast Cage</Link>
   <span>THE LITTLE BEAST // GAME LAB</span>
   <Link href="/beast-cage/talk">Real guest chat <ArrowRight size={16}/></Link>
   <Link href="/beast-cage/play">Adventure <ArrowRight size={16}/></Link>
  </header>
  <section className={styles.intro}>
   <span><Sparkles size={16}/> FREE PUBLIC PLAYGROUND • ZERO OWNER PERMISSIONS</span>
   <h1>Catch a star.<br/><em>Take it into your game.</em></h1>
   <p>Meet the same Spark Beast used by Customize, care and the owner dock. Preview its recorded-seed sprite, movement, eyes, stages and local generated voice, then carry that portable identity into Lost COSMOS or export a GBA-ready module. This playground is game software, not a consciousness or sensor claim.</p>
  </section>
  <GenesisForge value={creature} onChange={next=>{setCreature(next);selectProfile(next);setLook(next.baseLook);setDone(false);}} onAmbient={setAmbient}/>
  <div className={styles.grid}>
   <section className={styles.orbit} aria-label="Animated companion test environment">
    <span className={styles.constellation} aria-hidden="true">✧ ✦ ･｡ ☆ ﾟ</span>
    <div className={styles.model} data-ambient-behavior={ambient}><SparkBeastCompanion profile={creature} fallbackLook={look}
      state={mood} controls label={'Spark Beast game companion: '+mood}/></div>
    <div className={styles.status}><span aria-hidden="true">✧</span> {label.description}</div>
    <div className={styles.actions} role="group" aria-label="Explore illustrative companion animation states">
     {STATES.map(item=><button type="button" key={item.value} className={mood===item.value?styles.active:''}
       aria-pressed={mood===item.value} onClick={()=>setMood(item.value)}>{item.name}</button>)}
    </div>
    <small>Visual-only game sandbox. No camera, microphone or memory access.</small>
   </section>
   <section className={styles.panel} aria-label="Configure and export game companion">
    <span className={styles.eyebrow}>01 / CHOOSE YOUR COMPANION</span>
    <h2>Build your little monster.</h2>
    <p>Choose its appearance. This option is saved locally for this browser only.</p>
    <div className={styles.looks}>{LOOKS.map(item=><button key={item.value} type="button"
      aria-pressed={look===item.value} className={look===item.value?styles.chosen:''}
      onClick={()=>chooseLook(item.value)}>{item.name} <span>{look===item.value?'✦':'◇'}</span></button>)}</div>
    <div className={styles.export}>
     <span className={styles.eyebrow}>02 / RETRO GAME PORTAL</span>\n     <p><strong>The playable target keeps the current Lost COSMOS PR #31 / V11.2 bridge.</strong> The same Beast identity flows into its single cage and persistent player. Beast Box keeps the adventure/care experience, but does not embed the SIM EARTH planetary world.</p>
     <div className={styles.pixelArt}>
      <canvas ref={preview} role="img" aria-label={'Actual 64 by 64 pixel-art '+look+' sprite preview in '+mood+' state'}/>
      <div><Gamepad2 size={23}/><strong>GBA importable module</strong>
       <small>Four authentic pixel sprite frames • 4bpp tiles • C99 module • 60-byte legacy state {creature?'• new 64-byte GBA game-stat profile':''}</small></div>
     </div>
     <p>The downloadable bundle contains editable art, your chosen palette,
      code and a clearly labeled visual-only companion profile. Generated characters also include deterministic fictional game stats. Guest exports
      contain <strong>no private memories, measured CNS values or neural weights.</strong></p>
     <button type="button" disabled={busy} onClick={()=>void exportPack()} className={styles.download}>
      <Download size={18}/> {busy?'Building your game pack…':'Download my GBA companion (.zip)'}
     </button>
     <button type="button" className={styles.modelDownload} disabled={modelBusy}
       onClick={()=>void exportModel()} aria-label="Download original animated 3D model GLB">
       {modelBusy?'Exporting real 3D geometry…':'Download original 3D model (.glb)'}
     </button>
     {error?<p role="alert" className={styles.error}>{error}</p>:null}
     {done?<p role="status" className={styles.success}>Your portable game pack was generated in this browser.</p>:null}
     <p className={styles.disclaimer}><ShieldCheck size={16}/> To include actual COSMOS numeric
      synaptic signals instead, authenticate in the owner workstation and explicitly export
      a validated checkpoint from Synapse Trace. Guests never receive that data.</p>
    </div>
   </section>
  </div>
  <section className={styles.next}>
   <strong>Want to hear it talk for real?</strong>
   <p>The free visual sandbox works even when the model host is offline.
    The separate guest chat calls the existing limited, stateless RAWRPHØS route
    and shows errors rather than invented responses.</p>
   <Link href="/beast-cage/talk">Try real RAWRPHØS guest chat <ArrowRight size={16}/></Link>
   <Link href="/beast-cage/turntable">Spin the actual 360° 3D model ↻</Link>
  </section>
  <footer className={styles.footer}>CORY DAVIS // NAVISWORLD • MODEL ≠ MEMORY ≠ AUTHORITY • GBA ART ≠ LLM</footer>
 </main>;
}
