import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {createSandField,sandBudget,wellWeights,ownReceiptPath,SAND_LABEL} from '../lib/pocket-sand.mjs';
test('adaptive budget: phones and reduced motion get fewer particles',()=>{
 assert.equal(sandBudget({reduced:true}),260);assert.equal(sandBudget({width:390}),700);assert.ok(sandBudget({width:1440,cores:8})>sandBudget({width:390}));});
test('field is deterministic from the recorded seed and stays bounded',()=>{
 const a=createSandField({seed:'s1',count:200}),b=createSandField({seed:'s1',count:200}),c=createSandField({seed:'s2',count:200});
 assert.deepEqual([...a.pos],[...b.pos]);assert.notDeepEqual([...a.pos],[...c.pos]);
 for(let t=0;t<300;t++)a.step(1/30,[{x:0,z:0,r:1.2,s:2}]);
 for(let i=0;i<a.count;i++){assert.ok(Math.abs(a.pos[i*3])<=a.half+1e-6&&a.pos[i*3+1]>=0&&Number.isFinite(a.pos[i*3+1]));}});
test('creatures disturb the field',()=>{const a=createSandField({seed:'d',count:400}),b=createSandField({seed:'d',count:400});
 for(let t=0;t<30;t++){a.step(1/30,[]);b.step(1/30,[{x:0,z:0,r:2,s:4}]);}assert.notDeepEqual([...a.pos],[...b.pos]);});
test('receipt counts weight wells; no receipt means even weights and no attribution',()=>{
 assert.deepEqual(wellWeights(null),[1,1,1,1]);const w=wellWeights({'00':115,'01':136,'10':154,'11':107});assert.ok(Math.abs(w.reduce((a,b)=>a+b)-4)<1e-9);
 assert.equal(ownReceiptPath('/spark/azure-rigetti-qvm-20261009.json'),null);assert.equal(ownReceiptPath(null),null);
 assert.equal(ownReceiptPath('/spark/azure-wraith-20261010.json'),'/spark/azure-wraith-20261010.json');
 assert.equal(SAND_LABEL,'Simulated world seeded from recorded measurements');});
test('pocket wires sand with validated receipt only',()=>{const s=readFileSync(new URL('../components/cage-pocket-dimension.tsx',import.meta.url),'utf8');
 assert.ok(s.includes('sand.field.setCounts(qvmCounts)')&&readFileSync(new URL('../components/use-own-qvm-counts.ts',import.meta.url),'utf8').includes('validateRecordedQvmStimulus(j)')&&s.includes('sand.update(dt')&&s.includes('sand.dispose()')&&s.includes('{SAND_LABEL}'));});
