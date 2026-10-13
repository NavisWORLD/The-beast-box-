/** Isolated real storage/provider acceptance. Never touches a production creature. */
import {randomBytes,randomUUID} from 'node:crypto';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
import {PrivateCosmos,azurePrivateIO} from '../lib/cosmos/private-memory.mjs';
import {storageConfig} from '../lib/cosmos/azure-blob.mjs';
import {issueCredential,verifyCredential} from '../lib/cosmos/private-owner.mjs';
import {runPrivateGrowth} from '../lib/cosmos/private-growth-worker.mjs';
const out=process.argv[2]||'build/private-cosmos';mkdirSync(out,{recursive:true});
const config=storageConfig(),report={schema:'private-cosmos-cloud-acceptance/v1',azure:'BLOCKED_EXTERNAL',qvm:'BLOCKED_EXTERNAL',checks:[],cleanup:false};
if(!config||process.env.BEASTBOX_PRIVATE_PROBE_APPROVAL!=='YES_ISOLATED_PRIVATE_TEST'){writeFileSync(out+'/report.json',JSON.stringify(report,null,2));process.exit(2);}
const scope='integration-tests/issue-323/'+randomUUID(),io=azurePrivateIO(config),store=new PrivateCosmos(io,{scope}),secret=randomBytes(48).toString('hex'),a=issueCredential(secret),b=issueCredential(secret);
const profile=id=>({schema:'cosmos-beast-public/v1',id,name:'Same Name',provenance:{kind:'classical-seeded-game-generation',seed:'explicit-isolated-test-'+id},traits:{family:'VOID',stats:{energy:70,signal:50,resonance:60}}});
try{
 assert.equal(verifyCredential(secret,a.token).subject,a.subject);assert.equal(verifyCredential(secret,b.token).subject,b.subject);
 await store.admit(a.subject);await store.admit(b.subject);const id='test-'+randomBytes(8).toString('hex'),other='test-'+randomBytes(8).toString('hex');
 const first=await store.create(a.subject,profile(id),randomUUID());await store.create(b.subject,profile(other),randomUUID());
 await assert.rejects(store.read(b.subject,id));report.checks.push('actual cross-owner namespace read denied');
 const event=randomUUID();await store.update(a.subject,id,{kind:'memory',text:'ISOLATED SYNTHETIC NOTE A'},event,first.version);await store.update(a.subject,id,{kind:'memory',text:'ISOLATED SYNTHETIC NOTE A'},event,first.version);
 const reread=await new PrivateCosmos(io,{scope}).read(a.subject,id);assert.equal(reread.record.memory.length,1);assert.equal((await store.read(b.subject,other)).record.memory.length,0);report.checks.push('write/read-back, restart, idempotency and distinct worlds verified');
 await assert.rejects(store.update(a.subject,id,{kind:'memory',text:'stale'},randomUUID(),first.version));report.checks.push('stale version rejected');
 const consent=await store.update(a.subject,id,{kind:'growth-consent',enabled:true,schedule:false},randomUUID(),reread.version);
 if(process.env.BEASTBOX_PRIVATE_QVM_SMOKE==='true'){
 await store.update(a.subject,id,{kind:'simulation-request'},randomUUID(),consent.version);
 const worker=await runPrivateGrowth(store,async plan=>{
  writeFileSync(out+'/plan.json',JSON.stringify(plan,null,2));
  if(process.env.AZURE_QUANTUM_CONNECTION_STRING){const child=spawnSync('python',['scripts/zeref_diary_qvm.py',out+'/plan.json',out+'/qvm-raw.json','--private-bounded'],{stdio:['ignore','ignore','ignore'],timeout:300000});if(child.status!==0)report.checks.push('QVM driver unavailable or timed out');}
  try{return JSON.parse(readFileSync(out+'/qvm-raw.json'));}catch{return {ok:false,target:plan.target,beast_id:plan.beast_id,job_name:plan.job_name,shots:plan.shots,job_id:null,error:'QVM credential or driver unavailable'};}
 },{maxJobs:1});
 const applied=await store.read(a.subject,id),receipt=applied.record.simulationReceipts.at(-1);
 assert.equal((await store.read(b.subject,other)).record.simulationReceipts.length,0);report.worker=worker;
 report.qvm=receipt?.status||'BLOCKED_EXTERNAL';if(receipt)report.receipt={hash:receipt.receipt_hash,job_id:receipt.job_id,target:receipt.target,shots:receipt.shots,counts:receipt.counts,startedAt:receipt.startedAt,completedAt:receipt.completedAt,source:'remote simulator, never physical QPU'};
 }else report.qvm='NOT_REQUESTED';
 await store.remove(a.subject,id);await assert.rejects(store.read(a.subject,id));await store.revoke(b.subject);await assert.rejects(store.read(b.subject,other));report.checks.push('real conditional private deletion and credential revocation verified');report.azure='PASSED';
}catch(error){report.error=error?.code||'PRIVATE_ACCEPTANCE_FAILED';}
finally{
 try{for(const name of await io.list(scope+'/')){const blob=await io.get(name);if(blob)await io.delete(name,{ifMatch:blob.etag});}assert.equal((await io.list(scope+'/')).length,0);report.cleanup=true;}catch{report.cleanup=false;report.cleanupError='ISOLATED_CLEANUP_FAILED';}
 writeFileSync(out+'/report.json',JSON.stringify(report,null,2));console.log(JSON.stringify({azure:report.azure,qvm:report.qvm,cleanup:report.cleanup,job_id:report.receipt?.job_id||null}));
}
if(report.azure!=='PASSED'||!report.cleanup)process.exitCode=1;
