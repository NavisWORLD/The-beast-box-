import test from 'node:test';import assert from 'node:assert/strict';
import {seededBlackHoles,orbitOmega,seededInfall,BH_LABEL} from '../lib/universe/seeded-black-holes.mjs';
const U={seed:'ibm_marrakesh:abc',stars:[{id:'s1'}]};
test('one SEEDED black hole, deterministic, inside Cory\'s ranges (scaled)',()=>{const a=seededBlackHoles(U),b=seededBlackHoles(U);assert.deepEqual(a,b);assert.equal(a.length,1);const h=a[0];assert.equal(h.label,BH_LABEL);assert.ok(h.size>=15&&h.size<=25);assert.equal(h.mass,+(h.size*5000).toFixed(1));const d=Math.hypot(h.x,h.z);assert.ok(d>=160-1&&d<=480+1);assert.ok(Math.abs(h.y)<=16.1);});
test('different seed moves it; a real remnant suppresses the seeded one',()=>{assert.notDeepEqual(seededBlackHoles(U)[0].x,seededBlackHoles({...U,seed:'other'})[0].x);assert.equal(seededBlackHoles({seed:'x',stars:[{remnant:'black_hole'}]}).length,0);});
test('Kepler: closer orbits are faster; infall is deterministic',()=>{const h=seededBlackHoles(U)[0];assert.ok(orbitOmega(h,h.radius*1.5)>orbitOmega(h,h.radius*3));assert.deepEqual(seededInfall(h,'s',20),seededInfall(h,'s',20));});
