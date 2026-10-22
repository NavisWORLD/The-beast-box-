import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {buildLCQ1,parseLCE1,attachLCQ1,LCQ_OFFSET} from '../lib/companion/lc-ecosystem.mjs';
test('LCQ1 matches the cartridge tool byte for byte and is SIMULATED',()=>{
 const b=buildLCQ1(0xDEADA969,[1245,825,748,1278],26);
 assert.equal(Buffer.from(b).toString('hex'),'4c4351310101000069a9adde0708ff01f9f800ff07f901001a000000dd043903ec02fe040000000000000000000000000000000000000000bce8ae1f');assert.equal(b[5]&1,1);
 const sav=attachLCQ1(new Uint8Array(32768).fill(255),b);assert.deepEqual([...sav.subarray(LCQ_OFFSET,LCQ_OFFSET+4)],[76,67,81,49]);});
test('LCE1 written by the real cartridge in mGBA parses',()=>{
 const d=parseLCE1(new Uint8Array(readFileSync(new URL('./fixtures/lost-cosmos-v12-2b-cage-export.sav',import.meta.url))));
 assert.ok(d);assert.equal(d.identity,'ac5c83ca');assert.ok(d.cst_steps>0);assert.equal(Object.keys(d.channels).length,12);assert.match(d.label,/SIMULATED/);});
test('corrupt LCE1 is rejected',()=>{const s=new Uint8Array(readFileSync(new URL('./fixtures/lost-cosmos-v12-2b-cage-export.sav',import.meta.url)));s[24704+20]^=1;assert.equal(parseLCE1(s),null);});
import {latestSimulatedGrowth,injectLatestGrowth,countsTo2Bit,ecosystemEntryFromLCE1,buildLCQ1 as _b} from '../lib/companion/lc-ecosystem.mjs';
const SIM=(tick,counts)=>({tick,growth_source:{kind:'rigetti-qvm-simulated',simulated:true,job_id:'j'+tick,counts}});
test('V12.3: latest SIMULATED Rigetti tick is chosen, fallbacks skipped, 3-bit counts folded to 2-bit',()=>{
 assert.deepEqual(countsTo2Bit({'000':1,'001':2,'010':3,'011':4,'100':5,'101':6,'110':7,'111':8}),[3,7,11,15]);
 const recent=[{tick:9,growth_source:{kind:'deterministic-fallback',simulated:false}},SIM(8,{'000':10,'111':246}),SIM(3,{'000':256})];
 const g=latestSimulatedGrowth(recent);assert.equal(g.cycle,8);assert.deepEqual(g.counts,[10,0,0,246]);assert.equal(g.simulated,true);
 assert.equal(latestSimulatedGrowth([{tick:1,growth_source:{kind:'deterministic-fallback'}}]),null);
 assert.equal(latestSimulatedGrowth([{tick:1,growth_source:{kind:'rigetti-qvm-simulated',simulated:false,counts:{'000':1}}}]),null);});
test('V12.3: injectLatestGrowth attaches the same LCQ1 bytes buildLCQ1 makes, and is a no-op without simulated growth',()=>{
 const sav=new Uint8Array(32768);const r=injectLatestGrowth(sav,0xDEADA969,[SIM(8,{'000':10,'111':246})]);
 assert.deepEqual([...r.save.subarray(LCQ_OFFSET,LCQ_OFFSET+60)],[..._b(0xDEADA969,[10,0,0,246],8)]);assert.equal(r.save[LCQ_OFFSET+5]&1,1);assert.equal(sav[LCQ_OFFSET],0);
 const n=injectLatestGrowth(sav,0xDEADA969,[]);assert.equal(n.lcq1,null);assert.equal(n.save,sav);});
test('V12.3: an LCE1 from the real cartridge becomes an ecosystem entry for bb-<identity>',()=>{
 const d=parseLCE1(new Uint8Array(readFileSync(new URL('./fixtures/lost-cosmos-v12-2b-cage-export.sav',import.meta.url))));
 const e=ecosystemEntryFromLCE1(d,{now:'2026-10-21T00:00:00Z'});assert.equal(e.beast_id,'bb-ac5c83ca');assert.equal(e.schema,'lost-cosmos-game-experience/v1');assert.match(e.label,/SIMULATED/);});
