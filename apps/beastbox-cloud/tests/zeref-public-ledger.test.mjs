import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {verifyPublishedLedger} from '../public/spark/zeref-live-20261010/ledger-verify.mjs';
const text=readFileSync(new URL('../public/spark/zeref-live-20261010/quantum-ledger.jsonl',import.meta.url),'utf8');
const manifest=JSON.parse(readFileSync(new URL('../public/spark/zeref-live-20261010/ledger-manifest.json',import.meta.url),'utf8'));
test('browser verifies original Python ledger bytes including floating-point spellings',()=>{
 const result=verifyPublishedLedger(text,manifest);assert.equal(result.count,manifest.record_count);assert.equal(result.tip,manifest.tip_sha256);
});
test('changed model replies, truncated events and reordered rows are rejected',()=>{
 assert.throws(()=>verifyPublishedLedger(text.replace('The trotin has a choice.','A dragon has a choice.'),manifest));
 assert.throws(()=>verifyPublishedLedger(text.slice(0,-1),manifest));
 const lines=text.trim().split('\n');[lines[0],lines[1]]=[lines[1],lines[0]];
 assert.throws(()=>verifyPublishedLedger(lines.join('\n')+'\n',manifest));
});
