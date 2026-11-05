#!/usr/bin/env node
/**
 * Zeref 012E: expose BOTH blocked and successful actions from the EXISTING
 * canonical pocket experience stream. Reuses the site's exact world rules.
 *
 * No 012D weights, native ROM bytes, quantum records or visitors are changed.
 * Train/validation/held-out keys are disjoint; private histories never enter.
 */
import {createHash} from 'node:crypto';
import {readFileSync,mkdirSync,writeFileSync,existsSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {BASELINES,createGridEnv,notePolicyOutcome,stepEnv,metrics} from '../apps/beastbox-cloud/lib/zeref/pocket-grid-env.mjs';
import {verifyStream,trainingEligible} from '../apps/beastbox-cloud/lib/zeref/experience-record.mjs';

const ROOT=fileURLToPath(new URL('../',import.meta.url));
const POLICIES=Object.freeze(['random','pocket-learner','greedy-frontier']);
const LAYOUTS=Object.freeze({train:32,validation:12,heldout:24});
const STEPS=40;
export const SCHEMA='zeref-012e-visible-collision-example/v1';
export const QBEAST='bb-deada969';
export const DIGEST='23b4e2d6f736cf25f32242d0910d18df6939c3a89b1b50efecb83e94161363ad';
const SOURCE='deterministic_pocket_simulation';
const sum=(arr,f)=>arr.reduce((a,x)=>a+f(x),0);
const sha=s=>createHash('sha256').update(s).digest('hex');
const jsonl=x=>x.map(v=>JSON.stringify(v)+'\n').join('');
const keyFor=(split,i)=>'exp012e-'+split+'-'+i;

export function runEpisode({split,index,policy}){
 if(!(split in LAYOUTS)||!Number.isInteger(index)||index<0||index>=LAYOUTS[split]||!POLICIES.includes(policy))
  throw Error('Invalid preregistered rollout identity');
 const key=keyFor(split,index);
 const env=createGridEnv({digest:DIGEST,key,qbeast_id:QBEAST,maxSteps:STEPS});
 const records=[],examples=[];
 for(let i=0;i<STEPS;i++){
  const action=BASELINES[policy](env);
  const result=stepEnv(env,action,{policy});
  notePolicyOutcome(env,result.outcome);
  const record=result.record;
  const eligibility=trainingEligible(record,{identity:QBEAST});
  if(!eligibility.ok||record.origin!==SOURCE||record.real_game_progress!==false||record.simulated!==true)
   throw Error('Invalid canonical experience: '+JSON.stringify(eligibility));
  if(!['wall','rift','revisit','new_cell','rested'].includes(result.outcome.kind))
   throw Error('Unknown measured outcome');
  const eligibleAttempt=action!=='WAIT'&&record.observation.neighbors[action]?.kind==='open';
  const observedRift=eligibleAttempt&&result.outcome.kind==='rift';
  if(eligibleAttempt&&!['rift','revisit','new_cell'].includes(result.outcome.kind))
   throw Error('Unanticipated open-neighbor outcome');
  examples.push({
   schema:SCHEMA,split,episode:key,policy,step:i+1,qbeast_id:QBEAST,
   source_class:SOURCE,source_record_sha256:record.hash,
   observation:record.observation,action,
   observed_outcome:result.outcome.kind,observed_reward:result.reward,
   eligible_unknown_rift_attempt:eligibleAttempt,
   unseen_rift_collision:observedRift?1:0,
   labels_from_verified_outcome:true,
   native_game_progress:false,quantum_action_pair_verified:false,
   personal_user_data:false
  });
  records.push(record);
 }
 const audit=verifyStream(records);
 if(!audit.ok||audit.count!==STEPS)throw Error('Canonical experience hash-chain invalid');
 return {examples,proof:{
   split,key,policy,chain_head:audit.head,events:STEPS,
   source_hashes_sha256:sha(records.map(r=>r.hash).join('\n')),
   summary:metrics(env)
 }};
}
export function buildDataset({root=ROOT}={}){
 const rows={},proofs={};
 const sourceFiles=[
  'apps/beastbox-cloud/lib/zeref/pocket-grid-env.mjs',
  'apps/beastbox-cloud/lib/zeref/experience-record.mjs',
  'apps/beastbox-cloud/lib/zeref/zeref-pocket.mjs',
  'apps/beastbox-cloud/lib/zeref/pocket-learner.mjs',
  'scripts/zeref_012e_collision_dataset.mjs'
 ];
 const hashes=Object.fromEntries(sourceFiles.map(p=>[p,sha(readFileSync(resolve(root,p)))]));
 for(const split of Object.keys(LAYOUTS)){
  rows[split]=[];proofs[split]=[];
  for(let i=0;i<LAYOUTS[split];i++)for(const policy of POLICIES){
   const {examples,proof}=runEpisode({split,index:i,policy});
   rows[split].push(...examples);proofs[split].push(proof);
  }
 }
 const ids=Object.values(proofs).flat().map(x=>x.key);
 const trainKeys=new Set(proofs.train.map(x=>x.key));
 if(proofs.heldout.some(x=>trainKeys.has(x.key))||proofs.validation.some(x=>trainKeys.has(x.key)))
  throw Error('Train / validation / heldout overlap');
 const contents=Object.fromEntries(Object.entries(rows).map(([s,v])=>[s+'.jsonl',jsonl(v)]));
 const selected=Object.fromEntries(Object.entries(rows).map(([split,v])=>{
  const attempts=v.filter(x=>x.eligible_unknown_rift_attempt);
  return [split,{
   layouts:LAYOUTS[split],policies:POLICIES,episodes:proofs[split].length,
   records:v.length,open_neighbor_attempts:attempts.length,
   previously_hidden_rift_collisions:sum(attempts,x=>x.unseen_rift_collision),
   wall_attempts:v.filter(x=>x.observed_outcome==='wall').length,
   repeat_visits:v.filter(x=>x.observed_outcome==='revisit').length,
   newly_visited:v.filter(x=>x.observed_outcome==='new_cell').length,
   canonical_hash_chains_verified:proofs[split].length
  }];
 }));
 if(Object.values(selected).some(x=>!x.previously_hidden_rift_collisions||!x.open_neighbor_attempts))
  throw Error('No actual open-neighbor hazard observations');
 const manifest={
  schema:'zeref-012e-negative-outcome-manifest/v1',
  qbeast_id:QBEAST,scope:'canonical_public_classical_pocket_replay',
  source_policy:'existing_baselines_only',source_files_sha256:hashes,
  rows:selected,
  native_ROM_modified:false,production_weights_modified:false,
  approved_Zeref_parent_modified:false,language_branch_modified:false,
  verified_quantum_action_pairs:0,
  private_user_data_used:false,
  dataset_design:'ALL actual observations, including collisions; risk head may train only on open-neighbor attempts, never invisible future rift coordinates',
  evidence: Object.fromEntries(Object.entries(proofs).map(([split,episodes])=>[split,{
   episodes:episodes.map(x=>({key:x.key,policy:x.policy,chain_head:x.chain_head,source_hashes_sha256:x.source_hashes_sha256}))
  }])),
  artifacts:Object.fromEntries(Object.entries(contents).map(([name,data])=>[name,{sha256:sha(data),bytes:Buffer.byteLength(data)}]))
 };
 contents['manifest.json']=JSON.stringify(manifest,null,2)+'\n';
 return {manifest,contents};
}
export function writeDataset({root=ROOT,out='build/zeref-012e-negative-outcomes',check=false}={}){
 const {manifest,contents}=buildDataset({root}),directory=resolve(root,out);
 for(const [name,bytes] of Object.entries(contents)){
  const p=resolve(directory,name);
  if(check){if(!existsSync(p)||readFileSync(p,'utf8')!==bytes)throw Error('Non-reproducible '+name);}
  else{mkdirSync(dirname(p),{recursive:true});writeFileSync(p,bytes);}
 }
 return manifest;
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const flags=process.argv.slice(2);
 if(flags.some(f=>!['--write','--check','--summary'].includes(f)))throw Error('Invalid option');
 if(flags.includes('--write')&&flags.includes('--check'))throw Error('Conflicting output modes');
 const r=flags.includes('--write')?writeDataset():flags.includes('--check')?writeDataset({check:true}):buildDataset().manifest;
 console.log(JSON.stringify({schema:r.schema,stats:r.rows,quantum_pairs:0,training_model_weights_modified:false},null,2));
}
