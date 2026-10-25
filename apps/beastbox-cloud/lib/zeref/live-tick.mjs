/**
 * LIVE PER-SECOND TICK for the beast diary. A universe never stops receiving signal.
 *
 * Pure and deterministic: no clock, no Math.random, no network. The caller passes `nowMs`.
 * The state is a function of (last RECORDED diary tick, elapsed whole seconds), seeded from the existing diary
 * state (beast id, recorded tick, xp, signals, recent xp gains). Because it is computed from the clock rather than
 * accumulated, a tab that was hidden (or a background run that restarts) catches up exactly: second N is always second N.
 *
 * Honest labels: per-second growth is SIMULATED interpolation toward the next recorded step; the RECORDED chain still
 * advances only with real diary ticks, and the IBM birth spark is RECORDED. This is not a live quantum link and
 * does not replace or rewrite the hash-chained diary.
 * Arithmetic uses only + - * / and integer hashes (no sin/exp) so every JS engine gives identical results.
 */
import {sha256Hex} from '../../public/spark/sha.mjs';
export const LIVE_TICK_SCHEMA='beast-live-tick/v1';
export const LIVE_CADENCE_S=1800;
export const LIVE_MAX_SECONDS=30*86400;
export const LIVE_LABELS=Object.freeze({
 live:'LIVE · SIMULATED. Per-second growth is a deterministic simulation seeded from the last recorded diary tick; it does not replace the recorded entries.',
 recorded:'Recorded ticks are the real hash-chained diary entries. The IBM birth spark is RECORDED; the Rigetti growth circuits are SIMULATED.'
});
const clamp=(v,lo,hi)=>Math.min(hi,Math.max(lo,v));
const r2=v=>Math.round(v*100)/100,r4=v=>Math.round(v*1e4)/1e4;
function hash32(text){let h=0x811c9dc5;for(let i=0;i<text.length;i++){h^=text.charCodeAt(i);h=Math.imul(h,0x01000193);}return h>>>0;}
/** Build the live base from /api/zeref/diary JSON or the loop's state.json (+ optional recent entries). Returns null if there is no real recorded tick. */
export function liveBase(d){
 if(!d||typeof d!=='object')return null;
 const at=Date.parse(d.last_tick_at||'');
 if(!Number.isFinite(at))return null;
 const entries=Array.isArray(d.recent)?d.recent:[];
 const gains=entries.map(e=>Number(e?.xp_gain)).filter(g=>Number.isFinite(g)&&g>=0).slice(0,12);
 const avg_gain=gains.length?gains.reduce((s,g)=>s+g,0)/gains.length:10;
 const sig={};for(const [k,v] of Object.entries(d.signals||{}))if(Number.isFinite(Number(v)))sig[k]=Number(v);
 return {beast_id:String(d.identity?.beast_id||d.beast_id||'beast'),tick:Math.max(0,Math.floor(Number(d.tick)||0)),xp:Number(d.xp)||0,last_tick_at_ms:at,signals:sig,avg_gain:r4(avg_gain)};
}
/** Smooth deterministic wander for one signal: linear interpolation between per-7-second hashed anchors, within +-3 of the recorded value. */
function wander(base,key,sec){
 const P=7,a=Math.floor(sec/P),f=(sec-a*P)/P;
 const h=i=>((hash32(base.beast_id+':'+key+':'+i)%2001)-1000)/1000;
 return base.signals[key]+3*(h(a)+(h(a+1)-h(a))*f);
}
/** The live state for an absolute time. Same inputs, same output, on the page and in the background run. */
export function liveSecond(base,nowMs){
 const sec=clamp(Math.floor((nowMs-base.last_tick_at_ms)/1000),0,LIVE_MAX_SECONDS);
 const signals={};for(const k of Object.keys(base.signals))signals[k]=r2(clamp(wander(base,k,sec),0,100));
 const gained=base.avg_gain*sec/(sec+LIVE_CADENCE_S);
 const xp=r4(base.xp+gained);
 return {schema:LIVE_TICK_SCHEMA,beast_id:base.beast_id,recorded_tick:base.tick,seconds_since_recorded:sec,xp_live:xp,xp_gain_live:r4(gained),signals,label:'SIMULATED'};
}
export function formatElapsed(sec){const h=Math.floor(sec/3600),m=Math.floor(sec%3600/60),s=sec%60;return `${h>0?h+'h ':''}${String(m).padStart(2,'0')}m ${String(s).padStart(2,'0')}s`;}
/** Rolling per-second hash chain used by the background run: proves the state advanced second by second without storing every second. */
export function chainStep(prev,snap){
 return sha256Hex(prev+'|'+snap.seconds_since_recorded+'|'+snap.xp_live+'|'+Object.keys(snap.signals).sort().map(k=>k+'='+snap.signals[k]).join(','));
}
/** Advance the chain over [fromSec,toSec] inclusive. Pure, so a restarted run recomputes the same head. */
export function advanceChain(base,prev,fromSec,toSec){
 let h=prev;for(let s=fromSec;s<=toSec;s++)h=chainStep(h,liveSecond(base,base.last_tick_at_ms+s*1000));return h;
}
export const CHAIN_GENESIS=(base)=>sha256Hex('beast-live-tick-genesis|'+base.beast_id+'|'+base.tick+'|'+base.last_tick_at_ms);
const LINES=Object.freeze(['Still here. The signal keeps arriving, one second at a time.','Another quiet stretch in the pocket. Nothing stops.','Listening. Small changes add up while no one is watching.','The universe keeps ticking, so I keep growing a little.']);
/** A deterministic diary line for a batch boundary (a template, not a model). */
export function liveDiaryLine(snap){return LINES[hash32(snap.beast_id+':line:'+snap.recorded_tick+':'+snap.seconds_since_recorded)%LINES.length];}
