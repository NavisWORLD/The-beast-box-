import test from 'node:test';
import assert from 'node:assert/strict';
import {getOrCreateVisitorId,freshGrowth,readVisitorGrowth,writeVisitorGrowth,advanceVisitorGrowth,growthModelContext,GROWTH_SOURCE} from '../lib/companion/visitor-growth.mjs';
const a='11111111-1111-4111-8111-111111111111',b='22222222-2222-4222-8222-222222222222';
function store(){const m=new Map();return {getItem:k=>m.get(k)??null,setItem:(k,v)=>m.set(k,v),_map:m};}
test('visitor IDs are local, stable and separate; missing storage is not silently shared',()=>{
 const s=store(),t=store();
 assert.equal(getOrCreateVisitorId(s,()=>a),a);
 assert.equal(getOrCreateVisitorId(s,()=>b),a);
 assert.equal(getOrCreateVisitorId(t,()=>b),b);
 assert.equal(getOrCreateVisitorId({getItem(){throw Error('blocked');}},()=>a),null);
});
test('two visitors and two creatures never mix growth records',()=>{
 const s=store(),baseline=freshGrowth(a,'zeref:shared-model');
 const evolved=advanceVisitorGrowth(baseline,{text:'Look at my world',reply:'I see stars',verified:true});
 assert.equal(evolved.exchanges,1);assert.equal(evolved.stimulus.shots,8);
 assert.equal(evolved.stimulus.source,GROWTH_SOURCE);
 assert.equal(writeVisitorGrowth(s,evolved),true);
 assert.deepEqual(readVisitorGrowth(s,a,'zeref:shared-model'),evolved);
 assert.equal(readVisitorGrowth(s,b,'zeref:shared-model').exchanges,0);
 assert.equal(readVisitorGrowth(s,a,'spark:another').exchanges,0);
});
test('unverified responses cannot advance or invent an experience',()=>{
 const s=freshGrowth(a,'zeref');
 assert.equal(advanceVisitorGrowth(s,{text:'hi',reply:'hello'}),s);
 assert.equal(advanceVisitorGrowth(s,{text:'hi',reply:'',verified:true}),s);
 assert.equal(advanceVisitorGrowth(s,{text:'',reply:'hi',verified:true}),s);
});
test('deterministic bounded classical stimulus; only metadata is persisted or shared',()=>{
 const s=store();let v=freshGrowth(a,'zeref');
 for(let i=0;i<70;i++)v=advanceVisitorGrowth(v,{text:'personal secret '+i,reply:'another secret',verified:true});
 assert.equal(v.exchanges,70);assert.equal(v.stimulus.shots,48);assert.ok(v.curiosity<=100);
 assert.deepEqual(v,Array.from({length:70}).reduce((x,_,i)=>advanceVisitorGrowth(x,{text:'personal secret '+i,reply:'another secret',verified:true}),freshGrowth(a,'zeref')));
 writeVisitorGrowth(s,v);
 const raw=JSON.stringify([...s._map.values()]);
 const context=growthModelContext(v);
 assert.doesNotMatch(raw,/personal secret|another secret/);
 assert.doesNotMatch(context,/personal secret|another secret|11111111/);
 assert.match(context,/classical QVM-inspired simulation, not Rigetti hardware/);
 const key=[...s._map.keys()][0];s._map.set(key,JSON.stringify({...v,visitorId:b}));
 assert.equal(readVisitorGrowth(s,a,'zeref').exchanges,0);
});
