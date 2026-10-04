'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import {Activity,Eye,EyeOff,Pause,Play,ShieldCheck} from 'lucide-react';
import SparkBeastCompanion from './spark-beast-companion';
import {useCompanion} from './companion-provider';

type Props={
 model:string;connected:boolean;camera:boolean;speech:boolean;
 chatActive:boolean;trace:Record<string,unknown>[];checkpoint:unknown;
};
type SensorPacket={schema:'local-measurement-v1';kind:'microphone'|'camera';level:number;active?:boolean};
/**
 * This Spark Beast surface does not read raw camera frames, speech transcripts,
 * credentials or memory contents. Browser-only measurements only select bounded
 * visual moods; the recorded quantum seed is art/game provenance, not live sensing.
 * never authentic server telemetry or permission grants.
 */
export default function CosmicCompanionDock({model,connected,camera,speech,chatActive,trace,checkpoint}:Props){
 const {profile:cosmeticProfile}=useCompanion();
 const stoppedRef=useRef(false);
 const [hidden,setHidden]=useState(false),[paused,setPaused]=useState(false),[reduced,setReduced]=useState(false);
 const [perch,setPerch]=useState(0),[typing,setTyping]=useState(false);
 const [audioLevel,setAudioLevel]=useState(0),[memoryPulse,setMemoryPulse]=useState(false),[stopped,setStopped]=useState(false);
 const observed=useRef<string|null>(null),roamTick=useRef(0);
 const last=trace.length?trace[trace.length-1]:null;
 const receipt=last&&last.sequence!==undefined?String(last.sequence):null;

 useEffect(()=>{
  const media=window.matchMedia('(prefers-reduced-motion: reduce)');
  const update=()=>setReduced(media.matches);
  update();media.addEventListener('change',update);
  return()=>media.removeEventListener('change',update);
 },[]);
 useEffect(()=>{
  if(receipt===null)return;
  if(observed.current===null){observed.current=receipt;return;}
  if(receipt===observed.current)return;
  observed.current=receipt;
  setMemoryPulse(true);
  const timeout=window.setTimeout(()=>setMemoryPulse(false),2600);
  return()=>window.clearTimeout(timeout);
 },[receipt]);
 useEffect(()=>{
  const onMeasurement=(event:Event)=>{
   if(!(event instanceof CustomEvent))return;
   const packet=event.detail as SensorPacket|undefined;
   if(stoppedRef.current)return;
   if(packet?.schema!=='local-measurement-v1'||packet.kind!=='microphone')return;
   if(!Number.isFinite(packet.level)||packet.level<0||packet.level>1)return;
   setAudioLevel(packet.active===false?0:packet.level);
  };
  const stop=()=>{stoppedRef.current=true;setStopped(true);setAudioLevel(0);setMemoryPulse(false);};
  window.addEventListener('beastbox:local-sensor-level',onMeasurement);
  window.addEventListener('beastbox:master-privacy-stop',stop);
  return()=>{
   window.removeEventListener('beastbox:local-sensor-level',onMeasurement);
   window.removeEventListener('beastbox:master-privacy-stop',stop);
  };
 },[]);
 // A permission flag remaining true is NOT a valid signal to reset privacy stop.
 // Only a fresh component/session may reset this cosmetic latch; backend
 // restart authorization remains exclusively with the existing owner host.
 useEffect(()=>{if(!speech)setAudioLevel(0);},[speech]);
 useEffect(()=>{
  const focusIn=(event:FocusEvent)=>{
   const el=event.target;
   if(el instanceof HTMLElement&&(el.matches('input,textarea,[contenteditable="true"]')||!!el.closest('[role="dialog"]')))setTyping(true);
  };
  const focusOut=()=>{window.setTimeout(()=>setTyping(document.activeElement instanceof HTMLElement&&document.activeElement.matches('input,textarea,[contenteditable="true"]')),0);};
  document.addEventListener('focusin',focusIn);document.addEventListener('focusout',focusOut);
  return()=>{document.removeEventListener('focusin',focusIn);document.removeEventListener('focusout',focusOut);};
 },[]);
 useEffect(()=>{
  if(hidden||paused||typing||reduced)return;
  const timer=window.setInterval(()=>{
   if(document.hidden||window.innerWidth<900)return;
   roamTick.current++;
   setPerch(roamTick.current%3);
  },17000);
  return()=>window.clearInterval(timer);
 },[hidden,paused,typing,reduced]);
 const state=stopped?'halted' as const:chatActive?'thinking' as const:memoryPulse?'remembering' as const:camera?'observing' as const:speech?'listening' as const:!connected?'sleeping' as const:'idle' as const;
 const status=stopped?'Local privacy stop activated':chatActive?'Chat request in progress':memoryPulse?'New recorded trace receipt':camera?'Local camera enabled':speech?'Browser speech enabled':connected?'Idle · provider configured':'Idle · model not confirmed';
 const safe=typing||hidden;
 const show=useCallback(()=>setHidden(old=>!old),[]);
 return <div className={'companion-dock companion-perch-'+perch+(safe?' companion-parked':'')+(paused||reduced?' companion-still':'')} data-visual-signal={state} aria-label="Cosmic companion controls">
  <button className="companion-visibility" onClick={show} type="button" aria-label={hidden?'Show cosmic companion':'Minimize cosmic companion'} title={hidden?'Show companion':'Minimize companion'}>
   {hidden?<Eye size={15}/>:<EyeOff size={15}/>}<span>{hidden?'Show companion':'Hide'}</span>
  </button>
  {!hidden&&<div className="companion-floater">
   <SparkBeastCompanion profile={cosmeticProfile} fallbackLook={cosmeticProfile?.baseLook??'nebula'}
    state={stopped?'halted':paused?'sleeping':state} paused={paused||stopped}
    intensity={stopped?0:speech?audioLevel:0} compact
    label="Spark Beast companion reacting to permitted activity"/>
   <div className="companion-dock-plate"><span aria-hidden="true">✧</span><span>{status}</span></div>
   <div className="companion-dock-actions">
    <button type="button" onClick={()=>setPaused(p=>!p)} aria-label={paused?'Resume companion animation':'Pause companion animation'}>{paused?<Play size={13}/>:<Pause size={13}/>}</button>
    <span title="Cosmetic game profile only; actual provider readiness must be checked in Brain Bay">{connected?<Activity size={13}/>:<ShieldCheck size={13}/>} {model==='NOT CONNECTED'?'Awaiting model':model.slice(0,26)}</span>
   </div>
   <span className="sr-only" aria-live="polite">{status} · Checkpoint {checkpoint===null||checkpoint===undefined?'unavailable':'recorded in owner workstation'}.</span>
  </div>}
 </div>;
}
