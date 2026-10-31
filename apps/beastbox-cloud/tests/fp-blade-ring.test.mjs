import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const w=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
test('first person: sparse far blade ring 6-11 units per Cosmo spec',()=>{
 assert.match(w,/const RING_IN=6,RING_FULL=9\.5,RING_OUT=11;/);
 assert.match(w,/tier0==='LOW'\?Math\.round\(ringMax\/3\)/);
 assert.match(w,/lwStream\(u\.seed\+':blade-ring'\)/);
 assert.match(w,/vec3 p=\.85\*rK\*position\*/);
 assert.match(w,/const FP_RES_CLEAR=6;/);
 assert.ok(!w.includes('Math.random'));});
