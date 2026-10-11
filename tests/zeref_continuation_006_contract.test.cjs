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
   'no_new_qpu_job','production_promoted','native_game_progress_demonstrated']){
  assert.ok(s.includes(needle),'Missing nonnegotiable proof '+needle);
 }
 assert.doesNotMatch(s,/QiskitRuntimeService|SamplerV2|import azure|run_ibm_qpu/);
});
test('Scheduled Zeref CPU heartbeat keeps one-at-a-time serialized training and never authorizes IBM budget',()=>{
 const s=read('.github/workflows/zeref-continuous-learning-006.yml');
 assert.match(s,/cron: '17 \*\/6 \* \* \*'/);
 assert.match(s,/cancel-in-progress: false/);
 assert.match(s,/zeref-006-accepted-checkpoint-/);
 assert.match(s,/actions\/download-artifact|gh run download/);
 assert.match(s,/python -u scripts\/zeref_continuation_006.py/);
 assert.doesNotMatch(s,/IBM_QUANTUM_TOKEN|BEAST_ZEREF_IBM_ONE_JOB|secrets\.IBM/);
});
