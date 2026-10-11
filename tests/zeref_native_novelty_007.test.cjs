'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {evaluate,compare}=require('../scripts/zeref_native_novelty_007.cjs');
const a={status:'observed',source:'native-emulator-display',brightness:40,contrast:40,frameChange:12,dominant:'mixed'};
const b={...a,brightness:50};
const episode=(name,after=b)=>[{episode:0,rows:[{before:a,after,action:name==='WAIT'?'WAIT':'RIGHT'}]}];
test('native optical novelty cannot be mislabeled as game progress',()=>{
 const x=evaluate(episode('candidate'));
 assert.equal(x.unique_native_optical_signatures,2);
 assert.equal(x.real_game_progress,null);
 assert.equal(x.real_reward,null);
 assert.equal(x.independent_learning_proven,false);
});
test('candidate is compared against all five real native emulator controls',()=>{
 const baseline=Object.fromEntries(['WAIT','RIGHT','RANDOM','SCRIPT','original'].map(x=>[x,episode(x,a)]));
 const x=compare(episode('candidate'),baseline);
 assert.equal(x.candidate_exceeds_all_five_optical_baselines,true);
 assert.equal(x.game_objective_outperformance,null);
 assert.equal(x.novel_independent_strategy_proven,false);
});
test('reject synthetic frames',()=>assert.throws(()=>evaluate([{episode:0,rows:[{before:{...a,source:'fake'},after:b,action:'RIGHT'}]}])));
