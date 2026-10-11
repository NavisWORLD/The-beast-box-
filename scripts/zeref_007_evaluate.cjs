'use strict';
/* Experiment 007 consumes an independently measured 005-format native rollout.
 * No fabricated metrics; no model promotion; no QPU.
 */
const fs=require('node:fs');
const assert=require('node:assert/strict');
const {compare}=require('./zeref_native_novelty_007.cjs');
const input=process.argv[2],out=process.argv[3];
assert.ok(input&&out,'Usage: node scripts/zeref_007_evaluate.cjs native-report.json novelty-report.json');
const raw=JSON.parse(fs.readFileSync(input,'utf8'));
assert.equal(raw.schema,'beastbox-zeref-native-controlled-rollouts-005');
assert.equal(raw.source_class,'REAL_NATIVE_GBA_EMULATOR_OBSERVATIONS_AND_CONTROLLER_ACKS');
assert.equal(raw.qbeast_id,'bb-deada969');
assert.equal(raw.model_replies_are_real_cpu_inference,true);
const arms=raw.episodes;
assert.ok(arms&&typeof arms==='object');
for(const p of ['WAIT','RIGHT','RANDOM','SCRIPT','original','candidate']){
 assert.equal(arms[p]?.length,3,'Missing native episodes '+p);
 for(const e of arms[p])assert.equal(e.rows?.length,12,'Incomplete native action evidence');
}
const baselines=Object.fromEntries(['WAIT','RIGHT','RANDOM','SCRIPT','original'].map(p=>[p,arms[p]]));
const report=compare(arms.candidate,baselines);
report.qbeast_id=raw.qbeast_id;
report.native_source_sha256=raw.source_frame_sha256;
report.original_checkpoint_sha256=raw.baseline_original_weights_sha256;
report.candidate_checkpoint_sha256=raw.candidate_weights_sha256;
report.native_episodes=18;
report.actual_native_action_slots=216;
report.provenance='real native emulator observation/ACK trace, not native game progress';
fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');
console.log('ZEREF_007_REAL_OPTICAL_NOVELTY='+JSON.stringify({candidate:report.by_policy.candidate,
 baselines:Object.fromEntries(Object.entries(report.by_policy).filter(([k])=>k!=='candidate').map(([k,v])=>[k,v.unique_native_optical_signatures])),
 beats_all:report.candidate_exceeds_all_five_optical_baselines,objective_game_progress:null}));
