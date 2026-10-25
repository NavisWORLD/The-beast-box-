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
 */
export const WORLD_LIVE_SCHEMA='beast-world-live/v1';
export const STALE_AFTER_S=Object.freeze({spark:180,liveTick:1500,diary:5400});
export const WORLD_LIVE_LABELS=Object.freeze({
 spark:'Rigetti SIMULATED (rigetti.sim.qvm, not a QPU)',
 liveTick:'SIMULATED (per-second tick, deterministic)',
 diary:'RECORDED (hash-chained diary; its growth circuit is Rigetti SIMULATED)',
 brain:'RAWRPHØS pinned checkpoint (a 12D model simulation; not a claim of awareness)'
});
const HEX=/^[0-9a-f]{64}$/;
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
function sparkLink(spark,nowMs){
 const ok=spark&&spark.simulated===true&&spark.beast_id==='bb-deada969'&&Number.isInteger(spark.tick);
 if(!ok)return {state:'DOWN',label:WORLD_LIVE_LABELS.spark,reason:'no Zeref spark record'};
 const good=spark.last_ok&&typeof spark.last_ok==='object'?spark.last_ok:null;
 const goodAge=good?ageSeconds(nowMs,Number(good.at_epoch)*1000):null;
 const age=ageSeconds(nowMs,Number(spark.at_epoch)*1000);
 const feats=good?countsFeatures(good.counts):null;
 // Fresh only when the loop is ticking AND the last SUCCESSFUL simulator counts are fresh (a failing loop shows the age of the last good counts).
 const state=linkState(age,STALE_AFTER_S.spark)==='CONNECTED'&&linkState(goodAge,STALE_AFTER_S.spark*5)==='CONNECTED'?'CONNECTED':(age===null?'DOWN':'STALE');
 return {state,label:WORLD_LIVE_LABELS.spark,tick:spark.tick,age_s:age,last_ok_tick:good?.tick??null,last_ok_age_s:goodAge,status:spark.status==='ok'?'ok':'failed',
  late:spark.late===true,consecutive_failures:Number(spark.consecutive_failures)||0,interval_target_s:Number(spark.interval_target_s)||null,
  counts_sha256:HEX.test(spark.counts_sha256||'')?spark.counts_sha256:null,features:feats,stale_after_s:STALE_AFTER_S.spark};
}
function liveTickLink(live,head,nowMs){
 const ok=live&&live.schema==='beast-live-tick/v1'&&live.label==='SIMULATED'&&Number.isInteger(live.recorded_tick);
 if(!ok)return {state:'DOWN',label:WORLD_LIVE_LABELS.liveTick,reason:'no live-tick snapshot'};
 const age=head&&Number.isFinite(head.at_ms)?ageSeconds(nowMs,head.at_ms):null;
 return {state:linkState(age,STALE_AFTER_S.liveTick),label:WORLD_LIVE_LABELS.liveTick,recorded_tick:live.recorded_tick,seconds_since_recorded:live.seconds_since_recorded,
  xp_live:live.xp_live,signals:live.signals&&typeof live.signals==='object'?live.signals:{},batch_age_s:age,batch_s:600,stale_after_s:STALE_AFTER_S.liveTick};
}
function diaryLink(diary,nowMs){
 if(!diary||diary.ok!==true||!Number.isInteger(diary.tick))return {state:'DOWN',label:WORLD_LIVE_LABELS.diary,reason:'diary unreachable'};
 const at=Date.parse(diary.last_tick_at||'');
 const age=Number.isFinite(at)?ageSeconds(nowMs,at):null;
 return {state:linkState(age,STALE_AFTER_S.diary),label:WORLD_LIVE_LABELS.diary,tick:diary.tick,age_s:age,cadence_s:1800,stale_after_s:STALE_AFTER_S.diary};
}
function brainLink(pin){
 if(!pin||!Number.isInteger(pin.training_steps)||!HEX.test(pin.checkpoint_sha256||''))return {state:'DOWN',label:WORLD_LIVE_LABELS.brain,reason:'no pin'};
 return {state:'CONNECTED',label:WORLD_LIVE_LABELS.brain,step:pin.training_steps,checkpoint_sha256_prefix:pin.checkpoint_sha256.slice(0,12),
  source:'PIN (reviewed promotion PR; the host reports the same step to /api/guest)',changes_only_by:'a reviewed promotion that passes Gate v2'};
}
/** Build the world-live document from the already-fetched branch records. Any input may be null (that link is DOWN, never faked). */
export function buildWorldLive({spark=null,liveTick=null,liveHead=null,diary=null,pin=null,nowMs}){
 const links={spark:sparkLink(spark,nowMs),liveTick:liveTickLink(liveTick,liveHead,nowMs),diary:diaryLink(diary,nowMs),brain:brainLink(pin)};
 const states=Object.values(links).map(l=>l.state);
 const sp=links.spark;
 // Numbers the world may react to: bounded 0..1, only while the spark is fresh. Nothing here is random and nothing is a measurement of hardware.
 const drive=sp.state==='CONNECTED'&&sp.features?{source:'spark',label:'SIMULATED',tick:sp.tick,p0:sp.features.p0,p1:sp.features.p1,p2:sp.features.p2,odd:sp.features.odd,entropy:sp.features.entropy}:null;
 return {schema:WORLD_LIVE_SCHEMA,at_ms:nowMs,links,drive,all_connected:states.every(s=>s==='CONNECTED'),
  labels:{spark:'SIMULATED',liveTick:'SIMULATED',diary:'RECORDED',brain:'PINNED'}};
}
