import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=path=>readFileSync(new URL('../'+path,import.meta.url),'utf8');

test('on-device ASR is separate opt-in; unsupported browser never falls back to cloud',()=>{
 const ui=read('components/live-senses.tsx');
 assert.match(ui,/onDeviceOnly,setOnDeviceOnly/);
 assert.match(ui,/const ctor=\(window as SpeechWindow\)\.SpeechRecognition/);
 assert.match(ui,/typeof ctor\?\.available!=='function'/);
 assert.match(ui,/ctor\.available\(\{langs:\['en-US'\],processLocally:true\}\)/);
 assert.match(ui,/if\(Ctor!==w\.SpeechRecognition\|\|offlineStatus!=='available'\|\|typeof engine\.processLocally!=='boolean'\)/);
 assert.match(ui,/engine\.processLocally=true/);
 assert.match(ui,/if\(engine\.processLocally!==true\)/);
 assert.match(ui,/onDeviceOnly&&offlineStatus!=='available'/);
 assert.match(ui,/language-not-supported/);
});
test('language pack requires second deliberate owner click and never installs automatically',()=>{
 const ui=read('components/live-senses.tsx');
 assert.match(ui,/onClick=\{\(\)=>void checkOfflineSpeech\(\)\}/);
 assert.match(ui,/onClick=\{\(\)=>void installOfflineSpeech\(\)\}/);
 assert.match(ui,/offlineStatus!=='downloadable'/);
 assert.match(ui,/ctor\.install\(\{langs:\['en-US'\],processLocally:true\}\)/);
 assert.match(ui,/setOfflineStatus\(installed\?'unchecked':'error'\)/);
 assert.doesNotMatch(ui,/MediaRecorder|toDataURL\(|toBlob\(|localStorage|sessionStorage/);
});
