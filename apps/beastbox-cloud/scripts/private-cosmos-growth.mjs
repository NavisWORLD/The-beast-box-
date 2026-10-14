/** Scheduled server worker: no user data or provider secrets in stdout/artifacts. */
import {spawn} from 'node:child_process';
import {mkdtemp,readFile,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {storageConfig} from '../lib/cosmos/azure-blob.mjs';
import {azurePrivateIO,PrivateCosmos} from '../lib/cosmos/private-memory.mjs';
import {runPrivateGrowth} from '../lib/cosmos/private-growth-worker.mjs';
const cfg=storageConfig();
if(!cfg){console.log(JSON.stringify({status:'BLOCKED_EXTERNAL',reason:'PRIVATE_AZURE_STORAGE_UNCONFIGURED'}));process.exit(2);}
async function execute(plan){
 if(plan.target!=='rigetti.sim.qvm'||plan.shots>256||plan.cost_cap_usd!==0)throw Error('PRIVATE_QVM_BUDGET_REJECTED');
 if(!process.env.AZURE_QUANTUM_CONNECTION_STRING)return {ok:false,target:plan.target,beast_id:plan.beast_id,job_name:plan.job_name,shots:plan.shots,job_id:null,error:'PROVIDER_UNCONFIGURED'};
 const dir=await mkdtemp(join(tmpdir(),'private-qvm-'));try{
  await writeFile(join(dir,'plan.json'),JSON.stringify(plan),{mode:0o600});
  const child=spawn('python',['scripts/zeref_diary_qvm.py',join(dir,'plan.json'),join(dir,'result.json'),'--private-bounded'],{stdio:'ignore'});
  await new Promise((resolve,reject)=>{const timer=setTimeout(()=>{child.kill('SIGTERM');reject(Error('SUBMISSION_UNKNOWN'));},300000);child.once('error',()=>{clearTimeout(timer);reject(Error('EXECUTOR_UNAVAILABLE'));});child.once('close',()=>{clearTimeout(timer);resolve();});});
  return JSON.parse(await readFile(join(dir,'result.json'),'utf8'));
 }finally{await rm(dir,{recursive:true,force:true});}
}
try{const store=new PrivateCosmos(azurePrivateIO(cfg),{scope:process.env.BEASTBOX_PRIVATE_MEMORY_PREFIX||''});const report=await runPrivateGrowth(store,execute,{maxJobs:Number(process.env.BEASTBOX_PRIVATE_GROWTH_MAX_JOBS||2),maxAttempts:Number(process.env.BEASTBOX_PRIVATE_GROWTH_LIFETIME_ATTEMPTS||16),userDaily:Number(process.env.BEASTBOX_PRIVATE_GROWTH_USER_DAILY||2)});console.log(JSON.stringify(report));}catch{console.log(JSON.stringify({status:'BLOCKED_EXTERNAL',reason:'PRIVATE_WORKER_FAILED_CLOSED'}));process.exitCode=1;}
