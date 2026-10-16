import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {interpretModelResult,RAWRPHOS_PUBLIC_PIN} from '../lib/companion/brain.mjs';
import * as spark from '../public/spark/shared/brain.mjs';
const pin=JSON.parse(readFileSync(new URL('../lib/rawrphos-public-pin.json',import.meta.url)));
const base={provider:'rawrphos-local',model:'rawrphos-native',guest_stateless:true,reply:'Hi dad lol'};
test('brain pin mirrors lib/rawrphos-public-pin.json in both copies',()=>{
 for(const p of [RAWRPHOS_PUBLIC_PIN,spark.RAWRPHOS_PUBLIC_PIN])
  assert.deepEqual({...p},{step:pin.training_steps,checkpoint_sha256:pin.checkpoint_sha256});
});
test('pinned step accepted and returned as the real step',()=>{
 for(const f of [interpretModelResult,spark.interpretModelResult]){
  const r=f('guest-rawrphos',{...base,step:pin.training_steps,checkpoint_sha256:pin.checkpoint_sha256});
  assert.equal(r.ok,true);assert.equal(r.step,pin.training_steps);
  assert.equal(f('guest-rawrphos',{...base,step:pin.training_steps}).step,pin.training_steps);
 }
});
test('wrong step or wrong sha rejected; 14000 rollback still accepted',()=>{
 assert.equal(interpretModelResult('guest-rawrphos',{...base,step:15000}).ok,false);
 assert.equal(interpretModelResult('guest-rawrphos',{...base,step:pin.training_steps,checkpoint_sha256:'0'.repeat(64)}).ok,false);
 assert.equal(interpretModelResult('guest-rawrphos',{...base,step:14000}).step,14000);
});
