const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs/promises'),os=require('node:os'),path=require('node:path');
const {createSnapshot,generateCreature,BeastBridge,approveProposal}=require('../dist');
const {FileStore}=require('../bin/file-store.cjs');
const {toolDefinitions,callTool,openaiTools}=require('../dist/tools.js');
test('persistent store rejects stale writes, interruption artifacts and symlinks',async()=>{
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'qbeast-test-'));
 try{
  const initial=await createSnapshot(generateCreature('persistent-test')),store=new FileStore(path.join(dir,'beast.qbeast'));
  await store.install(initial);const one=await store.load(),two=await store.load();
  const bridge=await BeastBridge.load(one),p=await bridge.record_event({summary:'Approved public memory.',source_ref:'test:1'});
  const next=await approveProposal(one,p,{allow:['memory'],public_memory:true});
  await store.compareAndSwap(one.digest,next);await assert.rejects(()=>store.compareAndSwap(two.digest,next));
  const other=await createSnapshot(generateCreature('different-creature'));await assert.rejects(()=>store.compareAndSwap(next.digest,other));
  const rewind=await createSnapshot(generateCreature('persistent-test'));await assert.rejects(()=>store.compareAndSwap(next.digest,rewind));
  await fs.writeFile(path.join(dir,'.beast.qbeast.interrupted'),'garbage');assert.deepEqual(await store.load(),next);
  await assert.rejects(()=>store.install(initial));
  const link=path.join(dir,'symlink.qbeast');await fs.symlink(store.path,link);await assert.rejects(()=>new FileStore(link).load());
  const fake=path.join(dir,'proposals');await fs.mkdir(fake);await fs.symlink(store.path,path.join(fake,p.proposal_id+'.json'));
  await assert.rejects(()=>store.writeProposal(p));
 }finally{await fs.rm(dir,{recursive:true,force:true});}
});
test('model tool surface excludes host grants, filesystem and network and rejects extra arguments',async()=>{
 const b=await BeastBridge.load(await createSnapshot(generateCreature('tool-test')));
 const names=toolDefinitions().map(t=>t.name);assert.equal(names.length,9);assert.ok(!names.some(n=>/approve|commit|sensor|network/i.test(n)));
 assert.equal(openaiTools().length,9);
 const p=await callTool(b,'beast_record_event',{summary:'A public adventure.',source_ref:'test:2'});assert.equal(p.status,'pending_host_approval');
 await assert.rejects(()=>callTool(b,'beast_approve',{grant:'all'}));
 await assert.rejects(()=>callTool(b,'beast_get_profile',{creature_id:'some-other-beast'}));
 await assert.rejects(()=>callTool(b,'beast_recall',{query:'adventure',limit:999}));
 assert.equal(b.snapshot().events.length,0);
});
test('pending model proposals have a locked bounded queue; host approval frees space',async()=>{
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'qbeast-quota-'));
 try{
  const state=await createSnapshot(generateCreature('quota-test')),store=new FileStore(path.join(dir,'beast.qbeast'));await store.install(state);const b=await BeastBridge.load(state);let first;
  for(let i=0;i<64;i++){const p=await b.propose_message('Public proposal '+i);if(i===0)first=p;await store.writeProposal(p);}
  const overflow=await b.propose_message('Quota overflow');await assert.rejects(()=>store.writeProposal(overflow),/quota/);
  const next=await approveProposal(state,first,{allow:['message'],public_memory:true});await store.compareAndSwap(state.digest,next);await store.removeApprovedProposal(first.proposal_id);
  await store.writeProposal(await (await BeastBridge.load(next)).propose_message('New public proposal'));assert.equal((await fs.readdir(path.join(dir,'proposals'))).length,64);
  assert.equal((await store.load()).generation,1);
 }finally{await fs.rm(dir,{recursive:true,force:true});}
});
