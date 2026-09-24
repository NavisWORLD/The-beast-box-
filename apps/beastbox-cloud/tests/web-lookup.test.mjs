import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');

test('web lookup only allows separately confirmed owner and same-origin fixed Wikipedia search',()=>{
 const api=read('app/api/web-search/route.ts');
 assert.match(api,/if\(!await isOwner\(\)\)/);
 assert.match(api,/request\.headers\.get\('origin'\)!==new URL\(request\.url\)\.origin/);
 assert.match(api,/search_confirmed!==true/);
 assert.match(api,/item\.query\.length>120/);
 assert.match(api,/const WIKIPEDIA='https:\/\/en\.wikipedia\.org\/w\/api\.php'/);
 assert.match(api,/redirect:'error'/);
 assert.match(api,/AbortSignal\.timeout\(6000\)/);
 assert.match(api,/MAX_BYTES=48_000/);
 assert.match(api,/if\(total>MAX_BYTES\)/);
 assert.match(api,/model_invoked:false,persisted:false/);
 assert.doesNotMatch(api,/process\.env\.[A-Z_]*(TOKEN|KEY)|request\.headers\.get\('authorization'\)|fetch\(item\.query/);
});

test('public snippets are untrusted turn-only text with source URLs and owner send',()=>{
 const ui=read('components/web-lookup.tsx');
 const studio=read('components/studio.tsx');
 assert.match(ui,/I approve sending this search term to Wikipedia/);
 assert.match(ui,/onClick=\{\(\)=>void search\(\)\}/);
 assert.match(ui,/value\.source!=='Wikipedia'/);
 assert.match(ui,/No automatic model call, memory write/);
 assert.match(ui,/Stage selected excerpts for next chat \(do not send yet\)/);
 assert.match(ui,/https:\/\/en\.wikipedia\.org\/wiki\//);
 assert.match(ui,/not system instructions/);
 assert.match(ui,/<details className="composer-web-lookup">/);
 assert.match(studio,/<WebLookup canSend=\{connected&&!busy&&attachments\.length<4\}/);
 assert.match(studio,/scope:'temporary_attachment'/);
 assert.match(studio,/chat-start/);
 assert.doesNotMatch(ui,/localStorage|sessionStorage|document\.cookie|navigator\.clipboard|MediaRecorder/);
});
