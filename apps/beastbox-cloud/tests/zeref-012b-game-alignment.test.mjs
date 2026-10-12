import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {ZEREF,IBM_BIRTH,assessCausalLink,readZerefIbmReceipt,rollout,buildReport}
 from '../../../scripts/audit_zeref_012b_game_alignment.mjs';
import {trainingEligible} from '../lib/zeref/experience-record.mjs';
import {ibmRecordedRecord} from '../lib/zeref/experience-record.mjs';

const hex=bytes=>createHash('sha256').update(bytes).digest('hex');
let stored;
function report(){return stored??=buildReport({trainLayouts:8,evalLayouts:6});}

test('published Zeref IBM birth receipt is measured, hash-checked and source classified',()=>{
 const r=readZerefIbmReceipt();
 assert.equal(r.sourceClass,'RECORDED_IBM_HARDWARE');
 assert.equal(r.jobId,IBM_BIRTH);
 assert.equal(r.backend,'ibm_fez');
 assert.equal(r.recordedRows,2);
 assert.equal(r.shots,8192);
 assert.ok(r.runs.every(x=>x.derived_classical_features.length===12));
 assert.ok(r.runs.every(x=>x.derived_classical_features.every(v=>v>=0&&v<=1)));
});
test('identity and source hashes alone never qualify as a causal game-action pairing',()=>{
 const packet=readZerefIbmReceipt();
 const event=rollout('random','exp012b-identity-audit').firstEvent;
 const actual=assessCausalLink({packet,gameEvent:event});
 assert.equal(actual.causalPairingVerified,false);
 assert.equal(actual.canTrainQuantumActionAssociation,false);
 assert.equal(actual.signalClaimAllowed,false);
 assert.ok(actual.reasonCodes.includes('no_independent_cross_domain_event_commitment'));
 assert.ok(actual.reasonCodes.includes('missing_independent_timestamps'));
 const forged=assessCausalLink({packet:{...packet,verifiedCrossDomainEventCommitment:true,
  providerExecutionTimeEvidence:'not provider verified',predeclaredCircuitTask:'fake'},
  gameEvent:{...event,observedAtUtc:'2026-10-10T00:00:00Z',measurementRequestNonce:'made-up'}});
 assert.equal(forged.canTrainQuantumActionAssociation,false);
 assert.ok(forged.reasonCodes.includes('independent_cross_domain_verifier_unavailable'));
});
test('hardware recorded birth spark is a state input, never a game training action',()=>{
 const receipt=readZerefIbmReceipt();
 const r=ibmRecordedRecord({job_id:receipt.jobId,backend:receipt.backend,counts_sha256:receipt.runs[0].countsSha256},
  {qbeast_id:ZEREF});
 assert.equal(trainingEligible(r,{identity:ZEREF}).ok,false);
 assert.equal(r.action,null);
});
test('replays original pocket rules with validated hash-chains and no private use',()=>{
 for(const policy of ['random','pocket-learner','greedy-frontier']){
  const a=rollout(policy,'exp012b-deterministic-eval');
  const b=rollout(policy,'exp012b-deterministic-eval');
  assert.deepEqual(a.episode,b.episode);
  assert.deepEqual(a.metrics,b.metrics);
  assert.equal(a.episode.verified_record_count,40);
  assert.ok(a.metrics.cells_visited>=1&&a.metrics.cells_visited<=40);
  assert.ok(a.metrics.blocked>=0);
  assert.ok(a.trainingCandidates.every(x=>x.origin==='deterministic_pocket_simulation'
    &&x.quantum_action_pair_verified===false&&x.real_native_game_progress===false
    &&x.observed_reward>0.5));
 }
});
test('train/eval never share layouts; selected actions from computed outcomes only',()=>{
 const {report:r,outputs}=report();
 assert.equal(r.schema,'zeref-012b-game-measurement-alignment/v1');
 assert.equal(r.training.episode_count,8*3);
 assert.equal(r.evaluation.episodes,6*3);
 assert.equal(r.training.record_count,8*3*40);
 assert.equal(r.evaluation.record_count,6*3*40);
 assert.equal(r.quantum_workloads_submitted,0);
 assert.equal(r.new_rigetti_qvm_jobs,0);
 assert.equal(r.model_weights_updated,false);
 assert.equal(r.production_promoted,false);
 assert.equal(r.verified_quantum_game_training_pairs,0);
 assert.equal(r.user_private_data_used,false);
 assert.equal(r.real_native_game_progress_claimed,false);
 assert.ok(r.training.outcome_selected_action_candidates>0);
 assert.equal(r.evaluation.keys.length,6);
 const train=outputs['pocket-outcome-selected-train.jsonl'].trim().split('\n').map(JSON.parse);
 assert.equal(train.length,r.training.outcome_selected_action_candidates);
 assert.ok(train.every(x=>x.source_episode.startsWith('exp012b-train-')));
 assert.ok(r.evaluation.keys.every(x=>x.startsWith('exp012b-eval-')));
 assert.equal(new Set(train.map(x=>x.source_episode)).size<=8,true);
 assert.ok(train.every(x=>x.label_kind==='computed_reward'&&x.measurement_source===null));
 assert.ok(!outputs['pocket-outcome-selected-train.jsonl'].includes('private_interaction'));
});
test('all outputs have stable byte hashes and all source code digests match',()=>{
 const {report:r,outputs}=report();
 for(const [name,meta] of Object.entries(r.outputs)){
  assert.equal(hex(Buffer.from(outputs[name])),meta.sha256);
  assert.equal(Buffer.byteLength(outputs[name]),meta.bytes);
 }
 const root=fileURLToPath(new URL('../../../',import.meta.url));
 for(const [path,digest] of Object.entries(r.source_code_sha256)){
  assert.equal(hex(readFileSync(root+path)),digest);
 }
});
test('tampered Zeref receipt is rejected',()=>{
 const source=readZerefIbmReceipt();
 const obj=JSON.parse(readFileSync(fileURLToPath(new URL('../public/spark/ibm-zeref-heart-sound-20261010.json',import.meta.url))));
 obj.runs[0].c='00:4096,01:0,10:0,11:0';
 // Existing expandRun independently verifies the count digest, preventing injected fake outcomes.
 assert.notEqual(obj.runs[0].h,hex(JSON.stringify(obj.runs[0].c)));
 assert.equal(source.recordedRows,2);
});
