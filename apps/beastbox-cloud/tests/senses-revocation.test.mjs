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
});
