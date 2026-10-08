import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('home guide is a visual-only reaction, not a second QBEAST or new care store',()=>{
 const src=read('components/homepage-creature.tsx');
 assert.match(src,/setWaved\(value=>!value\)/);
 assert.match(src,/state=\{genome\?visualStateFromBeast\(savedBeast\):waveMood\}/);
 assert.match(src,/preferSprite=\{Boolean\(genome\)\}/);
 assert.match(src,/spriteId=\{savedBeast\?\.qbeast\?\.profile\?\.id\|\|''\}/);
 assert.match(src,/same QBEAST you saved/);
 assert.match(src,/Guide reaction is visual only/);
 assert.doesNotMatch(src,/change\(|localStorage\.setItem|adoptBeast\(/);
});
test('onboarding preserves real generator and creature destinations',()=>{
 const src=read('components/homepage-creature.tsx');
 assert.match(src,/href="\/spark\/index\.html"/);
 assert.match(src,/href="\/beast-cage#habitat"/);
 assert.match(src,/Wave hello/);
});
