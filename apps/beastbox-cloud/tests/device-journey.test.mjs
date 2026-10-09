import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {buildGenome} from '../public/spark/genome.mjs';
import {expandRun,validateQvmReceipt} from '../public/spark/runs.mjs';
import {selectSpark,readSparkSession,saveSparkSession,SESSION_KEY,QBEAST_KEY,PROFILE_KEY} from '../public/spark/identity.mjs';
import {careAction,finishTraining,advanceCreature} from '../lib/companion/session.mjs';
import {nameBeast,talkAndGrow} from '../lib/companion/adventure.mjs';
import {serializeDeviceJourney,readDeviceJourney,restoreDeviceJourney,retainedNativeBytes,DEVICE_JOURNEY_LIMIT} from '../public/spark/device-journey.mjs';
const table=JSON.parse(readFileSync(new URL('../public/spark/runs.json',import.meta.url)));
const run=expandRun(table.runs[0]),gen=buildGenome({focus:50,calm:60,spark:70},run,null,10),byKey=new Map([[run.key,run]]);
function storage(){const values=new Map();return {values,getItem:k=>values.get(k)??null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)};}
function learned(){
 const store=storage();selectSpark(store,gen);const session=readSparkSession(store);
 nameBeast(session,'Little Juniper');careAction(session,'pet');finishTraining(session,4,6);talkAndGrow(session,'sunflower code marigold');
 for(let i=0;i<90;i++)advanceCreature(session,{place:i<45?'grove':'shore',toy:.8,comfort:.5,noise:i%4===0?.7:0});
 saveSparkSession(store,session);return session;
}
test('whole journey restores alias, care, mind and exact bounded behavior after recent-log eviction',()=>{
 const original=learned(),text=serializeDeviceJourney(original,byKey),journey=readDeviceJourney(text,byKey),target=storage(),restored=restoreDeviceJourney(target,journey);
 assert.deepEqual(restored.beast.qbeast,original.beast.qbeast);assert.deepEqual(restored.beast.genome,original.beast.genome);
 assert.equal(restored.beast.displayName,'Little Juniper');assert.equal(restored.beast.xp,original.beast.xp);
 assert.equal(restored.beast.bond,original.beast.bond);assert.equal(restored.beast.energy,original.beast.energy);
 assert.deepEqual(restored.mind,original.mind);assert.deepEqual(restored.chat,original.chat);assert.deepEqual(restored.train,original.train);
 assert.deepEqual(restored.beast.behavior,original.beast.behavior);assert.equal(restored.beast.behavior.events.length,32);
 assert.deepEqual(readSparkSession(target).beast.behavior,original.beast.behavior);
 assert.deepEqual(restored.beast.qbeast.progress,{trust:0,bond:0,evolution_stage:0});
});
test('unsigned native bytes travel exactly but fresh import never grants native stage',()=>{
 const original=learned(),bytes=Uint8Array.from({length:32768},(_,i)=>i%256),native=Buffer.from(bytes).toString('base64');
 original.beast.nativeStage=3;original.beast.stage=3;original.beast.game={game_xp:543,game_stage:3,native_save:native};original.beast.localGrowth.game=original.beast.game;
 const restored=restoreDeviceJourney(storage(),readDeviceJourney(serializeDeviceJourney(original,byKey),byKey));
 assert.equal(restored.beast.nativeStage,1);assert.equal(restored.beast.stage,1);assert.deepEqual(restored.beast.game,{});
 assert.equal(restored.beast.journeyNative.status,'unsigned-unverified');assert.equal(restored.beast.journeyNative.nativeStage,3);
 assert.deepEqual(retainedNativeBytes(restored.beast),bytes);
 const again=readDeviceJourney(serializeDeviceJourney(restored,byKey),byKey);assert.equal(again.session.beast.journeyNative.game.native_save,native);
});
test('same-ID device keeps established cartridge state while imported unsigned memory restores',()=>{
 const incoming=learned();incoming.beast.nativeStage=3;incoming.beast.stage=3;incoming.beast.game={game_xp:20,game_stage:3};incoming.beast.localGrowth.game=incoming.beast.game;
 const target=storage();selectSpark(target,gen);const prior=readSparkSession(target);prior.beast.nativeStage=2;prior.beast.stage=2;prior.beast.game={game_xp:999,game_stage:2};prior.beast.localGrowth.game=prior.beast.game;prior.beast.localGrowth.applied=['native-existing'];saveSparkSession(target,prior);
 const restored=restoreDeviceJourney(target,readDeviceJourney(serializeDeviceJourney(incoming,byKey),byKey));
 assert.equal(restored.beast.nativeStage,2);assert.equal(restored.beast.stage,2);assert.equal(restored.beast.game.game_xp,999);
 assert.deepEqual(restored.beast.localGrowth.applied,['native-existing']);assert.equal(restored.beast.journeyNative.game.game_xp,20);
 assert.deepEqual(restored.mind,incoming.mind);
});
test('archived same-ID native state wins even while a different Beast is active',()=>{
 const target=storage();selectSpark(target,gen);const prior=readSparkSession(target);prior.beast.nativeStage=2;prior.beast.stage=2;prior.beast.game={game_xp:999,game_stage:2};prior.beast.localGrowth.game=prior.beast.game;saveSparkSession(target,prior);
 selectSpark(target,buildGenome({focus:90,calm:10,spark:20},run,null,10));
 const restored=restoreDeviceJourney(target,readDeviceJourney(serializeDeviceJourney(learned(),byKey),byKey));assert.equal(restored.beast.nativeStage,2);assert.equal(restored.beast.game.game_xp,999);
});
test('a later real native save and an earlier retained save both survive another journey import',()=>{
 const incoming=learned(),older=Buffer.alloc(32768,11).toString('base64'),newer=Buffer.alloc(32768,22).toString('base64');
 incoming.beast.journeyNative={status:'unsigned-unverified',nativeStage:2,game:{native_save:older,game_xp:20},applied:[]};incoming.beast.nativeStage=3;incoming.beast.stage=3;incoming.beast.game={native_save:newer,game_xp:80};incoming.beast.localGrowth.game=incoming.beast.game;
 const restored=restoreDeviceJourney(storage(),readDeviceJourney(serializeDeviceJourney(incoming,byKey),byKey));assert.equal(restored.beast.journeyNative.game.native_save,newer);assert.equal(restored.beast.journeyNative.retained[0].game.native_save,older);
 const text=serializeDeviceJourney(restored,byKey);assert.ok(text.includes(older));assert.ok(text.includes(newer));assert.equal(restored.beast.nativeStage,1);
});
test('file, numeric, chat and word bounds reject before a storage mutation',()=>{
 const original=JSON.parse(serializeDeviceJourney(learned(),byKey));
 for(const mutate of [x=>x.session.beast.xp=-1,x=>x.session.beast.energy=101,x=>x.session.train.score=1e100,x=>x.session.chat.push(...Array(81).fill({role:'you',text:'hi'})),x=>x.session.mind.weights[0][0]=5,x=>x.session.mind.vocab={...x.session.mind.vocab,...Object.fromEntries(Array.from({length:1025},(_,i)=>['word'+i,{count:1}]))}]){
  const file=structuredClone(original);mutate(file);assert.throws(()=>readDeviceJourney(JSON.stringify(file),byKey),/journey/i);
 }
 assert.throws(()=>readDeviceJourney(' '.repeat(DEVICE_JOURNEY_LIMIT+1),byKey),/under 2 MiB/);
});
test('forged recipe, kernel decision and imported authority are refused',()=>{
 const original=JSON.parse(serializeDeviceJourney(learned(),byKey));
 for(const mutate of [x=>x.session.beast.genome.body='invented',x=>x.session.beast.behavior.genesis_seed='wrong',x=>x.session.beast.behavior.events.at(-1).result.energyAfter=100,x=>x.session.ownerPermissions={all:true},x=>x.session.beast.behavior.signature='trusted',x=>x.qbeast.progress.evolution_stage=2]){
  const file=structuredClone(original);mutate(file);assert.throws(()=>readDeviceJourney(JSON.stringify(file),byKey));
 }
 const text=JSON.stringify(original).replace('"vocab":{','"vocab":{"__proto__":{"count":1},');assert.throws(()=>readDeviceJourney(text,byKey),/unsafe record/);
});
test('a failed restore rolls back selection, per-ID records, profile and care together',()=>{
 const target=storage(),other=buildGenome({focus:90,calm:10,spark:20},run,null,10);selectSpark(target,other);
 const before=new Map(target.values),originalSet=target.setItem;let refused=false;
 target.setItem=(key,value)=>{if(!refused&&key===SESSION_KEY&&JSON.parse(value).beast?.displayName==='Little Juniper'){refused=true;throw Error('fixture quota');}return originalSet(key,value);};
 assert.throws(()=>restoreDeviceJourney(target,readDeviceJourney(serializeDeviceJourney(learned(),byKey),byKey)),/quota/);
 assert.deepEqual(target.values,before);assert.equal(readSparkSession(target).beast.seed,other.seed);
 assert.ok(target.getItem(SESSION_KEY));assert.ok(target.getItem(QBEAST_KEY));assert.ok(target.getItem(PROFILE_KEY));
});
test('archived Rigetti simulator recipe round-trips through the same verifier',()=>{
 const receipt=JSON.parse(readFileSync(new URL('../public/spark/rigetti-qvm-sim.json',import.meta.url))),qvm=validateQvmReceipt(receipt)[0],g=buildGenome({focus:30,calm:40,spark:80},qvm,null,10),map=new Map([[qvm.key,qvm]]),store=storage();
 selectSpark(store,g);const original=readSparkSession(store);advanceCreature(original,{toy:.6});
 const restored=restoreDeviceJourney(storage(),readDeviceJourney(serializeDeviceJourney(original,map),map));
 assert.deepEqual(restored.beast.genome,g);assert.equal(restored.beast.qbeast.profile.id,original.beast.qbeast.profile.id);assert.equal(restored.beast.stage,1);
});
