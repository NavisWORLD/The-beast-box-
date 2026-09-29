import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');

test('owner HF catalog and model handoff preserve consent at both gateways',()=>{
 const gateway=read('app/api/bridge/[endpoint]/route.ts');
 const picker=read('components/model-switcher.tsx');
 for(const expected of ['hf-inventory','hf_owner_model','spend_approved']){
  assert.ok(gateway.includes(expected),expected);
  assert.ok(picker.includes(expected),expected);
 }
 assert.ok(gateway.includes('phera-ra/'));
 assert.ok(picker.includes('phera-ra'));
 assert.match(gateway,/if \(!await isOwner\(\)\)/);
 assert.match(gateway,/Same-origin owner action required/);
 assert.match(picker,/research_artifacts/);
 assert.match(picker,/entry\.selectable/);
 assert.match(picker,/inference_attested/);
});
