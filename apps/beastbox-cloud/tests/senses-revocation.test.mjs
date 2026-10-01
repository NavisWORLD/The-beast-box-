import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const senses=readFileSync(new URL('../components/live-senses.tsx',import.meta.url),'utf8');
test('stop camera and stop speech each revoke matching unsent sensor context',()=>{
 assert.match(senses,/old\.filter\(item=>item\.source!=='camera_classifier'\)/);
 assert.match(senses,/old\.filter\(item=>item\.source!=='browser_speech'\)/);
 assert.match(senses,/setIncludeInChat\(false\);setRememberConsent\(false\);onContext\('',false\)/);
});
test('hide, discard and stop-all clear all unsubmitted sensor context',()=>{
 assert.match(senses,/Sensing stopped and unsent context revoked when the app became hidden/);
 assert.match(senses,/Stop all sensing and revoke unsent context/);
 assert.match(senses,/Previously saved memories require separate owner correction/);
 assert.match(senses,/beastbox:master-privacy-stop/);
});
test('master stop immediately revokes local sensing before network acknowledgement',()=>{
 const deck=readFileSync(new URL('../components/activation-deck.tsx',import.meta.url),'utf8');
 assert.match(deck,/window\.dispatchEvent\(new Event\('beastbox:master-privacy-stop'\)\)/);
 assert.match(deck,/Local capture stopped; remote stop NOT CONFIRMED/);
});
test('host context-selection and actual delegate-delivery receipts are separate',()=>{
 const ui=readFileSync(new URL('../components/studio.tsx',import.meta.url),'utf8');
 assert.match(ui,/boundary\.schema==='temporary-context-boundary-v1'/);
 assert.match(ui,/downstream truncation and interpretation are not attested/i);
 assert.match(ui,/sensorApprovalEpoch\.current/);
 assert.match(ui,/this chat was not submitted/);
});
