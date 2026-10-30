// GENESIS X step 0: near-grass ground is the target-36 meadow (no cyan biome patches) in first person only; the SEEDED bay turns toward your heading on entering first person.
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const look=readFileSync(new URL('../lib/universe/one-world-look.ts',import.meta.url),'utf8');
const lw=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
test('first-person meadow recolour is gated on uFpMeadow and land only',()=>{assert.match(lw,/if\(uFpMeadow>\.5&&!\(uUseMap>\.5&&texture2D\(uHeight,eqUV\(n\)\)\.r<\.42\)&&b!=0\)/);assert.match(lw,/UG\.uFpMeadow\.value=1;/);assert.match(lw,/bayF=null;UG\.uFpMeadow\.value=0;/);});
test('bay faces the heading via a pure yaw',()=>{assert.match(look,/export function yawToward/);assert.match(lw,/\{fwd:bayF,bearing:p3\.bay\.bearing\}/);assert.doesNotMatch(look,/Math\.random/);});
test('yawToward maps the bearing onto the heading',async()=>{const THREE=await import('three');const q=new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,1,0),new THREE.Vector3(0,0,1));
 const src=look.match(/export function yawToward[\s\S]*?return new THREE\.Quaternion\(\)\.setFromAxisAngle\(u,th\);\}/)[0].replace(/:T|:import\('three'\)\.\w+|:number/g,'').replace('export ','');const yawToward=new Function('return '+src)();
 const up=new THREE.Vector3(0,0,1),fwd=new THREE.Vector3(1,1,0).normalize(),b=1.1;const q2=q.clone().premultiply(yawToward(THREE,q,up,fwd,b));const d=new THREE.Vector3(Math.cos(b),0,Math.sin(b)).applyQuaternion(q2);assert.ok(d.distanceTo(fwd)<1e-6,`${d.toArray()}`);});
