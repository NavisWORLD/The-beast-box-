import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import ts from 'typescript';
import * as ownerModule from '../lib/cosmos/private-owner.mjs';
import * as memoryModule from '../lib/cosmos/private-memory.mjs';
import * as originModule from '../lib/cosmos/private-origin.mjs';
import {privateGrowthPlan,sealWorkerReceipt} from '../lib/cosmos/private-qvm.mjs';
import {runPrivateGrowth} from '../lib/cosmos/private-growth-worker.mjs';

// In-memory conditional Blob transport; no cloud credentials or workloads.
const secret='SYNTHETIC-RECOVERY-FIXTURE-'.repeat(3);
const at=Date.parse('2026-10-14T00:00:00Z');
function storage(){
 const rows=new Map();let n=0;
 return {rows,get:async p=>rows.has(p)?{...rows.get(p)}:null,
  list:async p=>[...rows.keys()].filter(k=>k.startsWith(p)),
  put:async(p,text,o={})=>{const old=rows.get(p);if(o.ifMatch&&old?.etag!==o.ifMatch||o.ifNoneMatch==='*'&&old)throw Object.assign(Error('CAS'),{status:412});const etag='"'+(++n)+'"';rows.set(p,{text,etag});return etag;},
  delete:async(p,o)=>{if(rows.get(p)?.etag!==o.ifMatch)throw Object.assign(Error('CAS'),{status:412});rows.delete(p);}};
}
async function fixture(){
 const io=storage(),store=new memoryModule.PrivateCosmos(io),credential=ownerModule.issueCredential(secret),owner=credential.subject,id='bb-12345678';
 const profile={schema:'cosmos-beast-public/v1',id,name:'Fixture',provenance:{kind:'classical-seeded-game-generation',seed:'recovery-fixture'},traits:{family:'VOID',stats:{energy:70,signal:50,resonance:60}}};
 await store.admit(owner);await store.create(owner,profile,'fixture-create');
 await store.update(owner,id,{kind:'growth-consent',enabled:true,schedule:true},'fixture-consent',1);
 return {io,store,credential,owner,id};
}
const provider=calls=>async plan=>{calls.push(plan);return {ok:true,target:plan.target,beast_id:plan.beast_id,job_name:plan.job_name,job_id:'SYNTHETIC-FIXTURE-JOB',shots:256,counts:{'000':128,'111':128}};};
const privateObjects=io=>[...io.rows.keys()].filter(p=>p.includes('/beasts/')&&!p.endsWith('/head.json'));

for(const operation of ['revoke','remove']){
 test(`a simulator ledger created after ${operation} is erased before the failed apply returns`,async()=>{
  const {io,store,owner,id}=await fixture(),row=await store.read(owner,id),plan=privateGrowthPlan(row.record,'fixture-ledger-race',{now:new Date(at).toISOString()});
  const receipt=sealWorkerReceipt(secret,plan,await provider([])(plan),{startedAt:new Date(at).toISOString(),completedAt:new Date(at+1000).toISOString()});
  const put=io.put;let race=true;
  io.put=async(p,...args)=>{if(p.includes('/simulation-receipts/')&&race){race=false;await store[operation](owner,id);}return put(p,...args);};
  await assert.rejects(store.applyQvm(owner,id,plan,receipt,plan.event_id,row.version,secret));
  assert.deepEqual(privateObjects(io),[]);
 });
 test(`initial reserved worker data created after ${operation} is erased without executing`,async()=>{
  const {io,store,owner,id}=await fixture(),put=io.put,calls=[];let race=true;
  io.put=async(p,...args)=>{if(p.includes('/growth-jobs/')&&race){race=false;await store[operation](owner,id);}return put(p,...args);};
  const report=await runPrivateGrowth(store,provider(calls),{now:at});
  assert.equal(report.canceled,1);assert.equal(calls.length,0);assert.deepEqual(privateObjects(io),[]);
 });
}

test('revoked owner erasure can resume after a transient conditional delete failure',async()=>{
 const {io,store,owner}=await fixture(),del=io.delete;let fail=true;
 io.delete=async(...args)=>{if(fail){fail=false;throw Error('synthetic delete transport failure');}return del(...args);};
 await assert.rejects(store.revoke(owner));await assert.rejects(store.assertOwner(owner));
 assert.equal((await store.ownerStatus(owner)).erasurePending,true);
 assert.equal((await store.revoke(owner)).revoked,true);assert.deepEqual(privateObjects(io),[]);
 assert.equal((await store.ownerStatus(owner)).erasurePending,false);
});

test('a failed late-write cleanup fences the final erasure-complete marker',async()=>{
 const {io,store,owner,id}=await fixture(),list=io.list,del=io.delete;let reads=0,race=true;
 const late=store.path(owner,id)+'/simulation-receipts/fixture-late.json';
 io.list=async prefix=>{const names=await list(prefix);if(prefix.endsWith('/beasts/')&&++reads===2&&race){race=false;
  await io.put(late,'{"synthetic":"late private receipt"}',{ifNoneMatch:'*'});
  io.delete=async(...args)=>{if(args[0]===late){io.delete=del;throw Error('synthetic late cleanup transport failure');}return del(...args);};
  await assert.rejects(store.cleanupIfClosed(owner,id,late));
 }return names;};
 await assert.rejects(store.revoke(owner));assert.equal((await store.ownerStatus(owner)).erasurePending,true);
 assert.equal((await store.revoke(owner)).revoked,true);assert.deepEqual(privateObjects(io),[]);
 assert.equal((await store.ownerStatus(owner)).erasurePending,false);
});

test('the scheduler resumes revoked-owner erasure after a fenced late cleanup fails',async()=>{
 const {io,store,owner}=await fixture(),put=io.put,del=io.delete,calls=[];let race=true;
 io.put=async(p,...args)=>{if(p.includes('/growth-jobs/')&&race){race=false;await store.revoke(owner);
  io.delete=async(...args)=>{io.delete=del;throw Error('synthetic late cleanup transport failure');};
 }return put(p,...args);};
 await runPrivateGrowth(store,provider(calls),{now:at});assert.equal((await store.ownerStatus(owner)).erasurePending,true);
 await runPrivateGrowth(store,provider(calls),{now:at+1000});assert.deepEqual(privateObjects(io),[]);
 assert.equal((await store.ownerStatus(owner)).erasurePending,false);assert.equal(calls.length,0);
});

test('revoked-owner sweeping removes a late object if its writer died before fencing',async()=>{
 const {io,store,owner,id}=await fixture(),calls=[];await store.revoke(owner);
 // A process can die after Azure accepts PUT but before the post-write fence.
 await io.put(store.path(owner,id)+'/growth-jobs/fixture-crashed-writer.json','{"synthetic":"late private work"}',{ifNoneMatch:'*'});
 assert.equal((await store.ownerStatus(owner)).erasurePending,false);
 await runPrivateGrowth(store,provider(calls),{now:at});assert.deepEqual(privateObjects(io),[]);assert.equal(calls.length,0);
});

test('deleted-creature sweeping removes a late object if its writer died before fencing',async()=>{
 const {io,store,owner,id}=await fixture(),calls=[];await store.remove(owner,id);
 await io.put(store.path(owner,id)+'/simulation-receipts/fixture-crashed-writer.json','{"synthetic":"late private receipt"}',{ifNoneMatch:'*'});
 await runPrivateGrowth(store,provider(calls),{now:at});assert.deepEqual(privateObjects(io),[]);assert.equal(calls.length,0);
 assert.equal((await store.ownerStatus(owner)).active,true);
});

test('an interrupted cleanup of a late first commit remains pending for scheduler erasure',async()=>{
 const {io,store,owner}=await fixture(),put=io.put,del=io.delete,calls=[];let race=true;
 const profile={schema:'cosmos-beast-public/v1',id:'bb-87654321',name:'Fixture',provenance:{kind:'classical-seeded-game-generation',seed:'late-create-fixture'},traits:{family:'VOID',stats:{energy:70}}};
 io.put=async(p,...args)=>{if(p.endsWith('/commits/fixture-late-create.json')&&race){race=false;await store.revoke(owner);
  io.delete=async(...args)=>{io.delete=del;throw Error('synthetic late commit cleanup failure');};
 }return put(p,...args);};
 await assert.rejects(store.create(owner,profile,'fixture-late-create'));
 assert.equal((await store.ownerStatus(owner)).erasurePending,true);
 await runPrivateGrowth(store,provider(calls),{now:at});assert.deepEqual(privateObjects(io),[]);assert.equal(calls.length,0);
});

test('a first-commit write with a lost response after erasure cleans its possible late object',async()=>{
 const {io,store,owner}=await fixture(),put=io.put;let race=true;
 const profile={schema:'cosmos-beast-public/v1',id:'bb-87654321',name:'Fixture',provenance:{kind:'classical-seeded-game-generation',seed:'late-create-fixture'},traits:{family:'VOID',stats:{energy:70}}};
 io.put=async(p,...args)=>{if(p.endsWith('/commits/fixture-late-create.json')&&race){race=false;await store.revoke(owner);await put(p,...args);throw Error('synthetic write response lost');}return put(p,...args);};
 await assert.rejects(store.create(owner,profile,'fixture-late-create'));assert.deepEqual(privateObjects(io),[]);
});

test('pending QVM receipt rebases over an owner interaction while preserving immutable history',async()=>{
 const {io,store,owner,id}=await fixture(),put=io.put,calls=[];let interrupt=true;
 io.put=async(p,...args)=>{if(p.endsWith('/head.json')&&interrupt){interrupt=false;throw Error('synthetic head transport failure');}return put(p,...args);};
 assert.equal((await runPrivateGrowth(store,provider(calls),{now:at})).pending,1);
 const candidate=[...io.rows].find(([p])=>p.includes('/commits/growth-'));
 const interaction=await store.update(owner,id,{kind:'memory',text:'ordinary owner interaction'},'fixture-interaction',2);
 const committed=await io.get(store.path(owner,id)+'/commits/fixture-interaction.json');
 assert.equal((await runPrivateGrowth(store,provider(calls),{now:at+1000})).completed,1);
 const result=await store.read(owner,id);assert.equal(calls.length,1);assert.equal(result.record.growth.tick,1);
 assert.deepEqual(result.record.memory.map(m=>m.text),['ordinary owner interaction']);
 assert.equal(result.record.simulationReceipts.length,1);assert.equal(result.version,interaction.version+1);
 assert.equal((await io.get(candidate[0])).text,candidate[1].text);
 assert.equal((await io.get(store.path(owner,id)+'/commits/fixture-interaction.json')).text,committed.text);
});

test('completed work reconciles an interrupted budget finalization without provider resubmission',async()=>{
 const {io,store,owner,id}=await fixture(),put=io.put,calls=[];let interrupt=true;
 io.put=async(p,text,...args)=>{if(p.endsWith('/growth-budget.json')&&Object.values(JSON.parse(text).creatures||{}).some(x=>x.phase==='COMPLETE')&&interrupt){interrupt=false;throw Error('synthetic budget transport failure');}return put(p,text,...args);};
 assert.equal((await runPrivateGrowth(store,provider(calls),{now:at})).pending,1);
 const retry=await runPrivateGrowth(store,provider(calls),{now:at+1000});assert.equal(retry.completed,1);assert.equal(retry.unknown,0);assert.equal(calls.length,1);
 assert.equal((await store.read(owner,id)).record.growth.tick,1);
 const later=await runPrivateGrowth(store,provider(calls),{now:at+86400001});assert.equal(later.completed,1);assert.equal(calls.length,2);
});

test('explicit possibly accepted provider submission remains unknown after 24 hours',async()=>{
 const {store,owner,id}=await fixture();let calls=0;
 const execute=async plan=>{calls++;return {ok:false,target:plan.target,beast_id:plan.beast_id,job_name:plan.job_name,shots:256,job_id:null,submission_unknown:true,private_execution:true,quil_sha256:plan.quil_sha256,input_hash:plan.input_hash,event_id:plan.event_id,tick:plan.tick,error:'ConnectionError: submission response lost'};};
 const first=await runPrivateGrowth(store,execute,{now:at});assert.equal(first.unknown,1);assert.equal(first.blocked,0);
 const later=await runPrivateGrowth(store,execute,{now:at+86400001});assert.equal(later.unknown,1);assert.equal(calls,1);
 assert.equal((await store.read(owner,id)).record.simulationReceipts.length,0);
});

function loadTs(path,dependencies,env){
 const source=readFileSync(new URL(path,import.meta.url),'utf8');
 const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
 const module={exports:{}};new Function('require','module','exports','process',code)(name=>{if(!(name in dependencies))throw Error('Unexpected module '+name);return dependencies[name];},module,module.exports,{env});return module.exports;
}
function sessionHarness({io,credential}){
 const deleted=[];let token=credential.token;
 const cookieModule={cookies:async()=>({get:name=>name===ownerModule.PRIVATE_COOKIE&&token?{value:token}:undefined,delete:name=>{deleted.push(name);token='';}})};
 const env={BEASTBOX_CLOUD_AUTH_SECRET:secret,NODE_ENV:'production'};
 const api=loadTs('../lib/cosmos/private-api.ts',{'next/headers':cookieModule,'./azure-blob.mjs':{storageConfig:()=>({synthetic:true})},'./private-owner.mjs':ownerModule,'./private-memory.mjs':{...memoryModule,azurePrivateIO:()=>io},'./private-origin.mjs':originModule},env);
 const session=loadTs('../app/api/cosmos/private/session/route.ts',{'next/headers':cookieModule,'@/lib/cosmos/private-api':api,'@/lib/cosmos/private-owner.mjs':ownerModule},env);
 const req=()=>new Request('https://fixture.invalid/api/cosmos/private/session',{method:'DELETE',headers:{origin:'https://fixture.invalid',host:'fixture.invalid','Content-Type':'application/json'},body:'{}'});
 return {api,session,deleted,req};
}
test('signed inactive session advertises pending erasure and can retry deletion without read authority',async()=>{
 const setup=await fixture(),{io,store,owner}=setup,{api,session,deleted,req}=sessionHarness(setup);
 const del=io.delete;let fail=true;io.delete=async(...args)=>{if(fail){fail=false;throw Error('synthetic delete transport failure');}return del(...args);};
 assert.equal((await session.DELETE(req())).status,502);assert.deepEqual(deleted,[]);
 const pending=await (await session.GET()).json();assert.equal(pending.authorized,false);assert.equal(pending.erasurePending,true);assert.equal(pending.revokeRequired,true);
 await assert.rejects(api.privateContext(),e=>e.status===403);
 assert.equal((await session.DELETE(req())).status,200);assert.deepEqual(deleted,[ownerModule.PRIVATE_COOKIE]);assert.deepEqual(privateObjects(io),[]);
 assert.equal((await store.ownerStatus(owner)).erasurePending,false);
});

test('a session metadata storage failure remains factual and does not clear the signed credential',async()=>{
 const setup=await fixture(),{session,deleted}=sessionHarness(setup);
 setup.io.get=async()=>{throw Object.assign(Error('synthetic storage unavailable'),{status:503,code:'ServerBusy'});};
 const response=await session.GET();assert.equal(response.status,503);assert.equal((await response.json()).status,'ServerBusy');assert.deepEqual(deleted,[]);
});
