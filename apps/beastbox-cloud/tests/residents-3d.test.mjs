import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync,existsSync,statSync} from 'node:fs';
const root=new URL('../public/residents3d/',import.meta.url);
test('Frostmitt + Nyxbean ship a visual-hull mesh with front/side/back projections (artist-drawn, no quantum seed)',()=>{
 for(const id of ['art-frostmitt','art-nyxbean']){const meta=JSON.parse(readFileSync(new URL(id+'/meta.json',root),'utf8'));
  for(const f of ['mesh.bin','front.png','side.png','back.png'])assert.ok(existsSync(new URL(id+'/'+f,root)),id+f);
  assert.ok(meta.triangles>2000&&meta.triangles<60000,'phone-sized mesh');assert.match(meta.source,/no quantum seed/);assert.ok(meta.frames.used_times_s.length>=8,'built from many turntable frames');assert.match(meta.frames.matte,/rembg/);
  assert.equal(statSync(new URL(id+'/mesh.bin',root)).size,meta.vertices*24+meta.triangles*3*(meta.index==='u16'?2:4));}
 const r=readFileSync(new URL('../lib/companion/artist-residents.mjs',import.meta.url),'utf8');assert.match(r,/art-frostmitt/);
 const s=readFileSync(new URL('../components/resident-3d.ts',import.meta.url),'utf8');assert.ok(!/bb-7f9c2a03|bb-deada969|zeref/i.test(s.replace(/not Zeref/,'')),'residents are not Zeref');});

test('pocket: tap a creature to focus the camera on it; residents get rim light',()=>{
 const c=readFileSync(new URL('../components/cage-pocket-dimension.tsx',import.meta.url),'utf8');
 assert.match(c,/Raycaster/);assert.match(c,/__pocketFocus/);
 const r=readFileSync(new URL('../components/resident-3d.ts',import.meta.url),'utf8');assert.match(r,/rimColor/);});
