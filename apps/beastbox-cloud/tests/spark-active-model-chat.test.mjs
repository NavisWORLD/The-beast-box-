import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';

const read=(path)=>readFileSync(new URL('../'+path,import.meta.url),'utf8');

test('Spark active-model chat is owner-gated and keeps provider credentials off the public page',()=>{
 const route=read('app/api/spark/chat/route.ts');
 const app=read('public/spark/app.mjs');
 const html=read('public/spark/index.html');
 assert.match(route,/isOwner/);
 assert.match(route,/bridgeConfigured/);
 assert.match(route,/BEASTBOX_CLOUD_BRIDGE_TOKEN/);
 assert.match(route,/chat-start/);
 assert.match(route,/chat-job/);
 assert.match(route,/temporary_attachment/);
 assert.doesNotMatch(route,/OLLAMA_API_KEY|HF_TOKEN|ollama\.com\/api\/chat/);
 assert.match(app,/fetch\('\/api\/spark\/chat'/);
 assert.match(app,/credentials:'same-origin'/);
 assert.match(app,/rememberExchange/);
 assert.match(app,/LOCAL PATTERN/);
 assert.match(html,/active Brain Bay model/);
 assert.match(html,/key never enters this HTML/);
 assert.doesNotMatch(app+html,/Bearer\s|OLLAMA_API_KEY|sk-[A-Za-z0-9]/);
});

test('Spark client never chooses or silently approves a paid provider',()=>{
 const app=read('public/spark/app.mjs');
 const route=read('app/api/spark/chat/route.ts');
 assert.doesNotMatch(app,/spend_approved|ollama_cloud|huggingface/);
 assert.doesNotMatch(route,/spend_approved|choice:'ollama_cloud'|choice:"ollama_cloud"/);
 assert.match(route,/source:'active_brain_bay'/);
});
