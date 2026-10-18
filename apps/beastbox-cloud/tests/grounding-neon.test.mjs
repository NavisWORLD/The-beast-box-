import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {groundRay,planetWalk,plantFoot,airTarget} from '../lib/worlds/grounding.mjs';
import {normalizePocket3D,DEFAULT_POCKET_3D} from '../lib/companion/pocket-3d-settings.mjs';
const src=p=>fs.readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('ground ray: floor, island top, planet normal, branch',()=>{assert.equal(groundRay({x:0,y:1,z:0}).kind,'floor');
 const W=[{x:10,y:5,z:0,r:3,kind:'island',top:.15},{x:-20,y:5,z:0,r:4,kind:'planet'}];
 const i=groundRay({x:10.5,y:6,z:0},{worlds:W});assert.equal(i.kind,'island');assert.ok(Math.abs(i.y-5.15)<1e-9);
 const p=groundRay({x:-19,y:12,z:0},{worlds:W});assert.equal(p.kind,'planet');assert.ok(Math.abs(Math.hypot(p.n.x,p.n.y,p.n.z)-1)<1e-9&&p.n.x>0);
 const b=groundRay({x:1,y:2,z:0},{branches:[{a:{x:0,y:1.5,z:0},b:{x:3,y:1.5,z:0},r:.2}]});assert.equal(b.kind,'branch');assert.ok(Math.abs(b.y-1.7)<1e-9);
 assert.equal(groundRay({x:1,y:.5,z:0},{branches:[{a:{x:0,y:1.5,z:0},b:{x:3,y:1.5,z:0},r:.2}]}).kind,'floor');});
test('planet walk stays on the sphere; feet plant; air blend',()=>{const c={x:1,y:2,z:3};for(const a of [0,.4,.9]){const w=planetWalk(c,4,a,1.2);assert.ok(Math.abs(Math.hypot(w.pos.x-c.x,w.pos.y-c.y,w.pos.z-c.z)-4)<1e-9);}
 assert.equal(plantFoot(1.3,1,0),1);assert.equal(plantFoot(.7,1,0),1);assert.equal(plantFoot(3,1,1),3);assert.equal(airTarget('go'),1);assert.equal(airTarget('stay'),0);});
test('neon wire: config toggle, distance legibility, overlay not replacement, constant scale',()=>{assert.equal(DEFAULT_POCKET_3D.neonWire,true);assert.equal(normalizePocket3D({neonWire:false}).neonWire,false);
 const n=src('lib/worlds/neon-wire.ts');assert.match(n,/fwidth/);assert.match(n,/gl_FragColor\.rgb\+=/);assert.doesNotMatch(n,/gl_FragColor\.rgb=/);
 const c=src('components/cage-pocket-dimension.tsx');assert.match(c,/neonDistGain\(camera\.position\.distanceTo/);assert.match(c,/setFromUnitVectors\(_Y,_n\)/);assert.match(c,/contact-shadow/);
 const w=src('lib/worlds/worlds.ts');assert.doesNotMatch(w,/zHolder|scale\.setScalar\(.*tripT/);assert.match(src('components/universe-settings.tsx'),/Neon wireframe/);});
