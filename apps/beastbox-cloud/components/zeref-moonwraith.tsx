'use client';
import {useEffect,useId,useRef,useState} from 'react';
import ZerefFigure from './zeref-figure';
import {useUniverseMotion} from './use-universe-motion';
import {ZEREF_PROFILE,createMind,describeMind,forceBehavior,frameFor,greetMind,stepMind,tapMind,type ZerefMind,type ZerefProfile} from '../lib/zeref/zeref-mind.mjs';

type Props={
 profile?:ZerefProfile;care?:{energy?:number;bond?:number};className?:string;
 /** Increment to trigger a friendly greeting (e.g. the existing Wave hello button). */
 greet?:number;
 onMood?:(mood:ReturnType<typeof describeMind>)=>void;
 showCaption?:boolean;
};

const parts=(root:SVGSVGElement)=>{
 const map:Record<string,SVGElement>={};
 root.querySelectorAll<SVGElement>('[data-part]').forEach(el=>{map[el.dataset.part as string]=el;});
 return map;
};
const n=(v:number,d=2)=>Number.isFinite(v)?+v.toFixed(d):0;

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
  const tf=(el:SVGElement|undefined,v:string)=>{if(el)el.style.transform=v;};
  const op=(el:SVGElement|undefined,v:number)=>{if(el)el.style.opacity=String(n(Math.max(0,Math.min(1,v))));};
  const render=()=>{
   const f=frameFor(mind);
   tf(P.float,`translate(${n(f.floatX)}px,${n(f.floatY)}px) rotate(${n(f.rot)}deg) scaleX(${n(f.face,3)})`);
   P.float.style.transformOrigin='200px 340px';(P.float.style as any).transformBox='view-box';
   tf(P.body,`scale(${n(f.bodySX,3)},${n(f.bodySY,3)})`);
   tf(P.head,`translateY(${n(f.headY)}px) rotate(${n(f.headRot)}deg)`);
   tf(P.earL,`rotate(${n(f.earL)}deg)`);tf(P.earR,`rotate(${n(-f.earR)}deg)`);
   tf(P.wingL,`rotate(${n(-f.wingL)}deg)`);tf(P.wingR,`rotate(${n(-f.wingR)}deg)`);
   tf(P.tail,`rotate(${n(f.tail)}deg)`);
   tf(P.wisps,`translate(${n(Math.sin(f.wisp*1.7)*4)}px,${n(Math.cos(f.wisp*1.3)*5)}px)`);op(P.wisps,.45+Math.sin(f.wisp*2)*.25);
   tf(P.pawL,`translateY(${n(-f.pawL*34)}px) rotate(${n(-f.pawL*24)}deg)`);tf(P.pawR,`translateY(${n(-f.pawR*34)}px) rotate(${n(f.pawR*24)}deg)`);
   const gx=f.gazeX*8,gy=f.gazeY*7;
   tf(P.irisL,`translate(${n(gx)}px,${n(gy)}px)`);tf(P.irisR,`translate(${n(gx)}px,${n(gy)}px)`);
   tf(P.pupilL,`scale(${n(f.pupil,3)})`);tf(P.pupilR,`scale(${n(f.pupil,3)})`);
   const lid=Math.min(1,Math.max(0,f.lid)),low=Math.min(1,Math.max(0,f.lower));
   const lowUp=Math.max(low*40,lid*30);
   tf(P.lidL,`translateY(${n(lid*44)}px)`);tf(P.lidR,`translateY(${n(lid*44)}px)`);
   tf(P.lowL,`translateY(${n(-lowUp)}px)`);tf(P.lowR,`translateY(${n(-lowUp)}px)`);
   tf(P.browL,`translateY(${n(-f.brow*6)}px) rotate(${n(f.brow*-10)}deg)`);tf(P.browR,`translateY(${n(-f.brow*6)}px) rotate(${n(f.brow*10)}deg)`);
   (['smile','grin','o','frown','sleepy'] as const).forEach(k=>op(P['mouth-'+k],f.mouth[k]*1.15));
   op(P.blushL,.15+f.blush*.75);op(P.blushR,.15+f.blush*.75);
   op(P.aura,.25+f.glow*.55+f.charge*.2);P.crescent.style.filter=`drop-shadow(0 0 ${n(3+f.glow*10)}px #cfa8ff)`;
   op(P.gem,.6+f.glow*.4);op(P.ring,f.ring*.85);op(P.charge,f.charge*.75);
   tf(P.charge,`scale(${n(.85+f.charge*.2,3)})`);P.charge.style.transformOrigin='200px 230px';
   tf(P.shadow,`scaleX(${n(f.shadow,3)})`);op(P.shadow,.25+f.shadow*.35);
   op(P['fx-zzz'],f.fx.zzz);tf(P['fx-zzz'],`translateY(${n(-Math.abs(Math.sin(mind.t*.8))*8)}px)`);
   op(P['fx-question'],f.fx.question);op(P['fx-exclaim'],f.fx.exclaim);op(P['fx-heart'],f.fx.heart);
   tf(P['fx-heart'],`translateY(${n(-((mind.t*20)%14))}px)`);op(P['fx-sparkle'],f.fx.sparkle);
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
