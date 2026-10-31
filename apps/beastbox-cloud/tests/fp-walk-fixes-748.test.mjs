import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const w=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
test('Cosmo walk of #745/#746: wheel, pitch caps, shore margin, menu wording, tapped keys',()=>{
 assert.match(w,/if\(fpOn\|\|spawnRef\.current&&viewModeCamera\(viewRef\.current\)\.eye\)/);
 assert.match(w,/const FP_UP=65\*Math\.PI\/180;/);assert.match(w,/fpP=Math\.max\(-FP_DOWN,Math\.min\(FP_UP,fpP\)\)/);
 assert.match(w,/smoothstep\(\.435,\.47,hM\)/);
 assert.match(w,/✦ Spawn in · First person/);assert.match(w,/>View: First person</);assert.match(w,/>View: Orbit</);
 assert.match(w,/KeyboardEvent\('keydown',\{key:'Escape'\}\)/);
 assert.match(w,/performance\.now\(\)-kt<180/);
 assert.match(w,/const FP_RES_CLEAR=6;/);assert.ok(!w.includes('Math.random'));});
