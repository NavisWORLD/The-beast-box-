// Genesis motion. Pure function of seed + tick. The tick comes from the shared world clock.
// Reduced motion freezes every channel. This module does not write world, beast, or traveler state.
import {stream01} from './seed.ts';
import {ONE_WORLD_TICK_MS} from '../world/one-world-clock.mjs';

export const MOTION_LABEL='Genesis motion · SIMULATED';
/** Grass and trees are drawn by lib/look/foliage.ts from these hooks. */
export const FOLIAGE_IN_P1=true;
/**
 * Creature idle bob is not applied. The beast and the traveler are moved inside the living-world
 * frame, and writing their transforms would change that state. This look does not own that frame.
 */
export const CREATURE_MOTION=Object.freeze({
 applied:false,
 reason:'Idle bob would write beast and traveler transforms inside the living-world frame. That frame is owned by another change, so creature motion is skipped.',
});

export type MotionFrame={
 label:typeof MOTION_LABEL;
 reduced:boolean;
 tick:number;
 wavePhase:number;
 waveAmp:number;
 shoreRoll:number;
 hazePhase:number;
 hazeDensity:number;
 skyDrift:number;
 windPhase:number;
 windAmp:number;
 cloudPhase:number;
 treeSway:number;
 creature:null;
};

export function motionAt(seed:string,tick:number,reduced=false):MotionFrame{
 const t=reduced?0:(Number.isFinite(tick)?tick:0);
 const key=String(seed||'genesis');
 const wave0=stream01(key+':wave')*Math.PI*2;
 const shore0=stream01(key+':shore')*Math.PI*2;
 const haze0=stream01(key+':haze')*Math.PI*2;
 const sky0=stream01(key+':sky')*Math.PI*2;
 const wind0=stream01(key+':wind')*Math.PI*2;
 const cloud0=stream01(key+':cloud')*Math.PI*2;
 const tree0=stream01(key+':tree')*Math.PI*2;
 return {
  label:MOTION_LABEL,
  reduced:!!reduced,
  tick:t,
  wavePhase:t*1.15+wave0,
  waveAmp:reduced?0:.045,
  shoreRoll:t*.85+shore0,
  hazePhase:reduced?0:t*.21+haze0,
  hazeDensity:reduced?1:1+.06*Math.sin(t*.33+haze0),
  skyDrift:reduced?0:t*.04+sky0,
  windPhase:reduced?0:t*.7+wind0,
  windAmp:reduced?0:.15,
  cloudPhase:reduced?0:t*.05+cloud0,
  treeSway:reduced?0:Math.sin(t*.8+tree0),
  creature:null,
 };
}

/** Lateral grass lean. foliage.ts copies this into the grass shader. */
export function windSway(frame:MotionFrame,x:number,z:number){
 return Math.sin(frame.windPhase+x*.2+z*.17)*frame.windAmp;
}
/** P2 hook for drifting clouds. Not drawn in P1. */
export function cloudDrift(frame:MotionFrame){return frame.cloudPhase;}
/** Tree lean. foliage.ts copies this into the tree shader. */
export function treeSway(frame:MotionFrame){return frame.treeSway;}

/**
 * Fractional tick locked to the shared world tick and its period.
 * `tickChangedAtMs` is the presentation timestamp of the last tick edge. No timer is started here.
 */
export function presentationTick(worldTick:number,nowMs:number,tickChangedAtMs:number,reduced:boolean,period=ONE_WORLD_TICK_MS){
 if(reduced)return 0;
 const span=period>0?period:ONE_WORLD_TICK_MS;
 const frac=Math.max(0,Math.min(.999,(nowMs-tickChangedAtMs)/span));
 const base=Number.isFinite(worldTick)?worldTick:0;
 return base+frac;
}
