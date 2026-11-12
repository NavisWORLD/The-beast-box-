import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const src=readFileSync(new URL('../app/api/guest/forever/route.ts',import.meta.url),'utf8');

// Nov 12, 1:00 PM CT: promotion #944 moved the site pin to 40304 in about a minute while the bridge was still
// rebuilding on 39984, so every guest message got a bare 502 "Unverified guest model response".
test('forever door: bridge on an older step answers an honest 503 with a wait hint, never the old reply',()=>{
 const at=src.indexOf('PIN LAG');assert.ok(at>0);
 const block=src.slice(at,src.indexOf("// memory_used may be true ONLY",at));
 assert.match(block,/\(result\.step as number\)<PIN_STEP/,'only an OLDER bridge step is a lag; a newer or odd step stays unverified');
 assert.match(block,/safeJson\(503,/);
 assert.match(block,/Retry-After','60'/);
 assert.match(block,/pin_step:PIN_STEP,bridge_step:result\.step/);
 assert.doesNotMatch(block,/result\.reply/,'the older brain\'s reply is never passed through');
 // the full verification still follows, unchanged
 assert.ok(src.indexOf("result.step!==PIN_STEP||result.checkpoint_sha256!==PIN_SHA")>at);
 assert.match(src,/return safeJson\(502,\{error:'Unverified guest model response'\}\)/);
});
