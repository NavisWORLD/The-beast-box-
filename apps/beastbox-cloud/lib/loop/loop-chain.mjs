/**
 * ZEREF'S NEVER-ENDING LOOP — one clock, one chain, no pauses.
 *
 * Every call to stepLoop() advances the loop by exactly one tick. The tick carries state forward
 * (each creature's own brain state, the world well weights, the chain head) and mixes in whatever
 * real inputs exist at that moment:
 *   - MEASURED  fingertip pulse numbers (only when a sensor really gave them),
 *   - RECORDED  the IBM heart seed (v9 by default) that the chain starts from,
 *   - SIMULATED Rigetti tick counts from the simulator,
 *   - the creatures' brain state, the world state, and the hash of the previous event.
 *
 * Surprise moments come out of the chaotic, state-dependent dynamics (a coupled logistic map per
 * creature, kicked by the chain hash). There is NO Math.random and no clock here: the sequence is
 * deterministic given its inputs, but nobody can foresee it without running it. A moment is never
 * called "quantum random": it carries a SEEDED or SIMULATED label and a provenance line.
 *
 * Pure: no DOM, storage, network or clock. Every creature has its own brain state.
 */
import {canonicalJson} from '../../public/spark/genome.mjs';
import {sha256Hex} from '../../public/spark/sha.mjs';
import {makeRecord} from '../zeref/experience-record.mjs';

export const LOOP_SCHEMA='zeref-loop/v1';
export const TICK_SECONDS=1; // the one clock: sim seconds = tick * TICK_SECONDS
export const KEEP_MOMENTS=24;
export const LOOP_LABELS=Object.freeze({
 pulse:'MEASURED (only when a real sensor gave a number)',
 ibm_seed:'RECORDED on IBM hardware (never re-run)',
 rigetti:'SIMULATED (Rigetti simulator, not physical hardware)',
 placement:'SEEDED (the same inputs always place things the same way)',
 theory:'12D model simulation'
});
export const MOMENT_KINDS=Object.freeze([
 {kind:'spin-ripple',text:c=>`${c} spun twice; the sand rippled`},
 {kind:'odd-hum',text:c=>`${c} hummed toward the pocket wall`},
 {kind:'sand-spiral',text:c=>`Sand curled into a spiral near ${c}`},
 {kind:'pebble-carry',text:c=>`${c} carried a pebble across the pocket`},
 {kind:'color-flicker',text:c=>`A new color flickered in ${c}'s trail`},
 {kind:'stranger-shadow',text:c=>`A shadow crossed the pocket near ${c}`},
 {kind:'sudden-leap',text:c=>`${c} leapt, then looked around`}
]);
const r9=x=>Math.round(x*1e9)/1e9;
const clamp=(x,lo,hi)=>Math.min(hi,Math.max(lo,x));
const unit=(hex,i)=>parseInt(hex.slice((i%8)*8,(i%8)*8+8),16)/4294967296; // 8 hex chars -> [0,1)
const short=h=>String(h||'').slice(0,8);

/** Normalise the tick's inputs. Anything not really measured stays null (never invented). */
export function normalizeInputs(inp={}){
 const p=inp?.pulse,ok=p&&Number.isFinite(Number(p.bpm))&&Number(p.bpm)>30&&Number(p.bpm)<220&&(p.sqi==null||Number(p.sqi)>=.5);
 const a=inp?.audio,aok=a&&Number.isFinite(Number(a.rms_mean));
 const t=Number.isInteger(inp?.rigetti_ticks)&&inp.rigetti_ticks>0?Math.min(inp.rigetti_ticks,1e6):0;
 return {
  pulse:ok?{bpm:r9(Number(p.bpm)),hrv_rmssd_ms:Number.isFinite(Number(p.hrv_rmssd_ms))?r9(Number(p.hrv_rmssd_ms)):null,sqi:p.sqi==null?null:r9(Number(p.sqi))}:null,
  audio:aok?{rms_mean:r9(Number(a.rms_mean))}:null,
  rigetti_ticks:t
 };
}

/** Start a loop from a RECORDED seed (hex). Same seed + same creatures => same start. */
export function createLoop({seed,seedLabel='IBM heart seed v9',creatures=[{id:'bb-deada969',name:'Zeref'}]}={}){
 if(!/^[0-9a-f]{64}$/.test(String(seed||'')))throw Error('loop: seed must be a 64-hex recorded seed');
 const head=sha256Hex(canonicalJson({schema:LOOP_SCHEMA,seed,ids:creatures.map(c=>c.id)}));
 const list=creatures.map((c,i)=>({id:c.id,name:c.name||c.id,brain:[0,1,2,3].map(j=>r9(.05+.9*unit(sha256Hex(head+c.id),j+i)))}));
 return {schema:LOOP_SCHEMA,seed,seed_label:seedLabel,tick:0,sim_seconds:0,head,last_moment_hash:head,creatures:list,wells:[1,1,1,1],moments:[],moments_total:0};
}

const normWells=w=>{const s=w.reduce((a,b)=>a+b,0);return w.map(x=>r9(4*x/s));};

/** Advance exactly one tick. Never idles: always returns a new state with tick+1. */
export function stepLoop(state,inputs={}){
 const inp=normalizeInputs(inputs),tick=state.tick+1;
 const mix=sha256Hex(canonicalJson({prev:state.head,tick,inp,brains:state.creatures.map(c=>[c.id,c.brain]),wells:state.wells,last:state.last_moment_hash}));
 const eps=clamp((inp.pulse?clamp((inp.pulse.bpm-60)/80,0,1)*.2:0)+Math.min(.1,inp.rigetti_ticks*.01)+(inp.audio?clamp(inp.audio.rms_mean*20,0,.05):0),0,.3);
 const creatures=state.creatures.map((c,ci)=>{
  const r=3.7+.29*unit(mix,ci),cpl=.15+eps;
  const brain=c.brain.map((x,j)=>{
   const xn=c.brain[(j+1)%4],f=v=>r*v*(1-v);
   const kick=(unit(mix,ci+j+2)-.5)*2e-3; // tiny hash kick keeps the map off fixed points; still pure
   return r9(clamp((1-cpl)*f(x)+cpl*f(xn)+kick,.001,.999));
  });
  return {...c,brain};
 });
 const arousal=creatures.reduce((a,c)=>a+c.brain.reduce((s,x)=>s+x,0)/4,0)/Math.max(1,creatures.length);
 const p=clamp(.02+.12*arousal+(inp.pulse?.02*(inp.pulse.sqi??1):0),0,.3);
 // the world follows the first creature's brain, nudged each tick
 const lead=creatures[0]?.brain||[.5,.5,.5,.5];
 let wells=state.wells.map((w,i)=>.9*w+.1*(1+(lead[i]-.5)));
 let moment=null,last=state.last_moment_hash;
 if(creatures.length&&unit(mix,0)<p){
  const ci=Math.floor(unit(mix,1)*creatures.length),kind=MOMENT_KINDS[Math.floor(unit(mix,2)*MOMENT_KINDS.length)],well=Math.floor(unit(mix,3)*4);
  const c=creatures[ci];
  c.brain=c.brain.map((x,j)=>r9(clamp(x+(j===well?.08:-.02),.001,.999)));
  wells[well]+=.5;
  const label=inp.rigetti_ticks>0?'SIMULATED':'SEEDED';
  const prov=[`tick ${tick}`,inp.pulse?`pulse MEASURED ${inp.pulse.bpm} bpm`:'pulse none',`Rigetti ticks SIMULATED ${inp.rigetti_ticks}`,`${state.seed_label} RECORDED ${short(state.seed)}`,`chain ${short(mix)}`,`prev moment ${short(state.last_moment_hash)}`].join(' · ');
  const body={schema:'zeref-loop-moment/v1',tick,sim_seconds:tick*TICK_SECONDS,kind:kind.kind,creature:c.id,text:kind.text(c.name),effect:{well,weight_delta:.5},
   label,measured_input:Boolean(inp.pulse),provenance:prov,prev_hash:state.last_moment_hash};
  moment={...body,hash:sha256Hex(canonicalJson(body))};
  last=moment.hash;
 }
 wells=normWells(wells);
 return {...state,tick,sim_seconds:tick*TICK_SECONDS,head:mix,last_moment_hash:last,creatures,wells,
  moments:moment?[...state.moments,moment].slice(-KEEP_MOMENTS):state.moments,moments_total:state.moments_total+(moment?1:0)};
}

/** Run n ticks back to back (no waits). `inputsFor(tick)` supplies that tick's real inputs. */
export function runLoop(state,n,inputsFor=()=>({})){
 let s=state;for(let i=0;i<n;i++)s=stepLoop(s,inputsFor(s.tick+1)||{});return s;
}

/** The moment chain is self-verifying: each hash covers its body and points at the previous moment. */
export function verifyMoments(moments,startHash=null){
 let prev=startHash;
 for(let i=0;i<moments.length;i++){
  const {hash,...body}=moments[i];
  if(sha256Hex(canonicalJson(body))!==hash)return {ok:false,reason:'hash',index:i};
  if(prev!==null&&body.prev_hash!==prev)return {ok:false,reason:'chain',index:i};
  if(/quantum random/i.test(body.text+body.provenance+body.label))return {ok:false,reason:'label',index:i};
  prev=hash;
 }
 return {ok:true,count:moments.length,head:prev};
}

/** Well weights for the pocket universe (feed to field.setEnvironment; opt-in). Sum is 4. */
export const loopWellWeights=state=>[...state.wells];

/** A moment as a chat/diary/world line with its provenance. */
export const momentLine=m=>`${m.text} [${m.label}] ${m.provenance}`;

/**
 * A moment as an experience record in the existing canonical format (public game event scope).
 * Provenance only: this does not add anything to the training mix by itself.
 */
export function momentRecord(m,{prev=null}={}){
 return makeRecord({qbeast_id:m.creature,origin:'deterministic_pocket_simulation',step:m.tick,
  observation:{kind:'loop-moment',creature_brain_tick:m.tick},decision:{policy:'zeref-loop/v1'},action:{key:'WAIT'},
  outcome:{kind:m.kind,observed:true,label:m.label,well:m.effect.well},
  reward:{kind:'computed_reward',value:0,rule:'loop moments carry no reward'},
  labels:[{kind:'observed_outcome',value:m.kind,by:'zeref-loop/v1'}],source:{ref:'zeref-loop/v1',sha256:m.hash},prev});
}
