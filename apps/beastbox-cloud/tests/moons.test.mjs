import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {seedMoons,moonOffset,pickOccluder,MOONS_LABEL} from '../lib/universe/moons.mjs';
const U=JSON.parse(fs.readFileSync(new URL('../public/universe/tiny-universe-genesis.json',import.meta.url)));
test('moons are deterministic from the seed and always labeled seeded',()=>{
  const a=seedMoons(String(U.seed),U.planets),b=seedMoons(String(U.seed),U.planets);assert.deepEqual(a,b);
  assert.ok(a.length>0&&a.length<=3*U.planets.length);for(const m of a){assert.equal(m.seeded,true);assert.equal(m.tag,'seeded');assert.ok(U.planets.some(p=>p.id===m.planet));}
  assert.match(MOONS_LABEL,/SEEDED/);assert.notDeepEqual(seedMoons('other-seed',U.planets),a);
});
test('moon orbits are outside the planet, spaced, and follow Kepler (period ~ a^1.5)',()=>{
  const a=seedMoons(String(U.seed),U.planets);const by={};for(const m of a)(by[m.planet]??=[]).push(m);
  for(const ms of Object.values(by)){for(let i=0;i<ms.length;i++){assert.ok(ms[i].aPlanetR>=2.7);assert.ok(ms[i].radiusFrac<0.35);if(i)assert.ok(ms[i].aPlanetR-ms[i-1].aPlanetR>=1.8);}
    for(let i=1;i<ms.length;i++){const r=(ms[i].periodS/ms[i-1].periodS)/Math.pow(ms[i].aPlanetR/ms[i-1].aPlanetR,1.5);assert.ok(r>0.6&&r<1.6);}}
  const m=a[0];const p0=moonOffset(m,0),p1=moonOffset(m,m.periodS);assert.ok(Math.abs(p0.x-p1.x)<1e-6&&Math.abs(p0.z-p1.z)<1e-6);
  assert.ok(Math.abs(Math.hypot(p0.x,p0.y,p0.z)-m.aPlanetR)<1e-9);
});
test('pickOccluder finds the body on the sun line (eclipse), ignores ones behind',()=>{
  const sun={x:1,y:0,z:0};const hit=pickOccluder({x:0,y:0,z:0},sun,[{x:5,y:0.1,z:0,r:1},{x:-5,y:0,z:0,r:1},{x:5,y:9,z:0,r:1}]);assert.equal(hit.x,5);assert.equal(hit.y,0.1);
  assert.equal(pickOccluder({x:0,y:0,z:0},sun,[{x:-5,y:0,z:0,r:1}]),null);
});
