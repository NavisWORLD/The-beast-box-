import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const src=f=>readFileSync(new URL('../'+f,import.meta.url),'utf8');
test('first person (target 36): residents keep out of the near frame; far life starts at 25 m',()=>{const w=src('components/living-world.tsx');
 assert.match(w,/const FP_RES_CLEAR=6;/);assert.match(w,/if\(fpOn&&ang\(r\.n,pN\)<FP_RES_CLEAR\)/);
 assert.match(src('lib/universe/one-world-look.ts'),/band\?200\+rand\(\)\*400:25\+rand\(\)\*95/);assert.ok(!w.includes('Math.random'));});
