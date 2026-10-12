#!/usr/bin/env node
/**
 * ZEREF 012B: actual deterministic Cage-pocket rollouts and quantum/game
 * alignment audit. Read-only research, NO fake time pairing and NO model update.
 *
 * A historical IBM birthday measurement can identify Zeref, but the published
 * receipt does NOT establish a causal or temporal quantum -> action relation.
 * This tool refuses to train on that unsupported association.
 */
import {createHash} from 'node:crypto';
import {readFileSync,mkdirSync,writeFileSync,existsSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {BASELINES,createGridEnv,stepEnv,notePolicyOutcome,metrics} from '../apps/beastbox-cloud/lib/zeref/pocket-grid-env.mjs';
import {verifyStream,trainingEligible} from '../apps/beastbox-cloud/lib/zeref/experience-record.mjs';
import {expandRun} from '../apps/beastbox-cloud/public/spark/runs.mjs';
import {featuresFromCounts} from './prepare_rawrphos_quantum_conditioning.mjs';

export const ZEREF='bb-deada969';
export const ZEREF_DIGEST='23b4e2d6f736cf25f32242d0910d18df6939c3a89b1b50efecb83e94161363ad';
export const IBM_BIRTH='db4q484vf2bc73cuuuag';
export const SCHEMA='zeref-012b-game-measurement-alignment/v1';
const ROOT=fileURLToPath(new URL('../',import.meta.url));
const DEFAULT_OUT='build/zeref-012b-alignment';
const SOURCE='apps/beastbox-cloud/public/spark/ibm-zeref-heart-sound-20261010.json';
const POLICIES=['random','pocket-learner','greedy-frontier'];
const MAX_STEPS=40;
const hash=material=>createHash('sha256').update(material).digest('hex');
const canonical=record=>JSON.stringify(record)+'\n';
const actualKeys={train:i=>'exp012b-train-'+i,eval:i=>'exp012b-eval-'+i};

function round(n){return Number(n.toFixed(5));}
export function readZerefIbmReceipt(root=ROOT){
 const bytes=readFileSync(resolve(root,SOURCE)),doc=JSON.parse(bytes);
 if(doc.schema!=='spark-beasts-quantum-runs-compact-v1'||doc.source_class!=='RECORDED_IBM_HARDWARE'||!Array.isArray(doc.runs)||doc.runs.length!==2)
  throw Error('Zeref birth source schema/class changed');
 const runs=doc.runs.map(expandRun);
 if(runs.some(r=>r.job_id!==IBM_BIRTH||r.backend!=='ibm_fez'||r.num_bits!==2||r.shots!==4096))
  throw Error('Zeref birth job/backend/measurement identity changed');
 if(new Set(runs.map(r=>r.pub_index)).size!==2)throw Error('Zeref birth PUBs changed');
 return {path:SOURCE,fileSha256:hash(bytes),sourceClass:doc.source_class,
  jobId:IBM_BIRTH,backend:'ibm_fez',recordedRows:runs.length,shots:runs.reduce((a,r)=>a+r.shots,0),
  runs:runs.map(r=>({key:r.key,pub_index:r.pub_index,countsSha256:r.counts_sha256,
   derived_classical_features:featuresFromCounts(r)}))};
}

/**
 * A packet's origin and digest are meaningful, but identity alone is not
 * evidence that the job was executed for a particular game decision.
 * Only prospective independently verifiable temporal/task pairing can qualify.
 * This current offline audit has NO source demonstrating that relation.
 */
export function assessCausalLink({packet,gameEvent,claim}={}){
 const why=[];
 if(!packet||packet.sourceClass!=='RECORDED_IBM_HARDWARE'||packet.jobId!==IBM_BIRTH)why.push('missing_verified_hardware_origin');
 if(!gameEvent||gameEvent.origin!=='deterministic_pocket_simulation'||gameEvent.qbeast_id!==ZEREF)why.push('missing_matching_public_game_event');
 if(!gameEvent?.consent||gameEvent.consent.scope!=='public_game_event')why.push('missing_public_scope');
 if(!packet?.verifiedCrossDomainEventCommitment)why.push('no_independent_cross_domain_event_commitment');
 if(!packet?.providerExecutionTimeEvidence||!gameEvent?.observedAtUtc)why.push('missing_independent_timestamps');
 if(!packet?.predeclaredCircuitTask||!gameEvent?.measurementRequestNonce)why.push('missing_predeclared_measurement_game_task_binding');
 // Source inputs with no independent verification system may not be enabled by
 // callers merely providing strings in JSON fields.
 return {status:'NOT_VERIFIED_FOR_CAUSAL_GAME_PAIRING',causalPairingVerified:false,
  signalClaimAllowed:false,canTrainQuantumActionAssociation:false,
  reasonCodes:[...new Set(why.length?why:['independent_cross_domain_verifier_unavailable'])],
  userClaim:typeof claim==='string'?claim.slice(0,100):null};
}

export function rollout(policy,key){
 if(!POLICIES.includes(policy))throw Error('Unsupported policy');
 const e=createGridEnv({digest:ZEREF_DIGEST,key,qbeast_id:ZEREF,maxSteps:MAX_STEPS});
 const records=[],selected=[];
 for(let i=0;i<MAX_STEPS;i++){
  const action=BASELINES[policy](e);
  const result=stepEnv(e,action,{policy});
  notePolicyOutcome(e,result.outcome);
  records.push(result.record);
  const eligible=trainingEligible(result.record,{identity:ZEREF});
  if(!eligible.ok)throw Error('Invalid public simulation record: '+eligible.why);
  if(result.record.origin!=='deterministic_pocket_simulation'||result.record.real_game_progress!==false
     ||result.record.simulated!==true||result.record.consent.scope!=='public_game_event')
   throw Error('A pocket simulation was relabeled as native progress or private data');
  if(result.outcome.kind==='new_cell'&&result.reward>0.5){
   selected.push({schema:'zeref-012b-pocket-action-candidate/v1',qbeast_id:ZEREF,
    origin:'deterministic_pocket_simulation',task:'pocket_exploration_action_only',
    label_kind:'computed_reward',label:action,observed_reward:result.reward,
    observation:result.record.observation,hash_chain_record:result.record.hash,
    source_episode:key,source_policy:policy,measurement_source:null,
    quantum_action_pair_verified:false,real_native_game_progress:false});
  }
  if(result.done)break;
 }
 const verified=verifyStream(records);
 if(!verified.ok||verified.count!==MAX_STEPS)throw Error('Pocket canonical hash-chain failure: '+JSON.stringify(verified));
 return {metrics:metrics(e),episode:{key,policy,steps:MAX_STEPS,hash_chain_head:verified.head,
  record_hashes_sha256:hash(records.map(r=>r.hash).join('\n')),verified_record_count:verified.count},
  trainingCandidates:selected,firstEvent:records[0]};
}
const summarize=m=>Object.fromEntries(Object.entries(m).map(([key,value])=>[key,round(value)]));
function mean(rows,key){return rows.reduce((sum,r)=>sum+r.metrics[key],0)/rows.length;}
function policySummary(runs){
 return Object.fromEntries(POLICIES.map(policy=>{
  const rows=runs.filter(r=>r.episode.policy===policy);
  return [policy,{episodes:rows.length,steps:rows.reduce((s,r)=>s+r.metrics.steps,0),
   mean:summarize({cells_visited:mean(rows,'cells_visited'),new_cells:mean(rows,'new_cells'),
    blocked:mean(rows,'blocked'),rift_bumps:mean(rows,'rift_bumps'),wall_bumps:mean(rows,'wall_bumps'),
    poi_kinds_reached:mean(rows,'poi_kinds_reached'),action_entropy_bits:mean(rows,'action_entropy_bits')})}];
 }));
}
function serialize(records){return records.map(canonical).join('');}

/**
 * Fresh holdout family exp012b-eval, not reused from 011 train/val/eval.
 * Only training episodes contribute supervised candidate actions.
 */
export function buildReport({root=ROOT,trainLayouts=32,evalLayouts=24}={}){
 if(!Number.isInteger(trainLayouts)||trainLayouts<2||trainLayouts>64||
    !Number.isInteger(evalLayouts)||evalLayouts<2||evalLayouts>48)throw Error('Layout safety bound');
 const hardware=readZerefIbmReceipt(root);
 const train=[],heldout=[],candidates=[];
 for(const [split,n,into] of [['train',trainLayouts,train],['eval',evalLayouts,heldout]]){
  for(let i=0;i<n;i++)for(const policy of POLICIES){
   const run=rollout(policy,actualKeys[split](i));
   into.push(run);
   if(split==='train')candidates.push(...run.trainingCandidates);
  }
 }
 const trainKeys=new Set(train.map(x=>x.episode.key));
 if(heldout.some(x=>trainKeys.has(x.episode.key)))throw Error('Training/eval key leakage');
 const link=assessCausalLink({packet:{...hardware},gameEvent:heldout[0]?.firstEvent});
 if(link.causalPairingVerified||link.signalClaimAllowed||link.canTrainQuantumActionAssociation)
  throw Error('Unsupported quantum-action association was enabled');
 if(candidates.length===0||candidates.some(x=>x.quantum_action_pair_verified||x.measurement_source!==null))
  throw Error('Unproven quantum source injected into pocket examples');
 const training=serialize(candidates);
 const replaySummary=heldout.map(({metrics,episode})=>({episode,...metrics}));
 const evalJson=JSON.stringify(replaySummary,null,2)+'\n';
 const outputs={'pocket-outcome-selected-train.jsonl':training,'pocket-heldout-policy-replay.json':evalJson};
 const sourceFiles=Object.fromEntries([
  'apps/beastbox-cloud/lib/zeref/pocket-grid-env.mjs',
  'apps/beastbox-cloud/lib/zeref/experience-record.mjs',
  'apps/beastbox-cloud/scripts/zeref-pocket-grid-cli.mjs',
  'scripts/prepare_rawrphos_quantum_conditioning.mjs',
  'scripts/audit_zeref_012b_game_alignment.mjs'
 ].map(path=>[path,hash(readFileSync(resolve(root,path)))]));
 const report={
  schema:SCHEMA,model:'RAWRPHOS approved parent (frozen, not loaded here)',
  qbeast_id:ZEREF,recorded_ibm_birth:hardware,
  source_code_sha256:sourceFiles,
  quantum_action_pairing:link,verified_quantum_game_training_pairs:0,
  identity_link_only:true,
  quantum_workloads_submitted:0,new_rigetti_qvm_jobs:0,model_weights_updated:false,
  production_promoted:false,user_private_data_used:false,real_native_game_progress_claimed:false,
  simulation_origin:'deterministic_pocket_simulation',
  training:{layouts:trainLayouts,episode_count:train.length,record_count:trainLayouts*MAX_STEPS*POLICIES.length,
   outcome_selected_action_candidates:candidates.length,source_policies:POLICIES,
   label_kind:'computed_reward',candidate_action_origin:'deterministic_pocket_simulation',
   counts_as_true_game_progress:false},
  evaluation:{layouts:evalLayouts,episodes:heldout.length,record_count:evalLayouts*MAX_STEPS*POLICIES.length,
   by_policy:policySummary(heldout),keys:heldout.map(r=>r.episode.key).filter((x,i,a)=>a.indexOf(x)===i)},
  outputs:Object.fromEntries(Object.entries(outputs).map(([name,data])=>[name,{sha256:hash(data),bytes:Buffer.byteLength(data)}])),
  boundaries:['No historical IBM birth spark can be called a temporally aligned action label.',
   'No visitor conversations, microphone recordings, photos or personal state were ingested.',
   'Pocket results are deterministic classical simulations, not native ROM progress.',
   'Simulation outcome labels may train an independent future behavioral arm, but are not quantum labels.',
   'The audited baseline is not a claim the neural Zeref model outperforms any heuristic.']
 };
 outputs['manifest.json']=JSON.stringify(report,null,2)+'\n';
 return {report,outputs};
}
export function writeReport({root=ROOT,out=DEFAULT_OUT,check=false,trainLayouts=32,evalLayouts=24}={}){
 const {report,outputs}=buildReport({root,trainLayouts,evalLayouts});
 const directory=resolve(root,out);
 for(const [name,data] of Object.entries(outputs)){
  const path=resolve(directory,name);
  if(check){if(!existsSync(path)||readFileSync(path,'utf8')!==data)throw Error('Evidence mismatch: '+name);}
  else{mkdirSync(dirname(path),{recursive:true});writeFileSync(path,data);}
 }
 return report;
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const args=process.argv.slice(2);
 if(args.some(a=>!['--write','--check','--summary'].includes(a)))throw Error('Unknown option');
 if(args.includes('--check')&&args.includes('--write'))throw Error('Conflicting modes');
 const r=args.includes('--write')?writeReport():args.includes('--check')?writeReport({check:true}):buildReport().report;
 console.log(JSON.stringify({schema:r.schema,simulated_heldout:r.evaluation.by_policy,
  outcome_selected_candidates:r.training.outcome_selected_action_candidates,
  verified_quantum_game_training_pairs:r.verified_quantum_game_training_pairs,
  source_job:r.recorded_ibm_birth.jobId,output_hashes:r.outputs},null,2));
}
