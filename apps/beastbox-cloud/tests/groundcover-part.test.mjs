import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
const w=fs.readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
test('blades part around the live creature positions and lean with storm wind (no random, one clock)',()=>{assert.match(w,/uniform float uWindK/);assert.match(w,/push\+=normalize\(dq/);assert.match(w,/__lwGroundCover/);assert.match(w,/weather\.wind/);});
