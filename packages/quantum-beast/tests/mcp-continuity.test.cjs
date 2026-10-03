const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises'),os=require('node:os'),path=require('node:path');
const core=require('../dist'),{FileStore}=require('../bin/file-store.cjs');

test('failed MCP process creation rejects and completes cleanup',async()=>{
 const {McpClient}=require('../examples/mcp_client.cjs');
 const executable=process.execPath;let timer;
 process.execPath=path.join(os.tmpdir(),'qbeast-nonexistent-executable-'+process.pid);
 try{
  await assert.rejects(()=>Promise.race([
   McpClient.connect(path.join(os.tmpdir(),'qbeast-unused-store')),
   new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Failed spawn cleanup timed out')),1500);})
  ]),/ENOENT/);
 }finally{process.execPath=executable;clearTimeout(timer);}
});

test('independent MCP sessions observe only host-committed public outcomes',async()=>{
 const {McpClient}=require('../examples/mcp_client.cjs');
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'qbeast-continuity-'));
 const store=new FileStore(path.join(dir,'beast.qbeast'));
 const original=await core.parseSnapshot(await fs.readFile(path.join(__dirname,'../examples/unsigned-example.qbeast'),'utf8'));
 await store.install(original);
 let a,b,again;
 try{
  a=await McpClient.connect(store.path);
  const identity=await a.tool('beast_get_profile'),head=await a.tool('beast_get_lineage_head');
  const memories=await a.tool('beast_recall',{query:'adventure',limit:4});
  const proposal=await a.tool('beast_record_event',{summary:'Session A retrieved the approved adventure name Violet Grove.',source_ref:'test:actual-mcp-read'});
  assert.equal((await store.load()).lineage_head,head);
  await assert.rejects(()=>a.tool('beast_approve',{proposal_id:proposal.proposal_id}),/Unsupported model tool/);
  const approved=await core.approveProposal(await store.load(),await store.readProposal(proposal.proposal_id),{allow:['memory'],public_memory:true});
  await store.compareAndSwap(original.digest,approved);
  await store.removeApprovedProposal(proposal.proposal_id);
  await a.close();a=null;
  b=await McpClient.connect(store.path);
  assert.deepEqual(await b.tool('beast_get_profile'),identity);
  assert.equal(await b.tool('beast_get_lineage_head'),approved.lineage_head);
  assert.deepEqual((await b.tool('beast_recall',{query:'adventure',limit:4})).find(m=>m.event_hash===memories[0].event_hash),memories[0]);
  const pending=await b.tool('beast_propose_message',{text:'Violet Grove.'});
  assert.equal((await store.load()).digest,approved.digest);
  assert.equal((await store.readProposal(pending.proposal_id)).status,'pending_host_approval');
  await assert.rejects(()=>b.tool('beast_recall',{query:'adventure',limit:99}),/limit|recall/i);
  await b.close();b=null;
  again=await McpClient.connect(store.path);
  assert.deepEqual(await again.tool('beast_get_profile'),identity);
  assert.equal(await again.tool('beast_get_lineage_head'),approved.lineage_head);
  assert.equal((await again.tool('beast_verify')).integrity,true);
 }finally{
  await Promise.all([a?.close(),b?.close(),again?.close()]);
  await fs.rm(dir,{recursive:true,force:true});
 }
});
