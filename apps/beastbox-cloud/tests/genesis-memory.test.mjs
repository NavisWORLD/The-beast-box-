import test from 'node:test';
import assert from 'node:assert/strict';
import {createMind,observeText,recallAssociations,replyFromMind,importMind,exportMind,ASSOCIATION_LIMITS} from '../lib/companion/learn.mjs';
import {createBehavior,stepBehavior,advanceCreature,validateBehavior} from '../lib/companion/behavior.mjs';
import {createSession,adoptBeast,careAction,talk,exportSession,importSession,swapBrain} from '../lib/companion/session.mjs';
const seed='a'.repeat(64),genome={seed,inputs:{traits:{focus:60,calm:40,spark:80}}};
const session=()=>{const s=createSession();adoptBeast(s,genome,'Moss');return s;};
test('Genesis associations are read into replies, with genuine learned strength and matrix contribution',()=>{
 const mind=createMind();assert.deepEqual(recallAssociations(mind,'garden'),[]);
 for(let i=0;i<5;i++)observeText(mind,'garden starlight explore',{seed});
 const hits=recallAssociations(mind,'garden');
 assert.ok(hits.some(h=>h.word==='explore'));assert.ok(hits.every(h=>h.association>0&&h.matrix>=0));
 assert.match(replyFromMind(mind,'garden','Moss'),/explore|starlight/);
 const restored=importMind(JSON.parse(JSON.stringify(exportMind(mind))));
 assert.deepEqual(recallAssociations(restored,'garden'),hits);
});
test('learned associations influence the same existing behavior scores and survive model swap/restart',()=>{
 const s=session(),base=structuredClone(s);s.beast.behavior=createBehavior(s.beast);base.beast.behavior=createBehavior(base.beast);
 for(let i=0;i<12;i++)observeText(s.mind,'grove explore',{seed});
 const a=advanceCreature(s,{place:'grove'}),b=advanceCreature(base,{place:'grove'});
 assert.ok(a.event.scores.explore>b.event.scores.explore);
 assert.ok(a.event.input.associations.some(h=>h.word==='explore'));
 const before=JSON.parse(JSON.stringify(exportSession(s)));swapBrain(s,'loopback-ollama');
 const restored=importSession(JSON.parse(JSON.stringify(exportSession(s))));
 assert.deepEqual(restored.mind.associations,before.mind.associations);
 assert.deepEqual(restored.beast.behavior,before.beast.behavior);
 assert.deepEqual(advanceCreature(restored,{place:'shore'}),advanceCreature(s,{place:'shore'}));
 assert.equal(s.beast.seed,seed);assert.equal(s.beast.genome.seed,seed);
});
test('local pattern prose does not become fabricated experiences through self-learning',()=>{
 const s=session();talk(s,'garden starlight');
 assert.equal(s.mind.steps,1);assert.equal(s.mind.vocab.pattern,undefined);
 assert.equal(s.mind.associations.observations,1);
});
test('unsafe, huge and malformed imported memory remains bounded without prototype pollution',()=>{
 const mind=createMind(),before=exportMind(mind);observeText(mind,'this is porn');assert.deepEqual(exportMind(mind),before);
 for(let i=0;i<1800;i++)observeText(mind,`garden word${i} flora${i}`,{seed});
 assert.ok(Object.keys(mind.associations.concepts).length<=ASSOCIATION_LIMITS.concepts);
 assert.ok(Object.keys(mind.associations.links).length<=ASSOCIATION_LIMITS.links);
 assert.ok(Object.keys(mind.vocab).length<=ASSOCIATION_LIMITS.vocab);
 const imported=importMind(JSON.parse('{"schema":"beastbox-hebbian-mind-v1","dim":16,"steps":-42,"vocab":{"__proto__":{"polluted":1}},"next":{"constructor":{"prototype":20}},"associations":{"schema":"beastbox-associations-v1","observations":-9,"concepts":{"constructor":99},"links":{"garden|explore":null}}}'));
 assert.equal(imported.steps,0);assert.equal({}.polluted,undefined);assert.deepEqual(recallAssociations(imported,'garden'),[]);
});
test('malformed or foreign behavior cannot crash the existing single core',()=>{
 const b=session().beast,original=createBehavior(b);
 for(const bad of [{...original,preferences:null},{...original,position:{x:Infinity,y:0}},{...original,tick:-1},{...original,energy:NaN},{...original,events:123},{...original,seed:'b'.repeat(64)}]){
  assert.deepEqual(validateBehavior(bad,b),original);assert.doesNotThrow(()=>stepBehavior(bad,b));
 }
 assert.deepEqual(validateBehavior(JSON.parse(JSON.stringify(original)),b),original);
});
test('care affects bounded behavior needs without awarding automatic XP or rewriting native state',()=>{
 const s=session();s.beast.qbeast={profile:{id:'QTEST'}};s.beast.nativeStage=2;s.beast.game={native_save:'retained'};
 s.beast.behavior=createBehavior({...s.beast,energy:10});careAction(s,'feed');
 assert.ok(s.beast.behavior.energy>10);const xp=s.beast.xp;
 for(let i=0;i<100;i++)advanceCreature(s,{place:'nest'});
 assert.equal(s.beast.xp,xp);assert.equal(s.beast.nativeStage,2);assert.equal(s.beast.game.native_save,'retained');assert.equal(s.beast.qbeast.profile.id,'QTEST');
});
