'use client';
import {useEffect,useId,useMemo,useRef} from 'react';
import ZerefFigure from './zeref-figure';
import {rigParts,paintRig} from './zeref-paint';
import {ZEREF_PROFILE,createMind,forceBehavior,frameFor,greetMind,stepMind,tapMind,type ZerefMind} from '../lib/zeref/zeref-mind.mjs';
import {blendFrame,growthLook,sampleCombo,stepPocket} from '../lib/zeref/zeref-pocket.mjs';
import {isZerefBeast,seedFromGenome,skinFromGenome} from '../lib/zeref/rig-style.mjs';

export type PocketEvent={type:string;[key:string]:unknown};
/** Optional pocket driver supplied by the habitat arena. */
export type RigDriver={
 pocket:any|null;
 busy:()=>boolean;
 stage:number;
 onPocket?:(pocket:any,mind:ZerefMind)=>void;
 onEvent?:(event:PocketEvent,mind:ZerefMind)=>void;
 onMind?:(mind:ZerefMind)=>void;
};
type Props={gen:any;id:string;name:string;stats?:Record<string,number>;state:string;reduced:boolean;channel?:string;driver?:RigDriver|null;className?:string};

/**
 * The habitat beast drawn with the high-quality ZEREF vector rig instead of
 * the 64px pixel sprite. Zeref wears the canonical Moonwraith skin; every
 * other beast gets a variant tinted and featured from its own genome, and
 * its temperament comes from its own recorded-count features. Visual only:
 * never writes identity, stats or saves.
 */
export default function SparkRig({gen,id,name,stats,state,reduced,channel='habitat',driver,className}:Props){
 const uid='rig'+useId().replace(/[^a-zA-Z0-9]/g,'');
 const svgRef=useRef<SVGSVGElement>(null),growRef=useRef<SVGGElement>(null);
 const mindRef=useRef<ZerefMind|null>(null);
 const driverRef=useRef(driver);driverRef.current=driver;
 const zeref=isZerefBeast({id,name})||!gen;
 const skin=useMemo(()=>skinFromGenome(gen,{id,name}),[gen,id,name]);
 const seed=useMemo(()=>zeref?null:seedFromGenome(gen),[gen,zeref]);
 const paint=useRef<()=>void>(()=>{});

 useEffect(()=>{
  const svg=svgRef.current;if(!svg)return;
  const P=rigParts(svg);
  const profile=zeref?{...ZEREF_PROFILE,id:id||ZEREF_PROFILE.id,name:name||'Zeref'}:{id,name,stats:{energy:stats?.energy??70,signal:stats?.signal??60,memory:stats?.memory??50,resonance:stats?.resonance??60}};
  const mind=createMind({profile,reduced,hour:new Date().getHours(),seed});
  mindRef.current=mind;driverRef.current?.onMind?.(mind);
  const render=()=>{
   const d=driverRef.current;
   const f:any=frameFor(mind);
   if(d?.pocket)blendFrame(f,d.pocket,mind,{stage:d.stage});
   else{const g=growthLook(d?.stage||1);f.scale=g.scale;f.auraStage=g.aura;}
   const depth=d?.pocket?1+Math.max(-1,Math.min(1,d.pocket.y))*.1:1;
   if(growRef.current)growRef.current.setAttribute('transform',`translate(200 360) scale(${(f.scale*depth).toFixed(3)}) translate(-200 -360)`);
   paintRig(P,f,mind.t,{wisps:skin.features.tailTip!=='none'});
   if(d?.pocket){
    const combo=sampleCombo(d.pocket,f,mind);
    if(combo)d.onEvent?.({type:'combo',...combo},mind);
   }
   svg.dataset.behavior=mind.reaction||mind.behavior;
  };
  paint.current=render;
  let raf=0,prev=performance.now(),visible=!document.hidden,onScreen=true,stopped=false;
  const loop=(now:number)=>{
   raf=0;if(stopped)return;
   const dt=Math.min(.1,(now-prev)/1000);prev=now;
   const d=driverRef.current;
   stepMind(mind,dt,{hour:new Date().getHours()});
   if(d?.pocket){
    for(const ev of stepPocket(d.pocket,mind,dt,{busy:d.busy()}))d.onEvent?.(ev,mind);
    d.onPocket?.(d.pocket,mind);
   }
   render();
   if(visible&&onScreen&&!mind.reduced)raf=requestAnimationFrame(loop);
  };
  const start=()=>{if(!raf&&visible&&onScreen&&!mind.reduced){prev=performance.now();raf=requestAnimationFrame(loop);}};
  const stop=()=>{if(raf)cancelAnimationFrame(raf);raf=0;};
  const vis=()=>{visible=!document.hidden;visible?start():stop();};
  document.addEventListener('visibilitychange',vis);
  const io=typeof IntersectionObserver!=='undefined'?new IntersectionObserver(([e])=>{onScreen=e.isIntersecting;onScreen?start():stop();}):null;
  io?.observe(svg);
  // Arena cues: the same seeded attack the pixel sprite used, now acted out by the rig.
  const onCue=(event:Event)=>{
   const detail=(event as CustomEvent).detail as {channel?:string;cue?:string}|undefined;
   if(!detail||detail.channel!==channel)return;
   if(detail.cue==='charge')forceBehavior(mind,'charge');
   else if(detail.cue==='strike')forceBehavior(mind,mind.reduced?'curious':'pounce');
   else if(detail.cue==='tap')tapMind(mind);
   else if(detail.cue==='pet')tapMind(mind,{hold:true});
   else if(detail.cue==='greet')greetMind(mind);
   if(mind.reduced){stepMind(mind,.016);render();}
  };
  window.addEventListener('beastbox:rig-cue',onCue);
  if(driverRef.current?.pocket)driverRef.current.onPocket?.(driverRef.current.pocket,mind);
  render();start();
  return()=>{stopped=true;stop();io?.disconnect();document.removeEventListener('visibilitychange',vis);window.removeEventListener('beastbox:rig-cue',onCue);};
  // eslint-disable-next-line react-hooks/exhaustive-deps
 },[reduced,id,seed?.digest,zeref,driver?.pocket]);

 // Care visual state from the shared save: asleep / celebrating.
 useEffect(()=>{
  const m=mindRef.current;if(!m)return;
  if(state==='sleeping'||state==='halted')forceBehavior(m,'sleep');
  else if(state==='celebrating')greetMind(m);
  if(m.reduced)paint.current();
 },[state]);

 return <svg ref={svgRef} className={className} viewBox="0 0 400 400" fill="none" data-beast-sprite="true" data-rig={zeref?'zeref':'genome'}
   role="img" aria-label={`${name} · ${zeref?'Zeref Moonwraith rig':'creature rig tinted from its recorded genome'}`}>
  <g ref={growRef}><ZerefFigure id={uid} skin={skin}/></g>
 </svg>;
}
