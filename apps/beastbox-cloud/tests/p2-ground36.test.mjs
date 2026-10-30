import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const src=f=>readFileSync(new URL('../'+f,import.meta.url),'utf8');
test('P2 ground (target 36): green meadow palette, labelled, no random; old olive constants gone',()=>{const s=src('lib/universe/one-world-look.ts');
 assert.match(s,/MEADOW36=Object\.freeze\(\{label:'SEEDED'/);assert.match(s,/uBase:\{value:new THREE\.Color\(MEADOW36\.base\)\}/);assert.ok(!s.includes("#5F6B40"));assert.ok(!s.includes('vec3(.115,.147,.051)'));assert.ok(!s.includes('Math.random'));});
test('orbit: seeded ember stripes are fallback-only (no pink-orange arcs over the mapped sea)',()=>{assert.match(src('components/living-world.tsx'),/if\(b==7&&uUseMap<\.5\)col\+=vec3\(\.6,\.2,\.05\)/);});
test('first person: beast greets ahead, near the middle',()=>{assert.match(src('components/living-world.tsx'),/addScaledVector\(pF,2\.4\/PR\)\.addScaledVector\(side,\.35\/PR\)/);});
