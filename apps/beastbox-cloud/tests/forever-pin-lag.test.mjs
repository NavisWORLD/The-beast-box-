import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const src=readFileSync(new URL('../app/api/guest/forever/route.ts',import.meta.url),'utf8');

// Nov 12, 1:00 PM CT: promotion #944 moved the site pin to 40304 while the bridge was still on 39984, and every
// guest message got a 502, later an honest 503 wait (#945). Nov 12, 2:37 PM CT, Cory: "Loosen both the training
// gate and the chat door". The door now serves the bridge's OWN reply on whatever step it loaded, labelled.
test('forever door: a bridge on another step still answers, labelled with the step that answered',()=>{
 const at=src.indexOf('OWN-STEP DOOR');assert.ok(at>0);
 assert.doesNotMatch(src,/\(result\.step as number\)<PIN_STEP/,'no more 503 refusal for an older bridge step');
 assert.match(src,/const STRICT_PIN_MATCH=false;/,'old strict pin-match rule kept behind a one-line constant');
 assert.match(src,/if\(STRICT_PIN_MATCH&&!onPin\)return safeJson\(502,\{error:'Unverified guest model response'\}\)/);
 assert.match(src,/answered by step \$\{answeredStep\}, pin is \$\{PIN_STEP\}/);
 assert.match(src,/step:answeredStep,checkpoint_sha256:answeredSha,reply,/,'receipt carries the ANSWERING step, never the pin\'s');
 assert.match(src,/pin_step:PIN_STEP,pin_checkpoint_sha256:PIN_SHA,serving_pin:onPin,answered_by:answeredBy/);
 assert.match(src,/appendExchange\(cfg,threadId,\{guestText:text,reply,step:answeredStep as number,at\}\)/);
});
test('forever door: only Zeref\'s own brain speaks; no fallback or canned text',()=>{
 const at=src.indexOf('OWN-STEP DOOR');
 const block=src.slice(at,src.indexOf('const reply=result.reply as string;',at));
 assert.match(block,/result\.schema!=='beastbox-guest-local-v1'\|\|result\.model!=='rawrphos-native'/);
 assert.match(block,/\/\^\[0-9a-f\]\{64\}\$\/\.test\(answeredSha\)/);
 assert.match(block,/typeof result\.reply!=='string'\)/);
 assert.doesNotMatch(src,/reply:\s*['"`]/,'no literal reply text anywhere in the door');
 assert.match(src,/catch\{return safeJson\(502,\{error:'Local guest inference unavailable or timed out'\}\);\}/,'unreachable bridge is an honest error');
});
