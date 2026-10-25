// Real IBM Bio Connection: the NUMBERS-ONLY packet. Raw video, audio and frames never appear here.
// Same idea and fields as the repo's existing feature packets (12-vector, packet_sha256, raw_* flags false).
// Pure and deterministic: no DOM, no clock, no unseeded randomness. Seeds come from the measured numbers.
import {PPG_RULES} from './ppg.mjs';
export const BIO_SCHEMA='beastbox-real-ibm-bio-connection-v1';
export const BIO_SOURCE='browser_ppg_fingertip';
export const BIO_HONESTY='Heartbeat MEASURED on this device by fingertip camera PPG (not a medical device). Only numbers leave the phone; raw video and audio are never stored or published. IBM spark RECORDED only after the run; Rigetti SIMULATED.';
export const BIO_VECTOR_CHANNELS=Object.freeze(['bpm','hrv_rmssd','sqi','red_ac_dc','red_mean','green_mean','blue_mean','audio_rms','audio_zcr','audio_centroid','ibi_regularity','measurement_hash']);
const clamp=(x,lo,hi)=>Math.max(lo,Math.min(hi,x));
const r4=x=>Math.round(x*1e4)/1e4;
const num=(x,d=0)=>Number.isFinite(x)?x:d;
/** Canonical JSON (sorted keys, compact). All numbers are rounded to 4 decimals so JS and Python agree byte for byte. */
export function canonical(v){if(Array.isArray(v))return '['+v.map(canonical).join(',')+']';if(v&&typeof v==='object')return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';return JSON.stringify(v);}
const RANGES={
  pulse:{bpm:[PPG_RULES.min_bpm,PPG_RULES.max_bpm],hrv_rmssd_ms:[0,300,true],sqi:[PPG_RULES.min_sqi,1],beats:[PPG_RULES.min_beats,400,'int'],duration_s:[PPG_RULES.min_duration_s,120],fs_hz:[20,60]},
  light:{red_mean:[0,255],green_mean:[0,255],blue_mean:[0,255],red_ac_dc:[0,1]},
  audio:{enabled:'bool',rms_mean:[0,1],zcr:[0,1],centroid_norm:[0,1]},
};
const TOP=['schema','source','heartbeat_label','honesty','pulse','light','audio','bio_vector_12','raw_audio_published','raw_video_published','raw_frames_in_packet','packet_sha256'];
const inRange=(v,[lo,hi,opt])=>typeof v==='number'&&Number.isFinite(v)&&v>=lo&&v<=hi&&(opt!=='int'||Number.isInteger(v));
/** Strict validation. Returns {ok,errors}. Unknown keys, strings other than the fixed constants, and any array other than the 12-vector are rejected. */
export function validateBioPacket(p){
  const errors=[];const e=m=>errors.push(m);
  if(!p||typeof p!=='object'||Array.isArray(p))return {ok:false,errors:['not an object']};
  if(Object.keys(p).sort().join()!==[...TOP].sort().join())e('unexpected or missing top-level keys');
  if(p.schema!==BIO_SCHEMA)e('schema');if(p.source!==BIO_SOURCE)e('source');if(p.heartbeat_label!=='MEASURED')e('heartbeat_label');if(p.honesty!==BIO_HONESTY)e('honesty');
  if(p.raw_audio_published!==false||p.raw_video_published!==false||p.raw_frames_in_packet!==false)e('raw flags must be false');
  if(!/^[a-f0-9]{64}$/.test(String(p.packet_sha256)))e('packet_sha256');
  for(const [grp,spec] of Object.entries(RANGES)){const o=p[grp];if(!o||typeof o!=='object'||Array.isArray(o)){e(grp+' missing');continue;}
    if(Object.keys(o).sort().join()!==Object.keys(spec).sort().join())e(grp+' keys');
    for(const [k,r] of Object.entries(spec)){const v=o[k];if(r==='bool'){if(typeof v!=='boolean')e(grp+'.'+k);}else if(v===null&&r[2]===true){/* HRV not available, never invented */}else if(!inRange(v,r))e(grp+'.'+k+' out of range');}}
  if(!Array.isArray(p.bio_vector_12)||p.bio_vector_12.length!==12||!p.bio_vector_12.every(v=>typeof v==='number'&&v>=.05&&v<=.95))e('bio_vector_12');
  if(JSON.stringify(p).length>1800)e('packet too large');
  return {ok:errors.length===0,errors};
}
/** The 12 seed channels, derived only from the measured numbers (0.05..0.95). The last channel is a hash of the measurement. */
export function bioVector12({pulse,light,audio},hashHex){
  const v=[(pulse.bpm-40)/160,pulse.hrv_rmssd_ms===null?.05:pulse.hrv_rmssd_ms/150,pulse.sqi,light.red_ac_dc*20,light.red_mean/255,light.green_mean/255,light.blue_mean/255,audio.enabled?audio.rms_mean:0,audio.enabled?audio.zcr:0,audio.enabled?audio.centroid_norm:0,pulse.ibi_regularity??pulse.sqi,parseInt(hashHex.slice(0,8),16)/2**32];
  return v.map(x=>r4(clamp(num(x,.05),.05,.95)));
}
/**
 * Build the packet from a VALID measurement. Throws if the pulse is not valid (never fabricate).
 * sha256Hex: async or sync function (string)=>hex, supplied by the caller (WebCrypto in the browser, node:crypto on the server).
 */
export async function buildBioPacket({ppg,light,audio=null},sha256Hex){
  if(!ppg||ppg.valid!==true)throw new Error('no valid pulse');
  const pulse={bpm:r4(ppg.bpm),hrv_rmssd_ms:ppg.hrv_rmssd_ms===null?null:r4(clamp(ppg.hrv_rmssd_ms,0,300)),sqi:r4(ppg.sqi),beats:ppg.beats,duration_s:r4(ppg.duration_s),fs_hz:r4(ppg.fs_hz)};
  const L={red_mean:r4(clamp(num(light?.red_mean),0,255)),green_mean:r4(clamp(num(light?.green_mean),0,255)),blue_mean:r4(clamp(num(light?.blue_mean),0,255)),red_ac_dc:r4(clamp(num(light?.red_ac_dc),0,1))};
  const A=audio&&audio.enabled?{enabled:true,rms_mean:r4(clamp(num(audio.rms_mean),0,1)),zcr:r4(clamp(num(audio.zcr),0,1)),centroid_norm:r4(clamp(num(audio.centroid_norm),0,1))}:{enabled:false,rms_mean:0,zcr:0,centroid_norm:0};
  const mh=await sha256Hex(canonical({pulse,light:L,audio:A}));
  const body={schema:BIO_SCHEMA,source:BIO_SOURCE,heartbeat_label:'MEASURED',honesty:BIO_HONESTY,pulse,light:L,audio:A,
    bio_vector_12:bioVector12({pulse:{...pulse,ibi_regularity:r4(clamp(1-num(ppg.ibi_cv,.25)/.25,0,1))},light:L,audio:A},mh),
    raw_audio_published:false,raw_video_published:false,raw_frames_in_packet:false};
  const packet_sha256=await sha256Hex(canonical(body));
  return {...body,packet_sha256};
}
/** Recompute packet_sha256 (server and workflow do this too). */
export async function packetHash(p,sha256Hex){const {packet_sha256,...body}=p;return sha256Hex(canonical(body));}
/**
 * The payload for the repo's EXISTING bio endpoint (/api/bridge/bio, action 'preview', source 'browser_sensor').
 * This is the same schema BioPanel submits (numeric channels only); it adds a new caller, it does not change the loop.
 */
export function existingBioInjection(p){
  const readings={heart_rate_bpm:p.pulse.bpm};if(p.pulse.hrv_rmssd_ms!==null)readings.hrv_rmssd_ms=p.pulse.hrv_rmssd_ms;
  return {action:'preview',source:'browser_sensor',consent:true,readings};
}
