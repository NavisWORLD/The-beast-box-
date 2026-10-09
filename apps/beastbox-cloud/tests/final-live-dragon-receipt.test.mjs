import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runRealIBMDragonExperiment} from '../scripts/real-ibm-marrakesh-dragon-experiment.mjs';
const receipt=()=>JSON.parse(readFileSync(new URL('../experiment-input/ibm-final-live-20261009-receipt.json',import.meta.url)));
test('the existing dragon engine uses the supplied newly measured hardware source and replays it exactly',()=>{
 const input=receipt();
 const result=runRealIBMDragonExperiment({keeperPrefix:'Final-live-',hardwareReceipt:input});
 assert.equal(result.output.provenance.genesis_job,input.job_id);
 assert.equal(result.output.provenance.genesis_backend,input.backend_name);
 assert.equal(result.output.provenance.hardware_full_counts_sha256,input.counts_digest_sha256);
 assert.equal(result.output.genome.body,'dragonling');
 assert.notEqual(result.output.qbeast.id,'bb-82fbc8ff');
 assert.equal(result.output.acceptance.save_load_replay_exact,true);
 assert.equal(result.output.acceptance.unauthorized_xp_awarded,0);
 assert.deepEqual(input,receipt(),'Source receipt must remain immutable');
});
test('uncompleted, relabeled, inconsistent and corrupted hardware receipts are refused before generation',()=>{
 for(const change of [
  {job_status:'QUEUED'},{source_class:'SIMULATOR'},{backend_name:'rigetti.sim.qvm'},
  {job_id:'arbitrary-unverified-label'},{shot_count:16383},
  {counts_digest_sha256:'0'.repeat(64)},{beast_genesis_digest_sha256:'0'.repeat(64)},
  {expectations:{...receipt().expectations,bell_XX:0}},
  {measurements:{...receipt().measurements,decoupled_zz:{'00':4096}}},
 ]) assert.throws(()=>runRealIBMDragonExperiment({keeperPrefix:'Final-live-',hardwareReceipt:{...receipt(),...change}}));
});
