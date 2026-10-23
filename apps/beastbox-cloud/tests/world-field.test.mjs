import test from 'node:test';import assert from 'node:assert/strict';
import {createWorldField,stepWorldField,createCreatureLoop,stepCreature} from '../lib/universe/world-field.mjs';
import {verifyStream} from '../lib/zeref/experience-record.mjs';
const init=n=>({id:Math.abs(n[0])>.7?'deep_ocean':'grassland',h:Math.abs(n[0])>.7?-.2:.2});
const run=()=>{const F=createWorldField({seed:'s',W:16,H:8,initial:init});const B=createCreatureLoop('b','s',{qbeast_id:'bb-12345678'}),Z=createCreatureLoop('z','s');const recs=[];
 for(let i=0;i<400;i++){stepWorldField(F,1,{sun:[Math.cos(i/30),0,Math.sin(i/30)],activity:Math.sin(i/20)});recs.push(...stepCreature(B,F,[0,0,1],1,{curiosity:.5,joy:.5,calm:.5},{others:[Z]}).records);}
 return {F,recs};};
test('world field is deterministic, evolves from the CST loop, and keeps records chained',()=>{const a=run(),b=run();
 assert.deepEqual([...a.F.idx],[...b.F.idx]);assert.equal(a.F.tick,1600);assert.ok(Number.isFinite(a.F.S.L.z));
 assert.ok(a.recs.length>0);assert.equal(verifyStream(a.recs).ok,true);});
