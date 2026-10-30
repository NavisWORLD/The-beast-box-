import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {storageConfig} from '../lib/cosmos/azure-blob.mjs';
import {appendClassExchange,classThreadId,classroomBridgeIdentity,readClassThread,CLASSROOM_DIR} from '../lib/cosmos/classroom-store.mjs';
import {appendGuestEvent,bridgeIdentityForThread,exchangeId,GUESTBOOK_DIR} from '../lib/cosmos/forever-store.mjs';
import {confusedState,deriveEmotions,EMOTIONS} from '../lib/companion/emotion.mjs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
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
const AT='2026-10-29T21:00:00.000Z',SECRET='s'.repeat(40);
const withFake=async fn=>{const f=fakeBlobFetch();const real=globalThis.fetch;globalThis.fetch=f.fetch;try{await fn(f.blobs);}finally{globalThis.fetch=real;}};

test('classroom: owner gate on GET and POST before any work, polite page note for visitors',()=>{
 const route=read('app/api/classroom/route.ts');
 const gets=route.split('export async function');
 for(const fn of gets.slice(1))assert.match(fn.split('\n').slice(0,2).join('\n'),/if\(!\(await isOwner\(\)\)\)return safeJson\(403,NOT_OWNER\)/);
 const panel=read('components/classroom-panel.tsx');
 assert.match(panel,/fetch\('\/api\/session'/);
 assert.match(panel,/owner and his teachers only/);
 assert.ok(!/conscious|sentient|soul/i.test(panel),'no consciousness claims in UI copy');
 assert.match(panel,/Zeref&apos;s confused state/);assert.match(panel,/DERIVED/);
});

test('classroom: separate thread and bridge identity from the public door, same bridge path',()=>{
 const id=classThreadId('zeref-class');
 assert.match(id,/^[a-f0-9]{32}$/);assert.equal(id,classThreadId('zeref-class'));assert.notEqual(id,classThreadId('other'));
 assert.equal(classThreadId('Bad Name!'),null);
 assert.notEqual(classroomBridgeIdentity(SECRET,id),bridgeIdentityForThread(SECRET,id));
 const route=read('app/api/classroom/route.ts');
 assert.match(route,/'\/api\/guest-local'/);assert.match(route,/result\.step!==PIN_STEP/);
 assert.ok(!/Math\.random/.test(route+read('lib/cosmos/classroom-store.mjs')));
});

test('classroom: experience record written, text and numbers only, tagged, never counted twice',async()=>withFake(async blobs=>{
 const cfg=sasCfg();const id=classThreadId('zeref-class');
 const args={at:AT,teacherText:'Light rhymes with night.',reply:'Light, light.',topic:'rhyme',target:'night',drill:'miss',
  confused:confusedState({reply:'Light, light.',target:'night',drill:'miss'},{confused:true}),step:35184,checkpoint_sha256:'abc'};
 const w=await appendClassExchange(cfg,id,'zeref-class',args);
 assert.equal(w.persisted,true);assert.equal(w.recorded,true);assert.equal(w.duplicate,false);
 const again=await appendClassExchange(cfg,id,'zeref-class',args);
 assert.equal(again.duplicate,true);
 const lines=blobs.get(`${CLASSROOM_DIR}/experiences.jsonl`).text.trim().split('\n');
 assert.equal(lines.length,1);
 const rec=JSON.parse(lines[0]);
 assert.equal(rec.source_kind,'classroom');assert.equal(rec.reply,'Light, light.');assert.equal(rec.teacher_text,'Light rhymes with night.');
 assert.deepEqual(rec.drill,{target:'night',result:'miss'});assert.equal(rec.topic,'rhyme');
 assert.equal(rec.training_eligible,false);assert.equal(rec.media,'none');assert.equal(rec.confused.label,'DERIVED');
 assert.ok(!/audio|heartbeat|pulse/i.test(Object.keys(rec).join(',')));
 assert.equal((await readClassThread(cfg,id)).thread.turns.length,2);
 // never in the public guestbook, diary or lessons
 assert.ok(![...blobs.keys()].some(k=>k.startsWith(GUESTBOOK_DIR)||k.includes('/lessons/')||k.endsWith('diary.jsonl')));
}));

test('public records are tagged public and deduped by exchange_id',async()=>withFake(async blobs=>{
 const cfg=sasCfg();const x=exchangeId('public','t',AT,'hi','hello');
 const ev={at:AT,thread:'a'.repeat(32),step:1,checkpoint_sha256:'abc',guest_chars:2,reply_chars:5,exchange_id:x};
 await appendGuestEvent(cfg,ev);await appendGuestEvent(cfg,ev);
 const lines=blobs.get(`${GUESTBOOK_DIR}/events.jsonl`).text.trim().split('\n');
 assert.equal(lines.length,1);assert.equal(JSON.parse(lines[0]).source_kind,'public');
 assert.notEqual(x,exchangeId('classroom','t',AT,'hi','hello'));
}));

test('confused: opt-in, deterministic trigger, old emotions unchanged',()=>{
 assert.equal(confusedState({reply:'x',target:'night',drill:'miss'}),null,'off by default');
 assert.deepEqual(EMOTIONS,['joy','curiosity','fear','calm','mischief']);
 assert.ok(!('confused' in deriveEmotions({})));
 const on=o=>confusedState(o,{confused:true});
 assert.equal(on({reply:'Light and night.',target:'night',drill:'hit'}).active,false);
 assert.equal(on({reply:'Light and night.',target:'night',drill:'miss'}).active,true);
 assert.equal(on({reply:'Light, light.',target:'night'}).active,true);
 assert.equal(on({reply:'Nightly lights.',target:'night'}).active,true,'whole word only');
 assert.equal(on({reply:'NIGHT!',target:'Night'}).active,false);
 assert.deepEqual(on({reply:'a',target:'b',drill:'miss'}),on({reply:'a',target:'b',drill:'miss'}));
 assert.equal(on({reply:'a'}).label,'DERIVED');
});
