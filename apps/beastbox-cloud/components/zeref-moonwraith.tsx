'use client';
import {useEffect,useId,useRef,useState} from 'react';
import ZerefFigure from './zeref-figure';
import {rigParts as parts,paintRig} from './zeref-paint';
import {useUniverseMotion} from './use-universe-motion';
import {ZEREF_PROFILE,createMind,describeMind,forceBehavior,frameFor,greetMind,stepMind,tapMind,type ZerefMind,type ZerefProfile} from '../lib/zeref/zeref-mind.mjs';

type Props={
 profile?:ZerefProfile;care?:{energy?:number;bond?:number};className?:string;
 /** Increment to trigger a friendly greeting (e.g. the existing Wave hello button). */
 greet?:number;
 onMood?:(mood:ReturnType<typeof describeMind>)=>void;
 showCaption?:boolean;
};


/**
 * Live ZEREF rig. requestAnimationFrame drives a deterministic mind seeded
 * from recorded IBM counts + the beast's stats; taps, pointer, idle time,
 * time of day and page visibility are the only live inputs. Pauses when the
 * tab is hidden or the rig is off-screen; reduced motion renders still poses
 * that only change on interaction. Visual only: never writes Beast state.
 */
export default function ZerefMoonwraith({profile=ZEREF_PROFILE,care,className='',greet=0,onMood,showCaption=true}:Props){
 const id='zf'+useId().replace(/[^a-zA-Z0-9]/g,'');
 const svgRef=useRef<SVGSVGElement>(null),wrapRef=useRef<HTMLButtonElement>(null);
 const mindRef=useRef<ZerefMind|null>(null);
 const {reduced}=useUniverseMotion();
 const [mood,setMood]=useState(()=>describeMind(createMind({profile,care})));
 const moodKey=useRef('');
 const onMoodRef=useRef(onMood);onMoodRef.current=onMood;
 const holdRef=useRef<{timer:ReturnType<typeof setTimeout>|null;held:boolean}>({timer:null,held:false});
 const paint=useRef<()=>void>(()=>{});

 useEffect(()=>{
  const svg=svgRef.current,wrap=wrapRef.current;if(!svg||!wrap)return;
  const P=parts(svg);
  const mind=createMind({profile,care,reduced,hour:new Date().getHours()});
  mindRef.current=mind;
  const render=()=>{
   paintRig(P,frameFor(mind),mind.t);
   const d=describeMind(mind),key=d.state+'|'+d.energy;
   wrap.dataset.behavior=mind.behavior;wrap.dataset.reaction=mind.reaction||'';wrap.dataset.zerefState=d.state;
   if(d.state!==moodKey.current.split('|')[0]){setMood(d);onMoodRef.current?.(d);}
   moodKey.current=key;
  };
  paint.current=render;
  // Pointer: real eye-tracking within the viewport, relative to the rig.
  let pending:{x:number;y:number}|null=null;
  const onMove=(e:PointerEvent)=>{const r=svg.getBoundingClientRect();if(!r.width)return;
   pending={x:(e.clientX-(r.left+r.width/2))/(r.width*1.2),y:(e.clientY-(r.top+r.height*.42))/(r.height*1.2)};};
  window.addEventListener('pointermove',onMove,{passive:true});
  let raf=0,prev=performance.now(),visible=true,onScreen=true,stopped=false;
  const loop=(now:number)=>{
   raf=0;if(stopped)return;
   const dt=(now-prev)/1000;prev=now;
   stepMind(mind,dt,{hour:new Date().getHours(),pointer:pending?{...pending,moved:true}:undefined});pending=null;
   render();
   if(visible&&onScreen&&!mind.reduced)raf=requestAnimationFrame(loop);
  };
  const start=()=>{if(!raf&&visible&&onScreen&&!mind.reduced){prev=performance.now();raf=requestAnimationFrame(loop);}};
  const stop=()=>{if(raf)cancelAnimationFrame(raf);raf=0;};
  const vis=()=>{visible=!document.hidden;visible?start():stop();};
  document.addEventListener('visibilitychange',vis);
  const io=typeof IntersectionObserver!=='undefined'?new IntersectionObserver(([entry])=>{onScreen=entry.isIntersecting;onScreen?start():stop();}):null;
  io?.observe(wrap);
  visible=!document.hidden;
  // Evidence-only demo hook (?zerefDemo=1): lets screenshots step through named behaviours.
  const demo=new URLSearchParams(window.location.search).get('zerefDemo')==='1';
  if(demo)(window as any).__zerefDemo={force:(b:any)=>{forceBehavior(mind,b);render();return describeMind(mind);},tap:()=>{const r=tapMind(mind);render();return r;},state:()=>describeMind(mind)};
  render();start();
  return()=>{stopped=true;if((window as any).__zerefDemo)delete (window as any).__zerefDemo;stop();io?.disconnect();document.removeEventListener('visibilitychange',vis);window.removeEventListener('pointermove',onMove);};
  // eslint-disable-next-line react-hooks/exhaustive-deps
 },[reduced,profile.id,care?.energy,care?.bond]);

 // Reduced motion: no loop. Advance the mind in one step on interaction and once more when the reaction ends.
 const settleTimer=useRef<ReturnType<typeof setTimeout>|null>(null);
 const afterInteraction=()=>{
  const m=mindRef.current;if(!m)return;
  if(m.reduced){
   paint.current();
   if(settleTimer.current)clearTimeout(settleTimer.current);
   settleTimer.current=setTimeout(()=>{const mm=mindRef.current;if(!mm)return;stepMind(mm,Math.max(0,mm.reactionEnd-mm.t)+.01);while(mm.reaction)stepMind(mm,.1);paint.current();},2000);
  }
 };
 useEffect(()=>()=>{if(settleTimer.current)clearTimeout(settleTimer.current);if(holdRef.current.timer)clearTimeout(holdRef.current.timer);},[]);
 useEffect(()=>{if(!greet||!mindRef.current)return;greetMind(mindRef.current);afterInteraction();
  // eslint-disable-next-line react-hooks/exhaustive-deps
 },[greet]);

 const down=()=>{holdRef.current.held=false;if(holdRef.current.timer)clearTimeout(holdRef.current.timer);
  holdRef.current.timer=setTimeout(()=>{holdRef.current.held=true;const m=mindRef.current;if(m){tapMind(m,{hold:true});afterInteraction();}},550);};
 const up=()=>{if(holdRef.current.timer)clearTimeout(holdRef.current.timer);holdRef.current.timer=null;};
 const activate=()=>{if(holdRef.current.held){holdRef.current.held=false;return;}const m=mindRef.current;if(m){tapMind(m);afterInteraction();}};

 return <div className={'zeref-moonwraith '+className} data-zeref-id={profile.id} data-motion={reduced?'reduced':'active'}>
  <button ref={wrapRef} type="button" className="zeref-stage" onClick={activate} onPointerDown={down} onPointerUp={up} onPointerLeave={up} onPointerCancel={up}
   onContextMenu={e=>e.preventDefault()}
   aria-label={`Pet ${profile.name||'Zeref'}. ${profile.name||'Zeref'} is ${mood.mood}. Tap to play, press and hold to pet.`}
   data-behavior="idle" data-zeref-state={mood.state}>
   <svg ref={svgRef} className="zeref-svg" viewBox="0 0 400 400" fill="none" aria-hidden="true" focusable="false"><ZerefFigure id={id}/></svg>
  </button>
  {showCaption?<p className="zeref-caption" aria-live="polite"><strong>{profile.name||'Zeref'}</strong> · {profile.title||'Moonwraith'} · <span data-zeref-mood>{mood.mood}</span></p>:null}
 </div>;
}
