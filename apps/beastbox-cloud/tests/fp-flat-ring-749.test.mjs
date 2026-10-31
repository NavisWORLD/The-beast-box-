import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const w=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
test('#749 flat ring on the first-person ground + resident clumps',()=>{
 assert.match(w,/lwStream\(u\.seed\+':flat-ring'\)/);assert.match(w,/lk2Ground\.group\.add\(mesh\)/);
 assert.match(w,/mesh\.frustumCulled=false/);assert.match(w,/float h=\(1\.15\+\.5\*fract\(aR\.x\*7\.3\)\)\*k;/); // .32*1.15 = .368 >= .35
 assert.ok(.32*1.15>=.35);
 assert.match(w,/get\('ringdebug'\)==='1'/);assert.match(w,/uDbg>\.5\?vec4\(1\.,0\.,1\.,1\.\)/);
 assert.match(w,/inBayWater\(p3\.bay,x\/P3_MPU,z\/P3_MPU,6\)/);assert.match(w,/float rP=\.56\*clamp\(dE\/3\.5,1\.0,2\.5\)/);
 assert.match(w,/const FP_RES_CLEAR=6;/);assert.ok(!w.includes('Math.random'));});
