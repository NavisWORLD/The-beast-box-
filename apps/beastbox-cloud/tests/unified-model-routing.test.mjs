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

test('QC67 PHOS and SAMGO pass the same-origin owner model-selection gate',()=>{
 const gateway=read('app/api/bridge/[endpoint]/route.ts');
 const picker=read('components/model-switcher.tsx');
 const backend=read('bridge/owner_bridge.py');
 // Check the actual no-charge local branch rather than just the model names
 // appearing elsewhere in the file. This caught the real production UI bug.
 const localGate=gateway.match(/if\s*\(\s*\[([^\]]+)\]\.includes\(String\(choice\)\)\s*\)\s*\{/);
 assert.ok(localGate,'local choice allowlist must exist');
 for(const choice of ['qc67_phos','qc67_samgo']){
   assert.ok(localGate[1].includes("'"+choice+"'"),choice+' must be allowed through the web gateway');
   assert.ok(picker.includes("'"+choice+"'"),choice+' must appear in Brain Bay');
   assert.ok(backend.includes('"'+choice+'"'),choice+' must be handled by the owner bridge');
 }
 assert.match(gateway,/if \(!await isOwner\(\)\)/);
 assert.match(gateway,/Same-origin owner action required/);
 assert.match(gateway,/if\(keys!=='choice'\)/);
});
