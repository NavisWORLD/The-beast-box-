import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');

test('anonymous guest is a distinct bounded route, not owner session or bridge proxy',()=>{
 const source=read('app/api/guest/route.ts');
 const owner=read('app/api/bridge/[endpoint]/route.ts');
 assert.match(source,/Same-origin guest request required/);
 assert.match(source,/Guest request exceeds the size limit/);
 assert.match(source,/item\.text\.length>MAX_PROMPT/);
 assert.match(source,/bridgeConfigured\(\)/);
 assert.match(source,/BEASTBOX_CLOUD_BRIDGE_TOKEN/);
 assert.match(source,/createHmac\('sha256',secret\)/);
 assert.match(source,/new URL\('\/api\/guest-local',process\.env\.BEASTBOX_CLOUD_BRIDGE_URL!\)/);
 assert.match(source,/result\.memory_used!==false\|\|result\.owner_tools_used!==false/);
 assert.doesNotMatch(owner,/['"]guest-local['"]/);
 assert.doesNotMatch(source,/\/api\/bridge\/chat|\/api\/connections|\/api\/memory|\/api\/models|localStorage|sessionStorage/);
});

test('BYOK never reads owner key, uses exactly the HF router, no fallback or persistence',()=>{
 const source=read('app/api/guest/route.ts');
 const ui=read('app/try/page.tsx');
 assert.match(source,/const HF_ENDPOINT='https:\/\/router\.huggingface\.co\/v1\/chat\/completions'/);
 assert.match(source,/Authorization:'Bearer '\+item\.hf_key/);
 assert.match(source,/item\.spend_confirmed!==true/);
 assert.match(source,/max_tokens:128/);
 assert.match(source,/redirect:'error'/);
 assert.match(source,/AbortSignal\.timeout\(30_000\)/);
 assert.match(source,/boundedJson\(res,64000\)/);
 assert.match(source,/charged_to:'guests_own_huggingface_key'/);
 assert.doesNotMatch(source,/process\.env\.HF_TOKEN|\.vault|\.get\('cookie'\)|localStorage|sessionStorage|console\./);
 assert.doesNotMatch(ui,/localStorage|sessionStorage|document\.cookie|navigator\.clipboard/);
 assert.match(ui,/type="password" autoComplete="off"/);
 assert.match(ui,/setHfKey\(''\)/);
 assert.match(ui,/I approve sending my message and key/);
 assert.match(ui,/Local CPU/);
 assert.match(ui,/guest_stateless!==true/);
});

test('owner homepage links guest but keeps private workstation',()=>{
 const page=read('app/page.tsx');
 const guest=read('app/try/page.tsx');
 assert.match(page,/<Link href="\/try"/);
 assert.match(page,/<Link href="\/workspace"/);
 assert.match(guest,/href="\/workspace"/);
 const bridge=read('bridge/owner_bridge.py');
 assert.match(bridge,/if name == "guest-local":/);
 assert.match(bridge,/self\.chat_jobs\.acquire_guest\(\)/);
 assert.match(bridge,/self\.chat_jobs\.release_guest\(\)/);
 assert.match(read('../../beastbox/guest_local.py'),/sqlite3\.connect/);
 assert.match(read('../../beastbox/guest_local.py'),/TRIAL_SECONDS = 30 \* 86400/);
 assert.match(read('../../beastbox/guest_local.py'),/native_status\(\)/);
 assert.doesNotMatch(read('../../beastbox/guest_local.py'),/DurableRuntime|CosmicApp|ConnectionVault|HF_TOKEN/);
});
