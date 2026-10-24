import test from 'node:test';import assert from 'node:assert/strict';
import {blackBodyToRGB,coronaParams,G_UNIVERSE,orbitR,initSystem,advanceTo,sunIntensity,nightFactor,orbitSpeed,starMass} from '../lib/universe/genesis-sun.mjs';
test('blackBody: cool stars are red, hot are blue (Cory\'s Definitive Core formula)',()=>{
  const c=blackBodyToRGB(3000),h=blackBodyToRGB(15831),s=blackBodyToRGB(5800);
  assert.ok(c[0]>c[2]&&c[0]===1);assert.ok(h[2]>=h[0]);assert.ok(s[0]>=s[1]&&s[1]>s[2]);
  for(const v of [...c,...h,...s])assert.ok(v>=0&&v<=1);
});
test('corona params follow createStarCorona',()=>{const a=coronaParams(2000),b=coronaParams(20000);assert.equal(a.intensity,0.6);assert.ok(Math.abs(b.intensity-1.4)<1e-9);assert.equal(b.noiseScale,4);});
test('1 AU planet of a 1 solar star keeps 0.05 rad/s and its radius under N-body stepping',()=>{
  const st={mass_solar:1},pl={id:'p',orbit_au:1,phase:0.25,radius_earth:1};
  const sys=initSystem(st,[pl]);const state={t:0};const R=orbitR(1);
  assert.ok(Math.abs(orbitSpeed(G_UNIVERSE,starMass(st),R)/R-0.05)<1e-9);
  advanceTo(sys,state,60,1e6);const p=sys.planets[0].p;
  assert.ok(Math.abs(Math.hypot(...p)-R)/R<0.02,'orbit radius stays within 2% after 60 s');
});
test('deterministic: same seed, same time, same positions',()=>{
  const mk=()=>{const s=initSystem({mass_solar:2},[{id:'a',orbit_au:.5,phase:.1,radius_earth:2},{id:'b',orbit_au:2,phase:.7,radius_earth:4}]);const st={t:0};advanceTo(s,st,20,1e6);return JSON.stringify(s.planets.map(p=>p.p));};
  assert.equal(mk(),mk());
});
test('inverse-square light and day/night terminator',()=>{
  assert.ok(Math.abs(sunIntensity(1)-2.2*81*0.5-(2.2*81*(0.25*Math.log10(2))))<1e-9);
  assert.ok(nightFactor(-0.5)===1&&nightFactor(0.6)===0&&nightFactor(0.05)>0&&nightFactor(0.05)<1);
});
