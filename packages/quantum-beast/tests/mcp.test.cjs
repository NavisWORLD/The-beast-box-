const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs/promises'),os=require('node:os'),path=require('node:path'),{spawn}=require('node:child_process');
const {createSnapshot,generateCreature}=require('../dist');const {FileStore}=require('../bin/file-store.cjs');
test('real stdio process negotiates tools and persists proposals without committing',async()=>{
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'beast-mcp-')),store=new FileStore(path.join(dir,'beast.qbeast'));
 await store.install(await createSnapshot(generateCreature('mcp-integration')));
 const child=spawn(process.execPath,[path.join(__dirname,'../bin/quantum-beast.cjs'),'mcp','--store',store.path]);
 let buffer='',serial=0;const pending=new Map();let stderr='';
 child.stderr.on('data',d=>stderr+=d);child.stdout.on('data',d=>{buffer+=d;while(buffer.includes('\n')){const at=buffer.indexOf('\n'),line=buffer.slice(0,at);buffer=buffer.slice(at+1);const reply=JSON.parse(line),resolve=pending.get(reply.id);if(resolve){pending.delete(reply.id);resolve(reply);}}});
 const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++serial;pending.set(id,resolve);child.stdin.write(JSON.stringify({jsonrpc:'2.0',id,method,params})+'\n');const timer=setTimeout(()=>reject(Error('MCP timeout '+stderr)),5000);timer.unref();});
 try{
  const premature=await call('tools/list');assert.equal(premature.error.code,-32000);
  const init=await call('initialize',{protocolVersion:'2025-11-25',capabilities:{},clientInfo:{name:'test-client',version:'1.0'}});assert.equal(init.result.protocolVersion,'2025-11-25');
  child.stdin.write(JSON.stringify({jsonrpc:'2.0',method:'notifications/initialized'})+'\n');
  const tools=await call('tools/list');assert.equal(tools.result.tools.length,9);
  const profile=await call('tools/call',{name:'beast_get_profile',arguments:{}});assert.equal(profile.result.structuredContent.result.seed,'mcp-integration');
  const proposal=await call('tools/call',{name:'beast_record_event',arguments:{summary:'MCP approved adventure proposal.',source_ref:'mcp:test'}});
  const p=proposal.result.structuredContent.result;assert.equal(p.status,'pending_host_approval');assert.deepEqual(await store.readProposal(p.proposal_id),p);assert.equal((await store.load()).events.length,0);
  const denied=await call('tools/call',{name:'beast_approve',arguments:{}});assert.equal(denied.result.isError,true);
  assert.equal(stderr,'');
 }finally{child.kill();await fs.rm(dir,{recursive:true,force:true});}
});
