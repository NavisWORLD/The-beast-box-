/** Receipts for the W5 archive claims. These tests do not raise a window and do not add a store. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {storageConfig} from '../lib/cosmos/azure-blob.mjs';
import {appendArchive,appendExchange,parseArchiveLines,readArchive,newThreadId,MAX_THREAD_TURNS,ARCHIVE_SCHEMA,GUESTBOOK_DIR} from '../lib/cosmos/forever-store.mjs';
import {appendClassExchange,classThreadId,readClassArchive,CLASSROOM_DIR,MAX_CLASS_TURNS} from '../lib/cosmos/classroom-store.mjs';
import {createSession,talk,exportSession,importSession} from '../lib/companion/session.mjs';
import {createBehavior,stepBehavior,feedbackBehavior} from '../lib/companion/behavior.mjs';
import {createLoop,runLoop,verifyMoments,KEEP_MOMENTS} from '../lib/loop/loop-chain.mjs';
import {writeTalkLog,readTalkLog,readTalkArchive,MAX_LOG} from '../lib/companion/beast-talk.mjs';
import {CompanionMemory} from '../lib/companion-local.mjs';
const sha=s=>createHash('sha256').update(s).digest('hex');
const AT='2026-11-09T18:40:00.000Z';
const sasCfg=()=>storageConfig({AZURE_STORAGE_CONTAINER_SAS_URL:'https://acct.blob.core.windows.net/beast-cosmos?sv=x&sig=y'});
function fakeBlobFetch(opts={}){
 const blobs=new Map();let n=0;
 return {blobs,fetch:async(url,{method,headers,body})=>{
  const u=new URL(url);const name=decodeURIComponent(u.pathname.split('/').slice(2).join('/'));
  const H=Object.fromEntries(Object.entries(headers).map(([k,v])=>[k.toLowerCase(),v]));
  if(method==='PUT'&&u.searchParams.get('restype')==='container')return new Response('',{status:201});
  if(method==='GET'&&u.searchParams.get('comp')==='list'){const pre=u.searchParams.get('prefix')||'';
   return new Response('<r>'+[...blobs.keys()].filter(k=>k.startsWith(pre)).sort().map(k=>`<Name>${k}</Name>`).join('')+'<NextMarker></NextMarker></r>');}
  const cur=blobs.get(name);
  if(method==='GET')return cur?new Response(cur.text,{headers:{etag:cur.etag}}):new Response('',{status:404});
  if(opts.crashOn&&opts.crashOn(name,method))throw Error('crash mid-append');
  if(H['if-none-match']==='*'&&cur)return new Response('<Code>BlobAlreadyExists</Code>',{status:409});
  if(H['if-match']&&(!cur||cur.etag!==H['if-match']))return new Response('<Code>ConditionNotMet</Code>',{status:412});
  const etag='"e'+(++n)+'"';blobs.set(name,{text:String(body??''),etag});return new Response('',{status:201,headers:{etag}});
 }};
}
const withFake=async(opts,fn)=>{const f=fakeBlobFetch(opts);const real=globalThis.fetch;globalThis.fetch=f.fetch;try{await fn(f.blobs);}finally{globalThis.fetch=real;}};

test('a torn archive tail is ignored and the complete prefix keeps order, provenance and hashes',()=>{
 const id=newThreadId();
 const line=(text,at)=>JSON.stringify({schema:ARCHIVE_SCHEMA,thread:id,origin:'guest',source_kind:'public',training_eligible:false,at,from:'guest',text});
 const body=[line('first',AT),line('second',AT)].join('\n')+'\n{"schema":"beastbook-guest-thread-archive/v1","text":"torn';
 const once=parseArchiveLines(body,id);
 const twice=parseArchiveLines(body,id);
 assert.deepEqual(once.map(r=>r.text),['first','second']);
 assert.equal(once[0].origin,'guest');
 assert.equal(once[0].training_eligible,false);
 assert.equal(sha(JSON.stringify(once)),sha(JSON.stringify(twice)));
 assert.equal(sha(body.split('\n')[0]),sha(line('first',AT)));
});

test('the 40-turn window is not the retention boundary, and a failed append leaves the previous archive',async()=>{
 const id=newThreadId();
 await withFake({},async blobs=>{
  const cfg=sasCfg();
  for(let i=0;i<45;i++){
   const at=new Date(Date.parse(AT)+i*1000).toISOString();
   await appendExchange(cfg,id,{guestText:'guest '+i,reply:'reply '+i,step:37104,at});
   await appendArchive(cfg,id,{guestText:'guest '+i,reply:'reply '+i,step:37104,at,exchange_id:String(i).padStart(64,'a')});
  }
  const name=`${GUESTBOOK_DIR}/archive/${id}.jsonl`;
  const before=blobs.get(name).text;
  const all=await readArchive(cfg,id);
  assert.equal(all.length,90);
  assert.equal(all[0].text,'guest 0');
  assert.equal(all.at(-1).text,'reply 44');
  assert.equal(JSON.parse(blobs.get(`${GUESTBOOK_DIR}/threads/${id}.json`).text).turns.length,MAX_THREAD_TURNS);
  const again=await readArchive(cfg,id);
  assert.equal(sha(JSON.stringify(all)),sha(JSON.stringify(again)));
  assert.equal(before,blobs.get(name).text);
 });
 let seenArchivePut=false;
 await withFake({crashOn:(name,method)=>{
  if(!(method==='PUT'&&name.includes('/archive/')))return false;
  if(!seenArchivePut){seenArchivePut=true;return false;}
  return true;
 }},async blobs=>{
  const cfg=sasCfg();const id2=newThreadId();
  await appendArchive(cfg,id2,{guestText:'kept',reply:'kept reply',step:37104,at:AT,exchange_id:'b'.repeat(64)});
  const name=`${GUESTBOOK_DIR}/archive/${id2}.jsonl`;
  const kept=blobs.get(name).text;
  await assert.rejects(appendArchive(cfg,id2,{guestText:'lost',reply:'lost reply',step:37104,at:AT,exchange_id:'c'.repeat(64)}));
  assert.equal(blobs.get(name).text,kept);
  assert.deepEqual((await readArchive(cfg,id2)).map(r=>r.text),['kept','kept reply']);
 });
});

test('classroom archive keeps the unclipped teacher and reply; the thread window stays 40 turns',async()=>{
 await withFake({},async()=>{
  const cfg=sasCfg();const id=classThreadId('grove-class');
  const teacher='T'.repeat(1500);const reply='R'.repeat(1500);
  assert.ok(teacher.length>1200&&reply.length>1200);
  const wrote=await appendClassExchange(cfg,id,'grove-class',{at:AT,teacherText:teacher,reply,step:37104});
  assert.equal(wrote.recorded,true);
  assert.equal(wrote.record.teacher_text.length,1200);
  const all=await readClassArchive(cfg);
  assert.equal(all.length,1);
  assert.equal(all[0].teacher_text_full,teacher);
  assert.equal(all[0].reply_full,reply);
  assert.equal(all[0].teacher_text.length,1200);
  assert.equal(all[0].training_eligible,false);
  const {readClassThread}=await import('../lib/cosmos/classroom-store.mjs');
  const stored=await readClassThread(cfg,id);
  assert.equal(stored.thread.turns.length,2);
  assert.ok(stored.thread.turns.length<=MAX_CLASS_TURNS);
  assert.equal(stored.thread.turns[0].text.length,1200);
 });
});

test('session chat and behavior archives survive an export and a fresh import',()=>{
 const session=createSession();
 const said='marigold '.repeat(80);
 talk(session,said);
 assert.ok(said.length>400);
 assert.equal(session.chatArchive.at(-2).text,said);
 assert.equal(session.chat.at(-2).text,said.slice(0,400));
 const raw=exportSession(session);
 const restarted=importSession(raw);
 assert.equal(restarted.chatArchive.at(-2).text,said);
 assert.equal(restarted.chat.length,session.chat.length);
 const beast={seed:'ab'.repeat(16),energy:90,genome:{seed:'ab'.repeat(16),inputs:{traits:{spark:50,focus:50}}}};
 let state=createBehavior(beast);
 for(let i=0;i<40;i++)state=stepBehavior(state,beast,{place:i%2?'shore':'grove'}).state;
 state=feedbackBehavior(state,beast,{place:'grove',reward:1,kind:'keeper-encouragement-that-is-longer-than-thirty-two'});
 assert.equal(state.events.length,32);
 assert.equal(state.eventsArchive.length,40);
 assert.equal(state.eventsArchive[0].tick,0);
 assert.equal(state.events.at(-1).tick,39);
 assert.equal(state.memory.length,1);
 assert.equal(state.memory[0].kind.length,32);
 assert.ok(state.memoryArchive[0].kind_full.length>32);
 assert.equal(JSON.stringify(state.memory[0].kind_full),undefined);
});

test('talk log, loop moments and the untouched proposal caps',()=>{
 const mem=new Map();const storage={getItem:k=>mem.get(k)??null,setItem:(k,v)=>mem.set(k,v)};
 const rows=Array.from({length:30},(_,i)=>({role:i%2?'beast':'you',text:'line '+i,at:AT}));
 assert.equal(writeTalkLog(storage,'spark:z',rows),true);
 assert.equal(readTalkLog(storage,'spark:z').length,MAX_LOG);
 assert.equal(readTalkArchive(storage,'spark:z').length,30);
 assert.equal(readTalkArchive(storage,'spark:z')[0].text,'line 0');
 const before=mem.get('beastbox-talk-log-archive-v1:spark:z');
 storage.setItem=()=>{throw Error('quota');};
 assert.equal(writeTalkLog(storage,'spark:z',[{role:'you',text:'not stored'}]),false);
 assert.equal(mem.get('beastbox-talk-log-archive-v1:spark:z'),before);
 const loop=runLoop(createLoop({seed:'cd'.repeat(32)}),800);
 assert.ok(loop.moments_total>KEEP_MOMENTS);
 assert.equal(loop.moments.length,KEEP_MOMENTS);
 assert.equal(loop.moment_archive.length,loop.moments_total);
 assert.equal(verifyMoments(loop.moment_archive).ok,true);
 assert.equal(loop.moment_archive[0].prev_hash!==undefined,true);
 const restored=JSON.parse(JSON.stringify(loop));
 assert.equal(verifyMoments(restored.moment_archive).ok,true);
 assert.equal(createLoop({seed:'cd'.repeat(32)}).moment_archive,undefined);
 const diary=readFileSync(new URL('../lib/zeref/zeref-diary.mjs',import.meta.url),'utf8');
 const sync=readFileSync(new URL('../scripts/zeref-cloud-sync.mjs',import.meta.url),'utf8');
 assert.match(diary,/slice\(0,280\)/);
 assert.match(sync,/slice\(-1500\)/);
 assert.match(sync,/slice\(-400\)/);
});

test('companion memory search window is not the record',()=>{
 const memory=new CompanionMemory();
 for(let i=0;i<205;i++)memory.add('grove note number '+i,'note','keeper');
 assert.equal(memory.records.length,205);
 assert.equal(memory.search('grove',4).length,4);
 assert.equal(memory.records[0].text,'grove note number 0');
 assert.equal(memory.records[0].id,new CompanionMemory(memory.records).records[0].id);
});

test('pocket combo archive keeps every combo while the display stays at 60',async()=>{
 const mem=new Map();
 globalThis.window={localStorage:{getItem:k=>mem.get(k)??null,setItem:(k,v)=>mem.set(k,v)},dispatchEvent(){}};
 const {recordCombo,readJournal}=await import('../lib/zeref/pocket-journal.ts');
 for(let i=0;i<61;i++)assert.equal(recordCombo('bb-deada969',{key:'k'+i,name:'combo '+i}),true);
 const j=readJournal('bb-deada969');
 assert.equal(j.combos.length,60);
 assert.equal(j.combosArchive.length,61);
 assert.equal(j.keys.length,61);
 assert.equal(j.combosArchive.at(-1).key,'k0');
 assert.equal(j.combos[0].key,'k60');
});
