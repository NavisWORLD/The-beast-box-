import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const s=readFileSync(new URL('../lib/universe/one-world-look.ts',import.meta.url),'utf8');
test('skyline is a function of WORLD direction (parallax while moving, same hills when you come back)',()=>{
 assert.match(s,/vW=\(modelMatrix\*vec4\(position,1\.0\)\)\.xyz/);assert.match(s,/vec3 dw=normalize\(vW\)/);assert.match(s,/vn3\(dw\*F\+uP\)/);});
test('two nearer SEEDED hill layers, drawn after the old ones so their seeded draws are unchanged',()=>{
 assert.match(s,/export const RIDGES_NEAR=Object\.freeze\(\[\{d:130,/);assert.ok(s.indexOf('for(const r of RIDGES){')<s.indexOf('for(const r of RIDGES_NEAR){'));
 assert.match(s,/export const RIDGES=Object\.freeze\(\[\{d:300,crestDeg:1\.99,fade:\.077,hex:'#4F7A45'\}/);});
test('near hills stop at the bay; haze follows the live sky horizon',()=>{assert.match(s,/if\(uCut>\.5\)/);assert.match(s,/look\?\.hor\)U\.uHz\.value\.setRGB/);
 assert.match(readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8'),/\{hor:p3Sky\.hz,bay:p3\.bay\}/);});
test('no random calls',()=>{assert.doesNotMatch(s,/Math\.random/);});
