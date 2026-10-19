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
