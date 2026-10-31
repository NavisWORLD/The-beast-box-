import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const w=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
test('Cosmo #743 walk fixes: menu entries, eye floor, shore mask',()=>{
 assert.match(w,/data-lw-menu-orbit/);assert.match(w,/data-lw-menu-fp/);
 assert.match(w,/const FP_DOWN=40\*Math\.PI\/180;/);assert.match(w,/fpP=Math\.max\(-FP_DOWN,fpP\)/);
 assert.match(w,/smoothstep\(\.425,\.445,hM\)/);assert.match(w,/const FP_RES_CLEAR=6;/);assert.ok(!w.includes('Math.random'));});
