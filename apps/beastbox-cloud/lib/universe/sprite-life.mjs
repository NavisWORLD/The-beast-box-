/**
 * Sprite life for the artist residents: transforms only (scale about the feet, bob, tilt, sideways sway) from Cosmo's spritelife numbers.
 * Nothing is redrawn or replaced; the resident art is untouched. Pure: time `t` is passed in; no clock, no Math.random.
 * Labels: timings/phases SEEDED (recorded run), amplitudes and shapes SIMULATED hand-tuned suggestions (see sprite-life-data.mjs).
 * Residents map to Cosmo's keys: Frostmitt->frost, Nyxbean->kittenref, Velvetcoil, Shardhowl, Kairo. Anything else gets the identity transform.
 */
import {SPRITE_LIFE} from './sprite-life-data.mjs';
export const RESIDENT_LIFE_KEY=Object.freeze({Frostmitt:'frost',Nyxbean:'kittenref',Velvetcoil:'velvetcoil',Shardhowl:'shardhowl',Kairo:'kairo'});
const TAU=Math.PI*2,D2R=Math.PI/180;
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
export const IDENTITY=Object.freeze({sx:1,sy:1,dy:0,dx:0,rot:0});
/** Hop shape for u in [0,1] (phases: anticipate, launch, air, land, recover). dy is a fraction of sprite height, negative = up. */
export function hopAt(L,u){
 const [pa,pl,pr,pn]=L.hop.phases;const a=pa,b=a+pl,c=b+pr,d=c+pn;const k=clamp(u,0,1);
 if(k<a){const e=Math.sin(k/a*Math.PI/2);return {sy:1-L.hop.antic*e,sx:1+L.hop.antic*.5*e,dy:0};}
 if(k<b){const e=(k-a)/pl;return {sy:1-L.hop.antic*(1-e)+L.hop.stretch*e,sx:1+L.hop.antic*.5*(1-e)-L.hop.stretch*.5*e,dy:0};}
 if(k<c){const e=(k-b)/pr;return {sy:1+L.hop.stretch*(1-e),sx:1-L.hop.stretch*.5*(1-e),dy:-L.hop.height*4*e*(1-e)};}
 if(k<d){const e=(k-c)/pn;return {sy:1-L.hop.land*Math.sin(e*Math.PI),sx:1+L.hop.land*.5*Math.sin(e*Math.PI),dy:0};}
 return {sy:1,sx:1,dy:0};
}
/**
 * One frame. key = Cosmo key; t seconds; walk 0..1 (how much it is walking), sleep 0..1 (curl), hopU = null or progress 0..1; reduced = prefers-reduced-motion.
 * Returns {sx,sy,dx,dy,rot}: scale about the feet, dx/dy as fractions of sprite height (dy negative = up), rot in radians.
 */
export function lifeTransform(key,{t=0,walk=0,sleep=0,hopU=/** @type {number|null|undefined} */(undefined),reduced=false}={}){
 const L=SPRITE_LIFE[key];if(!L||reduced)return IDENTITY;
 const w=clamp(walk,0,1),z=clamp(sleep,0,1);
 const fi=TAU*(t/L.idle.period_s+L.idle.phase);
 let sy=1+L.idle.amp_y*Math.sin(fi),sx=1-L.idle.amp_x*Math.sin(fi),dy=0,dx=0,rot=L.idle.sway_deg*D2R*.3*Math.sin(fi-Math.PI/2);
 if(w>0){const f=TAU*(t/L.walk.period_s+L.walk.phase),s=Math.sin(f),as=Math.abs(s);
  sy=sy*(1-w)+(1-L.walk.squash*(1-as))*w;sx=sx*(1-w)+1*w;dy=-L.walk.bob*as*w;dx=L.walk.sway*s*w;rot=rot*(1-w)+L.walk.tilt_deg*D2R*s*w;}
 if(z>0){const f=TAU*t/L.sleep.breath_period_s,br=1+L.sleep.breath_amp*Math.sin(f);sx=sx*(1-z)+L.sleep.sx*z;sy=sy*(1-z)+L.sleep.sy*br*z;rot=rot*(1-z)+L.sleep.tilt_deg*D2R*z;dy=dy*(1-z);dx=dx*(1-z);}
 if(hopU!=null&&hopU>=0&&hopU<1){const h=hopAt(L,hopU);sx*=h.sx;sy*=h.sy;dy+=h.dy;}
 return {sx,sy,dx,dy,rot};
}
/** Seconds a hop lasts for this creature (its own period). */
export const hopSeconds=key=>SPRITE_LIFE[key]?.hop.period_s??0.9;
