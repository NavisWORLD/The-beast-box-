import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {ZEREF_PROFILE,createMind,stepMind,recordedSeed} from '../lib/zeref/zeref-mind.mjs';
import {createPocket,stepPocket,attachLearner,callBeast,setSenses} from '../lib/zeref/zeref-pocket.mjs';
import {createLearner,restoreLearner,learningSummary,enterCell,chooseGoal,goalUtilities,riftCells,cellOf,perceive} from '../lib/zeref/pocket-learner.mjs';
import {genesisForBeast,genesisState,stepDiary,verifyChain,planGrowthCircuit} from '../lib/zeref/zeref-diary.mjs';
import {validatePublicProfile,publicProfileFromCreature,publicProfileFromBeast,cosmosIdFor} from '../public/spark/cosmos-profile.mjs';
import {storageConfig} from '../lib/cosmos/azure-blob.mjs';
import {registerBeast,readBeast,planBatch,applyBatch} from '../lib/cosmos/cosmos-store.mjs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const digest=recordedSeed().digest;

function live(L,seconds,{call=-1,sound=null}={}){
 const m=createMind({profile:ZEREF_PROFILE,hour:14});const p=attachLearner(createPocket({digest,key:ZEREF_PROFILE.id}),L);
 if(sound)setSenses(p,{sound});
 const ev=[];
 for(let i=0;i<seconds*10;i++){stepMind(m,.1,{hour:14});if(i===call)callBeast(p);for(const e of stepPocket(p,m,.1))ev.push({...e,t:i});}
 return {p,ev};
}

test('no leash: the beast picks its own goals and learns measurably from outcomes',()=>{
 const L=createLearner();
 const a=live(L,90);
 const goals=new Set(a.ev.filter(e=>e.type==='decide').map(e=>e.goal));
 assert.ok(goals.size>=2,'chooses among several goals on its own: '+[...goals]);
 assert.ok(!a.ev.some(e=>e.type==='came'),'never comes over unless called');
 const s1=learningSummary(L,a.p.pois);
 assert.ok(s1.cells_visited>4,'explores new patches');
 for(let i=0;i<3;i++)live(L,90);
 const s2=learningSummary(L,a.p.pois);
 assert.ok(s2.cells_visited>=s1.cells_visited,'novelty map persists and grows');
 assert.ok(s2.moves_succeeded>s1.moves_succeeded);
 assert.ok(s2.known_rifts>=1&&s2.moves_blocked>=s2.known_rifts,'bumped into rifts and remembered them');
 // remembered rifts are never chosen as explore targets again
 const p=attachLearner(createPocket({digest,key:ZEREF_PROFILE.id}),L);const m=createMind({profile:ZEREF_PROFILE,hour:14});
 let r=1;const rand=()=>{r=(r*16807)%2147483647;return r/2147483647;};
 for(let i=0;i<60;i++){const g=chooseGoal(L,p,m,rand);if(g.target?.kind==='cell')assert.ok(!L.known_blocked.includes(Number(g.target.id.slice(5))));}
 // deterministic replay
 const L2=createLearner(),L3=createLearner();live(L2,60);live(L3,60);assert.deepEqual(L2,L3);
});

test('called or tapped: it comes over; a persisted learner is repaired, not trusted',()=>{
 const {ev}=live(createLearner(),40,{call:150});
 const came=ev.find(e=>e.type==='came');
 assert.ok(came&&came.t>150,'came to the user after being called');
 const bad=restoreLearner({schema:'pocket-learner/v1',cells:'x',known_blocked:[999,-1,3],moves:{succeeded:-5},prefs:{explore:99},value:{'__proto__':1,'portal-6':5}});
 assert.equal(bad.cells.length,40);assert.deepEqual(bad.known_blocked,[3]);assert.equal(bad.moves.succeeded,0);assert.equal(bad.prefs.explore,1);assert.equal(bad.value['portal-6'],1);
 const L=createLearner();assert.deepEqual(enterCell(L,5,[5]),{outcome:'blocked',fresh:false});assert.deepEqual(enterCell(L,6,[5]),{outcome:'ok',fresh:true});
 const pk=createPocket({digest,key:'k'});for(const c of riftCells(pk.pois,'k'))assert.ok(!pk.pois.some(o=>cellOf(o.x,o.y)===c),'rifts never sit on a place');
});

test('senses: works without the mic; loudness only shifts goals when the user enabled it',()=>{
 const p=createPocket({digest,key:'s'}),m=createMind({profile:ZEREF_PROFILE,hour:14}),L=createLearner();
 assert.equal(perceive(p).sound,null);assert.equal(perceive(p,{sound:{active:false,level:.9}}).sound,null);
 const quiet=goalUtilities(L,p,m,perceive(p)),loud=goalUtilities(L,p,m,perceive(p,{sound:{active:true,level:.2}}));
 assert.ok(loud.explore>quiet.explore&&loud.rest<quiet.rest);
 assert.equal(perceive(p,{others:[{id:'bb-1',x:.1,y:.1}]}).beasts.length,1);
 const src=read('components/pocket-learning-card.tsx');
 assert.match(src,/getUserMedia/);assert.match(src,/aria-pressed=\{hearing\}/);assert.match(src,/not consciousness/);
 assert.doesNotMatch(src,/fetch\(/,'mic level never leaves the browser');
});

test('diary ticks log measurable learning; Zeref identity unchanged',()=>{
 const g=genesisState();
 const a=stepDiary(g,{now:'2026-10-12T00:07:00Z'}),b=stepDiary(a.state,{now:'2026-10-12T00:37:00Z'});
 assert.deepEqual(b.state.identity,g.identity);
 for(const e of [a.entry,b.entry]){assert.ok(e.learning.cells_visited>0);assert.match(e.learning.label,/not consciousness/);assert.ok(Number.isInteger(e.learning.moves_blocked));}
 assert.ok(b.entry.learning.cells_visited>=a.entry.learning.cells_visited,'learner persists between ticks');
 assert.equal(verifyChain([a.entry,b.entry],g.identity).ok,true);
});

const creature={id:'bb-12345678',name:'Budpaw',seed:'life-engine-art-acceptance',family:'aurora',baseLook:'aurora',appearance:{hueShift:4,glow:.5},game:{stats:{energy:70,signal:60,memory:50,resonance:55}}};
test('public profile: allowlist only; chats, memory and keeper names are dropped',()=>{
 const pub=publicProfileFromCreature(creature);
 const v=validatePublicProfile({...pub,chat:['hi'],owner_memory:'x',traits:{...pub.traits,user_id:'cory'}});
 assert.equal(v.ok,true);assert.deepEqual(Object.keys(v.profile).sort(),['id','name','provenance','schema','traits']);
 assert.ok(!JSON.stringify(v.profile).includes('cory')&&!JSON.stringify(v.profile).includes('owner_memory'));
 assert.equal(validatePublicProfile({...pub,id:'../etc'}).ok,false);
 assert.equal(validatePublicProfile({...pub,name:'me@mail.com'}).ok,false);
 assert.equal(validatePublicProfile({...pub,provenance:{kind:'classical-seeded-game-generation',seed:'token=abc'}}).ok,false);
 assert.equal(validatePublicProfile({...pub,traits:{}}).ok,false,'needs stats');
 const beast={displayName:'Zeref',qbeast:{profile:{id:'bb-7f9c2a03'}},genome:{seed:'a'.repeat(64),island:'ember',element:'fire',body:'drake',stats:{energy:80,signal:70},
  inputs:{user_id:'Cory'},quantum:{backend:'ibm_fez',job_id:'d1abcdefgh',counts_sha256:'b'.repeat(64),marginals:[.4,.6],entropy_norm:.7},voice:{x:1}}};
 const bp=publicProfileFromBeast(beast);const bv=validatePublicProfile(bp);
 assert.equal(bv.ok,true);assert.ok(!JSON.stringify(bv.profile).includes('Cory'));assert.equal(bv.profile.provenance.backend,'ibm_fez');
 assert.equal(cosmosIdFor('seed:'+'c'.repeat(64)),'seed-'+'c'.repeat(24));
 const gb=genesisForBeast(pub);assert.equal(gb.identity.beast_id,'bb-12345678');assert.ok(gb.identity.seed_features);
 assert.equal(planGrowthCircuit(gb).job_name,'beast-growth-tick-1-bb-12345678');
 assert.deepEqual(genesisForBeast({...pub,id:'bb-7f9c2a03'}).identity,genesisState().identity,'Zeref keeps his identity');
});

// In-memory stand-in for the Blob REST API (create-only, etags, list).
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

test('cosmos store: per-beast folders, create-only identity, round-robin batches, honest fallback',async()=>{
 const {blobs,fetch}=fakeBlobFetch();const real=globalThis.fetch;globalThis.fetch=fetch;
 try{
  const cfg=storageConfig({AZURE_STORAGE_CONTAINER_SAS_URL:'https://acct.blob.core.windows.net/beast-cosmos?sv=x&sig=y'});
  assert.equal(storageConfig({}),null,'no secret -> storage not configured');
  const pub=publicProfileFromCreature(creature);
  assert.equal((await registerBeast(cfg,pub)).status,201);
  assert.equal((await registerBeast(cfg,{...pub,name:'Hijack'})).already,true,'existing folder is never overwritten');
  assert.match(blobs.get('beasts/bb-12345678/profile.json').text,/Budpaw/);
  assert.equal((await registerBeast(cfg,{bad:1})).status,400);
  for(const id of ['bb-aaaaaaa1','bb-aaaaaaa2'])await registerBeast(cfg,publicProfileFromCreature({...creature,id}));
  const p1=await planBatch(cfg,{batch:2});
  assert.deepEqual(p1.plans.map(p=>p.beast_id),['bb-12345678','bb-aaaaaaa1']);
  const counts={'000':128,'111':128};
  const done=await applyBatch(cfg,p1,[{ok:true,target:'rigetti.sim.qvm',job_id:'j1',job_name:p1.plans[0].job_name,shots:256,counts}]);
  assert.equal(done[0].growth,'rigetti-qvm-simulated');assert.equal(done[1].growth,'deterministic-fallback');
  const p2=await planBatch(cfg,{batch:2});
  assert.deepEqual(p2.plans.map(p=>p.beast_id),['bb-aaaaaaa2','bb-12345678'],'round-robin continues');
  await applyBatch(cfg,p2,[]);
  const r=await readBeast(cfg,'bb-12345678');
  assert.equal(r.diary.tick,2);assert.equal(r.diary.recent[0].growth_source.kind,'deterministic-fallback');
  assert.match(r.diary.recent[0].growth_source.error,/no receipt/);
  const log=blobs.get('beasts/bb-12345678/diary.jsonl').text.trim().split('\n').map(l=>JSON.parse(l));
  assert.equal(verifyChain(log,JSON.parse(blobs.get('beasts/bb-12345678/state.json').text).identity).ok,true);
  assert.ok(blobs.has('beasts/bb-12345678/runs/000001.json'));
 }finally{globalThis.fetch=real;}
});

test('workflow: per-beast steps use storage secrets only as env; quantum secret only in the simulator step',()=>{
 const wf=read('../../.github/workflows/zeref-diary-loop.yml');
 assert.equal((wf.match(/secrets\.AZURE_QUANTUM_CONNECTION_STRING/g)||[]).length,1);
 assert.match(wf,/cosmos-grow\.mjs plan/);assert.match(wf,/cosmos-grow\.mjs apply/);
 assert.doesNotMatch(wf,/echo .*AZURE_/);
 const route=read('app/api/cosmos/beasts/route.ts');
 assert.match(route,/limited\(ip\)/);assert.match(route,/registerBeast/);assert.match(route,/Cross-site/);
});
