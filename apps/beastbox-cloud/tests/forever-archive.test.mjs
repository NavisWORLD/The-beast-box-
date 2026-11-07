import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {storageConfig} from '../lib/cosmos/azure-blob.mjs';
import {appendExchange,appendArchive,readArchive,newThreadId,MAX_THREAD_TURNS,GUESTBOOK_DIR} from '../lib/cosmos/forever-store.mjs';
import {ownThreadItems,buildSelfMemory,readSelfMemory} from '../lib/zeref/self-memory.mjs';
const AT='2026-11-06T00:00:00.000Z';
const sasCfg=()=>storageConfig({AZURE_STORAGE_CONTAINER_SAS_URL:'https://acct.blob.core.windows.net/beast-cosmos?sv=x&sig=y'});
// In-memory Blob REST stand-in (same fake as forever-connection.test.mjs).
function fakeBlobFetch(){
 const blobs=new Map();let n=0;
 return {blobs,fetch:async(url,{method,headers,body})=>{
  const u=new URL(url);const name=decodeURIComponent(u.pathname.split('/').slice(2).join('/'));
  const H=Object.fromEntries(Object.entries(headers).map(([k,v])=>[k.toLowerCase(),v]));
  if(method==='PUT'&&u.searchParams.get('restype')==='container')return new Response('',{status:201});
  if(method==='GET'&&u.searchParams.get('comp')==='list'){const pre=u.searchParams.get('prefix')||'';
   return new Response('<r>'+[...blobs.keys()].filter(k=>k.startsWith(pre)).sort().map(k=>`<Name>${k}</Name>`).join('')+'<NextMarker></NextMarker></r>');}
  const cur=blobs.get(name);
  if(method==='GET')return cur?new Response(cur.text,{headers:{etag:cur.etag}}):new Response('',{status:404});
  if(H['if-none-match']==='*'&&cur)return new Response('<Code>BlobAlreadyExists</Code>',{status:409});
  if(H['if-match']&&(!cur||cur.etag!==H['if-match']))return new Response('<Code>ConditionNotMet</Code>',{status:412});
  const etag='"e'+(++n)+'"';blobs.set(name,{text:String(body??''),etag});return new Response('',{status:201,headers:{etag}});
 }};
}
const AN=id=>`${GUESTBOOK_DIR}/archive/${id}.jsonl`;

test('archive keeps every turn past the rolling window, append-only; prompt window still capped',async()=>{
 const {blobs,fetch}=fakeBlobFetch();const real=globalThis.fetch;globalThis.fetch=fetch;
 try{
  const cfg=sasCfg();const id=newThreadId();
  for(let i=0;i<60;i++){
   const at=new Date(Date.parse(AT)+i*1000).toISOString();
   await appendExchange(cfg,id,{guestText:'guest word '+i,reply:'reply '+i,step:36464,at});
   const prev=blobs.get(AN(id))?.text||'';
   const a=await appendArchive(cfg,id,{guestText:'guest word '+i,reply:'reply '+i,step:36464,at,exchange_id:String(i).padStart(64,'0')});
   assert.equal(a.archived,true);
   assert.ok(blobs.get(AN(id)).text.startsWith(prev),'old lines kept as an exact prefix');
  }
  const all=await readArchive(cfg,id);
  assert.equal(all.length,120);assert.equal(all[0].text,'guest word 0');
  assert.ok(all.every(r=>r.training_eligible===false&&r.thread===id&&r.origin==='guest'));
  assert.equal(JSON.parse(blobs.get(`${GUESTBOOK_DIR}/threads/${id}.json`).text).turns.length,MAX_THREAD_TURNS);
  const before=blobs.get(AN(id)).text;
  await appendArchive(cfg,id,{guestText:'guest word 0',reply:'reply 0',step:36464,at:AT,exchange_id:'0'.repeat(64)});
  assert.equal(blobs.get(AN(id)).text,before,'retry with same exchange_id is a no-op');
  assert.deepEqual(await readArchive(cfg,newThreadId()),[],'another guest reads nothing');
  assert.deepEqual(await readArchive(cfg,'../x'),[]);
 }finally{globalThis.fetch=real;}
});

test('first archive write carries the surviving window turns in before the new exchange',async()=>{
 const {fetch}=fakeBlobFetch();const real=globalThis.fetch;globalThis.fetch=fetch;
 try{
  const cfg=sasCfg();const id=newThreadId();
  const win=[{at:AT,from:'guest',text:'old one'},{at:AT,from:'zeref',text:'old reply',step:36464}];
  await appendArchive(cfg,id,{guestText:'new',reply:'r',step:36464,at:AT,exchange_id:'a'.repeat(64),windowTurns:win});
  const all=await readArchive(cfg,id);
  assert.deepEqual(all.map(r=>r.text),['old one','old reply','new','r']);
  assert.equal(all[0].carried_from,'thread-window');
 }finally{globalThis.fetch=real;}
});

test('own-thread retrieval reaches an archived turn older than the window; label unchanged',()=>{
 const archived=[{from:'guest',text:'my dragon is called Boto and has a long tail'}];
 const windowTurns=Array.from({length:40},(_,i)=>({from:'guest',text:'filler words number '+i}));
 const r=readSelfMemory(buildSelfMemory([]),'tell me about the dragon tail',{ownThread:ownThreadItems([...archived,...windowTurns])});
 assert.ok(r.memory_read.some(m=>m.label==='THREAD (your own)'));
 assert.match(r.text,/Boto/);
});

test('route reads and writes the archive keyed by its own thread id only',()=>{
 const src=readFileSync(new URL('../app/api/guest/forever/route.ts',import.meta.url),'utf8');
 assert.match(src,/readArchive\(cfg,threadId\)/);assert.match(src,/appendArchive\(cfg,threadId,/);
});
