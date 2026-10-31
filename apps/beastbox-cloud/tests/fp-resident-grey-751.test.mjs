import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const w=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
test('#751: fade completes on wall time, patches under residents, nopatch flag, LOW clumps 32',()=>{
 assert.match(w,/r\.fpFadeW=performance\.now\(\)/);assert.match(w,/\(performance\.now\(\)-r\.fpFadeW\)\/\(FP_FADE_S\*1000\)/);
 assert.match(w,/pm\.renderOrder=-1;/);assert.match(w,/polygonOffset:true/);assert.match(w,/get\('nopatch'\)==='1'/);
 assert.match(w,/const NC=lowT\?32:40/);assert.match(w,/__lwFpFade=/);assert.match(w,/const FP_RES_CLEAR=6;/);assert.ok(!w.includes('Math.random'));});
