/**
 * Grounded hop physics for creatures (Oct 16 2026): feet stay on the ground (groundY sampler: heightfield or raycast),
 * and jumps are ballistic with landing squash. When and how high a creature jumps comes from its CST state:
 * play → frequent bouncy hops, coherence → rhythmic/regular, chaos (Lorenz) → irregular explore hops, startle → a pop.
 * Fixed 120 Hz substeps so the arc is identical at 30 or 120 fps.
 */
import {seededRng,springStep,clamp} from './cst-integrator.mjs';
export function createHop(seed){return {r:seededRng('hop:'+seed),y:0,vy:0,air:false,cool:.8,sq:{x:0,v:0},acc:0,landed:0};}
/** @param {any} H @param {number} dt @param {{mode?:string,speed?:number,startle?:number,mp?:any,g?:number,scale?:number,groundY?:number}} [o]
 * opts: {mode,speed,startle,mp (motionParams), g (gravity, world units/s²), scale (body height), groundY} → {y (feet height above ground), squash, air} */
export function stepHop(H,dt,{mode='wander',speed=0,startle=0,mp=null,g=14,scale=1,groundY=0}={}){
 const h=1/120;H.acc=Math.min(H.acc+Math.max(0,dt||0),.1);
 const coh=mp?.mood?.calm??.6,chaos=mp?(mp.turbulence??.2):.2,joy=mp?.mood?.joy??.5;
 while(H.acc>=h){H.acc-=h;
  if(H.air){H.vy-=g*h;H.y+=H.vy*h;if(H.y<=0){H.y=0;H.air=false;H.sq.v-=Math.min(6,-H.vy*1.8);H.vy=0;H.landed++;}}
  else{H.cool-=h;
   const rate=mode==='play'?1.6+joy*1.4:mode==='chase'?1.1:mode==='wander'&&speed>.15?.12+chaos*.6:mode==='approach'?.25:0;
   const pop=startle>.9&&H.cool<.4;
   if(pop||(H.cool<=0&&rate>0&&H.r()<rate*h)){
    // jump height: play bounces higher, coherent creatures hop evenly, chaotic ones vary
    const base=mode==='play'?.32:.18,vary=1+(H.r()-.5)*(.2+chaos*1.2)*(1-coh*.5);
    const hgt=base*scale*vary*(pop?1.3:1);H.vy=Math.sqrt(2*g*hgt);H.air=true;H.sq.v+=2.5;H.cool=mode==='play'?.15+coh*.3:.9+H.r()*1.5;}
  }
  springStep(H.sq,0,mp?60*mp.stiffness:70,mp?6*mp.damping+2:8,h);
 }
 return {y:groundY+H.y,squash:clamp(H.sq.x*.18,-.22,.22),air:H.air};
}
