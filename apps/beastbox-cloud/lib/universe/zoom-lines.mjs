// Emeth's zoom_out / zoom_in lines and creature_notices, picked deterministically (lwStream) and shown verbatim.
import {LW_LINES} from './living-world-lines.mjs';
import {lwStream} from './living-world.mjs';
export const STAGE_RANK={Surface:0,Planet:1,Orbit:2,System:3,Neighbours:4,Universe:5};
const pick=(arr,key)=>arr[Math.floor(lwStream(key)()*arr.length)%arr.length];
/** Which Emeth key a stage change earns (null = none). Going OUT: Planet=globe, Orbit=sun, System=planets, Neighbours=stars, Universe=black hole (only if one exists) else far out. Going IN: System=toward_stars, Orbit=toward_planet. */
export function zoomLineKind(prev,next,{blackHole=false}={}){
  if(prev===next||!(prev in STAGE_RANK)||!(next in STAGE_RANK))return null;
  const out=STAGE_RANK[next]>STAGE_RANK[prev];
  if(out)return {kind:'zoom_out',key:{Planet:'see_globe',Orbit:'see_sun',System:'see_planets',Neighbours:'see_stars',Universe:blackHole?'see_black_hole':'far_out'}[next]||null};
  return {kind:'zoom_in',key:{System:'toward_stars',Orbit:'toward_planet'}[next]||null};
}
/** Door: leaving the ground (doorV drops from 1) and arriving home (doorV reaches 1). */
export function doorLineKind(prevV,v){
  if(prevV>=0.999&&v<0.999)return {kind:'zoom_out',key:'leave_ground'};
  if(prevV<0.999&&v>=0.999)return {kind:'zoom_in',key:'arrive_home'};
  return null;
}
export function zoomLine(kind,key,seed,n=0){const pool=LW_LINES[kind]?.[key];if(!pool)return null;return pick(pool,`${seed}:zoomline:${kind}:${key}:${n}`);}
/** Emeth's creature_notices. {beast} is replaced with the active beast's name, nothing else changes. */
export const NOTICE_KEYS=Object.freeze(Object.keys(LW_LINES.creature_notices));
export function noticeLine(key,beast,seed,n=0){const pool=LW_LINES.creature_notices[key];if(!pool)return null;
  return pick(pool,`${seed}:notice:${key}:${n}`).split('{beast}').join(beast||'Your beast');}
/** One notice at a time and a quiet gap between them: returns the next gate state and whether this one may show. */
export function noticeGate(state,key,tMs,gapMs=20000,repeatMs=90000){
  const s=state||{lastAny:-1e12,last:{}};
  if(tMs-s.lastAny<gapMs||tMs-(s.last[key]??-1e12)<repeatMs)return {state:s,show:false};
  return {state:{lastAny:tMs,last:{...s.last,[key]:tMs}},show:true};
}
