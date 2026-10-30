import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const src=f=>readFileSync(new URL('../'+f,import.meta.url),'utf8');
test('P1 fix-ups: one-sun lightRigFor drives the existing sun + hemisphere, no new light',()=>{const s=src('components/living-world.tsx');assert.match(s,/const rig=lightRigFor\(os1,renderer\.toneMappingExposure\);/);assert.match(s,/sun\.intensity=rig\.sunIntensity;hemi\.intensity=rig\.hemiIntensity/);});
test('P1 fix-ups: Motion · SIMULATED label sits with the view chips',()=>{assert.match(src('components/living-world.tsx'),/data-lw-motion[^>]*>Motion · SIMULATED</);});
test('P1 fix-ups: neighbour world smaller and higher in first person; ridges hazy; ground has seeded land noise; no Math.random',()=>{const s=src('lib/universe/one-world-look.ts');
 assert.match(s,/NEIGHBOUR_FP=Object\.freeze\(\{label:'SEEDED',elevationDeg:44,angularDeg:5\.4\}\)/);assert.match(s,/uHz/);assert.match(s,/fbm\(q\*3\.1/);assert.ok(!s.includes('Math.random'));});
test('P1 fix-ups: foam samples two rotated scales (breaks tiling)',()=>{assert.match(src('components/living-world.tsx'),/mat2\(\.8,-\.6,\.6,\.8\)\*fuv/);});
