import test from 'node:test';
import assert from 'node:assert/strict';
import {publicDiaryMood,publicDiaryLearning,publicPromotion,publicGate,publicFairGate,publicLivedState,publicTraining} from '../lib/liveness-public.mjs';
import {shapeLiveness} from '../lib/cosmos/forever-store.mjs';

const AT='2026-11-12T18:41:53Z';
const pin={
 training_steps:40304,
 checkpoint_sha256:'ee17330fcd5a643d585ece8c9c2f5d9b85e12063cea07437b93f4d4ff0719a24',
 promotion:{release_tag:'zeref-006-cycle-69-ee17330fcd5a',chat_not_worse:true,candidate_leaks:0,
  workflow_run:'https://github.com/NavisWORLD/The-beast-box-/actions/runs/43242148605'},
 gate_v2:{schema:'zeref-gate-v2',set_a_pin_nll:3.82,set_b_pin_nll:3.84},
};

test('diary mood comes from the latest recent entry; thought text is never copied',()=>{
 const mood=publicDiaryMood({recent:[{tick:804,mood:'Sleepy',thought:'private words must not leak'}]});
 assert.equal(mood.mood,'sleepy');
 assert.equal(mood.tick,804);
 assert.equal(mood.label,'RECORDED');
 assert.ok(!JSON.stringify(mood).includes('private words'));
 assert.equal(publicDiaryMood({recent:[{mood:'!!!'}]}),null,'junk mood is dropped, not invented');
 assert.equal(publicDiaryMood(null),null);
});

test('diary learning publishes counts and the honesty label, never thought or prefs',()=>{
 const learn=publicDiaryLearning({learning:{cells_visited:37,cells_total:40,known_rifts:3,moves_succeeded:11718,
  moves_blocked:665,blocked_rate:0.054,decisions:7125,favorite_spot:'Echo Prism',prefs:{play:1},
  thought:'do not republish',label:'learned behaviour from its own experience, not consciousness'}});
 assert.equal(learn.cells_visited,37);
 assert.equal(learn.favorite_spot,'Echo Prism');
 assert.ok(!('prefs' in learn));
 assert.ok(!('thought' in learn));
 assert.doesNotMatch(JSON.stringify(learn),/do not republish/);
 assert.equal(publicDiaryLearning({}),null);
});

test('promotion and gate are sliced from the public pin; fair-gate stays unpublished as a global',()=>{
 const promo=publicPromotion(pin,{sha:'e67183717babcdef',date:AT,message:'auto-promote step 40304 (ee17330fcd5a), both gates clean\n\nmore'});
 assert.equal(promo.promoted_at,AT);
 assert.equal(promo.release_tag,'zeref-006-cycle-69-ee17330fcd5a');
 assert.equal(promo.chat_not_worse,true);
 assert.equal(promo.step,40304);
 assert.equal(promo.pin_commit_message,'auto-promote step 40304 (ee17330fcd5a), both gates clean');
 assert.equal(promo.label,'PINNED');
 const noAt=publicPromotion(pin,null);
 assert.equal(noAt.promoted_at,null,'missing git metadata is omitted, not invented');
 const gate=publicGate(pin);
 assert.equal(gate.schema,'zeref-gate-v2');
 assert.equal(gate.chat_not_worse,true);
 assert.equal(gate.candidate_leaks,0);
 assert.match(gate.note,/G1–G10 unchanged/);
 const fg=publicFairGate();
 assert.equal(fg.status,'no public global result');
 assert.match(fg.note,/training_eligible:false/);
});

test('lived state: only a real 12-vector is published; otherwise unpublished, never invented',()=>{
 const no=publicLivedState(null);
 assert.equal(no.status,'unpublished');
 assert.equal(no.state12,null);
 assert.equal(no.dyn12,null);
 assert.match(no.reason,/will not invent/);
 const bad=publicLivedState({state12:[1,2,3]});
 assert.equal(bad.status,'unpublished');
 const yes=publicLivedState({state12:[0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1,1.1],label:'RECORDED',source:'test'});
 assert.equal(yes.status,'published');
 assert.equal(yes.state12.length,12);
 assert.equal(yes.state12[1],0.1);
});

test('training status is copied from the public Actions listing; cycle/step stay null when absent',()=>{
 const live=publicTraining({status:'in_progress',event:'schedule',name:'Zeref 006 - resumable real native RAWRPHOS learning heartbeat',
  html_url:'https://github.com/NavisWORLD/The-beast-box-/actions/runs/43296703742',run_started_at:AT,job_name:'train-zeref'},pin);
 assert.equal(live.status,'in_progress');
 assert.equal(live.pin_step,40304);
 assert.equal(live.cycle,null);
 assert.equal(live.step,null);
 assert.equal(live.job,'train-zeref');
 assert.match(live.note,/stay null/);
 const down=publicTraining(null,pin);
 assert.equal(down.state,'DOWN');
 assert.equal(down.pin_step,40304);
 const evil=publicTraining({status:'in_progress',html_url:'https://evil.example/runs/1'},pin);
 assert.equal(evil.html_url,null);
});

test('shapeLiveness never invents mood, promotion time, or a 12-vector when sources omit them',()=>{
 const empty=shapeLiveness({now:AT,pin:null,diary:null,bridge:null,azure:null,world:null});
 assert.equal(empty.diary.state,'DOWN');
 assert.equal(empty.promotion.promoted_at,null);
 assert.equal(empty.promotion.release_tag,null);
 assert.equal(empty.lived_state.status,'unpublished');
 assert.equal(empty.lived_state.state12,null);
 assert.equal(empty.learning.training.state,'DOWN');
 assert.ok(!('mood' in empty.diary));
 const full=shapeLiveness({now:AT,pin,diary:{tick:804,xp:11500,bond:100,stage:5,stage_name:'Crescent Sovereign',last_tick_at:AT,
   mood:'sleepy',learning:{cells_visited:37,cells_total:40,known_rifts:3,moves_succeeded:1,moves_blocked:0,blocked_rate:0,
    decisions:1,favorite_spot:'Echo Prism',thought:'secret',label:'learned behaviour from its own experience, not consciousness'},
   recent:[{tick:804,mood:'sleepy',thought:'secret'}]},
  diaryVerified:true,pinCommit:{sha:'e67183717babcdef',date:AT,message:'auto-promote step 40304'},
  training:{status:'in_progress',event:'schedule',name:'Zeref 006 heartbeat',html_url:'https://github.com/NavisWORLD/The-beast-box-/actions/runs/43296703742',job_name:'train-zeref'}});
 assert.equal(full.diary.mood,'sleepy');
 assert.equal(full.diary.learning.cells_visited,37);
 assert.ok(!('thought' in full.diary.learning));
 assert.doesNotMatch(JSON.stringify(full),/"secret"/);
 assert.equal(full.promotion.promoted_at,AT);
 assert.equal(full.gate.schema,'zeref-gate-v2');
 assert.equal(full.learning.training.status,'in_progress');
 assert.equal(full.learning.pin_step,40304);
 assert.equal(full.lived_state.status,'unpublished');
 assert.equal(full.fair_gate.status,'no public global result');
});
