// "The engine carries the sky", PR 4: land depth as pure functions. Tints go OVER the existing ground (base kept).
// Engine numbers win: snow exists only where the engine's snowAmount (terrain-detail.mjs, from the recorded planet temperature) is above 0;
// wetness is 0 at baseline moisture (storm tension adds to moisture through the engine, not here). Constants are Cosmo's stand-ins.
import {snowAmount} from './terrain-detail.mjs';
export {snowAmount};
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
const smooth=(a,b,x)=>{const t=clamp((x-a)/(b-a),0,1);return t*t*(3-2*t);};
const lerp=(a,b,t)=>a+(b-a)*t;
export const LAND=Object.freeze({snowSlope:[0.45,0.8],rockShed:0.5,breakup:0.25,minCover:0.02,snowShadow:[0.82,0.9,1.0],
  wetEdges:[0,0.35],wetDarken:0.58,wetSat:1.12,wetRoughMul:0.55,wetF0Add:0.04,sheenOnlyAbove:0.15,dryHalfLifeDay:0.04});
/** snow cover 0..1: snowAmount (engine) * slope blend * (1-.5 rock) * (1-.25 noise). Exactly 0 iff snowAmount is 0; otherwise at least minCover*snowAmount. */
export function snowCover({snowAmount:sa,normalY=1,rockiness=0,noise=0}){
  const a=clamp(+sa||0,0,1);if(a<=0)return 0;
  const c=a*smooth(LAND.snowSlope[0],LAND.snowSlope[1],normalY)*(1-LAND.rockShed*clamp(rockiness,0,1))*(1-LAND.breakup*clamp(noise,0,1));
  return Math.max(c,LAND.minCover*a);
}
/** wetness target = smoothstep(0, .35, max(0, moisture - baseline)); 0 at baseline moisture. */
export const wetnessTarget=(moisture,baseline)=>smooth(LAND.wetEdges[0],LAND.wetEdges[1],Math.max(0,(+moisture||0)-(+baseline||0)));
/** drying with hysteresis: wetness_next = max(target, wetness*(1-k)), k = ln2/half-life per engine tick. dayLengthTicks is the engine const (960). */
export function wetnessStep(prev,target,dayLengthTicks=960,dtTicks=1){
  const halfTicks=Math.max(1,LAND.dryHalfLifeDay*dayLengthTicks);const keep=Math.pow(0.5,dtTicks/halfTicks);return Math.max(target,prev*keep);
}
const sat=(c,k)=>{const m=(c[0]+c[1]+c[2])/3;return c.map(x=>Math.max(0,m+(x-m)*k));};
/** ground = lerp(base, snowTint, cover) * lerp(1, .58, wet) with chroma x lerp(1, 1.12, wet). All linear light. */
export function groundTint(base,{snowTint=[0.86,0.9,0.95],cover=0,wet=0}={}){
  let g=base.map((b,i)=>lerp(b,snowTint[i],cover));
  g=sat(g,lerp(1,LAND.wetSat,wet));return g.map(x=>x*lerp(1,LAND.wetDarken,wet));
}
/** sheen only when wet > .15: rougher floor falls, F0 rises */
export function wetSheen(wet,roughness,f0=0.04){const on=wet>LAND.sheenOnlyAbove?smooth(LAND.sheenOnlyAbove,1,wet):0;return {roughness:lerp(roughness,roughness*LAND.wetRoughMul,on),f0:f0+LAND.wetF0Add*on,on};}
