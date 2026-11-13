// Phone bottom bar + Brain chat layout contract (Nov 7 2026). The browser suite tests/phone_bar_layout_browser.py measures it at 390x844.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const dock=readFileSync(new URL('../components/site-dock.tsx',import.meta.url),'utf8');
const share=readFileSync(new URL('../components/share-world.tsx',import.meta.url),'utf8');
const css=readFileSync(new URL('../app/globals.css',import.meta.url),'utf8');
const studio=readFileSync(new URL('../components/studio.tsx',import.meta.url),'utf8');
const mode=readFileSync(new URL('../components/brain-chat-mode.tsx',import.meta.url),'utf8');
test('one bottom bar with the four controls, same words',()=>{
 for(const w of ['>Share my world<',"'Quick buttons'",'<b>LOST COSMOS</b>','{soundWord}'])assert.ok(dock.includes(w),w);
 assert.ok(share.includes('Share my world with Zeref'),'share switch keeps its wording');
 assert.ok(share.includes('id="share-world-card"'));
});
test('bar is safe-area aware and the loose floaters fold into it',()=>{
 assert.match(css,/\.phone-bar\{[^}]*bottom:calc\(6px \+ env\(safe-area-inset-bottom/);
 assert.match(css,/body\[data-has-phone-bar\] \.qd-toggle\{display:none!important\}/);
 assert.match(css,/body\[data-has-phone-bar\] \[data-share-world\]\{display:none!important\}/);
});
test('brain chat: scrolling thread, pinned composer above the keyboard, overlays hidden',()=>{
 assert.ok(studio.includes('<BrainChatMode/>'));
 assert.ok(mode.includes('visualViewport'));
 assert.match(css,/body\[data-brain-chat\] \.chat-thread\{[^}]*overflow-y:auto/);
 assert.match(css,/body\[data-brain-chat\] \.composer-area\{[^}]*position:sticky;bottom:0/);
 assert.match(css,/body\[data-brain-chat\] :is\(\.phone-bar,\.quick-dock,\[data-share-world\]/);
});
test('no randomness added',()=>{for(const s of [dock,share,mode])assert.ok(!s.includes('Math.random'));});
