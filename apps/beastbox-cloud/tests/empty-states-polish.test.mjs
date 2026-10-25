import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('the 404 and the route error use the warm lines, each 44 characters or fewer',()=>{
 const n=read('app/not-found.tsx');for(const l of ['This corner of the universe isn’t here.','The link may be old. Let’s get you home.'])assert.ok(n.includes(l)&&l.length<=44,l);
 assert.match(n,/Tiny Universe/);const e=read('app/error.tsx');assert.match(e,/That didn’t load\./);assert.match(e,/Tap to try again/);assert.doesNotMatch(e,/error\.message/);
});
test('loading and empty lines are plain, and an honest state is kept',()=>{
 assert.match(read('components/tiny-universe-view.tsx'),/Opening the tiny universe…/);assert.doesNotMatch(read('components/tiny-universe-view.tsx'),/Couldn’t load genesis/);
 assert.match(read('components/living-world-page.tsx'),/Opening your tiny world…/);
 assert.match(read('components/zeref-research-card.tsx'),/Nothing is assumed\./);assert.match(read('components/zeref-knowledge-diagnostics.tsx'),/Nothing is made up\./);
 assert.match(read('components/companion-local-bay.tsx'),/No beast chosen yet\. Pick one to begin\./);
});
test('the diary never says "fully grown" before it has loaded',()=>{
 const d=read('components/zeref-diary-panel.tsx');assert.match(d,/diary\?\(diary\.next_stage\?/);assert.match(d,/opening the diary…/);
});
