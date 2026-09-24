import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=path=>readFileSync(new URL('../'+path,import.meta.url),'utf8');

test('gravity-free RMS requires multiple fresh bounded browser samples; raw history is not stored',()=>{
 const ui=read('components/motion-panel.tsx');
 assert.match(ui,/const raw=event.acceleration;/);
 assert.match(ui,/bucket.count<100/);
 assert.match(ui,/now-bucket.start>2000/);
 assert.match(ui,/bucket.count>=3&&now-bucket.at<LIVE_AGE_MS/);
 assert.match(ui,/Math.sqrt\(bucket.sumSq\/bucket.count\)\/9.80665/);
 assert.match(ui,/aggregate.current=\{sumSq:0,count:0,start:0,at:0\}/);
 assert.doesNotMatch(ui,/navigator.geolocation|MediaRecorder|localStorage|sessionStorage/);
});
test('single owner consent guards existing host preview; no persistence or remote model call',()=>{
 const ui=read('components/motion-panel.tsx');
 const bridge=read('bridge/owner_bridge.py');
 assert.match(ui,/!previewConsent\|\|!sample\|\|sample.rmsG===null/);
 assert.match(ui,/config.enabled!==true/);
 assert.match(ui,/action:'preview',source:'browser_sensor',consent:true/);
 assert.match(ui,/readings:\{accelerometer_rms_g:sample.rmsG\}/);
 assert.match(ui,/result.persisted!==false\|\|result.model_invoked!==false/);
 assert.match(ui,/vector.length!==12/);
 assert.match(ui,/Date.now\(\)-sample.at>=SAMPLE_AGE_MS/);
 assert.doesNotMatch(ui,/action:'persist'|persist_confirmed|remote_share_confirmed/);
 assert.match(bridge,/if action == "preview":/);
 assert.match(bridge,/return 200, \{"event": event, "persisted": False, "model_invoked": False/);
});
