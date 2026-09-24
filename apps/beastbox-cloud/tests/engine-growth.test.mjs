import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');

test('engine growth is owner-only, GET-only and reads verified checkpoint history',()=>{
 const bff=read('app/api/bridge/[endpoint]/route.ts');
 const bridge=read('bridge/owner_bridge.py');
 const report=read('../../beastbox/engine_growth_report.py');
 assert.match(bff,/GET_ALLOW=new Set\(\[[^\n]*'engine-growth'/);
 assert.match(bff,/if \(!await isOwner\(\)\)/);
 assert.doesNotMatch(bff,/POST_ALLOW=new Set\(\[[^\n]*'engine-growth'/);
 assert.match(bridge,/if name == "engine-growth" and method == "GET":/);
 assert.match(bridge,/return 200, engine_growth_report\(self\.root\)/);
 assert.match(report,/runtime\.continuity\.history\(limit=50\)/);
 assert.match(report,/runtime\.inspect\(\)/);
 assert.match(report,/model_weight_growth_proven": False/);
 assert.match(report,/improved_intelligence_proven": False/);
 assert.match(report,/automatic_code_changes": False/);
 assert.match(report,/side_effects": "NONE_READ_ONLY"/);
 assert.doesNotMatch(report,/\.generate\(|\.respond\(|\.store_external_memory\(|\.append\(|\.commit\(/);
});

test('Orbit shows verified receipt and rejects simulated progress',()=>{
 const ui=read('components/engine-growth.tsx');
 const studio=read('components/studio.tsx');
 assert.match(studio,/<EngineGrowth\/>/);
 assert.match(ui,/Inspect verified engine changes/);
 assert.match(ui,/data\.model_weight_growth_proven!==false/);
 assert.match(ui,/data\.side_effects!=='NONE_READ_ONLY'/);
 assert.match(ui,/No model-weight training, intelligence improvement/);
});
