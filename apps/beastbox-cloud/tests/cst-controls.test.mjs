import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=path=>readFileSync(new URL('../'+path,import.meta.url),'utf8');

test('CST software preview has distinct host and owner authorization',()=>{
 const host=read('bridge/owner_bridge.py');
 const bff=read('app/api/bridge/[endpoint]/route.ts');
 const ui=read('components/bio-panel.tsx');
 assert.match(host,/BEASTBOX_CST_PREVIEW_ENABLED/);
 assert.match(host,/not self\.cst_preview_enabled/);
 assert.match(host,/compare_confirmed/);
 assert.match(host,/compare_sensor_state\(event\)/);
 assert.match(bff,/action==='cst_preview'/);
 assert.match(bff,/input\.compare_confirmed!==true/);
 assert.match(bff,/Same-origin owner action required/);
 assert.match(ui,/I separately approve running one isolated software CST/);
 assert.match(ui,/action:'cst_preview'/);
 assert.match(ui,/model_invoked!==false/);
 assert.match(ui,/persisted!==false/);
});
test('CST preview uses the existing numeric event; never actuates or persists',()=>{
 const src=read('../../beastbox/cst_sensor_preview.py');
 assert.match(src,/normalize_event\(event\)/);
 assert.match(src,/StateFamily\(\)\.update\(values\)/);
 assert.match(src,/"zero_gate": \[0\.0\] \* 12/);
 assert.match(src,/"shuffled": list\(drive\[1:\]\) \+ list\(drive\[:1\]\)/);
 assert.doesNotMatch(src,/DurableRuntime\(|CosmosRuntime\(|\.dispatch\(|\.generate\(|requests\.|urllib\.|open\(/);
});
