import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {snowAmount} from '../lib/universe/terrain-detail.mjs';
test('snow caps follow the recorded temperature: ice worlds always, hot/airless worlds never',()=>{
  assert.equal(snowAmount('volcanic',200),0);assert.equal(snowAmount('desert',100),0);assert.equal(snowAmount('moon',100),0);
  assert.ok(snowAmount('ice',400)>=0.8);assert.equal(snowAmount('temperate',320),0);assert.equal(snowAmount('temperate',200),1);
  const a=snowAmount('temperate',260),b=snowAmount('temperate',240);assert.ok(a>0&&a<b);
});
test('generated planet shader carries the terrain layers and no randomness',()=>{
  const g=fs.readFileSync(new URL('../lib/universe/planet-glsl.ts',import.meta.url),'utf8');
  for(const k of ['terrain texture (rock','uSnow','atlasTile'])assert.ok(g.includes(k),k);
  assert.ok(!/Math\.random/.test(fs.readFileSync(new URL('../lib/universe/terrain-detail.mjs',import.meta.url),'utf8')));
});
