// Visual Life Pass: the look pack data. Generated file = the JSON (sha256 recorded), SEEDED label, helpers, no clock.
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';import {createHash} from 'node:crypto';
import {VL_PACK,VL_WATER,VL_HERO,VL_ATMOSPHERE,VL_EVENTS,pairTable,arrTable} from '../lib/universe/vislife-look.mjs';
const raw=readFileSync(new URL('../lib/universe/data/vislife.json',import.meta.url));
const json=JSON.parse(raw);
test('the generated look data carries the sha256 of the JSON it came from and the SEEDED label',()=>{
 assert.equal(VL_PACK.sha256,createHash('sha256').update(raw).digest('hex'));assert.equal(VL_PACK.label,'SEEDED');
 const head=readFileSync(new URL('../lib/universe/vislife-look-data.mjs',import.meta.url),'utf8').split('\n').slice(0,4).join('\n');
 assert.match(head,new RegExp(VL_PACK.sha256));assert.match(head,/SEEDED/);assert.match(head,/engine's own values/);
 assert.deepEqual(JSON.parse(JSON.stringify(VL_WATER)),json.WATER);assert.deepEqual(JSON.parse(JSON.stringify(VL_HERO)),json.HERO);
 assert.deepEqual(JSON.parse(JSON.stringify(VL_ATMOSPHERE)),json.ATMOSPHERE);assert.deepEqual(JSON.parse(JSON.stringify(VL_EVENTS)),json.EVENTS);
});
test('pairTable and arrTable are clamped piecewise-linear',()=>{
 assert.equal(pairTable([[0,0],[1,10]],-1),0);assert.equal(pairTable([[0,0],[1,10]],.5),5);assert.equal(pairTable([[0,0],[1,10]],2),10);
 assert.equal(arrTable([0,2],[0,4],1),2);assert.equal(arrTable([0,2],[0,4],9),4);
});
test('foam pack numbers the engine reads: crest cap 8 = foamLifeS x 4 ticks, calm foam 0',()=>{
 const c=VL_WATER.foam.const_block;assert.deepEqual(c.age_cap_ticks.crest,8);assert.equal(c.calm_tick_foam,0);assert.equal(pairTable(c.birth_alpha_by_whitecap,0),0);assert.equal(pairTable(c.shore_birth_by_wind01,0),0);
});
