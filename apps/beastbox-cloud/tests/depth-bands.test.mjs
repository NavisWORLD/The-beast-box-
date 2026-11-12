import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {altitudeOf,depthBand,depthLOD,DEPTH_BANDS,DEPTH_LOD,DEPTH_LABEL} from '../lib/universe/depth-bands.mjs';
const src=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('depth bands run meadow to deep space along one zoom',()=>{
 assert.equal(altitudeOf(8,8),0);assert.equal(altitudeOf(4,8),0);
 assert.deepEqual([0,.1,.3,1,9].map(a=>depthBand(a).id),['meadow','canopy','sky','orbit','deep']);
 for(let i=1;i<DEPTH_BANDS.length;i++)assert.ok(DEPTH_BANDS[i].maxAlt>DEPTH_BANDS[i-1].maxAlt);
});
test('LOD weights are continuous and honest',()=>{
 assert.equal(depthLOD(0).ground,1);assert.equal(depthLOD(5).ground,0);assert.equal(depthLOD(0).lattice,0);assert.equal(depthLOD(5).lattice,1);
 let prev=1;for(let a=0;a<=1;a+=.01){const g=depthLOD(a).ground;assert.ok(g<=prev+1e-9);prev=g;}
 assert.match(DEPTH_LABEL,/12D model simulation/);assert.doesNotMatch(DEPTH_LABEL,/real physics|live quantum/i);
});
test('the living world and the ground cover read the same depth edges',()=>{
 const lw=src('components/living-world.tsx'),st=src('lib/universe/surface-three.ts');
 assert.match(lw,/depthLOD\(altitudeOf\(/);assert.match(lw,/data-lw-depth/);
 assert.match(st,/DEPTH_LOD\.groundIn/);assert.ok(!/Math\.random/.test(src('lib/universe/depth-bands.mjs')));
 assert.equal(DEPTH_LOD.groundIn<DEPTH_LOD.groundOut,true);
});
