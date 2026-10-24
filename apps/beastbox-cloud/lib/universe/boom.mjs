// "The engine carries the sky", PR 2b: THE BOOM, the supernova as an engine visual event with phases.
// The engine already records `supernova {star}` in history and fixes the physics (mass > 8 explodes; neutron_star remnant, black_hole if mass > 15; see tiny-universe.mjs grow()).
// This module adds its visual life as a PURE function of (the star's recorded numbers, event tick, current tick): replaying history reproduces it exactly and no animation state is stored.
// HONESTY: this is "SEEDED (stepped test universe)". The recording holds no supernova; the star list is seeded from the recorded IBM counts and the event is stepped by grow().
// The boom ENDS by becoming the black hole that already exists (seeded black holes, #544); it never builds a second one.
import {blackBodyToRGB} from './genesis-sun.mjs';
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
const mix=(a,b,t)=>a.map((x,i)=>x+(b[i]-x)*t);
export const BOOM_LABEL='SEEDED (stepped test universe)';
// ONE named constant block (only where the engine has no number of its own)
export const BOOM=Object.freeze({
 lifeTicks:64,             // visible life; history keeps the last 64 ticks, so a boom replays from history alone
 flashEnd:0.02,shellEnd:0.45,fadeEnd:0.80,   // phase boundaries as fractions of the life (spec: flash ~first 2%)
 shellKeep:0.35,           // intensity (of peak) when the shell hands over to the fade
 shellReachAu:3,           // the shell grows to this many AU (the engine's own orbitR scale reads it: 4+5*sqrt(au))
 flashTint:[0.8,0.9,1.0],flashPush:0.7,ember:[1.0,0.35,0.1],
 neutronGlow:0.15,wispFloor:0.04,
 skyCap:1,skyK:0.002,dayPale:0.85,          // sky term: min(cap, intensity*lum/d^2*K), day side pushed pale by up to this much
});
export const remnantFor=massSolar=>massSolar>15?'black_hole':massSolar>8?'neutron_star':null;
/** The star's luminosity AT the event. grow() sets a remnant's luminosity to 0, so a remnant falls back to the engine's own relation (makeStar: luminosity = mass^3.5). */
export const boomLuminosity=star=>(+star.luminosity>0?+star.luminosity:Math.pow(+star.mass_solar||0,3.5));
/** boomState(star, eventTick, tick) -> {phase:'none'|'flash'|'shell'|'fade'|'remnant', u, intensity, shellFrac, shellRadiusAu, colorRGB, remnantType, label}. Before the event or for a star that cannot explode: phase 'none'. */
export function boomState(star,eventTick,tick){
 const K=BOOM,rem=remnantFor(+star.mass_solar||0);const none={phase:'none',u:0,intensity:0,shellFrac:0,shellRadiusAu:0,colorRGB:blackBodyToRGB(+star.temperature_k||5800),remnantType:rem,label:BOOM_LABEL};
 if(!rem||!(tick>=eventTick))return none;
 const u=(tick-eventTick)/K.lifeTicks;const lum=boomLuminosity(star);
 const peak=clamp(0.6+0.4*Math.log10(1+lum)/4,0.6,1);const bb=blackBodyToRGB(+star.temperature_k||5800);
 const sT=clamp((u-K.flashEnd)/(K.fadeEnd-K.flashEnd),0,1);const shellFrac=1-Math.pow(1-sT,3); // ease-out on the engine clock
 let phase,intensity,colorRGB;
 if(u<K.flashEnd){phase='flash';const f=u/K.flashEnd;intensity=peak*Math.sin(Math.PI/2*f);colorRGB=mix(bb,K.flashTint,K.flashPush);}
 else if(u<K.shellEnd){phase='shell';const s=(u-K.flashEnd)/(K.shellEnd-K.flashEnd);intensity=peak*(K.shellKeep+(1-K.shellKeep)*Math.pow(1-s,2));colorRGB=mix(mix(bb,K.flashTint,K.flashPush),mix(bb,K.ember,0.6),s);}
 else if(u<K.fadeEnd){phase='fade';const f=(u-K.shellEnd)/(K.fadeEnd-K.shellEnd);intensity=Math.max(K.wispFloor,peak*K.shellKeep*Math.pow(1-f,1.5));colorRGB=mix(mix(bb,K.ember,0.6),K.ember,f);}
 else{phase='remnant';intensity=rem==='neutron_star'?K.neutronGlow:0;colorRGB=rem==='neutron_star'?[0.7,0.8,1]:K.ember;}
 return {phase,u,intensity,shellFrac,shellRadiusAu:shellFrac*K.shellReachAu,colorRGB,remnantType:rem,label:BOOM_LABEL};
}
/** Supernova events from the universe history, in tick order: [{star, tick}]. The star id is all the engine records; the star's own numbers come from u.stars. */
export function supernovaEvents(u){const out=[];for(const h of (u?.history||[]))for(const e of (h.events||[]))if(e.kind==='supernova'&&e.star)out.push({star:e.star,tick:h.tick});return out;}
/** Every boom in the universe at `tick`: [{star, eventTick, state}] (replayed from history, never stored). */
export function boomsAt(u,tick){const by=new Map((u?.stars||[]).map(s=>[s.id,s]));return supernovaEvents(u).map(e=>({star:e.star,eventTick:e.tick,state:by.has(e.star)?boomState(by.get(e.star),e.tick,tick):null})).filter(b=>b.state);}
/** The boom term a planet's sky sees: 0 before the event, peaks in the flash, 1/distance^2 against the star's luminosity, capped; the day side sees it pale (sunUp 0..1). */
export function boomSkyTerm(star,eventTick,tick,distance,sunUp=0){
 const K=BOOM,s=boomState(star,eventTick,tick);if(s.phase==='none')return 0;
 const d=Math.max(0.05,+distance||0.05);const t=Math.min(K.skyCap,s.intensity*boomLuminosity(star)/(d*d)*K.skyK);return t*(1-K.dayPale*clamp(sunUp,0,1));
}
