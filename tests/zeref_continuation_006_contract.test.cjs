'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const read=p=>fs.readFileSync(p,'utf8');
test('Zeref real native capture keeps canonical QBEAST, original ROM and real key ACKs',()=>{
 const s=read('apps/beastbox-cloud/tests/rawrphos-native-observed-play.cjs');
 assert.match(s,/id:'bb-deada969'/);
 assert.match(s,/source_job:'db4q484vf2bc73cuuuag'/);
 assert.match(s,/NAVISWORLD_NATIVE_TRAINING_CYCLE/);
 assert.match(s,/source:'agent'/);
 assert.match(s,/native_ack_digest/);
 assert.match(s,/teacher_cycle_offset/);
 assert.match(s,/reward_is_not_native_progress:true/);
});
test('Bounded optimizer resumes actual checkpoint and fails closed without fresh observations',()=>{
 const s=read('scripts/zeref_continuation_006.py');
 for(const needle of ['load_training_state=True','opt.load_state_dict(parent["state"]["optimizer"])','UPDATES=64',
   'source_digest==prior_digest','accepted_as_next_training_parent','teacher_agreement_not_worse',
   'no_new_qpu_job','production_promoted','native_game_progress_demonstrated',
   'CANONICAL_APPROVED_ROOT','canonical_lineage_root_sha256']){
  assert.ok(s.includes(needle),'Missing nonnegotiable proof '+needle);
 }
 assert.doesNotMatch(s,/QiskitRuntimeService|SamplerV2|import azure|run_ibm_qpu/);
});
test('Scheduled Zeref CPU heartbeat keeps one-at-a-time serialized training and never authorizes IBM budget',()=>{
 const s=read('.github/workflows/zeref-continuous-learning-006.yml');
 assert.match(s,/cron: '17 \*\/6 \* \* \*'/);
 assert.match(s,/cancel-in-progress: false/);
 assert.match(s,/zeref-006-accepted-checkpoint-/);
 assert.ok(s.includes('zeref-006-canonical-37ca3f8f'),'Exactly named canonical artifact needed to avoid 100-item GitHub paging loss');
 assert.ok(s.includes('38129248023'),'Bootstrap must use actual original approved 006 AdamW continuation');
 assert.ok(!s.includes('38109635009'),'Must never silently reset Zeref to old 004 CPU checkpoint');
 assert.ok(s.includes('ZEREF_010_VERIFIED_CANONICAL_PARENT'),'Verify parent SHA BEFORE capturing expensive new episodes');
 assert.match(s,/actions\/download-artifact|gh run download/);
 assert.match(s,/python -u scripts\/zeref_continuation_006.py/);
 assert.doesNotMatch(s,/IBM_QUANTUM_TOKEN|BEAST_ZEREF_IBM_ONE_JOB|secrets\.IBM/);
});

test('Observation diagnostics distinguish teacher imitation from verified game progress',()=>{
 const s=read('scripts/zeref_continuation_006.py');
 for(const needle of [
  'native_observation_diagnostics',
  'unique_before_frame_summaries',
  'unique_after_frame_summaries',
  'different_before_after_summaries',
  'scripted_teacher_action_histogram',
  'parent_policy_actions',
  'candidate_policy_actions',
  'dominant_action_fraction',
  'visual_metrics_not_verified_game_movement',
  'policy_diversity_not_quest_progress',
  'ZEREF_006_OBSERVATION_DIAGNOSTICS',
 ])assert.ok(s.includes(needle),'Missing observable policy/raster audit: '+needle);
 assert.match(s,/"native_game_progress_demonstrated":False/);
 assert.match(s,/"teacher_is_scripted_not_human":True/);
});
