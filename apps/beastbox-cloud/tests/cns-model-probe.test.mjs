import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');

test('CNS-to-native real model is strictly owner-only and separately consented',()=>{
 const bff=read('app/api/bridge/[endpoint]/route.ts');
 const bridge=read('bridge/owner_bridge.py');
 const ui=read('components/bio-panel.tsx');
 assert.match(bff,/POST_ALLOW=new Set\(\[[^\n]*'cns-model-probe'/);
 assert.match(bff,/if \(!await isOwner\(\)\)/);
 assert.match(bff,/endpoint==='cns-model-probe'/);
 assert.match(bff,/Same-origin owner action required/);
 assert.match(bff,/model_probe_confirmed!==true/);
 assert.match(bff,/Object.entries\(readings\)/);
 assert.match(bridge,/if name == "cns-model-probe":/);
 assert.match(bridge,/self\.chat_jobs\.run_when_idle\(lambda: cns_model_probe\(data\)\)/);
 assert.match(bridge,/BEASTBOX_CNS_MODEL_PROBE_ENABLED/);
 assert.match(ui,/Compare native CNS7 vs reference/);
 assert.match(ui,/model_probe_confirmed:true/);
 assert.match(ui,/weights_updated!==false/);
 assert.match(ui,/quantum_hardware_used!==false/);
 assert.doesNotMatch(ui,/localStorage|sessionStorage|document\.cookie/);
});

test('native API consumes fixed numeric control only at explicitly bounded probe endpoint',()=>{
 const server=read('../../models/rawrphos/inference/server.py');
 const model=read('../../models/rawrphos/architecture/model.py');
 const gen=read('../../models/rawrphos/architecture/generation.py');
 const engine=read('../../models/rawrphos/inference/engine.py');
 const adapter=read('../../beastbox/cns_model_probe.py');
 assert.match(server,/app\.post\('\/v1\/condition-probe'\)/);
 assert.match(server,/Engine\.validate_control/);
 assert.match(server,/run_in_threadpool\(engine\.condition_probe/);
 assert.match(engine,/def condition_probe\(/);
 assert.match(engine,/model_weights_changed':False/);
 assert.match(engine,/performance_gain_proven':False/);
 assert.match(model,/state_logits=self\.state_init\(x\)/);
 assert.match(model,/state=torch\.tanh\(state_logits\+control_vector/);
 assert.match(gen,/control_vector=control_vector/);
 assert.match(adapter,/CNS\(\)\.tick\(mission, packet\.safe_dict\(\)\)/);
 assert.match(adapter,/127\.0\.0\.1:8767\/v1\/condition-probe/);
 assert.doesNotMatch(adapter,/from \.durable import|\.store_external_memory\(|cloud_connections|HF_TOKEN|api\.openai|shell=True/);
});
