import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
// RECORDED is reserved for the real IBM run; Rigetti simulator results read SIMULATED.
test('research stage 015 results head says SIMULATED (Rigetti simulator runs), not RECORDED',()=>{
 const s=read('app/research/stage015/page.tsx');assert.ok(/02 \/ RESULTS FROM SIMULATED RUNS/.test(s));assert.ok(!/RECORDED RESULTS/.test(s));
});
test('spark page and arena never call simulator shots recorded',()=>{
 assert.ok(/256 SIMULATED shots/.test(read('public/spark/index.html')));assert.ok(!/256 recorded shots/.test(read('public/spark/index.html')));
 assert.ok(/run\.qvm\?'SIMULATED':'RECORDED'/.test(read('public/spark/app.mjs')));
 const c=read('components/spark-beast-companion.tsx');assert.ok(/SIMULATED RIGETTI SEED/.test(c)&&/IBM seed RECORDED on IBM hardware/.test(c));
});
test('privacy page splits RECORDED (IBM) from SIMULATED (Rigetti)',()=>{
 const s=read('app/privacy/page.tsx');assert.ok(/RECORDED seeds are the real IBM run/.test(s));assert.ok(/SIMULATED seeds are archived Rigetti simulator output/.test(s));assert.ok(!/Rigetti entries are archived/.test(s));
});
test('the dock honesty line uses the same case for both words',()=>{
 for(const f of ['components/honest-line.tsx','components/zeref-knowledge-diagnostics.tsx'])assert.ok(/IBM seed RECORDED · growth SIMULATED/.test(read(f)),f);
});
test('camera, mic and observatory text do not use recorded for things that are not the IBM run',()=>{
 assert.ok(/nothing is saved or uploaded/.test(read('components/camera-field.tsx')));
 assert.ok(!/Recorded events and genuine/.test(read('components/beast-cage-portal.tsx')));
});
