import test from 'node:test';
import assert from 'node:assert/strict';
import {runGodCoreExperiment} from '../scripts/god-core-experiments.mjs';
test('controlled genesis, behavior diversity, feedback ablation and deterministic replay',()=>{
 const r=runGodCoreExperiment();
 assert.equal(r.tests.A_repeated_genesis,36);
 assert.equal(r.tests.B_paired_source_comparison.length,12);
 assert.ok(r.tests.C_behavioral_diversity>1);
 assert.equal(r.tests.D_controlled_preference_change,6);
 assert.equal(r.tests.E_restart_replay,6);
 assert.equal(r.tests.F_long_bounded_runs,3);
 assert.ok(r.sourceRows.every(x=>x.genesis_seed.length===64));
 assert.ok(r.sourceRows.every(x=>Object.values(x.actions).reduce((a,b)=>a+b,0)===240));
 assert.equal(r.qvm_source_class,'NEW_AZURE_CLOUD_QVM_SIMULATION_NOT_QPU');
 console.log('GOD_CORE_001_RESULTS '+JSON.stringify({tests:r.tests,limits:r.limitations,comparison:r.comparisons.pairwise_differences}));
});
