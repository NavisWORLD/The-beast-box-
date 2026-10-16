import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {makePair,contributionBody,screenText,personaStyle,rememberPair,readPairs,readContribute,isTeacherRoute} from '../lib/companion/teacher-distill.mjs';
const mem=()=>{const m=new Map();return {getItem:k=>m.has(k)?m.get(k):null,setItem:(k,v)=>m.set(k,String(v)),removeItem:k=>m.delete(k)};};
test('RAWRPHOS is never a teacher; other brains are',()=>{
 assert.equal(isTeacherRoute('guest-rawrphos'),false);
 for(const r of ['local-ollama','hf-byok','connected-brain-bay'])assert.equal(isTeacherRoute(r),true);
 assert.equal(makePair({prompt:'hi',reply:'yo',route:'guest-rawrphos'}),null);
});
test('pairs stay on device and contribution is off by default',()=>{
 const s=mem();assert.equal(readContribute(s),false);
 const p=makePair({prompt:'What is the moon?',reply:'Earth\'s natural satellite.',route:'local-ollama',model:'qwen2.5:0.5b'});
 rememberPair(s,p);assert.equal(readPairs(s).length,1);assert.equal(readPairs(s)[0].role,'TEACHER_NOT_BEAST_VOICE');
});
test('privacy filter keeps secrets and PII out of shared training',()=>{
 for(const bad of ['my token is hf_abcdefghijklmnopqrst','mail me at a.b@example.com','call 555-123-4567 now','password: hunter2','sk-ABCDEFGHIJKLMNOP'])
  assert.equal(screenText(bad).ok,false,bad);
 const p=makePair({prompt:'email me at x@y.com',reply:'ok',route:'hf-byok'});
 assert.equal(contributionBody(p),null);
 const q=makePair({prompt:'Why is the sky blue?',reply:'Rayleigh scattering.',route:'hf-byok'});
 assert.deepEqual(Object.keys(contributionBody(q)).sort(),['consent','model','prompt','provider','teacher_reply']);
});
test('persona style filter drops teacher identity, keeps short knowledge',()=>{
 assert.equal(personaStyle('As an AI language model, I think...'),null);
 assert.equal(personaStyle('ACTION: RIGHT'),null);
 const s=personaStyle('**Bees** make honey from nectar. They store it in combs. It lasts a long time.');
 assert.equal(s,'Bees make honey from nectar. They store it in combs.');
});
test('Talk panel never presents teacher output as the Beast voice',()=>{
 const ui=fs.readFileSync(new URL('../components/beast-talk-panel.tsx',import.meta.url),'utf8');
 assert.match(ui,/route:'guest-rawrphos'/);
 assert.doesNotMatch(ui,/data-teacher-hint/);
 assert.match(ui,/data-coached-by/);
 assert.match(ui,/useState\(false\),\[pairCount/);
 const api=fs.readFileSync(new URL('../app/api/teacher-pairs/route.ts',import.meta.url),'utf8');
 assert.match(api,/consent!==true/);assert.match(api,/PENDING_REVIEW/);assert.match(api,/limited\(client\)/);
});
