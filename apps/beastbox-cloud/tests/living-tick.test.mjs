import test from 'node:test';
import assert from 'node:assert/strict';
import {LIVING_TICK_SCHEMA,LIVING_SOURCE,LIVING_DEFAULTS,livingEpochFor,freshLivingTick,validateLivingTick,planLivingSteps,applyLivingSteps} from '../lib/companion/living-tick.mjs';
import {createMind} from '../lib/companion/learn.mjs';

const SEED_A='a'.repeat(32),SEED_B='b'.repeat(32);
function beast(seed=SEED_A,id='bb-12345678',extra={}){
 return {id,seed,energy:80,genome:{seed,inputs:{traits:{focus:50,calm:50,spark:50}}},qbeast:{profile:{id}},xp:12,localGrowth:{signature:'unsigned-local',applied:[]},...extra};
}
function session(seed=SEED_A,id='bb-12345678'){
 return {beast:beast(seed,id),mind:createMind()};
}
const envFactory=()=>({place:'grove',sound:0,toy:0,attention:0,comfort:.5});
const T0='2026-10-14T00:00:00.000Z';
const at=ms=>new Date(Date.parse(T0)+ms).toISOString();

test('living epoch binds seed and QBEAST id; validation resets foreign records',()=>{
 assert.equal(livingEpochFor(beast(SEED_A,'bb-aaaaaaaa')),livingEpochFor(beast(SEED_A,'bb-aaaaaaaa')));
 assert.notEqual(livingEpochFor(beast(SEED_A,'bb-aaaaaaaa')),livingEpochFor(beast(SEED_A,'bb-bbbbbbbb')));
 assert.notEqual(livingEpochFor(beast(SEED_A,'bb-aaaaaaaa')),livingEpochFor(beast(SEED_B,'bb-aaaaaaaa')));
 const foreign=freshLivingTick(beast(SEED_A,'bb-aaaaaaaa'),T0);
 const reset=validateLivingTick(foreign,beast(SEED_A,'bb-bbbbbbbb'));
 assert.equal(reset.epoch,livingEpochFor(beast(SEED_A,'bb-bbbbbbbb')));
 assert.equal(validateLivingTick({schema:'bogus'},beast()).schema,LIVING_TICK_SCHEMA);
});

test('planning is bounded: a 24h absence yields at most maxSteps ordinary steps',()=>{
 const s=session(),living=freshLivingTick(s.beast,T0);
 const plan=planLivingSteps(living,s.beast,{nowIso:at(24*3600*1000)});
 assert.equal(plan.steps,LIVING_DEFAULTS.maxSteps);
 assert.equal(plan.capped,true);
 assert.equal(plan.source,LIVING_SOURCE);
 const short=planLivingSteps(living,s.beast,{nowIso:at(5000)});
 assert.equal(short.steps,0);
 assert.equal(short.reason,'interval-not-reached');
 const back=planLivingSteps(living,s.beast,{nowIso:at(-1000)});
 assert.equal(back.steps,0);
});

test('duplicate plan delivery applies zero steps (idempotent on behavior tick)',()=>{
 const s=session(),living=freshLivingTick(s.beast,T0);
 const plan=planLivingSteps(living,s.beast,{nowIso:at(60000)});
 assert.ok(plan.steps>0);
 const first=applyLivingSteps(s,living,plan,{environmentFactory:envFactory});
 assert.equal(first.ok,true);
 assert.equal(first.stepsApplied,plan.steps);
 assert.equal(first.duplicate,false);
 const second=applyLivingSteps(s,first.living,plan,{environmentFactory:envFactory});
 assert.equal(second.ok,true);
 assert.equal(second.stepsApplied,0);
 assert.equal(second.duplicate,true);
 assert.equal(s.beast.behavior.tick,first.behaviorTick);
});

test('recorded inputs reproduce recorded behavior deterministically',()=>{
 const mk=()=>session();
 const s1=mk(),s2=mk();
 const l1=freshLivingTick(s1.beast,T0),l2=freshLivingTick(s2.beast,T0);
 const p1=planLivingSteps(l1,s1.beast,{nowIso:at(90000)});
 const p2=planLivingSteps(l2,s2.beast,{nowIso:at(90000)});
 const r1=applyLivingSteps(s1,l1,p1,{environmentFactory:envFactory});
 const r2=applyLivingSteps(s2,l2,p2,{environmentFactory:envFactory});
 assert.deepEqual(s1.beast.behavior.events,s2.beast.behavior.events);
 assert.equal(r1.behaviorTick,r2.behaviorTick);
});

test('two same-name creatures keep independent living state',()=>{
 const s1=session(SEED_A,'bb-aaaaaaaa'),s2=session(SEED_B,'bb-bbbbbbbb');
 s1.beast.name='Zeref';s2.beast.name='Zeref';
 const l1=freshLivingTick(s1.beast,T0),l2=freshLivingTick(s2.beast,T0);
 assert.notEqual(l1.epoch,l2.epoch);
 const p1=planLivingSteps(l1,s1.beast,{nowIso:at(60000)});
 const r1=applyLivingSteps(s1,l1,p1,{environmentFactory:envFactory});
 assert.ok(r1.stepsApplied>0);
 assert.equal(s2.beast.behavior?.tick||0,0);
 const cross=applyLivingSteps(s2,l2,p1,{environmentFactory:envFactory});
 assert.equal(cross.ok,false);
});

test('living steps do not leak authority into XP or signed growth',()=>{
 const s=session();
 const before={xp:s.beast.xp,growth:structuredClone(s.beast.localGrowth)};
 const living=freshLivingTick(s.beast,T0);
 const plan=planLivingSteps(living,s.beast,{nowIso:at(60000)});
 const r=applyLivingSteps(s,living,plan,{environmentFactory:envFactory});
 assert.ok(r.stepsApplied>0);
 assert.equal(s.beast.xp,before.xp);
 assert.deepEqual(s.beast.localGrowth,before.growth);
 assert.ok(s.beast.behavior.energy>=0&&s.beast.behavior.energy<=100);
 assert.ok(s.beast.behavior.curiosity>=0&&s.beast.behavior.curiosity<=100);
});

test('identity change mid-stream is rejected, not merged',()=>{
 const s=session(SEED_A,'bb-aaaaaaaa');
 const living=freshLivingTick(s.beast,T0);
 const plan=planLivingSteps(living,s.beast,{nowIso:at(60000)});
 s.beast.qbeast.profile.id='bb-bbbbbbbb';
 const r=applyLivingSteps(s,living,plan,{environmentFactory:envFactory});
 assert.equal(r.ok,false);
 assert.equal(r.reason,'plan-epoch-mismatch');
});
