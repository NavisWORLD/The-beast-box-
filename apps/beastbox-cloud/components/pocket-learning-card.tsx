'use client';
import {useEffect,useRef,useState} from 'react';
import type {LearningSummary} from '../lib/zeref/pocket-learner.mjs';
import styles from './zeref-diary-panel.module.css';

const GOAL_TEXT:Record<string,string>={explore:'exploring somewhere new',visit:'visiting a favourite place',rest:'resting',play:'playing',come:'coming over to you'};

/**
 * What the beast has learned from its own experience in the pocket (this device),
 * plus the opt-in "let it hear the room" switch: microphone loudness is analysed
 * locally as one number; nothing is recorded, stored or uploaded. Off by default.
 */
export default function PocketLearningCard({journalId,beastName,loop}:{journalId:string;beastName:string;loop?:{cells_visited:number;cells_total:number;moves_blocked:number;moves_succeeded:number;favorite_spot:string|null}|null}){
 const [s,setS]=useState<LearningSummary|null>(null),[goal,setGoal]=useState<string|null>(null);
 const [hearing,setHearing]=useState(false),[level,setLevel]=useState(0),[err,setErr]=useState('');
 const stopRef=useRef<()=>void>(()=>{});
 useEffect(()=>{
  const on=(e:Event)=>{const d=(e as CustomEvent).detail;if(d?.journalId===journalId){setS(d.summary);setGoal(d.goal||null);}};
  window.addEventListener('beastbox:pocket-learning',on);
  return()=>window.removeEventListener('beastbox:pocket-learning',on);
 },[journalId]);
 useEffect(()=>()=>stopRef.current(),[]);
 async function toggleHearing(){
  if(hearing){stopRef.current();return;}
  setErr('');
  try{
   if(!window.isSecureContext||!navigator.mediaDevices?.getUserMedia)throw new Error('Microphone needs a secure page.');
   const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true},video:false});
   const ctx=new AudioContext(),src=ctx.createMediaStreamSource(stream),an=ctx.createAnalyser();an.fftSize=1024;src.connect(an);
   const silent=ctx.createGain();silent.gain.value=0;an.connect(silent);silent.connect(ctx.destination);await ctx.resume();
   const data=new Float32Array(an.fftSize);
   const iv=window.setInterval(()=>{an.getFloatTimeDomainData(data);const rms=Math.sqrt(data.reduce((a,x)=>a+x*x,0)/data.length);const lv=Math.min(1,Math.max(0,rms));setLevel(lv);
    window.dispatchEvent(new CustomEvent('beastbox:local-sensor-level',{detail:{schema:'local-measurement-v1',kind:'microphone',level:lv,active:true}}));},250);
   const onHide=()=>{if(document.hidden)stopRef.current();};document.addEventListener('visibilitychange',onHide);
   stopRef.current=()=>{window.clearInterval(iv);stream.getTracks().forEach(t=>t.stop());void ctx.close();document.removeEventListener('visibilitychange',onHide);
    window.dispatchEvent(new CustomEvent('beastbox:local-sensor-level',{detail:{schema:'local-measurement-v1',kind:'microphone',level:0,active:false}}));
    setHearing(false);setLevel(0);stopRef.current=()=>{};};
   setHearing(true);
  }catch{setErr('Microphone unavailable or permission denied. The beast is fine without it.');}
 }
 const total=s?s.moves_succeeded+s.moves_blocked:0;
 return <div className={styles.card} data-pocket-learning data-cells-visited={s?.cells_visited??0} data-moves-blocked={s?.moves_blocked??0}>
  <h3>What {beastName} has learned</h3>
  <p className={styles.small}>{beastName} chooses its own goals. Right now: <b>{goal?GOAL_TEXT[goal]||goal:'deciding'}</b>. Tap it or press Call and it comes over; otherwise it lives its own life.</p>
  {s?<ul className={styles.learn}>
   <li><b>{s.cells_visited}</b>/{s.cells_total} patches of the pocket explored</li>
   <li><b>{s.moves_succeeded}</b> move{s.moves_succeeded===1?'':'s'} succeeded · <b>{s.moves_blocked}</b> blocked by void rifts ({total?Math.round(s.blocked_rate*100):0}%) · {s.known_rifts} rift{s.known_rifts===1?'':'s'} remembered</li>
   <li>Favourite spot: <b>{s.favorite_spot||'still deciding'}</b></li>
   <li>Leaning: {Object.entries(s.prefs).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`${k} ${Math.round(v*100)}`).join(' · ')}</li>
  </ul>:<p className={styles.small}>Watching where it goes…</p>}
  {loop&&(loop.moves_succeeded+loop.moves_blocked)>0?<p className={styles.small}>In the scheduled loop: {loop.cells_visited}/{loop.cells_total} patches · {loop.moves_succeeded} ok / {loop.moves_blocked} blocked{loop.favorite_spot?` · favourite ${loop.favorite_spot}`:''}.</p>:null}
  <p className={styles.hearRow}><button type="button" className={styles.hear} aria-pressed={hearing} onClick={()=>void toggleHearing()}>{hearing?'👂 Hearing the room · stop':'👂 Let it hear the room (mic)'}</button>
   {hearing?<meter min={0} max={0.25} value={level} aria-label="Room loudness (local only)"/>:null}</p>
  {err?<p className={styles.small}>{err}</p>:null}
  <p className={styles.small}>Learned behaviour from its own experience (visit counts, move outcomes and running averages), not consciousness. Saved per beast in this browser. The mic is optional and off by default; only a loudness number is analysed locally, nothing is recorded or uploaded.</p>
 </div>;
}
