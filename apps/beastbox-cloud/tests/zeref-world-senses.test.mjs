import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {worldSensesLines,readingLine,sparkLine,sightLine} from '../lib/zeref/world-senses.mjs';
test('missing feeds compose nothing',()=>{assert.equal(worldSensesLines(),'');assert.equal(sightLine({links:{liveTick:{state:'DOWN'}}},1),'');});
test('reading and spark lines are labelled',()=>{
 assert.match(readingLine({date:'2026-10-31',picks:[{topic:'lost',title:'Lost'},{topic:'x',title:null}]}),/RECORDED.*"Lost" about lost/);
 const s=sparkLine({heart_seed_latest:{version:11,label:'RECORDED (x)',ibm_backend:'ibm_marrakesh',heart_seed_sha256:'bfc35208bb21af82'}});
 assert.match(s,/v11 \(RECORDED/);assert.doesNotMatch(s,/heartbeat/i);
});
test('sight is DERIVED and deterministic',()=>{
 const live={at_ms:1e12,links:{liveTick:{state:'CONNECTED'}}};
 const a=sightLine(live,1e12);assert.match(a,/DERIVED/);assert.equal(a,sightLine(live,1e12));
});
test('no randomness',()=>assert.doesNotMatch(readFileSync(new URL('../lib/zeref/world-senses.mjs',import.meta.url),'utf8'),/Math\.random/));
