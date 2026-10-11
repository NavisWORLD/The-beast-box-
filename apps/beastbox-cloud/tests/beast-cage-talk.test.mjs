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
test('galaxy creature art is preserved while the site icon moves to the Cosmic Forge Dragon crest',()=>{
 const icon=read('public/beast-icon.svg'),layout=read('app/layout.tsx'),manifest=read('app/manifest.ts');
 assert.match(icon,/iridescent petals and a golden orbiting star/);
 assert.doesNotMatch(layout,/beast-icon\.svg|'\/apple-icon'/);
 assert.doesNotMatch(manifest,/beast-icon\.svg/);
 assert.match(layout,/BRAND_ICONS\.apple180/);
});
