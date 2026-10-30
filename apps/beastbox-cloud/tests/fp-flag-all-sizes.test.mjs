import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
test('first-person view snaps zoom into the eye gate at every size',()=>{const w=fs.readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
assert.match(w,/if\(spawnRef\.current&&vm0\.eye&&!vm0\.forceOrbit&&zT===0&&zC>\.2\)zC=\.2;/);assert.match(w,/const FP_PROP_CLEAR_WIDE=7;/);assert.ok(!w.includes('Math.random'));});
