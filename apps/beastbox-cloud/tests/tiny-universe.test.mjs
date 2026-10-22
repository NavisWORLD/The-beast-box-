import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {genesis,grow,correlation,parseCounts} from '../lib/universe/tiny-universe.mjs';
const shard=JSON.parse(fs.readFileSync(new URL('../public/spark/ibm-marrakesh-reality-probe-20261009.json',import.meta.url)));
test('genesis is deterministic from recorded IBM counts',()=>{const a=genesis(shard),b=genesis(shard);assert.deepEqual(a,b);assert.equal(a.source.class,'RECORDED_IBM_HARDWARE');assert.ok(a.stars.length>=3);});
test('refuses non-hardware genesis',()=>assert.throws(()=>genesis({...shard,source_class:'SIMULATED'})));
test('correlation of Bell counts',()=>assert.ok(correlation(parseCounts('00:1994,01:27,10:18,11:2057'))>0.97));
test('growth is deterministic and always SIMULATED',()=>{const g=genesis(shard);const a=grow(g,50),b=grow(grow(g,20),30);assert.deepEqual(a,b);assert.ok(a.history.every(h=>h.source==='SIMULATED'));assert.match(a.growth_label,/SIMULATED/);assert.equal(g.tick,0);});
