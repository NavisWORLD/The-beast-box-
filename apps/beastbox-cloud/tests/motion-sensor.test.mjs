import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';

const read=path=>readFileSync(new URL('../'+path,import.meta.url),'utf8');

test('motion requires owner gesture and iOS permission prior to event listeners',()=>{
 const ui=read('components/motion-panel.tsx');
 const studio=read('components/studio.tsx');
 assert.match(ui,/onClick=\{\(\)=>active\?stop\(\):void start\(\)\}/);
 assert.match(ui,/requestPermission/);
 assert.match(ui,/await Promise\.all\(requests\)/);
 assert.match(ui,/window\.addEventListener\('devicemotion',onMotion\)/);
 assert.match(ui,/window\.addEventListener\('deviceorientation',onOrientation\)/);
 assert.match(studio,/import MotionPanel from '\.\/motion-panel'/);
 assert.match(studio,/<MotionPanel canSend=\{connected\}/);
});
test('motion is bounded, local, expires and never auto-transmits',()=>{
 const ui=read('components/motion-panel.tsx');
 assert.match(ui,/SAMPLE_AGE_MS=60_000/);
 assert.match(ui,/LIVE_AGE_MS=3_000/);
 assert.match(ui,/Math\.min\(200,Math\.hypot/);
 assert.match(ui,/!canSend\|\|!consent\|\|!sample/);
 assert.match(ui,/if\(Date\.now\(\)-sample\.at>=SAMPLE_AGE_MS\)/);
 assert.match(ui,/onDraft\(sample\.text\);stop\(\)/);
 assert.doesNotMatch(ui,/localStorage|sessionStorage|MediaRecorder|navigator\.geolocation|sendBeacon/);
 assert.match(ui,/if\(previewing\|\|!previewConsent\|\|!sample\|\|sample\.rmsG===null\)return/);
});
test('all motion listeners and samples stop on hide, page exit and unmount',()=>{
 const ui=read('components/motion-panel.tsx');
 assert.match(ui,/document\.addEventListener\('visibilitychange',hidden\)/);
 assert.match(ui,/window\.addEventListener\('pagehide',pagehide\)/);
 assert.match(ui,/window\.removeEventListener\('devicemotion',onMotion\)/);
 assert.match(ui,/window\.removeEventListener\('deviceorientation',onOrientation\)/);
 assert.match(ui,/motion\.current=null;orientation\.current=null/);
 assert.match(ui,/setSample\(null\);setConsent\(false\)/);
});
