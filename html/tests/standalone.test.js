import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const html=await readFile(new URL('../standalone.html',import.meta.url),'utf8');
test('standalone is a literal single-file runtime',()=>{assert.match(html,/<!doctype html>/i);assert.match(html,/<style>[\s\S]+<\/style>/i);assert.match(html,/<script>[\s\S]+<\/script>/i);assert.doesNotMatch(html,/<script[^>]+src=/i);assert.doesNotMatch(html,/<link[^>]+rel=["']stylesheet/i);assert.doesNotMatch(html,/<link[^>]+rel=["']manifest/i)});
test('standalone preserves Beast Box contracts and safety boundaries',()=>{for(const e of ['/api/orbit','/api/provider','/api/conversation','/api/memory','/api/trace','/api/storage','/api/chat','/api/context','/api/authority'])assert.ok(html.includes(e),`missing ${e}`);assert.match(html,/MODEL\s*≠\s*MEMORY/);assert.match(html,/AUTHORITY DOES NOT TRAVEL AUTOMATICALLY/);assert.match(html,/escapeHtml/);assert.match(html,/confirm_persist/)})
test('standalone is honest about local inference',()=>{assert.match(html,/requires a registered compatible browser inference adapter/i);assert.match(html,/GGUF HEADER: VALID/)})
