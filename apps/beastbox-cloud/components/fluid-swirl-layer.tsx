'use client';
import {useEffect,useRef} from 'react';
import {createFluid,setFlow,stepFluid,velocityAt} from '../lib/companion/fluid-swirl.mjs';
/**
 * Additive particle layer advected by a tiny classical 2D stable-fluids solver.
 * Exposes the flow to the creature via onSample(u,v) for secondary motion (sway).
 * 24x24 grid, ~90 particles, DPR capped at 2, pauses when hidden or reduced-motion.
 */
export default function FluidSwirlLayer({storm,chaos,seed=1,onSample,count=90}:{storm:number;chaos:number;seed?:number;onSample?:(u:number,v:number)=>void;count?:number}){
 const cv=useRef<HTMLCanvasElement>(null),fl=useRef<any>(null),sam=useRef(onSample);sam.current=onSample;
 useEffect(()=>{if(fl.current)setFlow(fl.current,{storm,chaos});},[storm,chaos]);
 useEffect(()=>{
  const c=cv.current;if(!c)return;const g=c.getContext('2d');if(!g)return;
  const reduced=typeof matchMedia!=='undefined'&&matchMedia('(prefers-reduced-motion: reduce)').matches;
  fl.current=createFluid(24,{storm,chaos,seed});
  let r=(seed>>>0)||7;const rnd=()=>((r=(Math.imul(r,1664525)+1013904223)>>>0)/4294967296);
  const P=Array.from({length:count},()=>({x:rnd(),y:rnd(),a:rnd()}));
  let raf=0,last=performance.now(),acc=0;
  const fit=()=>{const d=Math.min(2,devicePixelRatio||1);c.width=Math.max(1,c.clientWidth*d|0);c.height=Math.max(1,c.clientHeight*d|0);};fit();
  const ro=new ResizeObserver(fit);ro.observe(c);
  const tick=(t:number)=>{const dt=Math.min(.05,(t-last)/1000);last=t;
   if(!document.hidden){const f=fl.current;acc+=dt;if(acc>=1/30){stepFluid(f,acc);acc=0;} // solver at 30 Hz, draw at display rate
    const W=c.width,H=c.height;g.clearRect(0,0,W,H);g.fillStyle='#9aefff';
    for(const p of P){const {u,v}=velocityAt(f,p.x,p.y);p.x=(p.x+u*dt*.08+1)%1;p.y=(p.y+v*dt*.08+1)%1;
     g.globalAlpha=.25+.45*p.a;g.fillRect(p.x*W,p.y*H,3,3);}
    const s=velocityAt(f,.5,.8);sam.current?.(s.u,s.v);}
   if(!reduced)raf=requestAnimationFrame(tick);};
  raf=requestAnimationFrame(tick);
  return()=>{cancelAnimationFrame(raf);ro.disconnect();};
 },[seed,count]);// eslint-disable-line react-hooks/exhaustive-deps
 return <canvas ref={cv} aria-hidden data-fluid-swirl data-storm={storm.toFixed(2)} data-chaos={chaos.toFixed(2)} style={{position:'absolute',inset:0,width:'100%',height:'100%',pointerEvents:'none',mixBlendMode:'screen'}}/>;
}
