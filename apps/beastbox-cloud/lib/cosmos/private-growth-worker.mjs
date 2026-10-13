/** Trusted opt-in worker. Reuses the existing planner and authenticated executor.
 * A durable reservation precedes every provider attempt. Unknown submissions are
 * never retried automatically. Quotas survive private snapshot reset/recovery.
 */
import {randomBytes,randomUUID,createHash} from 'node:crypto';
import {canonicalJson} from '../../public/spark/genome.mjs';
import {privateGrowthPlan,sealWorkerReceipt} from './private-qvm.mjs';
const digest=x=>createHash('sha256').update(canonicalJson(x)).digest('hex');
const json=x=>canonicalJson(x)+'\n';
const parse=row=>{if(!row||row.text.length>262144)throw Error('CORRUPT_WORKER_RECORD');return JSON.parse(row.text);};
const bounded=(raw,max,fallback)=>Number.isInteger(raw)&&raw>=1?Math.min(raw,max):fallback;
const identity=(owner,id)=>digest({owner,id});
const accountKey=owner=>digest({owner});
async function signingKey(store){
 const path=store.scope+'private-system/receipt-key.json';let row=await store.io.get(path);
 if(!row){try{await store.io.put(path,json({schema:'private-receipt-key/v1',key:randomBytes(48).toString('hex')}),{ifNoneMatch:'*'});}catch(e){if(e.status!==412)throw e;}row=await store.io.get(path);}
 const value=parse(row);if(value.schema!=='private-receipt-key/v1'||!/^([a-f0-9]{96})$/.test(value.key||''))throw Error('CORRUPT_RECEIPT_KEY');return value.key;
}
class Budget{
 constructor(store,limits){this.store=store;this.path=store.scope+'private-system/growth-budget.json';this.limits=limits;}
 async read(){const row=await this.store.io.get(this.path),state=row?parse(row):{schema:'private-growth-budget/v1',cursor:0,users:{},creatures:{}};if(state.schema!=='private-growth-budget/v1'||!Number.isSafeInteger(state.cursor)||state.cursor<0||!state.users||!state.creatures||Object.keys(state.users).length>100||Object.keys(state.creatures).length>400)throw Error('CORRUPT_GROWTH_BUDGET');return {row,state};}
 async mutate(edit){for(let i=0;i<4;i++){const {row,state}=await this.read(),result=edit(state);if(!result)return null;try{await this.store.io.put(this.path,json(state),row?{ifMatch:row.etag}:{ifNoneMatch:'*'});return result;}catch(e){if(e.status!==412||i===3)throw e;}}}
 async reserve(owner,id,event,at,nextCursor,tick){return this.mutate(state=>{
  const key=identity(owner,id),user=accountKey(owner),old=state.creatures[key],date=new Date(at).toISOString().slice(0,10),daily=state.users[user]?.date===date?state.users[user]:{date,jobs:0};
  if(old&&(['RESERVED','SUBMITTING','APPLY_PENDING','UNKNOWN'].includes(old.phase)||old.attempts>=this.limits.maxAttempts||at-Date.parse(old.at)<86400000)||daily.jobs>=this.limits.userDaily||old?.lastTick&&old.lastTick!==tick)return null;
  state.creatures[key]={attempts:(old?.attempts||0)+1,at:new Date(at).toISOString(),eventId:event,phase:'RESERVED',lastTick:old?.lastTick||0};state.users[user]={date,jobs:daily.jobs+1};state.cursor=nextCursor;return state.creatures[key];
 });}
 async mark(owner,id,event,phase,{tick}={}){return this.mutate(state=>{const row=state.creatures[identity(owner,id)];if(!row||row.eventId!==event)throw Error('WORKER_RESERVATION_MISMATCH');row.phase=phase;if(tick!==undefined)row.lastTick=tick;return row;});}
}
function workRecord(value){const record={...value};delete record.hash;return {...record,hash:digest(record)};}
function verifyWork(blob,owner,id,event){const value=parse(blob),{hash,...unsigned}=value;if(hash!==digest(unsigned)||value.schema!=='private-growth-work/v1'||value.owner!==owner||value.beastId!==id||value.plan?.event_id!==event)throw Error('CORRUPT_GROWTH_WORK');return value;}
async function putWork(store,path,value,old){return store.putAuxiliary(value.owner,value.beastId,path,json(workRecord(value)),old?{ifMatch:old.etag}:{ifNoneMatch:'*'});}

export async function runPrivateGrowth(store,execute,{now=Date.now,maxJobs=2,maxAttempts=16,userDaily=2}={}){
 const time=typeof now==='function'?now:()=>now,limits={maxJobs:bounded(maxJobs,2,2),maxAttempts:bounded(maxAttempts,16,16),userDaily:bounded(userDaily,2,2)};
 const report={schema:'private-growth-worker-report/v1',completed:0,blocked:0,canceled:0,pending:0,unknown:0,attempted:0,target:'rigetti.sim.qvm',maximumShotsPerJob:256,costCapUsd:0};
 const admitted=await store.io.get(store.scope+'private-system/admission.json');if(!admitted)return report;const subjects=parse(admitted).subjects;if(!Array.isArray(subjects)||subjects.length>100)throw Error('CORRUPT_ADMISSION');
 const key=await signingKey(store),budget=new Budget(store,limits),initial=await budget.read(),start=initial.state.cursor%Math.max(1,subjects.length);let serviced=0;
 for(let offset=0;offset<subjects.length&&serviced<limits.maxJobs;offset++){
  const index=(start+offset)%subjects.length,owner=subjects[index];let account;
  try{account=parse(await store.assertOwner(owner));}catch{
   // Revoked credentials never regain read authority. Sweep even COMPLETE
   // owners for writers that died between a late PUT and its erasure fence.
   try{const status=await store.ownerStatus(owner);if(!status.active&&(status.erasurePending||(await store.io.list(store.scope+'users/'+owner+'/beasts/')).some(name=>!name.endsWith('/head.json'))))await store.revoke(owner);}catch{}continue;
  }
  for(const id of account.beasts||[]){
   if(serviced>=limits.maxJobs)break;let row;try{row=await store.read(owner,id);}catch(error){if(error.code==='PRIVATE_BEAST_DELETED'){try{await store.remove(owner,id);}catch{}}continue;}
   if(!row.record.growth.optedIn||(!row.record.growth.schedule&&!row.record.growth.pending))continue;
   const state=(await budget.read()).state,reservation=state.creatures[identity(owner,id)];let event=reservation?.eventId,jobBlob=event?await store.io.get(store.path(owner,id)+'/growth-jobs/'+event+'.json'):null,work=jobBlob?verifyWork(jobBlob,owner,id,event):null;
   const resumed=work?.phase==='APPLY_PENDING'||(['COMPLETE','BLOCKED_EXTERNAL'].includes(work?.phase)&&['RESERVED','SUBMITTING','APPLY_PENDING','UNKNOWN'].includes(reservation?.phase));
   if(resumed){
    // Complete the checkpoint/commit only; never execute the provider twice.
   }else{
    if(reservation&&['RESERVED','SUBMITTING','APPLY_PENDING','UNKNOWN'].includes(reservation.phase)){report.unknown++;break;}
    event='growth-'+randomUUID();let plan;try{plan=privateGrowthPlan(row.record,event,{now:new Date(time()).toISOString()});}catch{continue;}
    if(!await budget.reserve(owner,id,event,time(),(index+1)%subjects.length,row.record.growth.tick))continue;
    serviced++;report.attempted++;const path=store.path(owner,id)+'/growth-jobs/'+event+'.json';
    work={schema:'private-growth-work/v1',owner,beastId:id,plan,phase:'RESERVED',startedAt:new Date(time()).toISOString()};
    try{
     jobBlob=await putWork(store,path,work,null);
     const fresh=await store.read(owner,id);if(!fresh.record.growth.optedIn||fresh.record.growth.tick!==row.record.growth.tick)throw Object.assign(Error('CANCELED'),{status:403});
     await budget.mark(owner,id,event,'SUBMITTING');work.phase='SUBMITTING';jobBlob=await putWork(store,path,work,jobBlob);
     work.raw=await execute(plan);work.completedAt=new Date(time()).toISOString();
     if(work.raw?.submission_unknown===true){work.phase='UNKNOWN';jobBlob=await putWork(store,path,work,jobBlob);await budget.mark(owner,id,event,'UNKNOWN');report.unknown++;break;}
     // Recheck consent/revocation after external execution and before recording.
     const latest=await store.read(owner,id);if(!latest.record.growth.optedIn)throw Object.assign(Error('CANCELED'),{status:403});
     work.receipt=sealWorkerReceipt(key,plan,work.raw,{startedAt:work.startedAt,completedAt:work.completedAt});work.phase='APPLY_PENDING';jobBlob=await putWork(store,path,work,jobBlob);await budget.mark(owner,id,event,'APPLY_PENDING');
    }catch(error){
     const canceled=[403,404,410].includes(error.status);await budget.mark(owner,id,event,canceled?'CANCELED':'UNKNOWN');report[canceled?'canceled':'unknown']++;break;
    }
   }
   if(work.phase==='APPLY_PENDING'||resumed){
    if(resumed)serviced++;
    const path=store.path(owner,id)+'/growth-jobs/'+event+'.json';
    try{
     const latest=await store.read(owner,id);if(!latest.record.growth.optedIn)throw Object.assign(Error('CANCELED'),{status:403});
     const result=await store.applyQvm(owner,id,work.plan,work.receipt,event,latest.version,key);work.phase=work.receipt.status==='RIGETTI_QVM_REMOTE'?'COMPLETE':'BLOCKED_EXTERNAL';
     await putWork(store,path,work,jobBlob);await budget.mark(owner,id,event,work.phase,{tick:result.record.growth.tick});report[work.phase==='COMPLETE'?'completed':'blocked']++;
    }catch(error){const canceled=[403,404,410].includes(error.status);if(canceled){await budget.mark(owner,id,event,'CANCELED');report.canceled++;}else report.pending++;}
   }
   break; // at most one creature per owner in this run
  }
 }
 return report;
}
