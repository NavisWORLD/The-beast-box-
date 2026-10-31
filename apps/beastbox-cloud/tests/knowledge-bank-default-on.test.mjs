import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {bankLookup,_resetBankLookupCache} from '../lib/knowledge/server-lookup.mjs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const bankJson=JSON.parse(read('public/knowledge-bank/bank.json'));

test('guest chat: knowledge-bank lookup is ON by default and only off when the keeper turned it off',()=>{
 const s=read('components/beast-talk-panel.tsx');
 assert.match(s,/useState\(true\),bankRef/);
 assert.match(s,/getItem\(BANK_CONSENT_KEY\)!=='off'/);
 assert.match(s,/On by default; untick to turn it off/);
 assert.doesNotMatch(s,/each passage is shown with its source\)\. Off by default/);
});

test('class chat: server lookup adds verbatim passages with source and licence, labelled LOOKUP',async()=>{
 _resetBankLookupCache();
 const fetchImpl=async u=>{const p=new URL(u).pathname;const f=p==='/knowledge-bank/bank.json'?bankJson:JSON.parse(read('public'+p));return new Response(JSON.stringify(f));};
 const r=await bankLookup('https://example.test','What is the capital of France?',fetchImpl);
 assert.ok(Array.isArray(r.used));
 for(const u of r.used){assert.ok(u.source&&u.license&&u.provenance.includes(u.license));}
 if(r.used.length)assert.ok(r.text.length>0);
 const route=read('app/api/classroom/route.ts');
 assert.match(route,/bankLookup\(new URL\(request\.url\)\.origin,text\)/);
 assert.match(route,/kind:'LOOKUP'/);
 assert.match(route,/text:prompt,guest_identity:identity/);
 assert.match(route,/teacherText:text/); // the stored record keeps the teacher's own words, not the prompt
});

test('class chat: a failed lookup never blocks the reply and adds nothing',async()=>{
 _resetBankLookupCache();
 const r=await bankLookup('https://example.test','storms',async()=>{throw new Error('down');});
 assert.deepEqual(r.used,[]);assert.equal(r.text,'');assert.equal(r.error,'lookup unavailable');
});
