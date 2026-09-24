import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';

const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');

test('local photo analysis is owner-clicked, bounded, and never sends pixels',()=>{
 const vision=read('lib/attachment-vision.ts');
 const studio=read('components/studio.tsx');
 assert.match(vision,/objectUrl.startsWith\('blob:'\)/);
 assert.match(vision,/image.decode\(\)/);
 assert.match(vision,/4096\*4096/);
 assert.match(vision,/classifier.classify\(image\)/);
 assert.doesNotMatch(vision,/fetch\(|toBlob\(|toDataURL\(|MediaRecorder/);
 assert.match(studio,/onClick=\{\(\)=>void analyzePhoto\(a\)\}/);
 assert.match(studio,/Approximate category:/);
 assert.match(studio,/scope:'temporary_attachment'/);
 assert.match(studio,/if\(attachments.some\(a=>a.text===undefined\)\)/);
 assert.match(studio,/PDFs remain local-only/);
 assert.match(studio,/The selected text model received ONLY this prediction, never image pixels/);
});
test('file observation is separately consented and remains unverified',()=>{
 const ui=read('components/studio.tsx');
 const engine=read('../../beastbox/device_observations.py');
 assert.match(ui,/I separately approve storing only the selected photo CATEGORY/);
 assert.match(ui,/photoMemoryEnabled/);
 assert.match(ui,/source:'file_classifier'/);
 assert.match(ui,/persist_confirmed:true/);
 assert.match(ui,/Check Memory Vault before retrying/);
 assert.match(engine,/SOURCES = frozenset\(\{"camera_classifier", "file_classifier", "browser_speech"\}\)/);
 assert.match(engine,/source_verified": False/);
 assert.match(engine,/raw_media_transmitted": False/);
 assert.doesNotMatch(engine,/base64|image\/jpeg|raw_video/);
});
test('sensor context expires on a stricter client window than backend',()=>{
 const senses=read('components/live-senses.tsx');
 assert.match(senses,/FRESH_MS=4\*60\*1000/);
 assert.match(senses,/setInterval\(\(\)=>setClock\(Date.now\(\)\),15000\)/);
 assert.match(senses,/const selected=fresh\(observations,Date.now\(\)\)/);
 assert.match(senses,/observations:selected,consent:true,persist_confirmed:true/);
 assert.match(senses,/stopCamera\(\);stopSpeech\(\)/);
});
test('spoken replies are always opt-in and never claim model-native audio',()=>{
 const ui=read('components/studio.tsx');
 const speech=read('components/spoken-response.tsx');
 assert.match(ui,/<SpokenResponse text=\{t.text\}/);
 assert.match(ui,/<SpokenResponse text=\{temporaryReply.text\}/);
 assert.match(speech,/onClick=\{toggle\}/);
 assert.match(speech,/text.slice\(0,650\)/);
 assert.match(speech,/speechSynthesis.speak\(utterance\)/);
 assert.doesNotMatch(speech,/fetch\(|autoPlay|MediaRecorder|localStorage|sessionStorage/);
});
