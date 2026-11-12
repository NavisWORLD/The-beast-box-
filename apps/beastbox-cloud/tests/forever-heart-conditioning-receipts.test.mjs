import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const src=readFileSync(new URL('../app/api/guest/forever/route.ts',import.meta.url),'utf8');
test('forever door: heart and conditioning receipts are whitelisted, never owner state12', () => {
  assert.match(src,/heart_decoding:heartDecoding/);
  assert.match(src,/conditioning\}/);
  assert.match(src,/state12:'isolated',owner_state_used:false/);
  // the receipts are rebuilt field by field; the raw bridge objects are never spread into the response
  assert.doesNotMatch(src,/\.\.\.result\.heart_decoding|\.\.\.result\.conditioning|\.\.\.hd\b|\.\.\.cd\b/);
});
