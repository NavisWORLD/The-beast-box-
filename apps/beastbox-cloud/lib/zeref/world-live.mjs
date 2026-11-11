/**
 * WORLD LIVE LINKS: one honest read of every loop that should be flowing into the world.
 * Pure and deterministic: no clock, no Math.random, no network. The caller passes `nowMs` and the already-fetched records.
 *
 *  - spark     : Rigetti SIMULATED ticks (zeref-spark branch, bb-deada969), about one per minute.
 *  - liveTick  : the per-second SIMULATED tick, committed in 10-minute batches (zeref-live-tick branch).
 *  - diary     : the RECORDED hash-chained diary (zeref-diary branch), nominally every 30 minutes.
 *  - brain     : the live RAWRPHØS pin (step + checkpoint prefix; changes only through a reviewed promotion PR).
 *
 * A link is CONNECTED only while its newest record is younger than its stale-after window; otherwise STALE (old but readable)
 * or DOWN (unreadable). Nothing is invented to fill a gap, and numbers only: no counts of private signals, no raw audio, no tokens.
 *
 * Stall reporting (2026-11-06): when a link is STALE/DOWN it carries a `stall` object (age, stale_after, cause) so the world
 * feed never looks like a silent freeze. Recovery (re-reading the real tip) lives in the route; this module never synthesises ticks.
 */
export const WORLD_LIVE_SCHEMA='beast-world-live/v1';
export const STALE_AFTER_S=Object.freeze({spark:180,liveTick:1500,diary:5400});
export const LOCAL_SIM_LABEL='LOCAL SIMULATED (runner statevector, not Rigetti, not a QPU)';
export const WORLD_LIVE_LABELS=Object.freeze({
 spark:'Rigetti SIMULATED (rigetti.sim.qvm, not a QPU)',
 localSim:LOCAL_SIM_LABEL,
 liveTick:'SIMULATED (per-second tick, deterministic)',
 diary:'RECORDED (hash-chained diary; its growth circuit is Rigetti SIMULATED)',
 brain:'RAWRPHØS pinned checkpoint (a 12D model simulation; not a claim of awareness)'
});
/** Branch + file pairs the route reads. Hosts stay in the route so this module stays free of network strings. */
export const WORLD_LIVE_PATHS=Object.freeze({
 spark:{branch:'zeref-spark',file:'zeref/latest.json'},
 localSpark:{branch:'zeref-spark',file:'zeref/local-sim/latest.json'},
 liveTick:{branch:'zeref-live-tick',file:'live/latest.json'},
 liveHead:{branch:'zeref-live-tick',file:'live/head.json'},
 diary:{branch:'zeref-diary',file:'zeref/latest.json'}
});
const HEX=/^[0-9a-f]{64}$/;
const SHA1=/^[0-9a-f]{40}$/;
const r4=v=>Math.round(v*1e4)/1e4;
/** Age in whole seconds, or null when the timestamp is missing / invalid / in the future by more than a minute. */
export function ageSeconds(nowMs,atMs){
 if(!Number.isFinite(nowMs)||!Number.isFinite(atMs))return null;
 const d=(nowMs-atMs)/1000;
 return d<-60?null:Math.max(0,Math.floor(d));
}
export function linkState(age,staleAfter){
 if(age===null||age===undefined)return 'DOWN';
 return age<=staleAfter?'CONNECTED':'STALE';
}
/** Per-bit marginals, odd-parity share and normalised entropy of a 3-qubit counts record. null for anything malformed. */
export function countsFeatures(counts){
 if(!counts||typeof counts!=='object')return null;
 const keys=Object.keys(counts);if(!keys.length)return null;
 let n=0;
 for(const k of keys){const v=counts[k];if(!/^[01]{3}$/.test(k)||!Number.isInteger(v)||v<0)return null;n+=v;}
 if(n<=0)return null;
 const p=[0,1,2].map(i=>keys.reduce((a,k)=>a+(k[i]==='1'?counts[k]:0),0)/n);
 const odd=keys.reduce((a,k)=>a+((k.split('1').length-1)%2?counts[k]:0),0)/n;
 let h=0;for(const k of keys){const q=counts[k]/n;if(q>0)h-=q*Math.log2(q);}
 return {p0:r4(p[0]),p1:r4(p[1]),p2:r4(p[2]),odd:r4(odd),entropy:r4(h/3),shots:n};
}
/** Relative path on a data branch: "zeref-spark/zeref/latest.json". */
export function branchRelPath(branch,file){
 if(typeof branch!=='string'||typeof file!=='string'||!branch||!file)return null;
 return branch+'/'+file;
}
/** Relative path pinned to a commit tip: "<40-hex>/zeref/latest.json". */
export function tipRelPath(sha,file){
 if(!SHA1.test(sha)||typeof file!=='string'||!file)return null;
 return sha+'/'+file;
}
/** Tip sha from git's public smart-HTTP ref advertisement (github.com/<repo>.git/info/refs?service=git-upload-pack).
 *  Fallback for when the unauthenticated REST API is rate-limited (60 req/h per shared egress IP). Exact ref only;
 *  null when absent (never invent). */
export function parseRefsTipSha(text,branch){
 if(typeof text!=='string'||typeof branch!=='string'||!/^[A-Za-z0-9._/-]{1,100}$/.test(branch))return null;
 const esc=branch.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
 const m=new RegExp('([0-9a-f]{40}) refs/heads/'+esc+'(?:\\u0000|\\n|$)').exec(text);
 return m&&SHA1.test(m[1])?m[1]:null;
}
/** Accept list-or-object commits API JSON; return the 40-char tip sha or null (never invent). */
export function parseTipSha(apiJson){
 const row=Array.isArray(apiJson)?apiJson[0]:apiJson;
 const sha=row&&typeof row==='object'?row.sha:null;
 return typeof sha==='string'&&SHA1.test(sha)?sha:null;
}
/**
 * Prefer the fresher REAL spark record. Never synthesises ticks; never rewrites hashes.
 * Returns `a`, `b`, or null. Invalid / wrong-beast records are dropped.
 */
export function pickFresherSpark(a,b,nowMs){
 const ok=s=>s&&s.simulated===true&&s.beast_id==='bb-deada969'&&Number.isInteger(s.tick)&&Number.isFinite(Number(s.at_epoch));
 const A=ok(a)?a:null,B=ok(b)?b:null;
 if(!A)return B;if(!B)return A;
 const ageA=ageSeconds(nowMs,Number(A.at_epoch)*1000),ageB=ageSeconds(nowMs,Number(B.at_epoch)*1000);
 if(ageA===null)return B;if(ageB===null)return A;
 if(ageB<ageA)return B;if(ageA<ageB)return A;
 return B.tick>=A.tick?B:A;
}
/** True when the spark record's age already exceeds one interval (CDN may be holding an old latest.json). */
export function sparkNeedsTipReread(spark,nowMs){
 const ok=spark&&spark.simulated===true&&spark.beast_id==='bb-deada969'&&Number.isInteger(spark.tick);
 if(!ok)return true;
 const age=ageSeconds(nowMs,Number(spark.at_epoch)*1000);
 if(age===null)return true;
 const interval=Number(spark.interval_target_s);
 const gap=Number.isFinite(interval)&&interval>0?interval:60;
 return age>gap;
}
function stall(age,staleAfter,cause,extra){
 return {age_s:age,stale_after_s:staleAfter,cause,...(extra||{})};
}
/**
 * Senses this document can speak for, and the ones it cannot.
 * Face and pulse stay ESTIMATE here: this read has no face packet and no fingertip packet.
 * Sight's world sky is DERIVED; a visitor device reading would be MEASURED, and neither is in this read.
 * Rigetti stays a SIMULATOR. Nothing here is a claim of awareness.
 */
export const SENSE_TRACE=Object.freeze([
 {id:'spark',label:'SIMULATED',in_this_read:true,note:'Rigetti is a SIMULATOR (rigetti.sim.qvm), not a QPU. These ticks are simulated, not live quantum computation.'},
 {id:'live_tick',label:'SIMULATED',in_this_read:true,note:'Per-second deterministic tick, saved in batches. Lag behind the diary tick is reported. This read does not write ticks.'},
 {id:'diary',label:'RECORDED',in_this_read:true,note:'Hash-chained diary. Its growth circuit is Rigetti SIMULATED.'},
 {id:'brain',label:'PINNED',in_this_read:true,note:'Reviewed promotion of a 12D model simulation. Not a claim of awareness.'},
 {id:'face',label:'ESTIMATE',in_this_read:false,note:'Not in this read. Face estimates are the sensor seat. This surface does not invent a face.'},
 {id:'pulse',label:'ESTIMATE',in_this_read:false,note:'Not in this read. A fingertip packet can be MEASURED on the bio path. This document has no packet, so it is not labelled MEASURED.'},
 {id:'sight',label:'DERIVED',in_this_read:false,note:'Not in this read. World sky is DERIVED. A visitor device reading would be MEASURED. Neither number is here.'},
]);
/** Diary tick minus the recorded live tick, when the live batch is behind. Equal ticks and a live tick ahead are not a stall. Missing ticks are not invented. */
export function liveDiaryLag(diaryTick,liveRecordedTick){
 if(!Number.isInteger(diaryTick)||!Number.isInteger(liveRecordedTick))return null;
 const lag=diaryTick-liveRecordedTick;
 if(lag<=0)return null;
 return {age_s:null,stale_after_s:null,cause:'live_tick_behind_diary',lag_ticks:lag,diary_tick:diaryTick,live_recorded_tick:liveRecordedTick};
}
function localRecordOk(local){
 return !!(local&&local.backend==='local-sim'&&local.label===LOCAL_SIM_LABEL&&local.simulated===true
  &&local.beast_id==='bb-deada969'&&local.status==='ok'&&Number.isInteger(local.tick)
  &&Number.isFinite(Number(local.at_epoch)));
}
function sparkLink(spark,nowMs,localSpark){
 const localOk=localRecordOk(localSpark);
 const localGood=localOk&&localSpark.last_ok&&typeof localSpark.last_ok==='object'?localSpark.last_ok:null;
 const localLast=localGood&&Number.isInteger(localGood.tick)?localGood.tick:(localOk?localSpark.tick:null);
 const localAge=localOk?ageSeconds(nowMs,Number(localSpark.at_epoch)*1000):null;
 const localFresh=localOk&&linkState(localAge,STALE_AFTER_S.spark)==='CONNECTED';
 const ok=spark&&spark.simulated===true&&spark.beast_id==='bb-deada969'&&Number.isInteger(spark.tick);
 if(!ok){
  if(localFresh){
   const feats=countsFeatures(localSpark.counts);
   return {state:'CONNECTED',source:'local-sim',label:LOCAL_SIM_LABEL,tick:localSpark.tick,age_s:localAge,
    last_ok_tick:null,local_last_ok_tick:localLast,last_ok_age_s:null,status:'local-sim',late:false,
    consecutive_failures:0,interval_target_s:Number(localSpark.interval_target_s)||60,
    counts_sha256:HEX.test(localSpark.counts_sha256||'')?localSpark.counts_sha256:null,features:feats,
    stale_after_s:STALE_AFTER_S.spark};
  }
  return {state:'DOWN',label:WORLD_LIVE_LABELS.spark,reason:'no Zeref spark record',
   stall:stall(null,STALE_AFTER_S.spark,'missing'),local_last_ok_tick:localLast};
 }
 const good=spark.last_ok&&typeof spark.last_ok==='object'?spark.last_ok:null;
 const goodAge=good?ageSeconds(nowMs,Number(good.at_epoch)*1000):null;
 const age=ageSeconds(nowMs,Number(spark.at_epoch)*1000);
 const feats=good?countsFeatures(good.counts):null;
 const state=linkState(age,STALE_AFTER_S.spark)==='CONNECTED'&&linkState(goodAge,STALE_AFTER_S.spark*5)==='CONNECTED'?'CONNECTED':(age===null?'DOWN':'STALE');
 const out={state,label:WORLD_LIVE_LABELS.spark,tick:spark.tick,age_s:age,last_ok_tick:good?.tick??null,local_last_ok_tick:localLast,last_ok_age_s:goodAge,status:spark.status==='ok'?'ok':'failed',
  late:spark.late===true,consecutive_failures:Number(spark.consecutive_failures)||0,interval_target_s:Number(spark.interval_target_s)||null,
  counts_sha256:HEX.test(spark.counts_sha256||'')?spark.counts_sha256:null,features:feats,stale_after_s:STALE_AFTER_S.spark};
 if(state==='CONNECTED'&&spark.status==='ok'){
  out.source='rigetti.sim.qvm';
  return out;
 }
 if(localFresh){
  const localFeats=countsFeatures(localSpark.counts);
  return {state:'CONNECTED',source:'local-sim',label:LOCAL_SIM_LABEL,tick:spark.tick,age_s:age,
   last_ok_tick:good?.tick??null,local_last_ok_tick:localLast,last_ok_age_s:goodAge,status:'local-sim',
   rigetti_status:spark.status==='ok'?'ok':'failed',late:spark.late===true,
   consecutive_failures:Number(spark.consecutive_failures)||0,interval_target_s:Number(spark.interval_target_s)||null,
   counts_sha256:HEX.test(localSpark.counts_sha256||'')?localSpark.counts_sha256:null,features:localFeats,
   stale_after_s:STALE_AFTER_S.spark};
 }
 if(state!=='CONNECTED'){
  const cause=spark.status==='failed'?'failed_status':(age===null?'missing':'source_age');
  out.stall=stall(age,STALE_AFTER_S.spark,cause,{tick:spark.tick,at_epoch:Number(spark.at_epoch)||null});
 }
 return out;
}
function liveTickLink(live,head,nowMs){
 const ok=live&&live.schema==='beast-live-tick/v1'&&live.label==='SIMULATED'&&Number.isInteger(live.recorded_tick);
 if(!ok)return {state:'DOWN',label:WORLD_LIVE_LABELS.liveTick,reason:'no live-tick snapshot',
  stall:stall(null,STALE_AFTER_S.liveTick,'missing')};
 const age=head&&Number.isFinite(head.at_ms)?ageSeconds(nowMs,head.at_ms):null;
 const state=linkState(age,STALE_AFTER_S.liveTick);
 const out={state,label:WORLD_LIVE_LABELS.liveTick,recorded_tick:live.recorded_tick,seconds_since_recorded:live.seconds_since_recorded,
  xp_live:live.xp_live,signals:live.signals&&typeof live.signals==='object'?live.signals:{},batch_age_s:age,batch_s:600,stale_after_s:STALE_AFTER_S.liveTick};
 if(state!=='CONNECTED')out.stall=stall(age,STALE_AFTER_S.liveTick,age===null?'missing':'source_age',{recorded_tick:live.recorded_tick});
 return out;
}
function diaryLink(diary,nowMs){
 if(!diary||diary.ok!==true||!Number.isInteger(diary.tick))return {state:'DOWN',label:WORLD_LIVE_LABELS.diary,reason:'diary unreachable',
  stall:stall(null,STALE_AFTER_S.diary,'missing')};
 const at=Date.parse(diary.last_tick_at||'');
 const age=Number.isFinite(at)?ageSeconds(nowMs,at):null;
 const state=linkState(age,STALE_AFTER_S.diary);
 const out={state,label:WORLD_LIVE_LABELS.diary,tick:diary.tick,age_s:age,cadence_s:1800,stale_after_s:STALE_AFTER_S.diary};
 if(state!=='CONNECTED')out.stall=stall(age,STALE_AFTER_S.diary,age===null?'missing':'source_age',{tick:diary.tick});
 return out;
}
function brainLink(pin){
 if(!pin||!Number.isInteger(pin.training_steps)||!HEX.test(pin.checkpoint_sha256||''))return {state:'DOWN',label:WORLD_LIVE_LABELS.brain,reason:'no pin',
  stall:stall(null,null,'missing')};
 return {state:'CONNECTED',label:WORLD_LIVE_LABELS.brain,step:pin.training_steps,checkpoint_sha256_prefix:pin.checkpoint_sha256.slice(0,12),
  source:'PIN (reviewed promotion PR; the host reports the same step to /api/guest)',changes_only_by:'a reviewed promotion that passes Gate v2'};
}
/** Build the world-live document from the already-fetched branch records. Any input may be null (that link is DOWN, never faked). */
export function buildWorldLive({spark=null,localSpark=null,liveTick=null,liveHead=null,diary=null,pin=null,nowMs}){
 const links={spark:sparkLink(spark,nowMs,localSpark),liveTick:liveTickLink(liveTick,liveHead,nowMs),diary:diaryLink(diary,nowMs),brain:brainLink(pin)};
 const states=Object.values(links).map(l=>l.state);
 const sp=links.spark;
 const drive=sp.state==='CONNECTED'&&sp.features?(sp.source==='local-sim'
  ?{source:'local-sim',label:LOCAL_SIM_LABEL,tick:sp.local_last_ok_tick,p0:sp.features.p0,p1:sp.features.p1,p2:sp.features.p2,odd:sp.features.odd,entropy:sp.features.entropy}
  :{source:'spark',label:'SIMULATED',tick:sp.tick,p0:sp.features.p0,p1:sp.features.p1,p2:sp.features.p2,odd:sp.features.odd,entropy:sp.features.entropy}):null;
 const stalls=Object.fromEntries(Object.entries(links).filter(([,l])=>l&&l.stall).map(([k,l])=>[k,l.stall]));
 const river=liveDiaryLag(links.diary.tick,links.liveTick.recorded_tick);
 if(river)stalls.river=river;
 const senses=SENSE_TRACE.map(s=>{
  const link=s.id==='spark'?links.spark:s.id==='live_tick'?links.liveTick:s.id==='diary'?links.diary:s.id==='brain'?links.brain:null;
  if(s.id==='spark'&&links.spark.source==='local-sim')return {...s,label:'LOCAL SIMULATED',note:LOCAL_SIM_LABEL,state:links.spark.state};
  return {...s,state:link?link.state:null};
 });
 return {schema:WORLD_LIVE_SCHEMA,at_ms:nowMs,links,drive,all_connected:states.every(s=>s==='CONNECTED')&&!river,
  stalls:Object.keys(stalls).length?stalls:null,river,
  senses,
  labels:{spark:links.spark.source==='local-sim'?'LOCAL SIMULATED':'SIMULATED',liveTick:'SIMULATED',diary:'RECORDED',brain:'PINNED'}};
}
