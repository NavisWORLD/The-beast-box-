import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const w=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
const r=d=>0.56*Math.min(2.5,Math.max(1,d/3.5));
test('ring parting radius scales with distance, near patch unchanged',()=>{
 assert.match(w,/float rPart=\.56\*clamp\(aRing\.y\/3\.5,1\.0,2\.5\)\/uR;/);
 assert.match(w,/split\('smoothstep\(\.07,\.0,dd'\)\.join\('smoothstep\(rPart,\.0,dd'\)/);
 assert.match(w,/float k=smoothstep\(\.07,\.0,dd\)/);assert.match(w,/smoothstep\(\.07,\.0,ddT\)/);
 assert.ok(Math.abs(r(8)-1.28)<.01);assert.equal(r(20),1.4);assert.equal(r(2),.56);assert.ok(Math.abs(.07*8-.56)<1e-9);
 assert.match(w,/const FP_RES_CLEAR=6;/);assert.ok(!w.includes('Math.random'));});
