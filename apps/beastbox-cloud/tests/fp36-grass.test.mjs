import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const src=f=>readFileSync(new URL('../'+f,import.meta.url),'utf8');
test('first person (target 36): near blades go lush green, lit by the one sun, and sit below the eye',()=>{const w=src('components/living-world.tsx');
 assert.match(w,/uFpG:\{value:0\}/);assert.match(w,/mix\(mix\(c\.rgb,g,\.7\),m36,uFpG\)\*vL/);assert.match(w,/fpOn\?FP_BLADE_K:1/);assert.match(w,/const FP_BLADE_K=\.55;/);assert.ok(!w.includes('Math.random'));});
