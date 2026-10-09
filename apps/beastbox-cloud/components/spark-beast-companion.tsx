'use client';
import {useUniverseMotion} from './use-universe-motion';
import {useCallback,useEffect,useMemo,useRef,useState} from 'react';
import {getBeastAudio} from '../lib/companion/beast-audio-engine.mjs';
import {Volume2,VolumeX} from 'lucide-react';
import {generateCreature,type BaseLook,type CreatureProfile} from '../lib/creature-profile';
import {blit,renderBeast,SPRITE} from '../public/spark/draw.mjs';
import {buildGenome} from '../public/spark/genome.mjs';
import {Voice} from '../public/spark/voice.mjs';
import styles from './spark-beast-companion.module.css';
import {useBeastSession} from './beast-session';
import {loadSparkRuns} from '../public/spark/runs.mjs';

type VisualState='idle'|'listening'|'thinking'|'remembering'|'observing'|'sleeping'|'celebrating'|'halted';
type Run={
 key:string;backend:string;job_id:string;pub_index:number;num_bits:number;
 shots:number;counts:Record<string,number>;counts_sha256:string;
};
export type Genome={
 seed:string;
 names:Record<number,string>;island:string;temperament:string;element:string;body:string;
 pose:string;ears:string;wings:string;tail:string;quantum:{top_state:string};
 behavior:{
  gait:string;tempo_hz:number;amplitude_px:number;blink_mean_s:number;
  sensitivity:Record<string,number>;thresholds:Record<string,number>;
 };
 voice:Record<string,unknown>;
};
type Props={
 profile?:CreatureProfile|null;
 fallbackLook?:BaseLook;
 state?:VisualState;
 paused?:boolean;
 intensity?:number;
 compact?:boolean;
 controls?:boolean;
 audioChannel?:string;
 className?:string;
 label?:string;
 seedRunKey?:string;
 seedTraits?:{focus:number;calm:number;spark:number};
 /** Optional: receive the built Spark genome (e.g. for the seeded habitat attack moves). */
 onGenome?:(genome:Genome)=>void;
};

function expand(row:Record<string,unknown>):Run{
 const counts:Record<string,number>={};
 for(const part of String(row.c||'').split(',')){
  if(!part)continue;
  const [k,v]=part.split(':');
  if(k)counts[k]=Number(v)||0;
 }
 return {
  key:String(row.k||''),backend:String(row.b||''),job_id:String(row.j||''),
  pub_index:Number(row.p)||0,num_bits:Number(row.n)||0,shots:Number(row.s)||0,
  counts,counts_sha256:String(row.h||'')
 };
}
function clamp(n:number){return Math.max(0,Math.min(100,Math.round(n)));}
function traits(profile:CreatureProfile){
 const s=profile.game.stats,t=profile.temperament;
 return {
  focus:clamp((s.signal+s.memory+s.stability)/3),
  calm:clamp((s.stability+s.memory+t.caution)/3),
  spark:clamp((s.energy+s.resonance+t.playfulness)/3)
 };
}
function hash(text:string){
 let out=2166136261;
 for(const byte of new TextEncoder().encode(text)){out^=byte;out=Math.imul(out,16777619);}
 return out>>>0;
}
function moodFor(state:VisualState){
 if(state==='celebrating')return 'spark';
 if(state==='sleeping'||state==='remembering'||state==='halted')return 'calm';
 if(state==='thinking'||state==='observing'||state==='listening')return 'focus';
 return 'neutral';
}
function driveFor(mood:string,intensity:number){
 const base=Math.max(0,Math.min(1.2,intensity||0));
 return {
  focus:mood==='focus'?Math.max(.68,base):base*.2,
  calm:mood==='calm'?Math.max(.68,base):base*.2,
  spark:mood==='spark'?Math.max(.72,base):base*.2
 };
}

export default function SparkBeastCompanion({
 profile,fallbackLook='nebula',state='idle',paused=false,intensity=0,
 compact=false,controls=false,audioChannel,className='',label='Spark Beast companion',
 seedRunKey='',seedTraits,onGenome
}:Props){
 const fallback=useMemo(()=>generateCreature('beastbox-spark-'+fallbackLook,fallbackLook==='aurora'?'aurora':fallbackLook==='starlight'?'starlight':'nebula'),[fallbackLook]);
 const active=profile??fallback;
 const {session}=useBeastSession();
 const sameSpark=session?.beast?.qbeast?.profile?.id===active.id?session.beast:null;
 const canvas=useRef<HTMLCanvasElement>(null),mover=useRef<HTMLDivElement>(null);
 const frame=useRef<number>(0),lastEye=useRef(''),utterance=useRef(0);
 const voiceNodes=useRef(new Map<GainNode,ReturnType<typeof setTimeout>>());
 const [run,setRun]=useState<Run|null>(null),[gen,setGen]=useState<Genome|null>(null);
 const [stage,setStage]=useState<1|2|3>(2),[sound,setSound]=useState(false);
 const [error,setError]=useState('');
 const {reduced}=useUniverseMotion();


 useEffect(()=>{
  let cancelled=false;
  void (async()=>{
   const runs=await loadSparkRuns({includeQvm:Boolean(sameSpark)});
   const chosen=sameSpark?runs.find(item=>item.key===sameSpark.genome.inputs.quantum_run):(runs.find(item=>item.key===seedRunKey)||runs[hash(active.id+'|'+active.seed)%runs.length]);
   if(!chosen)throw new Error('Saved Spark run is unavailable');
   if(!cancelled)setRun(chosen);
  })().catch(err=>{if(!cancelled)setError(err instanceof Error?err.message:'Spark renderer unavailable');});
  return()=>{cancelled=true;};
 },[active.id,active.seed,sameSpark?.seed,seedRunKey]);

 useEffect(()=>{
  if(!run)return;
  try{
   // The JS Spark generator types its optional user id as null; run selection is already domain-separated by active.id above.
   const next=(sameSpark?sameSpark.genome:buildGenome(seedTraits||traits(active),run,null,10)) as unknown as Genome;
   setGen(next);setError('');lastEye.current='';
  }catch(err){setError(err instanceof Error?err.message:'Spark genome could not be built');}
 },[active,run,sameSpark?.genome,seedTraits]);
 useEffect(()=>{if(sameSpark){setStage(sameSpark.nativeStage||1);lastEye.current='';}},[sameSpark?.seed]);

 useEffect(()=>{if(gen&&onGenome)onGenome(gen);},[gen,onGenome]);

 useEffect(()=>{
  if(!gen||!canvas.current)return;
  const ctx=canvas.current.getContext('2d');
  if(!ctx)return;
  const scale=4;
  canvas.current.width=SPRITE*scale;canvas.current.height=SPRITE*scale;
  const start=performance.now();
  let previous=start;
  const behavior=gen.behavior;
  const mood=moodFor(state);
  const loop=(now:number)=>{
   const t=(now-start)/1000,dt=Math.min(.05,(now-previous)/1000||.016);previous=now;
   void dt;
   const blink=Math.max(1.5,Number(behavior.blink_mean_s)||3.5);
   let eye='open';
   if(state==='halted'||state==='sleeping')eye='sleepy';
   else if(mood==='spark')eye='sparkle';
   else if((t%blink)<.12)eye='closed';
   else if(mood==='calm')eye='sleepy';
   if(eye!==lastEye.current){
    blit(ctx,renderBeast(gen,stage,eye),0,0,scale);
    lastEye.current=eye;
   }
   const node=mover.current;
   if(node){
    if(paused||reduced||state==='halted'){
     node.style.transform='translate3d(0,0,0)';
    }else{
     const tempo=Math.max(.2,Number(behavior.tempo_hz)||.7);
     const phase=t*tempo*Math.PI*2;
     const amp=(compact?1.3:2.5)*(Math.max(1,Number(behavior.amplitude_px)||1));
     let x=0,y=0,r=0;
     switch(behavior.gait){
      case 'hop': y=-Math.abs(Math.sin(phase*.5))*amp*1.8;break;
      case 'sway': x=Math.sin(phase)*amp;r=Math.sin(phase)*2;break;
      case 'scuttle': x=Math.sin(phase*1.7)*amp*.9;break;
      case 'float': y=Math.sin(phase*.5)*amp-2;break;
      case 'wobble': x=Math.sin(phase)*amp*.7;r=Math.sin(phase*.7)*3;break;
      case 'pulse': y=Math.sin(phase)*amp*.35;break;
      default:y=-(.5-.5*Math.cos(phase))*amp*.8;
     }
     node.style.transform=`translate3d(${x.toFixed(2)}px,${y.toFixed(2)}px,0) rotate(${r.toFixed(2)}deg)`;
    }
   }
   frame.current=requestAnimationFrame(loop);
  };
  frame.current=requestAnimationFrame(loop);
  return()=>cancelAnimationFrame(frame.current);
 },[gen,stage,state,paused,reduced,compact]);

 const speak=useCallback(async(voiceIntensity=intensity||.55,explicit=false)=>{
  if(!gen)return;
  try{
   const engine=getBeastAudio();
   if(explicit){engine.sparkUnmute();engine.unlock();}
   const output=engine.output();if(!output)return;
   const {ctx,dest}=output;
   if(ctx.state==='suspended'){
    try{await ctx.resume();}catch{return;}
    if(ctx.state!=='running'||engine.getSnapshot().sparkMuted||engine.getSnapshot().hidden)return;
   }
   const mood=moodFor(state);
   const u=Voice.utterance(gen.voice,stage,mood,utterance.current++,driveFor(mood,voiceIntensity));
   const node=ctx.createGain();node.gain.value=.17;node.connect(dest);
   Voice.schedule(ctx,node,ctx.currentTime+.03,gen.voice,u);
   setSound(true);
   const timer=setTimeout(()=>{
    voiceNodes.current.delete(node);
    try{node.disconnect();}catch{}
    if(voiceNodes.current.size===0)setSound(false);
   },Math.max(400,Math.ceil((u.dur||1)*1000)+150));
   voiceNodes.current.set(node,timer);
  }catch(err){setError(err instanceof Error?err.message:'Creature voice unavailable');}
 },[gen,stage,state,intensity]);

 useEffect(()=>{
  const silence=()=>{
   for(const [node,timer] of voiceNodes.current){
    clearTimeout(timer);try{node.disconnect();}catch{}
   }
   voiceNodes.current.clear();setSound(false);
  };
  window.addEventListener('beastbox:spark-mute',silence);
  const visibility=()=>{if(document.hidden)silence();};
  document.addEventListener('visibilitychange',visibility);
  return()=>{window.removeEventListener('beastbox:spark-mute',silence);document.removeEventListener('visibilitychange',visibility);silence();};
 },[]);
 useEffect(()=>{
  if(!audioChannel)return;
  const onChirp=(event:Event)=>{
   if(!(event instanceof CustomEvent))return;
   const detail=event.detail as {channel?:string;intensity?:number}|undefined;
   if(detail?.channel!==audioChannel)return;
   void speak(Number(detail.intensity)||intensity||.55);
  };
  window.addEventListener('beastbox:spark-chirp',onChirp);
  return()=>window.removeEventListener('beastbox:spark-chirp',onChirp);
 },[audioChannel,intensity,speak]);

 const name=sameSpark?.displayName||gen?.names?.[stage]||active.name;
 return <figure className={[styles.root,compact?styles.compact:'',className].filter(Boolean).join(' ')}
   data-spark-beast="true" data-creature-id={active.id} data-cosmetic-hue={active.appearance.hueShift}
   data-state={state} data-stage={stage} aria-label={label}>
  <div className={styles.aura} aria-hidden="true"/>
  <div className={styles.mover} ref={mover}>
   <canvas ref={canvas} className={styles.canvas} aria-label={name+' pixel creature sprite'}/>
  </div>
  {!compact?<figcaption className={styles.meta}>
   <strong>{name}</strong>
   <span>{gen?gen.temperament+' · '+gen.body+' · '+gen.island:'Building Spark genome…'}</span>
   {run?<small>RECORDED QUANTUM SEED · {run.backend} · {run.num_bits}-bit · {run.counts_sha256.slice(0,10)}…</small>:null}
   <small>Recorded counts seed the game art. No live quantum link, awareness, or sensor authority.</small>
  </figcaption>:null}
  {controls&&!compact?<div className={styles.controls}>
   <div className={styles.stages} role="group" aria-label="Preview evolution stage">
    {([1,2,3] as const).map(value=><button type="button" key={value} aria-pressed={stage===value}
      onClick={()=>{setStage(value);lastEye.current='';}}>Preview {value}</button>)}
   </div>
   <button type="button" className={styles.voice} onClick={()=>void speak(intensity||.55,true)} disabled={!gen}
     aria-label="Play this creature's generated Spark voice">{sound?<VolumeX size={15}/>:<Volume2 size={15}/>} {sound?'Speaking…':'Hear Beast'}</button>
  </div>:null}
  {error?<span className={styles.error} role="status">{error}</span>:null}
 </figure>;
}
