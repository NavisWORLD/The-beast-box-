import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {pickType,planetLod,sunExposure,variantFor,glowSet,LAVA_K} from '../lib/universe/planet-types.mjs';
const U=JSON.parse(fs.readFileSync(new URL('../public/universe/tiny-universe-genesis.json',import.meta.url)));
const lcg=seed=>{let h=0;for(const c of seed)h=(h*31+c.charCodeAt(0))>>>0;return()=>{h=(h*1664525+1013904223)>>>0;return h/2**32;};};
test('pickType follows the pack rule except the documented 1500 K lava cutoff',()=>{
  assert.equal(pickType({atmosphere:.01,temperature_k:300}),'moon');
  assert.equal(pickType({atmosphere:.5,temperature_k:LAVA_K,water:.5}),'volcanic');
  assert.equal(pickType({atmosphere:.5,temperature_k:1000,water:.5}),'desert');
  assert.equal(pickType({atmosphere:.5,temperature_k:100,water:.5}),'ice');
  assert.equal(pickType({atmosphere:.5,temperature_k:280,water:.5}),'temperate');
  assert.equal(pickType({atmosphere:.5,temperature_k:280,water:.05}),'ice');
  assert.equal(pickType({atmosphere:.5,temperature_k:500,water:.9}),'desert');
});
test('the recorded 17 planets are not all lava (real land mix)',()=>{
  const c={};for(const p of U.planets){const t=pickType(p);c[t]=(c[t]||0)+1;}
  assert.equal(Object.values(c).reduce((a,b)=>a+b,0),17);assert.ok(c.volcanic<=6);assert.ok(c.desert>=4);
});
test('planetLod weights are continuous and monotone',()=>{
  let last=-1;for(let d=1000;d>=1.01;d/=1.05){const l=planetLod(d,1,55);assert.ok(l.s>=last);last=l.s;assert.ok(l.sprite>=0&&l.sprite<=1&&l.farAlpha>=0&&l.nearAlpha<=1);assert.ok(Math.abs(l.sprite+l.farAlpha-1)<1e-9);}
  assert.equal(planetLod(1e6,1,55).sprite,1);assert.equal(planetLod(1.2,1,55).nearAlpha,1);
});
test('sun exposure: inverse-square, clamped, deterministic',()=>{
  assert.ok(sunExposure(178,5)>=sunExposure(178,20));assert.equal(sunExposure(178,1e5),0.35);assert.equal(sunExposure(1e9,1),1.6);
  assert.equal(glowSet(3000),'orange');assert.equal(glowSet(5800),'yellow');assert.equal(glowSet(8000),'white');assert.equal(glowSet(20000),'blue_white');
  assert.deepEqual(variantFor('x',lcg),variantFor('x',lcg));
});
