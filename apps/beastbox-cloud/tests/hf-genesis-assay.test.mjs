import test from 'node:test';
import assert from 'node:assert/strict';
import {runHfGenesisExperiment} from '../../../scripts/experiment-hf-genesis.mjs';
test('the controlled memory ablation uses equal initial genomes and old matrices, with causal traces and restart replay',()=>{
 const {report,traces}=runHfGenesisExperiment();
 assert.equal(report.results.reproducible_renders,12);
 assert.equal(report.results.exact_restart_replays,12);
 assert.equal(report.results.exact_brain_swaps,12);
 assert.equal(traces.length,12240);
 for(const p of report.pairs){
  assert.deepEqual(p.initial.memory.beast,p.initial.ablated.beast);
  assert.deepEqual(p.initial.memory.mind.weights,p.initial.ablated.mind.weights);
  assert.deepEqual(p.initial.memory.mind.next,p.initial.ablated.mind.next);
  assert.equal(p.final.memory.beast.qbeast.profile.id,p.initial.memory.beast.qbeast.profile.id);
  const a=traces.find(x=>x.pair===p.index&&x.branch==='memory'),b=traces.find(x=>x.pair===p.index&&x.branch==='ablated');
  assert.ok(a.input.associations.some(h=>h.word==='explore'));
  assert.equal(b.input.associations.length,0);assert.ok(a.scores.explore>b.scores.explore);
 }
 assert.ok(report.interpretation.not_demonstrated.some(x=>/Quantum advantage/.test(x)));
});
