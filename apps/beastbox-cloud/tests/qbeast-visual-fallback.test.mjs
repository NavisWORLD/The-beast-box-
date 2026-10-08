import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=path=>readFileSync(new URL('../'+path,import.meta.url),'utf8');

test('QBEAST fallback uses the real shared seeded sprite and stage',()=>{
 const scene=read('components/cosmic-companion-3d.tsx');
 const home=read('components/homepage-creature.tsx');
 assert.match(scene,/import PixelBeast from '\.\/pixel-beast'/);
 assert.match(scene,/data-fallback="same-qbeast-sprite"/);
 assert.match(scene,/publicSpark pose=/);
 assert.match(scene,/setFallback\(true\)/);
 assert.match(scene,/renderer\.render\(scene,camera\)/);
 assert.match(home,/useBeastSession\(\)/);
 assert.match(home,/savedBeast\.qbeast\.profile\.id/);
 assert.match(home,/preferSprite=\{Boolean\(genome\)\}/);
 assert.match(home,/nativeStage\|\|savedBeast\?\.stage/);
});
test('fallback never mutates identity, growth or native battery',()=>{
 const files=['components/cosmic-companion-3d.tsx','components/homepage-creature.tsx','components/pixel-beast.tsx'];
 const src=files.map(read).join('\n');
 assert.doesNotMatch(src,/applyGameReturn|setItem\(|localStorage\.setItem|native_save\s*=/);
 assert.match(read('components/pixel-beast.tsx'),/catch\{/);
});
