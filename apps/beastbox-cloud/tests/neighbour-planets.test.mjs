import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {ringPlan,atmoRim,NEIGHBOUR_LABEL} from '../lib/universe/neighbour-planets.mjs';
const P=[{id:'a',radius_earth:1,atmosphere:.8,temperature_k:290,water:.7},{id:'b',radius_earth:6,atmosphere:.3,temperature_k:500},{id:'c',radius_earth:.4,atmosphere:0}];
test('biggest planet always has rings, plan is deterministic',()=>{const r=ringPlan(P);assert.ok(r[1]);assert.deepEqual(r,ringPlan(P));for(const x of r)if(x){assert.ok(x.outer>x.inner&&x.inner>1);}});
test('airless bodies get no atmosphere rim; air gives a rim',()=>{assert.equal(atmoRim(P[2]).strength,0);assert.ok(atmoRim(P[0]).strength>.5);});
test('honest label, no Math.random in module, lit by the one sun in the world',()=>{assert.match(NEIGHBOUR_LABEL,/SEEDED/);assert.doesNotMatch(fs.readFileSync(new URL('../lib/universe/neighbour-planets.mjs',import.meta.url),'utf8'),/Math\.random/);
 const w=fs.readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');assert.match(w,/ringPlan\(/);assert.match(w,/uRimC/);});
