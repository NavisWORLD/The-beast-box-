import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');

test('unified model options reach the owner-only validated gateway',()=>{
 const gateway=read('app/api/bridge/[endpoint]/route.ts');
 const picker=read('components/model-switcher.tsx');
 for(const model of ['rawrphos_native','rawrphos_native_18k_experimental','rawrphos_hf']){
   assert.ok(gateway.includes(model));
   assert.ok(picker.includes(model));
 }
 assert.match(gateway,/if \(!await isOwner\(\)\)/);
 assert.match(gateway,/Same-origin owner action required/);
 assert.match(gateway,/model-inventory/);
 assert.match(gateway,/engine-growth/);
 assert.match(gateway,/Invalid or unapproved Ollama Cloud model ID/);
 assert.match(gateway,/Remote model activation requires explicit usage approval/);
 assert.match(picker,/option\.configured/);
 assert.match(picker,/const experimental/);
 assert.match(picker,/quality gate/);
 assert.match(picker,/spend_approved:true/);
 assert.doesNotMatch(gateway,/['\"]workspace\/write['\"]/);
});
