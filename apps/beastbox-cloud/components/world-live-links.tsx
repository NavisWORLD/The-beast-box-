'use client';
import {useEffect,useState} from 'react';
import styles from './zeref-diary-panel.module.css';
import type {WorldLive,Link} from '../lib/zeref/world-live.mjs';

/** Browser event other world components can listen to: detail = {drive, states}. `drive` is null unless the Rigetti SIMULATED spark is fresh. */
export const WORLD_LIVE_EVENT='beastbox:world-live';
const POLL_MS=30000;
const fmt=(s:unknown)=>typeof s==='number'?(s<90?`${s}s`:s<5400?`${Math.round(s/60)}m`:`${(s/3600).toFixed(1)}h`)+' ago':'—';
const dot=(st:string)=>st==='CONNECTED'?'#5cf2a0':st==='STALE'?'#ffd36b':'#ff7a8a';
function Row({id,name,l,detail}:{id:string;name:string;l:Link;detail:string}){
 return <li data-world-link={id} data-link-state={l.state} title={l.label}>
  <span aria-hidden="true" style={{display:'inline-block',width:8,height:8,borderRadius:99,background:dot(l.state),marginRight:6}}/>
  <b>{name}</b> · {l.state} · {detail}
 </li>;
}
/**
 * WORLD LIVE LINKS: shows whether the forever loops are really flowing into the world right now (Rigetti SIMULATED spark ticks,
 * the per-second SIMULATED tick, the RECORDED diary, and the pinned RAWRPHØS brain) and broadcasts the fresh spark numbers.
 * A stale or unreadable link is shown as STALE/DOWN; nothing is filled in.
 */
export default function WorldLiveLinks(){
 const [w,setW]=useState<WorldLive|null>(null),[failed,setFailed]=useState(false);
 useEffect(()=>{
  let alive=true;
  const load=async()=>{
   try{
    const r=await fetch('/api/world/live',{cache:'no-store'});
    if(!r.ok)throw new Error('http '+r.status);
    const d=await r.json() as WorldLive;
    if(!alive)return;
    setW(d);setFailed(false);
    const states=Object.fromEntries(Object.entries(d.links).map(([k,v])=>[k,v.state]));
    window.dispatchEvent(new CustomEvent(WORLD_LIVE_EVENT,{detail:{drive:d.drive,states}}));
   }catch{if(alive)setFailed(true);}
  };
  void load();
  const t=window.setInterval(()=>{if(!document.hidden)void load();},POLL_MS);
  const vis=()=>{if(!document.hidden)void load();};
  document.addEventListener('visibilitychange',vis);
  return()=>{alive=false;window.clearInterval(t);document.removeEventListener('visibilitychange',vis);};
 },[]);
 if(!w)return <div className={styles.live} data-world-live={failed?'down':'pending'}><p className={styles.liveHead}>WORLD LINKS</p><p className={styles.small}>{failed?'Could not read the loops right now.':'Checking the loops…'}</p></div>;
 const {spark,liveTick,diary,brain}=w.links as Record<string,any>;
 return <div className={styles.live} data-world-live={w.all_connected?'connected':'partial'} data-spark-tick={spark.tick??''}>
  <p className={styles.liveHead}>WORLD LINKS · {w.all_connected?'ALL CONNECTED':'CHECK BELOW'}</p>
  <ul style={{listStyle:'none',margin:0,padding:0,fontSize:12,lineHeight:1.7,color:'#cfd7f2'}}>
   <Row id="spark" name="Rigetti spark" l={spark} detail={`tick ${spark.tick??'—'} · ${fmt(spark.age_s)} · SIMULATED`}/>
   <Row id="live-tick" name="Per-second tick" l={liveTick} detail={`tick ${liveTick.recorded_tick??'—'} · saved ${fmt(liveTick.batch_age_s)} · SIMULATED`}/>
   <Row id="diary" name="Recorded diary" l={diary} detail={`tick ${diary.tick??'—'} · ${fmt(diary.age_s)} · RECORDED`}/>
   <Row id="brain" name="Brain (RAWRPHØS)" l={brain} detail={`step ${brain.step??'—'} · ${brain.checkpoint_sha256_prefix??''}… · pinned`}/>
  </ul>
  <p className={styles.small}>Rigetti is a simulator, never a QPU; the IBM birth spark is RECORDED. Nothing is filled in when a loop is late.</p>
 </div>;
}
