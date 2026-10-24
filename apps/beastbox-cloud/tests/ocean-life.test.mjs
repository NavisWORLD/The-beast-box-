import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {oceanLife,memberAt,surfacing,planktonGlow,OCEAN_LABEL} from '../lib/universe/ocean-life.mjs';
const sea=n=>n[1]<.2;// a fake world whose south is water
test('ocean life is deterministic and only in water',()=>{const a=oceanLife('seed-x',sea),b=oceanLife('seed-x',sea),c=oceanLife('seed-y',sea);
 assert.deepEqual(a,b);assert.notDeepEqual(a.schools[0].n,c.schools[0].n);assert.ok(a.schools.length>=15);
 for(const s of a.schools){assert.ok(sea(s.n));for(let i=0;i<s.count;i++)for(const t of [0,5,30])assert.ok(Math.hypot(...memberAt(s,i,t))>.999);}
 for(const p of a.plankton)assert.ok(sea(p.n));assert.ok(a.plankton.length>50);});
test('kinds, label, scaling and animation',()=>{const a=oceanLife('k',sea);const kinds=new Set(a.schools.map(s=>s.kind));assert.deepEqual([...kinds].sort(),['fish','ray','whale']);
 assert.match(a.label,/SEEDED/);assert.equal(OCEAN_LABEL,a.label);assert.ok(oceanLife('k',sea,{life:2}).schools.length>a.schools.length);
 const s=a.schools[0];assert.notDeepEqual(memberAt(s,0,0),memberAt(s,0,3));
 const w=a.schools.find(s=>s.kind==='whale');assert.ok([...Array(40)].some((_,i)=>surfacing(w,i)>.5));assert.equal(planktonGlow(1,2,0),0);assert.ok(planktonGlow(1,2,1)>0);});
test('no Math.random in the module',()=>{assert.ok(!/Math\.random/.test(readFileSync(new URL('../lib/universe/ocean-life.mjs',import.meta.url),'utf8')));});
