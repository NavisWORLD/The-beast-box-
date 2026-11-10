import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');

test('the share switch is one shell-level session, mounted in the layout, stream owned outside any page',()=>{
 const layout=read('app/layout.tsx');assert.match(layout,/ShareWorld/);
 const shell=read('components/share-world.tsx');
 assert.match(shell,/shareStream/);assert.match(shell,/beastbox:master-privacy-stop/);
 assert.match(shell,/role="switch"/);assert.match(shell,/data-share-pip/);
 const stream=read('lib/environment/share-stream.ts');
 assert.match(stream,/SHARE_PREF_KEY = 'beastbox-share-world-v1'/);
 assert.match(stream,/facingMode: \{ ideal: this.facing \}/);
 assert.match(stream,/resume/);
});

test('person-facing surfaces now default to the front camera and carry a flip toggle',()=>{
 for(const p of ['components/field-perception.tsx','components/live-senses.tsx','components/device-panel.tsx']){
  const s=read(p);assert.match(s,/useRef<'user'\|'environment'>\('user'\)/,p);assert.match(s,/data-senses-flip/,p);
  assert.doesNotMatch(s,/facingMode:\{ideal:'environment'\}/,p);
 }
});

test('the fingertip measurement keeps the rear camera and torch: it is a finger on the lens, not a face surface',()=>{
 const capture=read('lib/bio/capture.ts');
 assert.match(capture,/facingMode:\{ideal:'environment'\}/);assert.match(capture,/torch/);
});

test('the face channel is labelled estimates end to end and never enters the sealed packet',()=>{
 const shell=read('components/share-world.tsx');assert.match(shell,/buildFaceEstimates/);assert.match(shell,/\(estimate\)/);
 const packet=read('lib/bio/bio-packet.mjs');assert.doesNotMatch(packet,/face/i);
 const est=read('lib/bio/face-estimates.mjs');assert.match(est,/heartbeat_label: 'ESTIMATE'/);
});

test('shared samples land in the same on-device experience log Zeref already reads',()=>{
 const shell=read('components/share-world.tsx');
 assert.match(shell,/LOG_KEY/);assert.match(shell,/experience\(cur, now\)/);
 assert.doesNotMatch(shell,/zeref:share-sample/);
});
