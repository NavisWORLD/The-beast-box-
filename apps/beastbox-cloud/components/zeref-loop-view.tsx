'use client';
import {useEffect,useRef,useState} from 'react';
import {createLoop,stepLoop,momentLine,LOOP_LABELS} from '../lib/loop/loop-chain.mjs';
type Moment={tick:number;text:string;label:string;provenance:string;hash:string};
/** The never-ending loop, running in this tab on one clock (a tick every second). Nothing is stored or sent. */
export function ZerefLoopView(){
 const loop=useRef<ReturnType<typeof createLoop>|null>(null);
 const [tick,setTick]=useState(0),[moments,setMoments]=useState<Moment[]>([]),[err,setErr]=useState('');
 useEffect(()=>{
  let live=true,timer:ReturnType<typeof setInterval>|null=null;
  fetch('/spark/zeref-bio-spark.json').then(r=>r.json()).then(j=>{
   if(!live)return;loop.current=createLoop({seed:j.heart_seed_v9_sha256});
   timer=setInterval(()=>{if(!loop.current)return;const cur=stepLoop(loop.current,{});loop.current=cur;setTick(cur.tick);setMoments([...cur.moments].reverse().slice(0,8));},1000);
  }).catch(()=>setErr('The recorded seed could not be loaded, so the loop is not running.'));
  return()=>{live=false;if(timer)clearInterval(timer);};
 },[]);
 return <section data-zeref-loop aria-live="polite">
  <p>Tick {tick} · sim second {tick}. The loop never pauses: each tick carries the creature&apos;s brain state, the world and the last moment into the next. No pulse is attached here, so nothing is shown as MEASURED.</p>
  <small>{LOOP_LABELS.ibm_seed} · {LOOP_LABELS.placement}</small>
  {err?<p role="alert">{err}</p>:null}
  <ol>{moments.map(m=><li key={m.hash}>{momentLine(m as never)}</li>)}</ol>
 </section>;
}
