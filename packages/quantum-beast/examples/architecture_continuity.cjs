/** Genuine RAWRPHOS -> SmolLM2/Llama -> RAWRPHOS through separate MCP sessions.
 * Host-directed calls are explicit; this does not claim autonomous tool use.
 * Every raw model reply is retained, including rejected/off-topic replies.
 */
const fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const {spawnSync}=require('node:child_process'),{createHash}=require('node:crypto');
const core=require('../dist'),{FileStore}=require('../bin/file-store.cjs'),{McpClient}=require('./mcp_client.cjs');
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const A_HASH='4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5';
const ANCHOR='a1b16ea7518653d9b790f8af327945016f156fd6cc8a4ee9bbf2aaa86f54ea70';

async function main(){
 const args=process.argv.slice(2);
 const flag=name=>{const i=args.indexOf('--'+name);if(i<0||!args[i+1])throw Error('Required --'+name);return path.resolve(args[i+1]);};
 const repo=flag('beastbox-root'),aPath=flag('model-a'),bPath=flag('model-b'),python=flag('python'),out=flag('output');
 // Fresh isolated demo output; never overwrite another demo or owner save.
 await fs.mkdir(out,{mode:0o700});
 const source=await fs.readFile(path.join(__dirname,'beast.qbeast'),'utf8');
 const original=await core.parseSnapshot(source,{trustedPublicKey:ANCHOR});
 const sourceVerification=await core.verifySnapshot(original,{trustedPublicKey:ANCHOR});
 const signer=await core.createSigningKey(),options={trustedPublicKey:signer.publicKey};
 const store=new FileStore(path.join(out,'beast.qbeast'),options);
 let state=await core.signSnapshot(original,signer.privateKey,signer.publicKey);
 assert.equal(state.digest,original.digest);await store.install(state);
 const identity=structuredClone(state.profile),protectedState={public_state:state.public_state,progress:state.progress};
 const receipt={schema:'qbeast-mcp-architecture-continuity-v1',creature_id:identity.id,
  source:{file_sha256:sha(source),digest:original.digest,lineage_head:original.lineage_head,generation:original.generation,verification:sourceVerification},
  demo_host:{public_key:signer.publicKey,note:'Independent isolated demo host verified the pinned source, then attested the same content. This is not owner-key rotation; private keys are not saved.'},
  turns:[],host_receipts:[],mcp_sessions:[],paid_api_calls:0,training_performed:false,network_inference:false,
  orchestration:'Host-directed MCP calls, local inference, separate host approval; not autonomous model tool planning',
  not_proven:['hosted inference from two paid providers','general recall reliability','autonomous tool choice','quantum hardware','physical GBA/iPhone acceptance','full game campaign']};
 const write=()=>fs.writeFile(path.join(out,'continuity.json'),JSON.stringify(receipt,null,2)+'\n');
 let client;
 const connect=async label=>{client=await McpClient.connect(store.path,options);client.label=label;const tools=await client.request('tools/list');assert.equal(tools.tools.length,9);assert.ok(!tools.tools.some(t=>t.name.includes('approve')));};
 const close=async()=>{if(!client)return;const current=client;client=null;const exit=await current.close();receipt.mcp_sessions.push({label:current.label,exit,transcript:current.transcript});await write();};
 const context=async user=>{
  const profile=await client.tool('beast_get_profile');assert.deepEqual(profile,identity);
  const memories=await client.tool('beast_recall',{query:'adventure',limit:4});
  return {creature_id:profile.id,name:profile.name,family:profile.family,memories,user};
 };
 const infer=(brain,context)=>{
  const driver=path.join(__dirname,brain==='A'?'native_model.py':'public_model.py');
  const input=JSON.stringify(context),driverArgs=brain==='A'?[driver,repo,aPath,A_HASH,input]:[driver,bPath,input];
  // The optional inference process gets public data and ordinary local runtime
  // settings, with no inherited owner/provider credentials.
  const env={PATH:process.env.PATH,PYTHONNOUSERSITE:'1',HF_HUB_OFFLINE:'1',TRANSFORMERS_OFFLINE:'1',HF_HUB_DISABLE_TELEMETRY:'1'};
  const result=spawnSync(python,driverArgs,{encoding:'utf8',env,timeout:60000,maxBuffer:1000000});
  if(result.status!==0)throw Error(result.stderr||'Local inference failed');
  return {...JSON.parse(result.stdout),driver_sha256:null,context,context_sha256:sha(input),stderr:result.stderr};
 };
 const approve=async(proposal,reason)=>{
  const before=await store.load();assert.equal(proposal.expected_head,before.lineage_head);
  assert.deepEqual(await store.readProposal(proposal.proposal_id),proposal);
  const next=await core.approveProposal(before,proposal,{allow:[proposal.kind],public_memory:true},options);
  state=await core.signSnapshot(next,signer.privateKey,signer.publicKey);
  await store.compareAndSwap(before.digest,state);await store.removeApprovedProposal(proposal.proposal_id);
  receipt.host_receipts.push({decision:'approved',reason,proposal_id:proposal.proposal_id,kind:proposal.kind,previous_head:before.lineage_head,lineage_head:state.lineage_head,digest:state.digest,generation:state.generation});
  await write();
 };
 const reviewMessage=async(turn)=>{
  const before=await store.load(),proposal=await client.tool('beast_propose_message',{text:turn.output});
  assert.equal((await store.load()).digest,before.digest);
  turn.pending_proposal_id=proposal.proposal_id;
  // Demo host permits exactly the name in the independently verified original
  // approved memory. It never repairs/substitutes a model's generated output.
  if(/^Violet Grove[.!]?$/i.test(turn.output.trim())){
   await approve(proposal,'Exact generated adventure name matches the approved source memory');turn.host_decision='approved';
  }else{
   await store.removeApprovedProposal(proposal.proposal_id);turn.host_decision='rejected';
   receipt.host_receipts.push({decision:'rejected',reason:'Generated reply did not match this bounded recall task',proposal_id:proposal.proposal_id,lineage_head:before.lineage_head,digest:before.digest,generation:before.generation});
  }
  await write();
 };
 try{
  await connect('A: RAWRPHOS-native');
  const initialState=await client.tool('beast_get_state');
  const aContext=await context('What did we name our next adventure? Answer only with the adventure name.');
  assert.equal(aContext.memories.find(m=>m.event_hash===original.lineage_head)?.summary,'We named our next adventure Violet Grove.');
  const a=infer('A',aContext);a.driver_sha256=sha(await fs.readFile(path.join(__dirname,'native_model.py')));receipt.turns.push({label:'A',...a});
  await reviewMessage(receipt.turns.at(-1));
  const proposal=await client.tool('beast_record_event',{summary:'Session A retrieved the approved adventure name Violet Grove.',source_ref:'demo:actual-mcp-a-recall'});
  await approve(proposal,'Actual MCP read returned the previously approved source event; public demo observation');
  await close();

  await connect('B: Transformers/SmolLM2-Llama');
  const bContext=await context('What did we name our next adventure? Answer only with the adventure name.');
  assert.deepEqual(bContext.memories.find(m=>m.event_hash===original.lineage_head),aContext.memories.find(m=>m.event_hash===original.lineage_head));
  const b=infer('B',bContext);b.driver_sha256=sha(await fs.readFile(path.join(__dirname,'public_model.py')));receipt.turns.push({label:'B',...b});
  await reviewMessage(receipt.turns.at(-1));
  const bState=await client.tool('beast_get_state');await close();

  await connect('A reconnected: RAWRPHOS-native');
  const returningContext=await context('What did we name our next adventure? Answer only with the adventure name.');
  const returning=infer('A',returningContext);returning.driver_sha256=a.driver_sha256;receipt.turns.push({label:'A-returned',...returning});
  const finalState=await client.tool('beast_get_state');assert.deepEqual(finalState,bState);
  assert.deepEqual(returningContext.memories,bContext.memories);
  assert.deepEqual({public_state:finalState.public_state,progress:{trust:finalState.trust,bond:finalState.bond,evolution_stage:finalState.evolution_stage}},protectedState);
  receipt.verification=await client.tool('beast_verify');
  receipt.model_b_answer_matches_source=/^Violet Grove[.!]?$/i.test(b.output.trim());
  const finalSnapshot=await store.load();assert.deepEqual(finalSnapshot.events.slice(0,original.generation),original.events);
  const exported=await client.tool('beast_export_gba');await fs.writeFile(path.join(out,'beast-gba.zip'),Buffer.from(exported.data,'base64'),{flag:'wx'});
  const pack=await core.exportGba(finalSnapshot,options),originalPack=await core.exportGba(original,{trustedPublicKey:ANCHOR});
  assert.equal(exported.sha256,pack.sha256);assert.equal(sha(Buffer.from(exported.data,'base64')),pack.sha256);
  receipt.game_asset_sha256={};
  for(const name of ['gba/companion_state.bin','gba/companion_profile.bin','gba/companion_tiles.4bpp','gba/companion_palette.bgr555','companion.profile.json']){
   assert.deepEqual(pack.files[name],originalPack.files[name]);receipt.game_asset_sha256[name]=sha(pack.files[name]);
  }
  receipt.final={digest:finalSnapshot.digest,lineage_head:finalSnapshot.lineage_head,generation:finalSnapshot.generation,snapshot_file_sha256:sha(await fs.readFile(store.path)),gba_zip_sha256:pack.sha256};
  receipt.continuity={same_creature:true,original_event_prefix_preserved:true,original_memory_retrieved_by_all:true,model_swap_preserves_state:true,protected_fields_unchanged:true,game_assets_unchanged:true,initial_generation:initialState.generation,final_generation:finalState.generation};
  await close();await write();
  console.log(JSON.stringify({creature_id:identity.id,model_b_output:b.output,model_b_answer_matches_source:receipt.model_b_answer_matches_source,...receipt.final,paid_api_calls:0}));
 }catch(e){receipt.failure=String(e.message);await close();await write();throw e;}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
