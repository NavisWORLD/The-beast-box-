import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
test('every living-core / creature point shader caps its size and fades inside the lens radius', () => {
  for (const f of ['../lib/living-core/living-core.js','../components/zeref-glb-3d.tsx','../lib/living-core/roam-extras.ts','../lib/living-core/river-flow.ts']) {
    const s=read(f);const sizes=s.match(/gl_PointSize=[^;]*;/g)||[];assert.ok(sizes.length>0,f);
    for (const g of sizes.filter(x=>x!=="gl_PointSize=0.;")) { assert.match(g,/smoothstep\(\.35,1\.1,-mv\.z\)/,f+': '+g); assert.match(g,/min\(|clamp\(/,f+': '+g); }
  }
  const nl=read('../lib/living-core/near-lens.ts');assert.match(nl,/MAX_POINT_PX=40/);assert.match(nl,/logdepthbuf_vertex/);
  const cage=read('../components/cage-pocket-dimension.tsx');assert.match(cage,/capScenePoints\(scene\)/);assert.match(cage,/pushCameraOut\(camera\.position/);
});
test('pushCameraOut keeps the camera outside every creature radius', () => {
  const src=read('../lib/living-core/near-lens.ts');const body=src.slice(src.indexOf('export function pushCameraOut'));
  const fn=new Function('LENS_RADIUS',body.replace(/export function pushCameraOut\(cam:\{[^)]*\},bodies:[^)]*\]\s*,R=LENS_RADIUS\)/,'return function(cam,bodies,R=LENS_RADIUS)').replace(/:\{x:number;y:number;z:number;r\?:number\}\[\]/g,''))(1);
  const cam={x:.1,y:.2,z:.1};fn(cam,[{x:0,y:0,z:0,r:.4}]);assert.ok(Math.hypot(cam.x,cam.y,cam.z)>=1.4-1e-9);
  const c2={x:5,y:5,z:5};assert.equal(fn(c2,[{x:0,y:0,z:0,r:.4}]),0);
});
