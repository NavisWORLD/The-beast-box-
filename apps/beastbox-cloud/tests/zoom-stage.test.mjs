import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const src=readFileSync(new URL('../components/universe-3d.tsx',import.meta.url),'utf8');
test('zoom stage labels cover six levels, so Neighbours and Universe are reachable and the labels move',()=>{
 const m=src.match(/export function zoomStage\(d:number\)\{return ([^}]+)\}/);assert.ok(m);const f=new Function('d','return '+m[1].replace(/;$/,''));
 const seq=[3,10,25,80,300,900].map(f);assert.deepEqual(seq,['Surface','Planet','Orbit','System','Neighbours','Universe']);});
test('planet sun direction refreshes the parent matrix before reading its world position',()=>{
 const b=readFileSync(new URL('../lib/universe/planet-body-three.ts',import.meta.url),'utf8');assert.match(b,/updateWorldMatrix\(true,false\)[^]*getWorldPosition\(cen\)/);});
test('selected worlds slow their orbit',()=>{assert.match(src,/pinned\?\.1:1/);assert.match(src,/place\(simT\)/);});
