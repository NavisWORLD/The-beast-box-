// GENESIS X P3: the first-person ocean. Pure numbers only (no DOM, no clock, no random calls); the renderer is p3-ocean-three.ts.
// The sea is the SAME engine sea as the planet (sea-state.mjs seaFrom: CST wind -> direction, storm tension -> amplitude, chop, whitecaps).
// Light comes only from the one engine sun (240 s day): glitter from sunGlitter(), dark water at night. Wave motion is SIMULATED on engine time.
// The bay's bearing and width are SEEDED from the world seed stream. Nothing here is stored in the engine JSON.
import {seaFrom,sunGlitter,SEA} from './sea-state.mjs';
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
const mix=(a,b,t)=>a+(b-a)*t;
/** SEEDED look numbers (metres, sRGB hexes). */
export const OCEAN3=Object.freeze({label:'SEEDED',motion:'SIMULATED',light:'one sun',
 innerM:70,outerM:2400,halfWidthDeg:[38,62],shoreM:16,
 deep:'#0A3550',mid:'#14607A',shallow:'#2E8C8C',foam:'#EEF5F2',sand:'#CBB98A',
 waveM:Object.freeze([38,21,7.5,3.2]), // wavelengths in metres for the 4 SEA layers (swell, swell, chop, chop)
 ampM:Object.freeze({calm:.18,storm:1.6}),
 roughCalm:.06,roughStorm:.55,roughWind:.12});
/** Seeded bay placement: bearing (radians in the local ground frame) and half width. rand() is a seeded stream (lwStream). */
export function bayFrom(rand){const b=rand()*Math.PI*2;const hw=mix(OCEAN3.halfWidthDeg[0],OCEAN3.halfWidthDeg[1],rand())*Math.PI/180;return {bearing:+b.toFixed(6),halfWidth:+hw.toFixed(6),innerM:OCEAN3.innerM,outerM:OCEAN3.outerM};}
/** Is a point in the bay water? x,z are metres in the local ground frame (same frame as the shader). A conservative wedge: wider than the drawn coast
 * by `margin` metres (the shader's coast wobble is about +-13 m), so a creature steered out of it never stands in the drawn sea. Pure maths, no random calls. */
export function inBayWater(bay,x,z,margin=16){const r=Math.hypot(x,z);if(r<1e-6)return false;let a=Math.atan2(z,x)-bay.bearing;a=((a+Math.PI)%(2*Math.PI)+2*Math.PI)%(2*Math.PI)-Math.PI;
 const sd=Math.min((bay.halfWidth*1.25-Math.abs(a))*r,r-bay.innerM*.55);return sd>-margin;}
/** A walker going round a circle of radius rM metres (sweep angle theta, unbounded, on the clock) keeps to the land arc: inside the bay
 * wedge it turns back (ping-pong), so it never walks on the drawn sea. Returns the bearing to stand at. Pure maths, no random calls. */
export function landArcAngle(bay,rM,theta,margin=16){if(rM<bay.innerM*.55-margin)return theta;const open=Math.min(Math.PI*.95,bay.halfWidth*1.25+(margin+2)/Math.max(rM,1));
 const L=2*Math.PI-2*open;const u=((theta/L)%2+2)%2;const s=(u<1?u:2-u)*L;return bay.bearing+open+s;}
/** The ocean state this frame, from the engine field, the one sun and storm. sunElev = sin(sun elevation) at the eye (-1..1), day 0..1. */
export function oceanAt(o){
 const F=o?.field||null;const storm=clamp(Math.max(+F?.storm||0,+o?.storm||0),0,1);
 const sea=seaFrom(F?{...F,storm}:{storm});const day=clamp(+o?.day||0,0,1);const se=clamp(+o?.sunElev||0,-1,1);
 const ampM=mix(OCEAN3.ampM.calm,OCEAN3.ampM.storm,storm)*(0.35+0.65*sea.wind)+0.05;
 const rough=clamp(OCEAN3.roughCalm+OCEAN3.roughStorm*storm+OCEAN3.roughWind*sea.wind,0.03,0.8);
 const g=sunGlitter(se,sea);
 return {label:'DERIVED',motion:'SIMULATED',dir:sea.dir,wind:sea.wind,storm,chop:sea.chop,whitecap:sea.whitecap,ampM:+ampM.toFixed(4),rough:+rough.toFixed(4),
  glint:+(g.intensity*day*(1-0.75*storm)).toFixed(4),glintWidth:+g.width.toFixed(4),glintColor:g.color,darken:+(0.55*storm).toFixed(4),day};
}
/** Wave layer table for the shader: [wavelength m, amplitude share, speed m/s (deep-water dispersion), direction offset, phase]. Shares and offsets come from SEA.layers. */
export function waveLayers(){return SEA.layers.map((l,k)=>{const L=OCEAN3.waveM[k];const c=Math.sqrt(9.81*L/(2*Math.PI));return [L,l[1],+c.toFixed(4),l[3],l[4]];});}
