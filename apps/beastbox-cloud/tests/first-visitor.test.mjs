import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {beastDisplayName,activeBeastName,fillBeast,SESSION_KEY,COMPANION_KEY} from '../lib/companion/beast-name.mjs';
import {shownName} from '../lib/companion/session.mjs';
import {isPublicDiaryEntry,publicDiaryEntries} from '../lib/zeref/diary-privacy.mjs';
const store=o=>({getItem:k=>k in o?o[k]:null});
test('one source of truth for the active beast name',()=>{
 const b={stage:2,genome:{names:{1:'A',2:'B'}},qbeast:{profile:{name:'Q'}}};
 assert.equal(beastDisplayName(b),'B');assert.equal(shownName(b),'B');
 assert.equal(beastDisplayName({...b,displayName:'Mine'}),'Mine');
 assert.deepEqual(activeBeastName(store({[SESSION_KEY]:JSON.stringify({beast:b}),[COMPANION_KEY]:'{"name":"Cagey"}'})),{name:'B',source:'saved'});
 assert.deepEqual(activeBeastName(store({[COMPANION_KEY]:'{"name":"Cagey"}'})),{name:'Cagey',source:'seeded'});
 assert.equal(fillBeast('Meet {beast}',null),'Meet your beast');
});
test('no hardcoded beast names in the name source or menu',()=>{
 for(const f of ['lib/companion/beast-name.mjs','lib/site-nav.ts'])assert.doesNotMatch(readFileSync(new URL('../'+f,import.meta.url),'utf8'),/Yewling|Zorion|Gearray/);
});
test('diary never shows private lines',()=>{
 const ok={thought:{text:'The tide hums.',by:'rawrphos-step-1'}};
 assert.ok(isPublicDiaryEntry(ok));
 for(const bad of [{...ok,private:true},{...ok,visibility:'owner'},{thought:{text:'Cory told me a secret',by:'x'}},{thought:{text:'mail me a@b.co',by:'x'}},{thought:{text:'hi',by:'cory'}}])assert.equal(isPublicDiaryEntry(bad),false);
 assert.equal(publicDiaryEntries([ok,{...ok,private:true}]).length,1);
});
test('dev wording is gone from visitor pages',()=>{
 const r=f=>readFileSync(new URL('../'+f,import.meta.url),'utf8');
 assert.doesNotMatch(r('components/tiny-universe-view.tsx'),/art Cosmo|Hearth\* placeholder|placeholder name/);
 assert.doesNotMatch(r('app/connect/meta-muse/page.tsx'),/no connector storage configured/);
 assert.doesNotMatch(r('app/research/stage015/page.tsx'),/Open the research PR/);
 assert.doesNotMatch(r('components/beast-talk-panel.tsx'),/real reply verified/);
 assert.match(r('lib/site-nav.ts'),/talk\?with=zeref/);
});
