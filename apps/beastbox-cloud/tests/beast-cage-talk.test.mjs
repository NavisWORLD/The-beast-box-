import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('cage links a real, stateless model conversation separate from owner console',()=>{
 const cage=read('components/beast-cage-portal.tsx'),talk=read('components/beast-cage-talk.tsx');
 assert.match(cage,/href="\/beast-cage\/talk"/);
 assert.match(talk,/fetch\('\/api\/guest'/);
 assert.match(talk,/provider:'rawrphos-local'/);
 assert.match(talk,/result\.model!=='rawrphos-native'/);
 assert.match(talk,/result\.step!==14000/);
 assert.match(talk,/result\.guest_stateless!==true/);
 assert.doesNotMatch(talk,/\/api\/bridge|localStorage|ownerToken|mockReply|fakeAnswer|Math\.random/);
});
test('speech and pending status remain explicit and reversible',()=>{
 const talk=read('components/beast-cage-talk.tsx');
 assert.match(talk,/SpeechRecognition/);assert.match(talk,/You review text before sending/);
 assert.match(talk,/controller\.abort\(\)/);assert.match(talk,/hasReply/);
 assert.match(talk,/Response|response/);
 assert.match(talk,/window\.speechSynthesis/);
});
test('old abstract favicon is replaced by galaxy creature art',()=>{
 const icon=read('public/beast-icon.svg'),apple=read('app/apple-icon.tsx');
 assert.match(icon,/iridescent petals and a golden orbiting star/);
 assert.match(apple,/radial-gradient/);
 assert.doesNotMatch(apple,/>B</);
});
