// Synthetic recall-receipt fixtures only. No stored transcripts.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {canonicalRecallJson,canonicalRecallText,entrySha256,recallReceiptBody,RECALL_HASH_SPEC} from '../lib/zeref/recall-receipt.mjs';
import {itemsFrom,ownThreadItems,buildSelfMemory,readSelfMemory,sha256} from '../lib/zeref/self-memory.mjs';

const CREATED='2026-11-08T00:00:00.000Z';
const THREAD='0123456789abcdef0123456789abcdef';
const RAW='hello moon  \r\n';
const CANON='{"created_at":"2026-11-08T00:00:00.000Z","role":"guest","source":"thread","spec":"beastbox-recall-v1","text":"hello moon","thread_id":"0123456789abcdef0123456789abcdef"}';
const HASH='5b598d7f5fe7b7b115228af166a2c4fabbf036240e0ae17421b0ef4dd85c20bd';
const fields={text:RAW,role:'guest',source:'thread',thread_id:THREAD,created_at:CREATED};

test('canonical text: NFC, LF, trailing whitespace off, internal spaces kept',()=>{
 assert.equal(canonicalRecallText(RAW),'hello moon');
 assert.equal(canonicalRecallText('hello moon\n'),'hello moon');
 assert.equal(canonicalRecallText('hello moon\r\n\n'),'hello moon');
 assert.equal(canonicalRecallText('hello  moon'),'hello  moon');
 assert.equal(canonicalRecallText('  hello moon'),'  hello moon');
 assert.equal(canonicalRecallText('left \n right \t'),'left\n right');
 assert.equal(canonicalRecallText('cafe\u0301'),canonicalRecallText('caf\u00e9'));
});

test('entry_sha256 matches the documented canonical JSON and sha256sum bytes',()=>{
 assert.equal(canonicalRecallJson(fields),CANON);
 assert.equal(canonicalRecallJson({created_at:CREATED,thread_id:THREAD,text:'hello moon',source:'thread',role:'guest'}),CANON);
 assert.equal(entrySha256(fields),HASH);
 assert.equal(entrySha256({...fields,text:'hello moon'}),HASH);
 assert.equal(createHash('sha256').update(CANON,'utf8').digest('hex'),HASH);
 assert.equal(entrySha256({...fields,text:'cafe\u0301'}),entrySha256({...fields,text:'caf\u00e9'}));
 assert.notEqual(entrySha256({...fields,created_at:'2026-11-08T00:00:01.000Z'}),HASH);
 assert.notEqual(entrySha256({...fields,text:'hello  moon'}),HASH);
 const body=recallReceiptBody(fields);
 assert.equal(body.entry_sha256,HASH);
 assert.equal(body.entry_hash_spec,RECALL_HASH_SPEC);
 assert.match(body.entry_hash_note,/beastbox-recall-v1/);
 assert.equal(body.role,'guest');
 assert.equal(body.thread_id,THREAD);
 assert.equal(body.created_at,CREATED);
 assert.equal(canonicalRecallJson({text:'hello moon'}).includes('"created_at":""'),true);
});

test('guest thread receipt keeps the legacy raw-text id and adds a matching entry_sha256',()=>{
 const legacy=sha256('thread\n'+RAW);
 const items=ownThreadItems([{from:'guest',text:RAW,at:CREATED,thread:THREAD}]);
 assert.equal(items.length,1);
 assert.equal(items[0].sha256,legacy);
 assert.equal(items[0].id,'thread:'+legacy.slice(0,16));
 assert.equal(items[0].id,'thread:e5876d956a769171');
 assert.equal(items[0].text,'hello moon');
 assert.equal(items[0].label,'THREAD (your own)');
 const hit=readSelfMemory(buildSelfMemory([]),'hello moon',{ownThread:items,minScore:0}).memory_read[0];
 assert.equal(hit.id,items[0].id);
 assert.equal(hit.sha256,legacy);
 assert.equal(hit.label,'THREAD (your own)');
 assert.equal(hit.entry_sha256,HASH);
 assert.equal(hit.entry_sha256,entrySha256({text:RAW,role:'guest',source:'thread',thread_id:THREAD,created_at:CREATED}));
 assert.notEqual(hit.entry_sha256,hit.sha256);
 assert.equal(hit.entry_hash_spec,'beastbox-recall-v1');
 assert.match(hit.entry_hash_note,/trailing whitespace removed/);
});

test('window turns take the door thread id; legacy id ignores it',()=>{
 const door='abcdef0123456789abcdef0123456789';
 const a=ownThreadItems([{from:'guest',text:'hello moon',at:CREATED}],door)[0];
 const b=ownThreadItems([{from:'guest',text:'hello moon',at:CREATED,thread:door}])[0];
 assert.equal(a.id,b.id);
 assert.equal(a.sha256,sha256('thread\nhello moon'));
 assert.equal(a.id,'thread:f01d8c02e527350c');
 const hit=readSelfMemory(buildSelfMemory([]),'hello moon',{ownThread:[a],minScore:0}).memory_read[0];
 assert.equal(hit.thread_id,door);
 assert.equal(hit.entry_sha256,entrySha256({text:'hello moon',role:'guest',source:'thread',thread_id:door,created_at:CREATED}));
});

test('diary receipt is additive: legacy collapsed hash unchanged, entry_sha256 covers the source line and at',()=>{
 const line='The silver fern grew beside the path.  \r\n';
 const collapsed='The silver fern grew beside the path.';
 const item=itemsFrom({diary:[{tick:1,hash:'h',at:CREATED,thought:{text:line,by:'deterministic-template'}}]})[0];
 assert.equal(item.sha256,sha256('diary\n'+collapsed));
 assert.equal(item.id,'diary:'+item.sha256.slice(0,16));
 assert.equal(item.text,collapsed);
 assert.equal(item.label,'RECORDED');
 const read=readSelfMemory(buildSelfMemory([item]),'silver fern path',{minScore:0});
 assert.match(read.text,/The silver fern grew beside the path\./);
 assert.doesNotMatch(read.text,/entry_sha256|beastbox-recall-v1/);
 const hit=read.memory_read[0];
 assert.equal(hit.id,item.id);
 assert.equal(hit.sha256,item.sha256);
 assert.equal(hit.role,'diary');
 assert.equal(hit.source,'diary');
 assert.equal(hit.thread_id,'');
 assert.equal(hit.created_at,CREATED);
 assert.equal(hit.entry_sha256,entrySha256({text:line,role:'diary',source:'diary',thread_id:'',created_at:CREATED}));
});

test('forever door passes its thread id into own-thread receipts',()=>{
 const src=readFileSync(new URL('../app/api/guest/forever/route.ts',import.meta.url),'utf8');
 assert.match(src,/ownThreadItems\(\[\.\.\.archiveTurns,\.\.\.\(threadRec\?\.thread\?\.turns\|\|\[\]\)\],threadId\)/);
});
