'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {parseModel,seededRandom,teacher,optic,opticsSignature,summarizeArm}=require('../scripts/zeref_native_rollout_policy_005.cjs');
const observation={status:'observed',source:'native-emulator-display',brightness:52,contrast:34,frameChange:20,dominant:'mixed'};
test('Only literal bounded ACTION tokens control native inputs',()=>{
 assert.equal(parseModel('ACTION: UP'),'UP');
 assert.equal(parseModel('ACTION: WAIT'),'WAIT');
 for(const text of ['RIGHT','ACTION: START','ACTION: UP && delete files','ACTION: RIGHT\nACTION: LEFT',null,'ACTION: MORE'])assert.equal(parseModel(text),null);
});
test('Scripted optical teacher and random comparator are deterministic',()=>{
 assert.equal(optic(observation),true);
 assert.equal(teacher({...observation,brightness:12},0,0),'A');
 assert.equal(teacher({...observation,frameChange:1},0,0),'RIGHT');
 assert.equal(teacher({...observation,contrast:81},0,0),'LEFT');
 assert.equal(teacher({...observation,dominant:'blue'},0,0),'UP');
 assert.equal(teacher({...observation,dominant:'green'},0,0),'DOWN');
 assert.equal(teacher({...observation,brightness:85},0,0),'B');
 let a=seededRandom(20261011),b=seededRandom(20261011);
 assert.deepEqual(Array.from({length:16},a),Array.from({length:16},b));
 assert.ok(opticsSignature(observation).includes('mixed'));
});
test('No optical feature changes can ever be reported as earned rewards or dialogue progression',()=>{
 const copy={...observation,brightness:66};
 const episodes=[{rows:[{before:observation,after:copy,is_model:true,action:'RIGHT',model_valid_action:true,scripted_target:'RIGHT',native_ack_digest:'sha256'}]}];
 const report=summarizeArm(episodes);
 assert.equal(report.episodes,1);
 assert.equal(report.actual_native_observations,2);
 assert.equal(report.model_valid_actions,1);
 assert.equal(report.earned_rewards,null);
 assert.equal(report.game_progress,null);
 assert.equal(report.dialogue_advancement,null);
 assert.equal(report.distinct_explored_game_areas,null);
 assert.equal(report.native_objective_metrics_available,false);
});
