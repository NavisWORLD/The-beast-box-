import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {storageConfig,putBlob} from '../lib/cosmos/azure-blob.mjs';
import {appendExchange,appendGuestEvent,composeContinuityPreface,countZerefCloud,diaryEventLine,
 isThreadId,newThreadId,readThread,readZerefModel,shapeLiveness,GUESTBOOK_DIR} from '../lib/cosmos/forever-store.mjs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');

// In-memory stand-in for the Blob REST API (same fake as beast-cosmos-autonomy.test.mjs).
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
const sasCfg=()=>storageConfig({AZURE_STORAGE_CONTAINER_SAS_URL:'https://acct.blob.core.windows.net/beast-cosmos?sv=x&sig=y'});
const AT='2026-10-28T21:00:00.000Z';

test('guestbook: thread round-trip is server-written, guest-origin, training-excluded',async()=>{
 const {blobs,fetch}=fakeBlobFetch();const real=globalThis.fetch;globalThis.fetch=fetch;
 try{
  const cfg=sasCfg();const id=newThreadId();
  assert.ok(isThreadId(id));
  const w1=await appendExchange(cfg,id,{guestText:'hello zeref',reply:'I am here.',step:33904,at:AT});
  assert.equal(w1.persisted,true);assert.equal(w1.turns,2);
  const w2=await appendExchange(cfg,id,{guestText:'what is a sentence?',reply:'Words in a row.',step:33904,at:AT});
  assert.equal(w2.turns,4);
  const got=await readThread(cfg,id);
  assert.equal(got.thread.schema,'beastbook-guest-thread/v1');
  assert.equal(got.thread.training_eligible,false);
  assert.equal(got.thread.beast_id,'bb-deada969');
  assert.deepEqual(got.thread.turns.map(t=>t.from),['guest','zeref','guest','zeref']);
  assert.equal(got.thread.turns[1].step,33904);
  assert.ok(blobs.has(`${GUESTBOOK_DIR}/threads/${id}.json`));
  // the guestbook never touches his diary chain or lessons
  assert.ok(![...blobs.keys()].some(k=>k.endsWith('diary.jsonl')||k.includes('/lessons/')));
  // thread turns are capped
  for(let i=0;i<25;i++)await appendExchange(cfg,id,{guestText:'x',reply:'y',step:33904,at:AT});
  assert.ok((await readThread(cfg,id)).thread.turns.length<=40);
 }finally{globalThis.fetch=real;}
});

test('guestbook: events carry counts only — never guest text',async()=>{
 const {blobs,fetch}=fakeBlobFetch();const real=globalThis.fetch;globalThis.fetch=fetch;
 try{
  const cfg=sasCfg();const id=newThreadId();const sentinel='SENTINEL-GUEST-WORDS-12345';
  assert.equal(await appendGuestEvent(cfg,{at:AT,thread:id,step:33904,checkpoint_sha256:'abc',guest_chars:sentinel.length,reply_chars:9}),true);
  assert.equal(await appendGuestEvent(cfg,{at:AT,thread:id,step:33904,checkpoint_sha256:'abc',guest_chars:3,reply_chars:4}),true);
  const raw=blobs.get(`${GUESTBOOK_DIR}/events.jsonl`).text;
  assert.ok(!raw.includes(sentinel),'event log must not contain guest text');
  const lines=raw.trim().split('\n').map(l=>JSON.parse(l));
  assert.equal(lines.length,2);
  for(const e of lines){assert.equal(e.kind,'guest_exchange');assert.equal(e.origin,'guest');assert.equal(e.training_eligible,false);}
 }finally{globalThis.fetch=real;}
});

test('guestbook: hostile or malformed thread ids are refused',async()=>{
 const {fetch}=fakeBlobFetch();const real=globalThis.fetch;globalThis.fetch=fetch;
 try{
  const cfg=sasCfg();
  for(const bad of ['../profile','..%2f..%2fprofile','zzzz','',null,undefined,42])
   assert.equal(await readThread(cfg,bad),null);
  assert.deepEqual(await appendExchange(cfg,'../../etc',{guestText:'x',reply:'y',step:1,at:AT}),{persisted:false,turns:0});
  assert.equal(isThreadId('a'.repeat(32)),true);
  assert.equal(isThreadId('a'.repeat(31)),false);
 }finally{globalThis.fetch=real;}
});

test('forever store: reads his Azure model record and counts approved lessons/experiences',async()=>{
 const {fetch}=fakeBlobFetch();const real=globalThis.fetch;globalThis.fetch=fetch;
 try{
  const cfg=sasCfg();
  assert.equal(await readZerefModel(cfg),null);
  await putBlob(cfg,'beasts/bb-deada969/model.json',JSON.stringify({model_id:'rawrphos-native',training_steps:33904,checkpoint_sha256:'f'.repeat(64)}));
  await putBlob(cfg,'beasts/bb-deada969/lessons/2026-10-28/l1.json','{}');
  await putBlob(cfg,'beasts/bb-deada969/experiences/zeref-006-cycle-49-11de94461bde.json','{}');
  const m=await readZerefModel(cfg);
  assert.equal(m.training_steps,33904);
  assert.deepEqual(await countZerefCloud(cfg),{lessons:1,experiences:1});
 }finally{globalThis.fetch=real;}
});

test('continuity preface: server-sourced state, honest labels, bounded',()=>{
 const diary={tick:31,xp:1142,bond:7.75,stage_name:'Duskwing',recent:[
  {tick:31,growth_source:{kind:'rigetti-qvm-simulated',simulated:true},learning:{new_cells:3}},
  {tick:30,growth_source:{kind:'deterministic-fallback',simulated:false},learning:{new_cells:0}}]};
 const out=composeContinuityPreface({pinStep:33904,diary,threadTurns:[{from:'guest',text:'hi'},{from:'zeref',text:'hello'}]});
 assert.match(out,/step 33904/);assert.match(out,/Duskwing/);assert.match(out,/bond 7\.75/);assert.match(out,/tick 31/);
 assert.match(out,/rigetti-qvm-simulated \(simulated\)/);
 const long=composeContinuityPreface({pinStep:33904,diary,threadTurns:Array.from({length:8},()=>({from:'guest',text:'x'.repeat(500)}))},300);
 assert.ok(long.length<=300,'preface respects its budget');
 const bare=composeContinuityPreface({pinStep:33904});
 assert.match(bare,/step 33904/);assert.doesNotMatch(bare,/XP \d/,'no diary -> no invented life numbers');
 assert.equal(diaryEventLine(null),null);
 assert.equal(diaryEventLine({tick:'x'}),null);
});

test('liveness shaping: missing sources are DOWN, never invented; pin cross-check is honest',()=>{
 const empty=shapeLiveness({now:AT,pin:null,diary:null,bridge:null,azure:null,world:null});
 assert.equal(empty.diary.state,'DOWN');assert.equal(empty.bridge.state,'DOWN');
 assert.equal(empty.azure.configured,false);assert.equal(empty.brain.step,null);
 assert.equal(empty.guestbook.training_eligible,false);assert.equal(empty.identity_note.merged,false);
 const pin={training_steps:33904,checkpoint_sha256:'f'.repeat(64)};
 const full=shapeLiveness({now:AT,pin,diary:{tick:31,xp:1142,bond:7.75,stage:2,stage_name:'Duskwing',last_tick_at:AT},
  diaryVerified:true,bridge:{schema:'beastbox-bridge-health-v2',pin_step:33904,served_step:33904,served_readiness:'INSTALLED_AND_READY',serving_pin:true},
  azure:{configured:true,model:{training_steps:33904},counts:{lessons:5,experiences:3}},
  world:{schema:'beast-world-live/v1',links:{spark:{state:'CONNECTED'}},all_connected:false,labels:{spark:'SIMULATED'}}});
 assert.equal(full.diary.xp,1142);assert.equal(full.diary.verified,true);
 assert.equal(full.bridge.serving_pin,true);assert.equal(full.azure.model_matches_pin,true);
 assert.equal(full.life_signals.all_connected,false);
 const drift=shapeLiveness({now:AT,pin,azure:{configured:true,model:{training_steps:33584},counts:{lessons:0,experiences:0}}});
 assert.equal(drift.azure.model_matches_pin,false,'a stale Azure model record is flagged, not hidden');
});

test('forever door route: same bridge verification as /api/guest, guestbook writes only via the store',()=>{
 const src=read('app/api/guest/forever/route.ts');
 assert.match(src,/result\.memory_used!==false\|\|result\.owner_tools_used!==false/);
 assert.match(src,/result\.step!==PIN_STEP\|\|result\.checkpoint_sha256!==PIN_SHA/);
 assert.match(src,/guest_stateless:false/);
 assert.match(src,/training_eligible:false/);
 assert.match(src,/HttpOnly/);
 assert.match(src,/appendExchange/);assert.match(src,/composeContinuityPreface/);
 assert.doesNotMatch(src,/putBlob|storeLesson|stepDiary|diary\.jsonl/);
});

test('liveness route: read-only, per-request, shaped from the shared store helpers',()=>{
 const src=read('app/api/cosmos/liveness/route.ts');
 assert.match(src,/shapeLiveness/);
 assert.match(src,/buildWorldLive/);
 assert.match(src,/no-store/);
 assert.doesNotMatch(src,/putBlob|appendGuestEvent|method:'POST'/);
});

test('the stateless door is untouched by the forever layer',()=>{
 const src=read('app/api/guest/route.ts');
 assert.match(src,/guest_stateless:true/);
 assert.doesNotMatch(src,/forever-store|guestbook|Set-Cookie/);
});
