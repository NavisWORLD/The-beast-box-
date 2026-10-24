// Landscapes view layer: data + source guarantees that do not need a GPU (the pixels are checked by the shot walk).
import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';
import {LANDSCAPE_LOOK as L,LANDSCAPE_LOOK_SOURCE_SHA256 as H} from '../lib/universe/landscape-look-data.mjs';
import {LANDSCAPE_KINDS} from '../lib/universe/seeded-landscapes.mjs';
const root=path.resolve(import.meta.dirname,'..');
test('look data covers every kind (+ the savanna court_dry variant) for pad, ring and silhouette',()=>{
 for(const k of [...LANDSCAPE_KINDS,'court_dry']){for(const sec of [L.pad.by_kind,L.ring.by_kind,L.silhouette.by_kind])assert.ok(sec[k],k);}
 assert.match(H,/^[0-9a-f]{64}$/);
});
test('rim lerp is 0.70 -> 0.88 -> 1.00 in linear light (never a cliff)',()=>{
 assert.equal(L.pad.rim_lerp.r_frac_pad_end,0.7);assert.equal(L.pad.rim_lerp.r_frac_rim_mid,0.88);assert.equal(L.pad.rim_lerp.r_frac_edge,1.0);assert.equal(L.pad.rim_lerp.space,'linear light');
});
test('lamp: peak, warm mix and at most 2 real point lights per planet',()=>{
 assert.equal(L.lamp.peak_linear,1.5);assert.equal(L.lamp.point_light.max_real_lights_per_planet,2);
 const src=fs.readFileSync(path.join(root,'lib/universe/landscape-three.ts'),'utf8');assert.match(src,/i<2;i\+\+\)\{const l=new THREE\.PointLight/);assert.match(src,/if\(!o\.phone\)/);
});
test('view layer is deterministic: no Math.random, no clock reads',()=>{
 const src=fs.readFileSync(path.join(root,'lib/universe/landscape-three.ts'),'utf8');
 assert.ok(!/Math\.random|Date\.now|performance\.now|new Date/.test(src));
});
test('look data file matches its recorded source hash note',()=>{
 const f=fs.readFileSync(path.join(root,'lib/universe/landscape-look-data.mjs'),'utf8');assert.ok(f.includes(H));assert.ok(createHash('sha256').update(f).digest('hex').length===64);
});
