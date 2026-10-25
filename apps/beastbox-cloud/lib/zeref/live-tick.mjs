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
 * Arithmetic uses only + - * / and integer hashes (no sin/exp) so every JS engine gives identical results
 * (the CST engine below adds Math.sqrt of 5 for φ, Math.abs, Math.min/max: all exact/correctly rounded in IEEE-754).
 *
 * ENGINES (SIMULATED either way). The per-second wiggle of each recorded signal comes from:
 *  - 'cst' (default when the diary has signals): the CST integrator `stepCSTState` (Lorenz + coherence + Hebbian relaxation,
 *    with the opt-in ψ MODEL nudge) is driven by the RECORDED signals (energy→arousal, resonance→valence, signal/memory→curiosity),
 *    settled for a fixed warm-up, then stepped CST_SUBSTEPS times per live second. The displayed signal is
 *    recorded ± 3 where the offset is the movement of one CST channel since second 0. Second N is still always second N: the
 *    state is a pure function of (base, N) (a per-base cursor only caches it; going backwards recomputes from second 0).
 *    Integration is bounded: past CST_MAX_SECONDS (1 day without a new recorded tick) it falls back to
 *  - 'wander' (the previous engine, kept unchanged as the fallback): hash-anchored interpolation within ±3.
 * Lorenz dt note: stepCSTState integrates the Lorenz system at dt·0.35, the Sim Earth reference at dt·0.035 (see
 * docs/CST_PSI_MODEL.md). Here dt = 0.05 and 6 substeps per second, so one live second ≈ 0.105 Lorenz time units. A model tempo
 * choice, not a calibration.
 */
import {sha256Hex} from '../../public/spark/sha.mjs';
import {createCSTState,stepCSTState,clamp as clamp01} from '../physics/cst-integrator.mjs';
export const LIVE_TICK_SCHEMA='beast-live-tick/v1';
export const LIVE_TICK_SCHEMA_CST='beast-live-tick/v2';
export const CST_SUBSTEPS=6,CST_DT=.05,CST_WARMUP_STEPS=600,CST_MAX_SECONDS=86400,CST_AMPLITUDE=3;
const CST_OPTS=Object.freeze({psi:true}); // ψ is MODEL: bounded ±0.05 nudge on the coherence/Hebbian targets
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
export function liveBase(d,{engine}={}){
 if(!d||typeof d!=='object')return null;
 const at=Date.parse(d.last_tick_at||'');
 if(!Number.isFinite(at))return null;
 const entries=Array.isArray(d.recent)?d.recent:[];
 const gains=entries.map(e=>Number(e?.xp_gain)).filter(g=>Number.isFinite(g)&&g>=0).slice(0,12);
 const avg_gain=gains.length?gains.reduce((s,g)=>s+g,0)/gains.length:10;
 const sig={};for(const [k,v] of Object.entries(d.signals||{}))if(Number.isFinite(Number(v)))sig[k]=Number(v);
 return {beast_id:String(d.identity?.beast_id||d.beast_id||'beast'),tick:Math.max(0,Math.floor(Number(d.tick)||0)),xp:Number(d.xp)||0,last_tick_at_ms:at,signals:sig,avg_gain:r4(avg_gain),
  engine:engine==='wander'||!Object.keys(sig).length?'wander':'cst'};
}
/** Smooth deterministic wander for one signal: linear interpolation between per-7-second hashed anchors, within +-3 of the recorded value. */
function wander(base,key,sec){
 const P=7,a=Math.floor(sec/P),f=(sec-a*P)/P;
 const h=i=>((hash32(base.beast_id+':'+key+':'+i)%2001)-1000)/1000;
 return base.signals[key]+3*(h(a)+(h(a+1)-h(a))*f);
}
// ---------------------------------------------------------------- CST engine (SIMULATED, driven by the recorded signals)
const num=(v)=>Number.isFinite(v)?v:undefined;
/** Recorded 0..100 signals → CST emotion inputs (0..1). Missing channels are simply not driven. */
function cstEmotion(base){
 const v=Object.values(base.signals),mean=v.length?v.reduce((a,b)=>a+b,0)/v.length:50,g=(...ks)=>{for(const k of ks)if(k in base.signals)return base.signals[k];return mean;};
 return {arousal:num(g('energy')/100),valence:num(g('resonance','warmth')/100),curiosity:num(g('curiosity','signal','memory')/100)};
}
/** Which CST quantity moves each recorded signal. Spans = observed ranges of each source, so ±1 maps to ±CST_AMPLITUDE. */
const SOURCE_SPAN=Object.freeze({chaos:.5,lorenz_x:.6,instability:.25,coherence:.08,resonance:.05,hebb:.03});
const SOURCE_FOR=Object.freeze({energy:'chaos',signal:'lorenz_x',memory:'coherence',resonance:'resonance'});
const SOURCE_KEYS=Object.freeze(['chaos','lorenz_x','instability','coherence','resonance','hebb']);
const sourceOf=key=>SOURCE_FOR[key]||SOURCE_KEYS[hash32('src:'+key)%SOURCE_KEYS.length];
const readSources=S=>({chaos:S.ch.chaos,lorenz_x:clamp01(.5+S.L.x/40),instability:S.ch.instability,coherence:S.ch.coherence,resonance:S.ch.resonance,hebb:S.hebb});
const CURSORS=new WeakMap(); // per-base cache only: results never depend on it
function cstAt(base,sec){
 let c=CURSORS.get(base);
 if(!c||c.sec>sec){
  const emotion=cstEmotion(base),S=createCSTState(base.beast_id+':'+base.tick,{emotion});
  for(let i=0;i<CST_WARMUP_STEPS;i++)stepCSTState(S,CST_DT,emotion,CST_OPTS);
  c={sec:0,S,emotion,s0:readSources(S)};CURSORS.set(base,c);
 }
 while(c.sec<sec){for(let i=0;i<CST_SUBSTEPS;i++)stepCSTState(c.S,CST_DT,c.emotion,CST_OPTS);c.sec++;}
 return c;
}
function cstSignals(base,sec){
 const c=cstAt(base,sec),now=readSources(c.S),signals={};
 for(const k of Object.keys(base.signals)){const src=sourceOf(k);signals[k]=r2(clamp(base.signals[k]+CST_AMPLITUDE*clamp((now[src]-c.s0[src])/SOURCE_SPAN[src],-1,1),0,100));}
 return {signals,cst:{coherence:r4(c.S.ch.coherence),chaos:r4(c.S.ch.chaos),hebb:r4(c.S.hebb),label:'SIMULATED · ψ nudge is MODEL'}};
}
/** True when this base/second is produced by the CST engine (else the hash-wander fallback). */
export const usesCst=(base,sec)=>base.engine==='cst'&&sec<=CST_MAX_SECONDS;
/** The live state for an absolute time. Same inputs, same output, on the page and in the background run. */
export function liveSecond(base,nowMs){
 const sec=clamp(Math.floor((nowMs-base.last_tick_at_ms)/1000),0,LIVE_MAX_SECONDS);
 const gained=base.avg_gain*sec/(sec+LIVE_CADENCE_S);
 const xp=r4(base.xp+gained);
 if(usesCst(base,sec)){const {signals,cst}=cstSignals(base,sec);
  return {schema:LIVE_TICK_SCHEMA_CST,engine:'cst',beast_id:base.beast_id,recorded_tick:base.tick,seconds_since_recorded:sec,xp_live:xp,xp_gain_live:r4(gained),signals,cst,label:'SIMULATED'};}
 const signals={};for(const k of Object.keys(base.signals))signals[k]=r2(clamp(wander(base,k,sec),0,100));
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
export const CHAIN_GENESIS=(base)=>sha256Hex('beast-live-tick-genesis|'+(base.engine==='cst'?'cst/v2|':'')+base.beast_id+'|'+base.tick+'|'+base.last_tick_at_ms);
const LINES=Object.freeze(['Still here. The signal keeps arriving, one second at a time.','Another quiet stretch in the pocket. Nothing stops.','Listening. Small changes add up while no one is watching.','The universe keeps ticking, so I keep growing a little.']);
/** A deterministic diary line for a batch boundary (a template, not a model). */
export function liveDiaryLine(snap){return LINES[hash32(snap.beast_id+':line:'+snap.recorded_tick+':'+snap.seconds_since_recorded)%LINES.length];}
