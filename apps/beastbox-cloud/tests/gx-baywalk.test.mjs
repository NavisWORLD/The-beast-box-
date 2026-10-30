import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {inBayWater,bayFrom,OCEAN3} from '../lib/universe/p3-ocean.mjs';
const bay={bearing:0.5,halfWidth:50*Math.PI/180,innerM:OCEAN3.innerM};
test('points out in the bay are water, the shore you stand on is not',()=>{
 assert.equal(inBayWater(bay,Math.cos(.5)*300,Math.sin(.5)*300),true);
 assert.equal(inBayWater(bay,0,0),false);
 assert.equal(inBayWater(bay,Math.cos(.5)*10,Math.sin(.5)*10),false);
 assert.equal(inBayWater(bay,Math.cos(.5+Math.PI)*300,Math.sin(.5+Math.PI)*300),false);});
test('the wedge is wider than the drawn coast (margin covers the coast wobble)',()=>{
 const a=.5+bay.halfWidth+.05;assert.equal(inBayWater(bay,Math.cos(a)*400,Math.sin(a)*400),true);});
test('pure: same input same answer, works with a seeded bay',()=>{let i=0;const r=()=>((i++*0.618)%1);const b=bayFrom(r);
 assert.equal(inBayWater(b,100,20),inBayWater(b,100,20));});
test('residents steer out of the first-person bay',()=>{const s=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
 assert.match(s,/inBayWater\(p3\.bay,bayV\.x\/P3_MPU,bayV\.z\/P3_MPU\)/);assert.doesNotMatch(readFileSync(new URL('../lib/universe/p3-ocean.mjs',import.meta.url),'utf8'),/Math\.random\(/);});
import {landArcAngle} from '../lib/universe/p3-ocean.mjs';
test('far walkers on their circles never stand in the bay (whole sweep)',()=>{for(const rM of [30,60,120,250,600])for(let th=-40;th<40;th+=.037){const a=landArcAngle(bay,rM,th);
 assert.equal(inBayWater(bay,Math.cos(a)*rM,Math.sin(a)*rM),false,`r=${rM} th=${th}`);}});
test('the walk is continuous (turns back, no teleport)',()=>{let p=landArcAngle(bay,200,0);for(let th=.01;th<30;th+=.01){const a=landArcAngle(bay,200,th);assert.ok(Math.abs(a-p)<.05);p=a;}});
test('ground walkers use the bay',()=>{const s=readFileSync(new URL('../lib/universe/one-world-look.ts',import.meta.url),'utf8');assert.match(s,/landArcAngle\(bay,L\.r\/M,a0\)/);
 assert.match(readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8'),/lk2Ground\.step\(t,p3\.bay\)/);});
