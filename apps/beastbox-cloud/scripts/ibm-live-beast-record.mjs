/**
 * Real local Beast Box engine log; no mock self-awareness or unobserved gameplay.
 * pending: deterministic archived Lagoonfry talks and behaves after IBM submission.
 * post: fresh hardware counts create a new, provenance-tagged QBEAST and timeline.
 * This is an OFFLINE rule-based/local Hebbian companion, not an Ollama model reply.
 */
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {deflateSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {buildGenome,canonicalJson} from '../public/spark/genome.mjs';
import {sha256Hex} from '../public/spark/sha.mjs';
import {expandRun,validateRun} from '../public/spark/runs.mjs';
import {buildQbeast,serializeQbeast} from '../public/spark/qbeast.mjs';
import {renderBeast} from '../public/spark/draw.mjs';
import {createSession,adoptBeast,beastIdentity,talk,exportSession} from '../lib/companion/session.mjs';
import {createBehavior,advanceCreature} from '../lib/companion/behavior.mjs';

const [phase,outputPath]=process.argv.slice(2);
const out=resolve(outputPath||'_beast_ibm_live');
const hex=x=>createHash('sha256').update(typeof x==='string'?x:Buffer.from(x)).digest('hex');
const read=p=>JSON.parse(readFileSync(p,'utf8'));
const save=(p,v)=>writeFileSync(join(out,p),JSON.stringify(v,null,2)+'\n');
const check=(condition,message)=>{if(!condition)throw Error(message);};
const T={focus:70,calm:60,spark:80};
function sessionFor(genome){
 const session=createSession();
 const qbeast=buildQbeast(genome);
 adoptBeast(session,genome,genome.names[1]);
 session.beast.qbeast=qbeast;
 session.beast.behavior=createBehavior(session.beast);
 return {session,qbeast};
}
function step(session,environment,number){
 const result=advanceCreature(session,environment);
 check(result.ok,'God Core tick failed');
 return {step:number,action:result.event.action,
   energy:result.state.energy,curiosity:result.state.curiosity,
   preferences:result.state.preferences,position:result.state.position,
   scores:result.event.scores,reason_contract:'scored_actual_god_core_transition'};
}
function makePng(pixels){
 check(pixels.length===64*64*4,'Expected original 64x64 RGBA renderer');
 const scale=8,size=64*scale,bytes=Buffer.alloc(size*(size*4+1));
 for(let y=0;y<size;y++){
  const row=y*(size*4+1);
  for(let x=0;x<size;x++){
   const source=(Math.floor(y/scale)*64+Math.floor(x/scale))*4;
   Buffer.from(pixels.buffer,pixels.byteOffset+source,4).copy(bytes,row+1+x*4);
  }
 }
 const table=Array.from({length:256},(_,i)=>{let c=i;for(let n=0;n<8;n++)c=(c&1)?0xedb88320^(c>>>1):c>>>1;return c>>>0;});
 const crc=value=>{let c=0xffffffff;for(const b of value)c=table[(c^b)&255]^(c>>>8);return(c^0xffffffff)>>>0;};
 const chunk=(kind,data)=>{
  const k=Buffer.from(kind),head=Buffer.alloc(4),tail=Buffer.alloc(4);
  head.writeUInt32BE(data.length);tail.writeUInt32BE(crc(Buffer.concat([k,data])));
  return Buffer.concat([head,k,data,tail]);
 };
 const header=Buffer.alloc(13);header.writeUInt32BE(size,0);header.writeUInt32BE(size,4);header[8]=8;header[9]=6;
 return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),
   chunk('IHDR',header),chunk('IDAT',deflateSync(bytes,{level:9})),chunk('IEND',Buffer.alloc(0))]);
}
function collectTalk(session,words,label){
 const result=talk(session,words);
 return {source:'local_hebbian_rule_companion_not_llm',
   initiating_message:words,actual_local_reply:result.reply,
   memory_steps:result.steps,safe:result.safe,beast_id:beastIdentity(session.beast),
   phase:label};
}
function beforeHardware(){
 const source=read(resolve('apps/beastbox-cloud/public/spark/runs.json'));
 check(source.runs.length>0,'Archived IBM seed pack unavailable');
 const run=expandRun(source.runs[0]);
 const genome=buildGenome(T,run,null,10);
 const {session,qbeast}=sessionFor(genome);
 const id=beastIdentity(session.beast);
 const dialogue=[collectTalk(session,
   'Lagoonfry, while the IBM job is pending, how are you feeling in the observatory?','after_qpu_submission_not_necessarily_executing')];
 const behaviors=Array.from({length:20},(_,i)=>step(session,{place:'observatory',
   sound:.25,toy:.35,attention:.48,comfort:.66},i));
 const report={
  schema:'beastbox-live-qpu-concurrent-local-activity-v1',
  phase:'after_qpu_submission_before_result',
  source:'archived_recorded_ibm_genesis',
  caveat:'This is a real deterministic local companion run, not physical browser/ROM gameplay, authenticated cloud cognition, or evidence of QPU executing concurrently.',
  beast:{name:genome.names[1],id,genome_seed:genome.seed,temperament:genome.temperament},
  messages:dialogue,behaviors,
  no_native_game_input:true,no_native_progress:true,
  no_llm_inference:true,model_api_requests:0,
  unchanged_qbeast_id:id===beastIdentity(session.beast)};
 save('beast-pending-activity.json',report);
 save('beast-pending-session-unsigned.json',exportSession(session));
 return report;
}
function afterHardware(){
 const receipt=read(join(out,'measurements.json'));
 check(receipt.source_class==='ibm_quantum_hardware_measurement' &&
  receipt.linked?.counts&&receipt.decoupled?.counts,'Measured counts not available');
 const counts=receipt.linked.counts;
 const shots=Object.values(counts).reduce((a,b)=>a+b,0);
 const row=validateRun({key:'hardware:'+receipt.job_id+':0',backend:receipt.backend,
   job_id:receipt.job_id,pub_index:0,num_bits:2,shots,
   counts,counts_sha256:sha256Hex(canonicalJson(counts))});
 const genome=buildGenome(T,row,null,10);
 check(canonicalJson(genome)===canonicalJson(buildGenome(T,row,null,10)),'Nonreproducible hardware genesis');
 const {session,qbeast}=sessionFor(genome);
 const initialId=beastIdentity(session.beast);
 // Explicit deterministic software mapping of hardware counts to an environment.
 // NOT full quantum state-vector reconstruction or a physical causal mechanism.
 const linked=receipt.linked.statistics.p_equal;
 const separate=receipt.decoupled.statistics.p_equal;
 const env={place:'observatory',attention:Math.max(0,Math.min(1,linked)),
   sound:Math.max(0,Math.min(1,1-separate)),
   toy:Math.max(0,Math.min(1,Math.abs(linked-separate))),
   comfort:Math.max(0,Math.min(1,separate))};
 const pre=collectTalk(session,
  'Hello little Spark. You were generated from a verified IBM result. What do you notice here?',
  'after_ibm_measurement');
 const actions=Array.from({length:30},(_,i)=>step(session,env,i));
 const post=collectTalk(session,
  'Would you rather explore, inspect, or rest after the measurement?',
  'after_ibm_stimulated_behavior');
 check(initialId===beastIdentity(session.beast),'QBEAST changed during God Core');
 check(session.beast.xp===0,'Native game progress fabricated');
 const png=makePng(renderBeast(genome,1,'open'));
 writeFileSync(join(out,'beast-portrait.png'),png);
 writeFileSync(join(out,'beast.qbeast'),serializeQbeast(qbeast));
 save('beast-session-unsigned.json',exportSession(session));
 const report={
  schema:'beastbox-live-ibm-spark-genesis-v1',
  source_class:'ibm_quantum_hardware_measurement',
  hardware_job_id:receipt.job_id,backend:receipt.backend,
  counts_sha256:receipt.counts_sha256,
  qbeast_id:initialId,
  genesis:{name:genome.names[1],family:qbeast.profile.family,seed:genome.seed,
   body:genome.body,temperament:genome.temperament,origin:genome.island},
  environment_transform:{source:'recorded hardware outcome proportions',
   mapping:'linked p_equal -> attention; 1-control p_equal -> sound; difference -> toy; control p_equal -> comfort',
   coefficients:env,source_is_real_qpu:true,transform_is_classical_heuristic:true},
  conversation:[pre,post],actions,
  results:{energy:session.beast.behavior.energy,curiosity:session.beast.behavior.curiosity,
   action_counts:actions.reduce((a,b)=>(a[b.action]=(a[b.action]||0)+1,a),{}),
   genome_reproducible:true,qbeast_identity_unchanged:true,xp_awarded:0,
   portrait_sha256:hex(png),session_sha256:hex(canonicalJson(exportSession(session)))},
  no_native_gameplay_claim:true, no_azure_cosmos_write:true,
  no_hosted_inference_claim:true, no_entanglement_measurement_claim:true,
 };
 save('beast-posthardware-report.json',report);
 return report;
}
mkdirSync(out,{recursive:true});
if(phase==='pending'){
 const report=beforeHardware();
 console.log(JSON.stringify({phase,beast:report.beast,messages:report.messages.length,
  ticks:report.behaviors.length,source:report.messages[0].source}));
}else if(phase==='post'){
 const report=afterHardware();
 console.log(JSON.stringify({phase,name:report.genesis.name,id:report.qbeast_id,
  ticks:report.actions.length,talk:report.conversation.map(x=>x.actual_local_reply),
  action_counts:report.results.action_counts}));
}else{
 throw Error('Use pending or post');
}
