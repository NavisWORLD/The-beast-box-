import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('cage links a real, shared model conversation with explicit owner pairing',()=>{
 const cage=read('components/beast-cage-portal.tsx'),talk=read('components/beast-cage-talk.tsx');
 const panel=read('components/beast-talk-panel.tsx'),lib=read('lib/companion/beast-talk.mjs');
 assert.match(cage,/href="\/beast-cage\/talk"/);
 assert.match(talk,/<BeastTalkPanel/);
 assert.match(lib,/fetchImpl\("\/api\/guest"/);
 assert.match(lib,/provider: "rawrphos-local"/);
 assert.match(lib,/interpretModelResult\("guest-rawrphos", payload\)/);
 assert.doesNotMatch(talk+panel+lib,/ownerToken|mockReply|fakeAnswer|Math\.random/);
});
test('speech and pending status remain explicit and reversible',()=>{
 const panel=read('components/beast-talk-panel.tsx');
 assert.match(panel,/SpeechRecognition/);
 assert.match(panel,/controller\.abort\(\)/);
 assert.match(panel,/Model offline/);
 assert.match(panel,/window\.speechSynthesis/);
 assert.match(panel,/Brain: \{info\.label\}/);
});
test('galaxy creature art is preserved while the site icon moves to the Cosmic Forge Dragon crest',()=>{
 const icon=read('public/beast-icon.svg'),layout=read('app/layout.tsx'),manifest=read('app/manifest.ts');
 assert.match(icon,/iridescent petals and a golden orbiting star/);
 assert.doesNotMatch(layout,/beast-icon\.svg|'\/apple-icon'/);
 assert.doesNotMatch(manifest,/beast-icon\.svg/);
 assert.match(layout,/BRAND_ICONS\.apple180/);
});
