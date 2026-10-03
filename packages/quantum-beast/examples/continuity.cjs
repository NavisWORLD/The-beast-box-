/** Genuine local A(14K) -> B(18K) -> A(14K) checkpoint inference demonstration.
 * These are two checkpoints of the same native architecture, not two providers.
 * Their raw outputs are evidence, never a claim of reliable generative recall.
 */
const fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict'),{spawnSync}=require('node:child_process');
const core=require('../dist'),{FileStore}=require('../bin/file-store.cjs');
async function main(){
 const args=process.argv.slice(2);function flag(name){const i=args.indexOf('--'+name);if(i<0||!args[i+1])throw Error('Required --'+name);return path.resolve(args[i+1]);}
 const repo=flag('beastbox-root'),a=flag('model-a'),b=flag('model-b'),out=flag('output');
 await fs.mkdir(out,{recursive:true});
 const shaA='4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5',shaB='20932937afb3e0e1b62a4e5f38f92170046ae2928b437dc31b8a37d6538e701e';
 const signer=await core.createSigningKey(),store=new FileStore(path.join(out,'beast.qbeast'),{trustedPublicKey:signer.publicKey});
 let state=await core.signSnapshot(await core.createSnapshot(core.generateCreature('quantum-beast-first-contact','nebula')),signer.privateKey,signer.publicKey);
 await store.install(state);const identity=structuredClone(state.profile),initialHead=state.lineage_head;
 function infer(checkpoint,sha,bridge,user){
  const p=bridge.get_profile(),context={creature_id:p.id,name:p.name,family:p.family,memories:bridge.recall('adventure',4),user};
  const result=spawnSync('python3',[path.join(__dirname,'native_model.py'),repo,checkpoint,sha,JSON.stringify(context)],{encoding:'utf8',timeout:60000,maxBuffer:1000000});
  if(result.status!==0)throw Error(result.stderr||'Native inference failed');return JSON.parse(result.stdout);
 }
 const first=await core.BeastBridge.load(await store.load(),store.options),turnA=infer(a,shaA,first,'We named our next adventure Violet Grove.');
 // This is the actual public user event in this demo, not an invented won battle.
 const pending=await first.record_event({summary:'We named our next adventure Violet Grove.',source_ref:'demo:public-user-message-1'});
 const hostApproved=await core.approveProposal(state,pending,{allow:['memory'],public_memory:true},store.options);
 state=await core.signSnapshot(hostApproved,signer.privateKey,signer.publicKey);await store.compareAndSwap(first.snapshot().digest,state);
 const second=await core.BeastBridge.load(await store.load(),store.options),selected=second.recall('adventure',4);
 assert.equal(selected[0].summary,'We named our next adventure Violet Grove.');const turnB=infer(b,shaB,second,'What did we name our next adventure?');
 const returning=await core.BeastBridge.load(await store.load(),store.options),turnAgain=infer(a,shaA,returning,'What did we name our next adventure?');
 assert.deepEqual(returning.get_profile(),identity);assert.equal(returning.get_lineage_head(),second.get_lineage_head());assert.deepEqual(returning.get_state(),second.get_state());
 const pack=await returning.export_gba();await fs.writeFile(path.join(out,'beast-gba.zip'),pack.zip,{flag:'wx'});
 const receipt={schema:'qbeast-native-model-continuity-demo-v1',creature_id:state.profile.id,public_key:signer.publicKey,initial_head:initialHead,final_head:state.lineage_head,snapshot_digest:state.digest,
  model_a:turnA,model_b:turnB,returning_a:turnAgain,retrieved_memories:selected,verification:await returning.verify(),gba_zip_sha256:pack.sha256,
  paid_api_calls:0,verified:['real local inference from two pinned RAWRPHOS checkpoints','same seed-derived identity and stats','real disk reopen between checkpoints','exact approved memory delivered as bounded context','unchanged genome/trust/bond/evolution on swap','existing BCG1/BCP1 export'],
  not_proven:['two different AI providers','reliable model-generated recall or autonomous actions','quantum hardware','full LOST COSMOS campaign or physical iPhone acceptance']};
 await fs.writeFile(path.join(out,'continuity.json'),JSON.stringify(receipt,null,2)+'\n');
 console.log(JSON.stringify({creature_id:state.profile.id,model_a_steps:turnA.training_steps,model_b_steps:turnB.training_steps,context_continuity:true,lineage_head:state.lineage_head,gba_zip_sha256:pack.sha256,paid_api_calls:0}));
}
main().catch(e=>{console.error(e);process.exitCode=1;});
