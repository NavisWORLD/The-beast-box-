import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const src=f=>readFileSync(new URL('../'+f,import.meta.url),'utf8');
test('first person (target 36): biome cutouts leave the near frame and come back outside first person',()=>{const w=src('components/living-world.tsx');
 assert.match(w,/const FP_PROP_CLEAR=4;/);assert.match(w,/const nearF=fpOn&&ang\(ps\.n,pN\)<FP_PROP_CLEAR;/);assert.match(w,/else if\(ps\.fpHid\)\{ps\.fpHid=0;ps\.spr\.visible=true;\}/);assert.ok(!w.includes('Math.random'));});
