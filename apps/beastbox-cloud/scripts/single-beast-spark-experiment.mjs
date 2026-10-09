/**
 * Single Spark Beast: an executable, evidence-producing GENESIS -> QBEAST ->
 * pinned Azure Rigetti QVM simulator stimulus -> memory -> God Core -> save/replay.
 * This invokes NO quantum provider, LLM, paid API, browser or cloud database.
 * All QVM phases are historical SIMULATOR count receipts, not full state vectors,
 * entanglement measures, live hardware or newly executed Azure jobs.
 */
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {deflateSync} from 'node:zlib';
import {buildGenome,canonicalJson} from '../public/spark/genome.mjs';
import {expandRun,validateQvmReceipt} from '../public/spark/runs.mjs';
import {scenarioRuns,growthFromQvmBatch,QVM_SOURCE_CLASS} from '../public/spark/qvm-growth.mjs';
import {buildQbeast,serializeQbeast} from '../public/spark/qbeast.mjs';
import {renderBeast} from '../public/spark/draw.mjs';
import {createSession,adoptBeast,advanceCreature,recordCreatureExperience,exportSession,importSession,swapBrain,beastIdentity} from '../lib/companion/session.mjs';
import {createBehavior,ACTIONS} from '../lib/companion/behavior.mjs';
import {observeText} from '../lib/companion/learn.mjs';

const DIR=dirname(fileURLToPath(import.meta.url));
const sha=x=>createHash('sha256').update(typeof x==='string'?x:Buffer.from(x)).digest('hex');
const canonical=x=>canonicalJson(x);
const check=(ok,why)=>{if(!ok)throw Error(why)};
const clamp=x=>Math.max(0,Math.min(1,x));
const TRAITS={focus:70,calm:60,spark:80};
const TICKS=90, ROOM_TICKS=30;
const SOURCE_CLASS='RECORDED_IBM_ARCHIVE_LABEL_NOT_LIVE_REATTESTED';
const crcTable=Array.from({length:256},(_,i)=>{let c=i;for(let j=0;j<8;j++)c=(c&1)?(0xedb88320^(c>>>1)):(c>>>1);return c>>>0;});
function crc32(bytes){let c=0xffffffff;for(const n of bytes)c=crcTable[(c^n)&255]^(c>>>8);return(c^0xffffffff)>>>0;}
function chunk(name,data){
 const nameBytes=Buffer.from(name,'ascii'),len=Buffer.alloc(4),end=Buffer.alloc(4);
 len.writeUInt32BE(data.length,0);end.writeUInt32BE(crc32(Buffer.concat([nameBytes,data])),0);
 return Buffer.concat([len,nameBytes,data,end]);
}
function png(pixels,width=64,multiplier=8){
 check(pixels.length===width*width*4,'Rendered RGBA length changed');
 const w=width*multiplier,rows=Buffer.alloc((w*4+1)*w);
 for(let y=0;y<w;y++){
  const row=y*(w*4+1);
  for(let x=0;x<w;x++){const pos=(Math.floor(y/multiplier)*width+Math.floor(x/multiplier))*4;Buffer.from(pixels.buffer,pixels.byteOffset+pos,4).copy(rows,row+1+x*4);}
 }
 const header=Buffer.alloc(13);header.writeUInt32BE(w,0);header.writeUInt32BE(w,4);header[8]=8;header[9]=6;
 return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',header),chunk('IDAT',deflateSync(rows,{level:9})),chunk('IEND',Buffer.alloc(0))]);
}
function makeSession(genome,profile){
 const s=createSession();adoptBeast(s,genome,genome.names[1]);s.beast.qbeast=structuredClone(profile);s.beast.energy=80;s.beast.behavior=createBehavior(s.beast);return s;
}
function environmentAt(t,phases){
 const idx=Math.floor(t/ROOM_TICKS),pulse=phases[idx].pulse;
 const place=['grove','observatory','shore'][idx];
 return {place,sound:clamp(pulse.entropy),toy:clamp(pulse.p11*2),
  attention:clamp(.2+pulse.delta),comfort:clamp(pulse.p00)};
}
function run(){
 const compact=JSON.parse(readFileSync(join(DIR,'../public/spark/runs.json'),'utf8'));
 check(Array.isArray(compact.runs)&&compact.runs.length>0,'Pinned IBM archive unavailable');
 // Strictly the first published source row, no cherry-picking for temperament.
 const recorded=expandRun(compact.runs[0]),genome=buildGenome(TRAITS,recorded,null,10);
 check(canonical(genome)===canonical(buildGenome(TRAITS,recorded,null,10)),'Genome not deterministic');
 const imageA=renderBeast(genome,1,'open'),imageB=renderBeast(genome,1,'open');
 check(Buffer.from(imageA).equals(Buffer.from(imageB)),'Image not deterministic');
 const qbeast=buildQbeast(genome);
 const receipt=JSON.parse(readFileSync(join(DIR,'../public/spark/rigetti-qvm-sim.json'),'utf8'));
 const simulator=validateQvmReceipt(receipt);
 const phases=scenarioRuns(simulator,1).map(row=>({job_id:row.job_id,phase:row.qvm.phase,
  source_class:QVM_SOURCE_CLASS,source_digest:row.qvm.source_sha256,
  shots:row.shots,counts:row.counts,pulse:growthFromQvmBatch(row)}));
 check(phases.length===3&&phases.reduce((n,p)=>n+p.shots,0)===256,'Pinned three-phase Rigetti simulator scenario changed');
 const original=makeSession(genome,qbeast),control=makeSession(genome,qbeast);
 const originalIdentity=beastIdentity(original.beast),genesis=canonical(genome),profile=canonical(qbeast);
 const realMemoryPhrase='grove explore';
 // Scripted learning observations, NOT experiences claimed to come from a player.
 for(let i=0;i<12;i++)observeText(original.mind,realMemoryPhrase,{seed:genome.seed});
 const stateBefore=JSON.parse(JSON.stringify(exportSession(original)));
 const actions=Object.fromEntries(ACTIONS.map(a=>[a,0])),controlActions={...actions};
 const samples=[],snapshots=[],counterfactual=[];
 let checkpoint=null,replay=null,exact=true,firstImpact=null;
 for(let t=0;t<TICKS;t++){
  const env=environmentAt(t,phases);
  if(t===18||t===54){
   // Clearly scripted feedback, equally applied to the learned/ablated runs.
   for(const s of [original,control])recordCreatureExperience(s,{place:env.place,reward:.5,kind:'scripted-keeper-feedback'});
   if(replay)recordCreatureExperience(replay,{place:env.place,reward:.5,kind:'scripted-keeper-feedback'});
  }
  const a=advanceCreature(original,env),b=advanceCreature(control,env);
  check(a.ok&&b.ok,'Behavior runtime refused the environment');
  actions[a.event.action]++;controlActions[b.event.action]++;
  if(t===0)firstImpact={learned_scores:a.event.scores,control_scores:b.event.scores,
   associations:a.event.input.associations,action:a.event.action};
  const interesting=t<15||t%15===0||t>=87;
  if(interesting)samples.push({tick:t,phase:phases[Math.floor(t/ROOM_TICKS)].phase,
   room:env.place,action:a.event.action,energy:a.state.energy,curiosity:a.state.curiosity,
   memory_bonus:a.event.input.memoryBonus,associations:a.event.input.associations,
   scores:a.event.scores,position:a.state.position});
  if(t===44){
   checkpoint=JSON.parse(JSON.stringify(exportSession(original)));
   replay=importSession(checkpoint);
   check(canonical(replay.beast.behavior)===canonical(original.beast.behavior),'Checkpoint invalid');
   const prior=canonical({id:beastIdentity(replay.beast),genome:replay.beast.genome,mind:replay.mind,behavior:replay.beast.behavior});
   swapBrain(replay,'local-pattern-demo-offline');
   check(canonical({id:beastIdentity(replay.beast),genome:replay.beast.genome,mind:replay.mind,behavior:replay.beast.behavior})===prior,'Model swap altered identity/state');
  }else if(t>=45){
   const next=advanceCreature(replay,env);
   if(canonical(next.event)!==canonical(a.event))exact=false;
  }
  if(t%30===29)snapshots.push({tick:t+1,phase:phases[Math.floor(t/ROOM_TICKS)].phase,
   energy:a.state.energy,curiosity:a.state.curiosity,preferences:a.state.preferences,
   position:a.state.position,lastAction:a.event.action});
 }
 check(exact&&canonical(replay.beast.behavior)===canonical(original.beast.behavior),'Save/load replay changed behavior');
 check(canonical(original.beast.genome)===genesis&&canonical(original.beast.qbeast)===profile,'Genesis/identity mutated');
 check(beastIdentity(original.beast)===originalIdentity&&original.beast.xp===0,'Behavior manufactured game progress');
 check(original.beast.behavior.memory.length<=24&&original.beast.behavior.events.length<=32,'Runtime grew beyond bounded state');
 check(Object.values(actions).reduce((a,b)=>a+b,0)===TICKS,'Tick accounting changed');
 const portrait=png(imageA,64,8);
 const output={
  schema:'beastbox-single-qbeast-spark-experiment-v1',
  provenance:{genesis:SOURCE_CLASS,genesis_backend:recorded.backend,genesis_job:recorded.job_id,
   genesis_pub_index:recorded.pub_index,genesis_counts_sha256:recorded.counts_sha256,
   genesis_shots:recorded.shots,simulator:QVM_SOURCE_CLASS,simulator_backend:'rigetti.sim.qvm',
   qvm_scenario:1,simulator_source_sha256:receipt.public_rows_sha256,
   quantum_hardware_jobs_submitted:0,azure_jobs_submitted:0,azure_db_writes:0,model_inference_calls:0,
   warning:'Recorded distributions are not a density matrix, complex amplitudes, or an entanglement witness.'},
  genome:{seed:genome.seed,genome_sha256:sha(canonical(genome)),
   name:genome.names[1],name_stages:genome.names,island:genome.island,element:genome.element,
   body:genome.body,temperament:genome.temperament,pose:genome.pose,
   ears:genome.ears,wings:genome.wings,tail:genome.tail,pattern:genome.pattern,
   eye_style:genome.eye_style,glow:genome.glow,voice_style:genome.voice?.style||'unknown',
   behavioral_tic:genome.behavior?.tic,stage:1,genome_traits:genome.inputs.traits},
  qbeast:{id:originalIdentity,family:qbeast.profile.family,snapshot_digest:qbeast.digest,
   identical_across_replay:true,native_stage_unchanged:true,native_progress_awarded:false},
  protocol:{genesis_selection:'first row of existing compact public IBM archive',
   training:'12 scripted grove explore observations in learned branch only',
   ablation:'matched untrained branch; identical genome, stimulus schedule and scripted feedback',
   simulator:'Three preserved Azure Rigetti QVM scenario-1 count batches provide bounded ENVIRONMENT stimulus only',
   signal_mapping:'entropy->sound, p11*2->toy, .2+delta->attention, p00->comfort (explicit classical heuristic)',
   steps:TICKS,rooms:['grove','observatory','shore'],checkpoint_tick:45,
   runtime:'classical deterministic God Core; offline, no browser, model, hardware, or cloud reads/writes'},
  simulator_phases:phases,
  observed:{action_counts:actions,untrained_action_counts:controlActions,
   action_histograms_differ:canonical(actions)!==canonical(controlActions),
   first_tick_memory_score_difference:firstImpact,
   initial_energy:80,initial_curiosity:stateBefore.beast.behavior.curiosity,
   final_energy:original.beast.behavior.energy,final_curiosity:original.beast.behavior.curiosity,
   learned_preferences:original.beast.behavior.preferences,observations:original.mind.steps,
   final_position:original.beast.behavior.position,final_action:original.beast.behavior.lastAction,
   phase_checkpoints:snapshots,trace_samples:samples,trace_sha256:sha(canonical(samples))},
  acceptance:{repeat_genome_exact:true,repeat_portrait_exact:true,
   save_load_replay_exact:exact,model_swap_identity_exact:true,
   qbeast_identity_preserved:true,unauthorized_xp_awarded:0,hardware_spend_seconds:0},
  portrait:{size_px:512,rgba_original_px:64,sha256:sha(portrait),format:'png'},
  limitations:['This is one seeded specimen in one scripted environment, not a population result.',
   'No physical state-vector reconstruction or entanglement measure is available from count histograms alone.',
   'Scripted text associations and environmental mappings are computational assays, not sensory observations of a real physical room.',
   'No Azure Cosmos DB endpoint, permission, ETag, persistence write or unlimited free simulations were verified.',
   'The creature has state-dependent computational behavior; no subjective consciousness, biological life or quantum advantage is established.']
 };
 return {output,portrait,qbeast,session:original};
}
export function runSingleBeastSparkExperiment(){return run();}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const {output,portrait,qbeast,session}=run();
 const dir=resolve(DIR,'../experiment-evidence/one-beast-spark-001');
 mkdirSync(dir,{recursive:true});
 writeFileSync(join(dir,'receipt.json'),JSON.stringify(output,null,2)+'\n');
 writeFileSync(join(dir,'beast.png'),portrait);
 writeFileSync(join(dir,'qbeast.json'),serializeQbeast(qbeast));
 writeFileSync(join(dir,'unsigned-session.json'),JSON.stringify(exportSession(session),null,2)+'\n');
 console.log('BEAST_SPARK_RESULT '+JSON.stringify({name:output.genome.name,id:output.qbeast.id,
  body:output.genome.body,temperament:output.genome.temperament,
  source:output.provenance.genesis_backend,simulator:output.provenance.simulator_backend,
  actions:output.observed.action_counts,energy:output.observed.final_energy,
  curiosity:output.observed.final_curiosity,replay_ok:output.acceptance.save_load_replay_exact,
  memory_effect:output.observed.action_histograms_differ,receipt_sha256:sha(canonical(output))}));
}