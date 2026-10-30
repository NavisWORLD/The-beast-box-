// The shared graphics state for every view (technique from GENESIS X's GENESIS_UNIFORMS, Cory's MIT sim; ported, not pasted).
// It never owns time or the sun: uSun* come from the ONE engine sun (one-sun.mjs / the living-world day clock), uTime from the
// caller's clock. Chaos and grain are SEEDED from the pack seed and the frame counter; no Math.random anywhere.
import {seedFrom} from '../seeded-stream.mjs';
import {P1POST} from './data/p1post.mjs';
export const GRAPHICS_STATE_KEYS=Object.freeze(['uTime','uChaos','uEnergy','uHue','uAudio','uGravity','uSunPosition','uMoonPosition','uPlayerPos','uWarp','uSunVisible','uFrame']);
export function createGraphicsState(){
  return {uTime:0,uChaos:0,uEnergy:1,uHue:0,uAudio:0,uGravity:1,uSunPosition:[0,1,0],uMoonPosition:[0,-1,0],uPlayerPos:[0,0,0],uWarp:0,uSunVisible:0,uFrame:0};
}
const ss=(a,b,x)=>{const t=Math.min(1,Math.max(0,(x-a)/(b-a)));return t*t*(3-2*t);};
/** The pack's sun gate (DERIVED): smoothstep(-2,6,elev) * on_screen * (1 - occluded). ndc is the sun's projected [x,y] (or null if behind). */
export function sunVisible(elevDeg,ndc,occluded=0){
  if(!ndc||!isFinite(ndc[0])||!isFinite(ndc[1]))return 0;
  const on=ss(1.3,0.9,Math.max(Math.abs(ndc[0]),Math.abs(ndc[1])));
  return ss(-2,6,elevDeg)*on*(1-Math.min(1,Math.max(0,occluded)));
}
const SEED=seedFrom(P1POST.seed.stream);
/** Grain seed for a frame: a 32-bit hash of the pack seed and the frame counter, as a float in [0,1). Never Math.random. */
export function grainSeed(frame){let h=(SEED^Math.imul((frame>>>0)+1,0x9E3779B1))>>>0;h^=h>>>16;h=Math.imul(h,0x85EBCA6B)>>>0;h^=h>>>13;h=Math.imul(h,0xC2B2AE35)>>>0;h^=h>>>16;return (h>>>0)/4294967296;}
/** One step of the shared state from engine values. Pure: returns a new object. */
export function stepGraphicsState(prev,{time,frame,sunDir,moonDir,sunElevDeg,sunNdc,occluded=0,playerPos,chaos=0,hue=0,audio=0}){
  return {...prev,uTime:+time||0,uFrame:frame>>>0,uSunPosition:sunDir?[...sunDir]:prev.uSunPosition,uMoonPosition:moonDir?[...moonDir]:prev.uMoonPosition,
    uPlayerPos:playerPos?[...playerPos]:prev.uPlayerPos,uChaos:Math.min(1,Math.max(0,+chaos||0)),uHue:+hue||0,uAudio:Math.min(1,Math.max(0,+audio||0)),
    uSunVisible:sunVisible(sunElevDeg,sunNdc,occluded)};
}
