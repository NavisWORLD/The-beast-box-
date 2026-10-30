import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHmac} from 'node:crypto';
import {storageConfig,putBlob} from '../lib/cosmos/azure-blob.mjs';
import {appendExchange,appendGuestEvent,bridgeIdentityForThread,composeContinuityPreface,countZerefCloud,diaryEventLine,
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
 // A memory claim is accepted ONLY on the bridge's persisted mode (PR #675);
 // the exact relaxed conjunct replaces the old memory_used!==false check.
 assert.match(src,/\(result\.memory_used!==false&&result\.hebbian_mode!=='persisted'\)\|\|result\.owner_tools_used!==false/);
 assert.doesNotMatch(src,/result\.memory_used!==false\|\|/,'the old unconditional memory rejection is gone');
 assert.match(src,/result\.step!==PIN_STEP\|\|result\.checkpoint_sha256!==PIN_SHA/);
 assert.match(src,/guest_stateless:false/);
 assert.match(src,/training_eligible:false/);
 assert.match(src,/HttpOnly/);
 assert.match(src,/appendExchange/);assert.match(src,/composeContinuityPreface/);
 assert.doesNotMatch(src,/putBlob|storeLesson|stepDiary|diary\.jsonl/);
});

test('forever door route: context contract to the bridge, persistence receipts surfaced, no truncation retry',()=>{
 const src=read('app/api/guest/forever/route.ts');
 // The composed pieces go through the context object, not the prompt text.
 assert.match(src,/assembleBridgeContext/);
 assert.match(src,/\{text,guest_identity:identity,context:bridgeContext\.context\}/);
 assert.match(src,/\{text,guest_identity:identity\}/,'over-cap visitor text falls back to the plain contract');
 assert.match(src,/MAX_TEXT_WITH_CONTEXT=1200/);
 // The bridge's persistence receipts are surfaced in the door's own response.
 assert.match(src,/hebbian_mode:hebbianMode,guest_thread:guestThread/);
 assert.match(src,/bridge_context:\{sent:contextSent,bytes:sentContextBytes/);
 // No 400-truncation retry for context requests (BRIDGE-PERSISTENCE.md step 1).
 assert.doesNotMatch(src,/LEGACY_BRIDGE_PROMPT|slice\(-/);
 assert.equal((src.match(/await send\(\)/g)||[]).length,1,'exactly one bridge send');
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
 // The plain door never sends context and carries no persistence wiring.
 assert.doesNotMatch(src,/hebbian_mode|guest_thread|assembleBridgeContext|context:bridgeContext/);
 assert.match(src,/body:JSON\.stringify\(\{text:prompt,guest_identity:identity\}\)/,'its bridge body stays exactly {text, guest_identity}');
});

test('bridge identity: derived from the thread id, stable per cookie, blind to the network',()=>{
 const secret='s'.repeat(40);
 const idA=newThreadId(),idB=newThreadId();
 const a=bridgeIdentityForThread(secret,idA);
 // The exact derivation, recomputed independently: HMAC over 'thread:' + id.
 assert.equal(a,createHmac('sha256',secret).update(`thread:${idA}`).digest('hex'));
 assert.match(a,/^[a-f0-9]{64}$/,'the same 64-hex shape the bridge has always received');
 // Two simulated requests sharing a cookie resolve the same thread id and
 // therefore present the same bridge identity — that is what lets the
 // bridge load the thread it stored on the previous visit.
 assert.equal(bridgeIdentityForThread(secret,idA),a);
 // A different visitor (different cookie) is a different bridge guest.
 assert.notEqual(bridgeIdentityForThread(secret,idB),a);
 // Never the raw thread id, and domain-separated from a bare-id HMAC.
 assert.notEqual(a,idA);
 assert.notEqual(a,createHmac('sha256',secret).update(idA).digest('hex'));
 // Not the retired IP derivation, for any address the visitor arrives from:
 // an IP rotation between visits can no longer restart the bridge thread.
 for(const ip of ['203.0.113.7','198.51.100.23','2001:db8::1','unknown'])
  assert.notEqual(a,createHmac('sha256',secret).update(ip).digest('hex'));
 // Hostile or unusable inputs derive nothing (the route only ever passes
 // an isThreadId-checked or freshly minted id, so this is defence in depth).
 for(const bad of ['../profile','..%2f..%2fprofile','zzzz','',null,undefined,42])
  assert.equal(bridgeIdentityForThread(secret,bad),null);
 assert.equal(bridgeIdentityForThread('short',idA),null);
 assert.equal(bridgeIdentityForThread(undefined,idA),null);
});

test('forever door route: one thread id feeds the bridge identity, the guestbook and the cookie',()=>{
 const src=read('app/api/guest/forever/route.ts');
 // The id is resolved (cookie/body offer) or minted exactly once, at
 // request start, before anything downstream consumes it.
 assert.equal((src.match(/const threadId=offered\|\|newThreadId\(\);/g)||[]).length,1);
 assert.match(src,/const minted=!offered;/);
 const iThread=src.indexOf('const threadId=offered||newThreadId();');
 const iIdentity=src.indexOf('bridgeIdentityForThread(secret,threadId)');
 const iAppend=src.indexOf('appendExchange(cfg,threadId,');
 assert.ok(iThread>=0&&iIdentity>iThread,'the bridge identity derives from the resolved thread id');
 assert.ok(iAppend>iThread,'the guestbook append keys off the same id');
 // The cookie the response carries out is that same id, so a first visit
 // (minted at start) stores its bridge thread under the identity the
 // cookied second visit presents.
 assert.match(src,/\$\{COOKIE\}=\$\{threadId\}/);
 assert.match(src,/continuity:\{thread_id:threadId,identity_source:'thread'/);
 // The bridge body still sends that one identity in both contract shapes.
 assert.match(src,/\{text,guest_identity:identity,context:bridgeContext\.context\}/);
 assert.match(src,/\{text,guest_identity:identity\}/);
 // No IP-derived identity remains in this route: the forwarded-IP headers
 // are not read here any more, and the HMAC lives in the store helper.
 assert.doesNotMatch(src,/x-vercel-forwarded-for|x-forwarded-for/);
 assert.doesNotMatch(src,/createHmac/);
});

test('the IP quota-bucket derivation survives only in /api/guest, with no thread wiring',()=>{
 const src=read('app/api/guest/route.ts');
 // The plain door's quota-bucket derivation is byte-identical to before:
 // an HMAC of the forwarded IP, sent to the bridge as guest_identity.
 assert.match(src,/x-vercel-forwarded-for/);
 assert.match(src,/createHmac\('sha256',secret\)\.update\(forwarded\.slice\(0,256\)\)\.digest\('hex'\)/);
 // And the forever fix did not leak into it: no thread identity, no
 // 'thread:' derivation, no store helper — no thread concept at all.
 assert.doesNotMatch(src,/bridgeIdentityForThread|thread/);
});
