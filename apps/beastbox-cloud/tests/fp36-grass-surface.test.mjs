import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const src=f=>readFileSync(new URL('../'+f,import.meta.url),'utf8');
test('first person (target 36): the surface ground-cover grass (lilac/teal blade + tip) goes lush green, off in the Cage and orbit',()=>{const s=src('lib/universe/surface-three.ts'),w=src('components/living-world.tsx');
 assert.match(s,/uFp36:\{value:0\}/);assert.match(s,/const fpG=cfg\.thin===1\|\|\/blade\|tip\/i\.test/);assert.match(s,/diffuseColor\.rgb=mix\(diffuseColor\.rgb,m36,uFp36\)/);assert.match(s,/setFirstPerson/);
 assert.match(w,/\(surface as any\)\?\.setFirstPerson\?\.\(fg\.value\)/);assert.ok(!s.includes('Math.random')&&!w.includes('Math.random'));});
