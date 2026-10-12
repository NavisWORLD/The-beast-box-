#!/usr/bin/env node
/**
 * Read-only, offline RAWRPHØS quantum conditioning export.
 *
 * All published IBM count rows pass existing count-hash validation and are
 * transformed into a fixed 12D numerical feature vector. New October 9-10
 * IBM receipts are separate from the 5,676-row archive. Rigetti QVM samples
 * are kept in a SEPARATE simulator file and never enter IBM train/val/test.
 *
 * This exports source-conditioned INPUTS, not labels for action or language,
 * performs NO training and does not alter the approved RAWRPHØS checkpoint.
 */
import {createHash} from 'node:crypto';
import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {loadGenesisSources} from './audit-creature-genesis.mjs';
import {expandRun,FEZ_HARDWARE_PATH,MARRAKESH_HARDWARE_PATH,FINAL_HARDWARE_PATH,
 SECOND_FINAL_HARDWARE_PATH,THIRD_FINAL_HARDWARE_PATH,MUSIC12D_IBM_HARDWARE_PATH,
 ZEREF_HEART_HARDWARE_PATH,WRAITH_HARDWARE_PATH,BONE_PIG_HARDWARE_PATH,
 LUMENWISP_HARDWARE_PATH,ZEREF_NIGHTCAT_HARDWARE_PATH,UMBRASCALE_STARSEED_HARDWARE_PATH,
 PISTONWYRM_GEARSEED_HARDWARE_PATH,HEARTFLARE_MOONFIRE_HARDWARE_PATH,
 MOONWRAITH_CASSETTE_HARDWARE_PATH} from '../apps/beastbox-cloud/public/spark/runs.mjs';

const ROOT=fileURLToPath(new URL('../',import.meta.url));
const PUBLIC='apps/beastbox-cloud/public';
const OUT='build/rawrphos-quantum-conditioning';
const SCHEMA='rawrphos-recorded-count-conditioning/v1';
const hex=x=>createHash('sha256').update(x).digest('hex');
const sorted=(a,b)=>a<b?-1:a>b?1:0;
const asJson=x=>JSON.stringify(x)+'\n';
const extraPaths=Object.freeze([FEZ_HARDWARE_PATH,MARRAKESH_HARDWARE_PATH,
 FINAL_HARDWARE_PATH,SECOND_FINAL_HARDWARE_PATH,THIRD_FINAL_HARDWARE_PATH,
 MUSIC12D_IBM_HARDWARE_PATH,ZEREF_HEART_HARDWARE_PATH,WRAITH_HARDWARE_PATH,
 BONE_PIG_HARDWARE_PATH,LUMENWISP_HARDWARE_PATH,ZEREF_NIGHTCAT_HARDWARE_PATH,
 UMBRASCALE_STARSEED_HARDWARE_PATH,PISTONWYRM_GEARSEED_HARDWARE_PATH,
 HEARTFLARE_MOONFIRE_HARDWARE_PATH,MOONWRAITH_CASSETTE_HARDWARE_PATH]);
export const FEATURE_LABELS=Object.freeze(['p1_bit0','p1_bit1','p1_bit2','p1_bit3','p1_bit4',
 'mean_one_fraction','even_parity_probability','maximum_outcome_probability',
 'normalized_shannon_entropy','observed_support_fraction','all_zero_probability','all_one_probability']);

export function featuresFromCounts(run){
 const probs=Array(5).fill(0);
 let ones=0,even=0,maximum=0,entropy=0,allZero=0,allOne=0,nonzero=0;
 for(const [bits,count] of Object.entries(run.counts)){
  if(count===0)continue;
  const p=count/run.shots,k=[...bits].filter(b=>b==='1').length;
  for(let i=0;i<Math.min(5,run.num_bits);i++)if(bits[i]==='1')probs[i]+=p;
  ones+=p*k/run.num_bits;
  if(k%2===0)even+=p;
  maximum=Math.max(maximum,p);
  entropy-=p*Math.log2(p);
  if(k===0)allZero+=p;
  if(k===run.num_bits)allOne+=p;
  nonzero++;
 }
 const rounded=x=>Number(x.toFixed(8));
 return [...probs,ones,even,maximum,entropy/run.num_bits,
   nonzero/2**run.num_bits,allZero,allOne].map(x=>rounded(Math.max(0,Math.min(1,x))));
}

/** No claim that all twelve values are independent measured channels. */
export function featureRow(run,source,sourceClass,split){
 if(!/^ibm_/.test(run.backend) && sourceClass==='RECORDED_IBM_HARDWARE')throw Error('Hardware backend mismatch');
 if(sourceClass==='RECORDED_AZURE_RIGETTI_QVM_SIMULATOR' && !/rigetti\.sim\.qvm/.test(run.backend))throw Error('Simulator backend mismatch');
 const features=featuresFromCounts(run);
 if(features.length!==12||features.some(x=>!Number.isFinite(x)||x<0||x>1))throw Error('Invalid numerical features');
 return {
  schema:SCHEMA,role:'STATE_CONDITIONING_ONLY',
  source_class:sourceClass,split,
  run_key:run.key,backend:run.backend,job_id:run.job_id,pub_index:run.pub_index,
  measured_bits:run.num_bits,shots:run.shots,counts_sha256:run.counts_sha256,
  published_source:{path:source.path,file_sha256:source.fileSha256,row_index:source.rowIndex},
  feature_labels:FEATURE_LABELS,features,
  independent_physical_channels_claimed:false,
  action_label:null,reward_label:null,dialogue_target:null,
 };
}

class DisjointSet{
 constructor(){this.parent=new Map();}
 root(x){if(!this.parent.has(x))this.parent.set(x,x);const p=this.parent.get(x);if(p!==x)this.parent.set(x,this.root(p));return this.parent.get(x);}
 join(a,b){a=this.root(a);b=this.root(b);if(a!==b)this.parent.set(a<b?b:a,a<b?a:b);}
}

/**
 * Leakage-safe split: connected components of shared job AND exact raw-count
 * digest. A multi-PUB job or identical archived counts cannot straddle splits.
 */
export function splitIbmRuns(runs){
 const groups=new DisjointSet();
 for(const r of runs)groups.join('job:'+r.backend+':'+r.job_id,'counts:'+r.counts_sha256);
 const assignments=new Map();
 for(const r of runs){
  const group=groups.root('job:'+r.backend+':'+r.job_id);
  const bucket=parseInt(hex(group).slice(0,8),16)%10;
  assignments.set(r.key,bucket<8?'train':bucket===8?'validation':'test');
 }
 const jobs=new Map(),counts=new Map();
 for(const r of runs){
  const split=assignments.get(r.key),job=r.backend+':'+r.job_id;
  if(jobs.has(job)&&jobs.get(job)!==split)throw Error('Train/test job leakage');
  if(counts.has(r.counts_sha256)&&counts.get(r.counts_sha256)!==split)throw Error('Train/test identical-count leakage');
  jobs.set(job,split);counts.set(r.counts_sha256,split);
 }
 return assignments;
}

const digestInfo=(bytes,path)=>({path,sha256:hex(bytes),bytes:bytes.length});
const summary=rows=>({rows:rows.length,shots:rows.reduce((s,r)=>s+r.shots,0),jobs:new Set(rows.map(r=>r.backend+':'+r.job_id)).size});
const sortedRows=rows=>rows.slice().sort((a,b)=>sorted(a.run_key,b.run_key));
const serialize=rows=>sortedRows(rows).map(asJson).join('');

export function buildCorpus({root=ROOT}={}){
 const genesis=loadGenesisSources({root});
 const sourceRows=new Map(),newRuns=[];
 const allSeen=new Map(genesis.archiveRuns.map(r=>[r.key,r]));
 for(const path of extraPaths){
  if(!/^\/spark\/ibm-[a-z0-9-]+\.json$/.test(path))throw Error('Unapproved source path');
  const relative=PUBLIC+path,bytes=readFileSync(resolve(root,relative)),doc=JSON.parse(bytes);
  if(!['spark-beasts-public-seed-shard-v1','spark-beasts-quantum-runs-compact-v1'].includes(doc.schema)||
     doc.source_class!=='RECORDED_IBM_HARDWARE'||!Array.isArray(doc.runs))throw Error('Non-IBM or unclassified source: '+path);
  for(const [index,entry] of doc.runs.entries()){
   const run=expandRun(entry),old=allSeen.get(run.key);
   if(old){
    if(old.counts_sha256!==run.counts_sha256)throw Error('Conflicting duplicate measurement');
    continue;
   }
   allSeen.set(run.key,run);newRuns.push(run);
   sourceRows.set(run.key,{path:relative,fileSha256:hex(bytes),rowIndex:index});
  }
 }
 const full=genesis.sortedArchiveRuns.concat(newRuns);
 const splits=splitIbmRuns(full);
 const ibmRows=full.map(run=>featureRow(run,
   genesis.rowSources.get(run.key)||sourceRows.get(run.key),'RECORDED_IBM_HARDWARE',splits.get(run.key)));
 const qvmFile=PUBLIC+'/spark/rigetti-qvm-sim.json';
 const qvmRows=genesis.qvmRuns.map((run,i)=>featureRow(run,
   {path:qvmFile,fileSha256:genesis.sources.qvm.sha256,rowIndex:i},
   'RECORDED_AZURE_RIGETTI_QVM_SIMULATOR','simulator_separate'));
 const partitions=Object.fromEntries(['train','validation','test'].map(split=>[split,ibmRows.filter(r=>r.split===split)]));
 if(genesis.archiveRuns.length!==5676||genesis.sources.archive.shots!==25576380||
    genesis.qvmRuns.length!==24||genesis.sources.qvm.shots!==2048)throw Error('Pinned published baseline census changed');
 const contents={
  'ibm-train.jsonl':serialize(partitions.train),
  'ibm-validation.jsonl':serialize(partitions.validation),
  'ibm-test.jsonl':serialize(partitions.test),
  'rigetti-qvm-simulator-held-separate.jsonl':serialize(qvmRows),
 };
 const artifacts=Object.fromEntries(Object.entries(contents).map(([path,data])=>[path,digestInfo(Buffer.from(data),path)]));
 const manifest={
  schema:'rawrphos-quantum-conditioning-manifest/v1',derived_only:true,
  owner_private_training_data_imported:false,model_weights_updated:false,provider_jobs_submitted:0,
  source_attestation:'Published count digests, repo bytes and selected retained receipt subsets; not provider reauthentication',
  model:'RAWRPHOS (Zeref research lineage); NO checkpoint changed',
  export_role:'state conditioning only; no language/action/reward supervision',
  feature_labels:FEATURE_LABELS,
  snapshots:{archive:genesis.sources.archive,additional_recorded_ibm:summary(newRuns),
   combined_ibm:summary(ibmRows),qvm_simulator:summary(qvmRows)},
  split_basis:'Union of job and identical-count digest; deterministic SHA-256 buckets by connected component',
  split_counts:Object.fromEntries(Object.entries(partitions).map(([key,rows])=>[key,summary(rows)])),
  source_files:[...genesis.sources.tables.map(({path,sha256,bytes})=>({path,sha256,bytes})),
   ...extraPaths.map(path=>{const p=PUBLIC+path,bytes=readFileSync(resolve(root,p));return digestInfo(bytes,p);}),
   {path:qvmFile,sha256:genesis.sources.qvm.sha256,bytes:genesis.sources.qvm.bytes}],
  exports:artifacts,
  boundary:['IBM classified rows are retained historical measurement counts, not a fresh provider run.',
   'Rigetti source is an Azure cloud QVM simulator; samples never enter IBM partitions.',
   '12 numerical features are classical postprocessing, not 12 independent quantum measurements.',
   'No chat, voice, user ID, QBEAST identity association or model-weight update in this export.',
   'Training later requires an explicit approved parent, curriculum, baselines and regression gates.'],
 };
 contents['manifest.json']=JSON.stringify(manifest,null,2)+'\n';
 return {manifest,contents};
}
export function writeCorpus({root=ROOT,out=OUT,check=false}={}){
 const {manifest,contents}=buildCorpus({root}),dir=resolve(root,out);
 for(const [name,data] of Object.entries(contents)){
  const file=resolve(dir,name);
  if(check){if(!existsSync(file)||readFileSync(file,'utf8')!==data)throw Error('Export out of date: '+name);}
  else{mkdirSync(dirname(file),{recursive:true});writeFileSync(file,data);}
 }
 return manifest;
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const flags=process.argv.slice(2);
 if(flags.some(f=>!['--write','--check','--summary'].includes(f)))throw Error('Unknown option');
 if(flags.includes('--write')&&flags.includes('--check'))throw Error('Choose write or check');
 const result=flags.includes('--write')?writeCorpus():flags.includes('--check')?writeCorpus({check:true}):buildCorpus().manifest;
 process.stdout.write(JSON.stringify({schema:result.schema,snapshots:result.snapshots,
  split_counts:result.split_counts,export_hashes:result.exports,model_weights_updated:false},null,2)+'\n');
}
