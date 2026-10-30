// Visual Life Pass B6: event sounds. DEFAULT OFF, one toggle, EVENTS ONLY (boom, storm, growth); never background music or ambience.
// Two pure parts: detectEvents(state, ch) finds events from the engine's own channels (boom phase edge, storm tension crossing, mean growth step), counted in ENGINE ticks (no Date, no rAF state);
// recipe(kind, magnitude) turns an event into a small synth recipe whose loudness comes from the engine magnitude. The view owns the AudioContext, created only after the user turns the toggle on.
// Noise uses a seeded LCG, never Math.random. The boom is boom.mjs's SEEDED event; storm and growth are SIMULATED (stepped by the world loop).
export const SOUND=Object.freeze({
 stormEdges:[0.25,0.5,0.75],   // the pack's landfall thresholds of the ENGINE storm tension
 growthStep:0.02,              // mean growth must rise by this to chime
 minGapTicks:{boom:4,storm:24,growth:16},   // per-kind rate limit in engine ticks (4 Hz)
 maxGain:0.22,                 // a hard ceiling on any event
});
export const initialState=()=>({boomPhase:'none',stormBand:0,growthMark:null,last:{boom:-1e9,storm:-1e9,growth:-1e9}});
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
/** state + channels -> {state, events:[{kind,magnitude,tick}]}. ch = {tick, boomPhase:'none'|flash|shell|fade|remnant, boomTerm 0..1 (engine sky term), storm 0..1 (F.storm), grow (mean F.grow)}.
 *  Pure: returns a new state; the caller keeps it. A first call only primes the state (no event at load). */
export function detectEvents(state,ch){
 const S=state||initialState();const ev=[];const N={...S,last:{...S.last}};const tick=ch.tick|0;
 const ok=k=>tick-S.last[k]>=SOUND.minGapTicks[k];
 // boom: the flash edge and the shell edge (phase changes of boom.mjs boomState)
 const ph=ch.boomPhase||'none';
 if(S.primed&&ph!==S.boomPhase&&(ph==='flash'||ph==='shell')&&ok('boom')){ev.push({kind:ph==='flash'?'boom':'boom_shell',magnitude:clamp(ch.boomTerm||0,0,1),tick});N.last.boom=tick;}
 N.boomPhase=ph;
 // storm: tension crosses an edge upward
 let band=0;for(const e of SOUND.stormEdges)if(ch.storm>=e)band++;
 if(S.primed&&band>S.stormBand&&ok('storm')){ev.push({kind:'storm',magnitude:clamp(ch.storm,0,1),tick});N.last.storm=tick;}
 N.stormBand=band;
 // growth: mean growth rises one step above the last mark
 if(S.growthMark==null)N.growthMark=ch.grow;
 else if(ch.grow>=S.growthMark+SOUND.growthStep){if(S.primed&&ok('growth')){ev.push({kind:'growth',magnitude:clamp((ch.grow-S.growthMark)/SOUND.growthStep*0.5,0.2,1),tick});N.last.growth=tick;}N.growthMark=ch.grow;}
 else if(ch.grow<S.growthMark-SOUND.growthStep)N.growthMark=ch.grow;
 N.primed=true;
 return {state:N,events:ev};
}
/** A small synth recipe: {parts:[{wave,freq,freqEnd,at,dur,gain}], noise:{dur,gain,lp}|null}. Gain scales with the engine magnitude and is capped. */
export function recipe(kind,magnitude){
 const m=clamp(+magnitude||0,0,1),g=SOUND.maxGain*(0.25+0.75*m);
 switch(kind){
  case 'boom':return {kind,parts:[{wave:'sine',freq:90,freqEnd:34,at:0,dur:1.1,gain:g}],noise:{dur:0.5,gain:g*0.6,lp:900}};
  case 'boom_shell':return {kind,parts:[{wave:'sine',freq:52,freqEnd:38,at:0,dur:2.2,gain:g*0.6}],noise:{dur:1.6,gain:g*0.25,lp:300}};
  case 'storm':return {kind,parts:[{wave:'sine',freq:60,freqEnd:42,at:0,dur:1.8,gain:g*0.5}],noise:{dur:1.8,gain:g*0.7,lp:420}};
  case 'growth':return {kind,parts:[{wave:'sine',freq:523.25,freqEnd:523.25,at:0,dur:0.5,gain:g*0.5},{wave:'sine',freq:783.99,freqEnd:783.99,at:0.12,dur:0.6,gain:g*0.4}],noise:null};
  default:return null;
 }
}
/** Seeded noise samples in -1..1 (LCG), so the same event sounds the same. */
export function noiseSamples(n,seed=1){let x=(seed>>>0)||1;const o=new Float32Array(n);for(let i=0;i<n;i++){x=(Math.imul(x,1664525)+1013904223)>>>0;o[i]=x/2147483648-1;}return o;}
