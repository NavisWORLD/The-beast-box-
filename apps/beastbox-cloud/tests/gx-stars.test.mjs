// GENESIS X step 3: night starfield with depth + nebula colour in the first-person sky dome. On the one sun's night only, thinned by cloud and storm. No random calls.
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const look=readFileSync(new URL('../lib/universe/one-world-look.ts',import.meta.url),'utf8');
const lw=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
test('three star layers (far faint many, mid, near bright with halo) and a nebula band',()=>{assert.equal((look.match(/st\+=starLayer\(/g)||[]).length,3);assert.match(look,/vec3 nightSky\(/);assert.match(look,/export const STARS3=Object\.freeze\(\{label:'SEEDED'/);});
test('gated by night amount from the one sun day factor, cloud cover and storm',()=>{assert.match(look,/if\(uNight>\.002&&e>-\.02\)c\+=nightSky/);assert.match(lw,/amount:\(1-os1\.day\)\*\(1-\.85\*p2s\.cover\)\*\(1-p2s\.darken\)/);});
test('nebula axis is SEEDED from the world seed stream',()=>{assert.match(lw,/lwStream\(u\.seed\+':nebula'\)/);});
test('no Math.random',()=>{assert.doesNotMatch(look,/Math\.random/);});
