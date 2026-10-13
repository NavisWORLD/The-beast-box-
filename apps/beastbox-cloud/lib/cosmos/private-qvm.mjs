/** Trusted-worker adapter for the EXISTING Rigetti QVM planner/executor.
 * Remote provider output is sealed server-side; browser-created receipts cannot pass.
 */
import {createHmac,timingSafeEqual} from 'node:crypto';
import {canonicalJson} from '../../public/spark/genome.mjs';
import {sha256Hex} from '../../public/spark/sha.mjs';
import {genesisForBeast,planGrowthCircuit,countsFeatures} from '../zeref/zeref-diary.mjs';
const h=value=>sha256Hex(canonicalJson(value));
const seal=(secret,value)=>createHmac('sha256',secret).update('private-qvm/v1\0'+canonicalJson(value)).digest('hex');
export function privateGrowthPlan(record,eventId,{now=new Date().toISOString()}={}){
 if(!record?.growth?.optedIn||record.growth.jobs>=16)throw Error('PRIVATE_QVM_CONSENT_OR_JOB_CAP');
 if(record.growth.lastCompleted&&Date.parse(now)-Date.parse(record.growth.lastCompleted)<86400000)throw Error('PRIVATE_QVM_DAILY_CAP');
 const state=genesisForBeast(record.profile);state.tick=record.growth.tick;state.signals={...state.signals,...record.profile.traits.stats};
 const plan=planGrowthCircuit(state);if(plan.target!=='rigetti.sim.qvm'||plan.shots>256||plan.shots<1)throw Error('PRIVATE_QVM_BUDGET_OR_TARGET');
 return {...plan,schema:'private-growth-plan/v1',scope:'private-cosmos',owner:record.owner,beast_id:record.beastId,event_id:eventId,input_hash:h({owner:record.owner,id:record.beastId,tick:plan.tick,signals:state.signals,quil_sha256:plan.quil_sha256}),job_name:'private-qvm-'+h({owner:record.owner,eventId}).slice(0,24),planned_at:now,cost_cap_usd:0};
}
export function sealWorkerReceipt(secret,plan,raw,{startedAt=null,completedAt=null}={}){
 if(typeof secret!=='string'||secret.length<32)throw Error('QVM_SIGNING_UNCONFIGURED');
 const valid=typeof startedAt==='string'&&typeof completedAt==='string'&&Number.isFinite(Date.parse(startedAt))&&Date.parse(completedAt)>=Date.parse(startedAt)&&raw?.ok===true&&raw.target==='rigetti.sim.qvm'&&raw.beast_id===plan.beast_id&&raw.job_name===plan.job_name&&raw.shots===plan.shots&&/^[-a-zA-Z0-9]{8,100}$/.test(raw.job_id||'')&&countsFeatures(raw.counts,plan.shots);
 const record={schema:'private-qvm-receipt/v1',owner:plan.owner,beast_id:plan.beast_id,tick:plan.tick,event_id:plan.event_id,input_hash:plan.input_hash,quil_sha256:plan.quil_sha256,target:'rigetti.sim.qvm',status:valid?'RIGETTI_QVM_REMOTE':'BLOCKED_EXTERNAL',simulated:true,job_id:raw?.job_id||null,shots:plan.shots,counts:valid?raw.counts:null,error:valid?null:'Authenticated provider execution did not produce a valid matching result.',startedAt,completedAt,request:plan,providerReceipt:raw};
 return {...record,receipt_hash:h(record),mac:seal(secret,record)};
}
export function verifyWorkerReceipt(secret,record,plan){
 if(typeof record?.mac!=='string'||!/^[0-9a-f]{64}$/.test(record.mac)||typeof secret!=='string'||secret.length<32)return false;
 const {mac,receipt_hash,...unsigned}=record;
 if(h(unsigned)!==receipt_hash||!timingSafeEqual(Buffer.from(mac),Buffer.from(seal(secret,unsigned))))return false;
 return record.owner===plan.owner&&record.beast_id===plan.beast_id&&record.tick===plan.tick&&record.event_id===plan.event_id&&record.input_hash===plan.input_hash&&record.quil_sha256===plan.quil_sha256&&record.shots===plan.shots&&record.target==='rigetti.sim.qvm'&&record.request?.quil===plan.quil&&plan.shots<=256&&plan.cost_cap_usd===0;
}
