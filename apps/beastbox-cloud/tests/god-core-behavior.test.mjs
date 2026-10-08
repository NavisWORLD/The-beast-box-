import test from 'node:test';import assert from 'node:assert/strict';
import {createBehavior,stepBehavior,feedbackBehavior,advanceCreature,recordCreatureExperience,ACTIONS} from '../lib/companion/behavior.mjs';
const make=(seed='a'.repeat(64))=>({seed,genome:{seed,t:{spark:80,focus:70}},energy:70,bond:12,qbeast:{profile:{id:'QTEST-1'}}});
test('same verified genome and environment replay all scores',()=>{
 const b=make(),state=createBehavior(b),a=stepBehavior(state,b,{place:'grove',toy:1}),c=stepBehavior(state,b,{place:'grove',toy:1});
 assert.deepEqual(a,c);assert.equal(state.tick,0);assert.equal(a.state.tick,1);assert.equal(ACTIONS.includes(a.event.action),true);
});
test('bounded event log, bounded energy and immutable QBEAST',()=>{
 const beast={...make(),xp:40,nativeStage:2,game:{native_save:'test-save'}},s={beast};
 for(let i=0;i<120;i++)advanceCreature(s,{place:'grove'});
 assert.equal(beast.behavior.tick,120);assert.equal(beast.behavior.events.length,32);
 assert.ok(beast.behavior.energy>=0&&beast.behavior.energy<=100);
 assert.equal(beast.xp,40);assert.equal(beast.nativeStage,2);assert.equal(beast.game.native_save,'test-save');assert.equal(beast.qbeast.profile.id,'QTEST-1');
});
test('feedback changes future preference-weighted decisions and survives JSON',()=>{
 const b=make(),base=createBehavior(b),trained=feedbackBehavior(base,b,{place:'grove',reward:1});
 assert.ok(stepBehavior(trained,b,{place:'grove'}).event.scores.explore>stepBehavior(base,b,{place:'grove'}).event.scores.explore);
 const session={beast:b};recordCreatureExperience(session,{place:'grove',reward:1});
 assert.equal(session.beast.behavior.preferences.grove,1);
 assert.deepEqual(JSON.parse(JSON.stringify(session.beast.behavior)),session.beast.behavior);
});
test('invalid lineage seed does not initialize runtime',()=>assert.throws(()=>createBehavior({seed:'invalid'}),/Verified genesis/));
