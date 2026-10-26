// "My surroundings give the pocket universe life" (consent, per user, revocable). Numbers only.
// Pure: no DOM, storage, clock, network or random source. The pocket reads these derived numbers and tilts the SAME four
// sand wells that the Rigetti-SIMULATED receipt counts already weight (same recorded IBM seed). Nothing here is a waveform.
import {wellWeights} from '../pocket-sand.mjs';
import {seedFrom} from '../seeded-stream.mjs';
export const ENV_SCHEMA='beastbox-environment-numbers-v1';
export const ENV_FRESH_MS=15000;
export const STATES=Object.freeze(['MEASURED','off','denied','unavailable']);
export const LIGHT_SOURCES=Object.freeze(['ambient-light-sensor','camera-brightness']);
export const CHANNELS=Object.freeze(['light','sound','motion','heart']);
/** Visible labels. The world is a SIMULATION; only the environment numbers are measured, and only when the sensor really gave them. */
export const ENV_LABELS=Object.freeze({ibm_seed:'RECORDED',rigetti:'SIMULATED',environment:'MEASURED only when real',world_placement:'SEEDED'});
export const ENV_NOTE='IBM seed RECORDED · Rigetti SIMULATED · your surroundings MEASURED only when a sensor really reports · where the world places things is SEEDED. Numbers only: never audio, video or a heartbeat waveform.';
const r3=x=>Math.round(x*1000)/1000;
const num=(v,lo,hi)=>typeof v==='number'&&Number.isFinite(v)&&v>=lo&&v<=hi;
const KEYS={light:['state','level','source'],sound:['state','level'],motion:['state','level'],heart:['state','bpm','sqi']};
/** -> {ok,numbers,errors}. A channel that is not MEASURED carries no values at all (nothing is invented). */
export function validateEnvironment(raw){
 const errors=[];
 if(!raw||typeof raw!=='object'||Array.isArray(raw))return {ok:false,numbers:null,errors:['environment must be an object']};
 for(const k of Object.keys(raw))if(!CHANNELS.includes(k))errors.push('unknown field: '+String(k).slice(0,24));
 const numbers={schema:ENV_SCHEMA};
 for(const ch of CHANNELS){
  const c=raw[ch]===undefined?{state:'off'}:raw[ch];
  if(!c||typeof c!=='object'||Array.isArray(c)){errors.push(ch+' must be an object');continue;}
  for(const k of Object.keys(c))if(!KEYS[ch].includes(k))errors.push(ch+': unknown field '+String(k).slice(0,24));
  if(!STATES.includes(c.state)){errors.push(ch+': state must be one of '+STATES.join('/'));continue;}
  if(c.state!=='MEASURED'){const extra=Object.keys(c).filter(k=>k!=='state');if(extra.length)errors.push(ch+': '+c.state+' carries no numbers');numbers[ch]={state:c.state};continue;}
  if(ch==='heart'){
   if(!num(c.bpm,30,220)||!num(c.sqi,0.6,1))errors.push('heart: MEASURED needs bpm 30..220 and sqi 0.6..1 (otherwise: no valid pulse)');
   else numbers.heart={state:'MEASURED',bpm:r3(c.bpm),sqi:r3(c.sqi)};
  }else if(!num(c.level,0,1))errors.push(ch+': level must be a number 0..1');
  else if(ch==='light'){if(!LIGHT_SOURCES.includes(c.source))errors.push('light: source must be '+LIGHT_SOURCES.join('/'));else numbers.light={state:'MEASURED',level:r3(c.level),source:c.source};}
  else numbers[ch]={state:'MEASURED',level:r3(c.level)};
 }
 return errors.length?{ok:false,numbers:null,errors}:{ok:true,numbers,errors:[]};
}
const unit=(x,lo,hi)=>Math.max(0,Math.min(1,(x-lo)/(hi-lo)));
/** Channel -> sand well (the four wells the Rigetti counts '00','01','10','11' weight). Missing channel = neutral 1. */
export function wellMultipliers(numbers){
 const lv=[numbers?.light,numbers?.sound,numbers?.motion].map(c=>c&&c.state==='MEASURED'?c.level:null);
 const h=numbers?.heart&&numbers.heart.state==='MEASURED'?unit(numbers.heart.bpm,40,180):null;
 return [...lv,h].map(v=>v===null?1:r3(0.6+0.8*v));// 0.6..1.4, bounded
}
/** Same normalisation as the receipt weights (sum 4), then the environment tilt. counts null -> even weights tilted. */
export function environmentWeights(counts,numbers){
 const base=wellWeights(counts),m=wellMultipliers(numbers),w=base.map((b,i)=>b*m[i]),s=w.reduce((a,b)=>a+b,0);
 return s>0?w.map(x=>r3(4*x/s)):base;
}
/** Is any channel really measuring right now? (age is the caller's clock, passed in: this module has none.) */
export function isFresh(numbers,measuredAtMs,nowMs){
 if(!numbers||!Number.isFinite(measuredAtMs)||nowMs-measuredAtMs>ENV_FRESH_MS||nowMs<measuredAtMs-2000)return false;
 return CHANNELS.some(c=>numbers[c]&&numbers[c].state==='MEASURED');
}
/** Where the world PLACES things stays seeded: a per-user, per-label phase from the recorded IBM seed. */
export function seededPhase(label){return seedFrom('environment:'+String(label))/4294967296;}
/** Plain per-channel words for the panel; says so instead of inventing. */
export function describeChannel(ch,c){
 const name={light:'Light',sound:'Sound level',motion:'Motion',heart:'Heartbeat'}[ch];
 if(!c||c.state==='off')return name+': off';
 if(c.state==='denied')return name+': permission denied, not used';
 if(c.state==='unavailable')return name+': no valid reading on this device, not used';
 return ch==='heart'?name+': '+Math.round(c.bpm)+' bpm (measured snapshot)':name+': '+Math.round(c.level*100)+'% (measured)';
}
