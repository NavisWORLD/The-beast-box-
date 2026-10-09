/** Approved archived counts. Integrity validation does not attest a physical QPU. */
import {canonicalJson} from './genome.mjs';
import {sha256Hex} from './sha.mjs';
import {expandQvmReceipt,QVM_SOURCE_CLASS,QVM_SOURCE_SHA,QVM_TARGET} from './qvm-growth.mjs';

export const SPARK_INDEX_PATH='/spark/user-seeds-20261004.json';
export const SPARK_BASE_PATH='/spark/runs.json';
export const QVM_RECEIPT_PATH='/spark/rigetti-qvm-sim.json';
// Independent real IBM Fez 2026-10-09 job; not part of historical October 4 archive counts.
export const REAL_FEZ_DRAGON_SOURCE_PATH='/spark/ibm-fez-reality-probe-20261009.json';
const HEX=/^[a-f0-9]{64}$/;
const approvedPath=path=>typeof path==='string'&&/^\/spark\/[a-z0-9-]+\.json$/.test(path);

export function validateRun(run){
 if(!run||['key','backend','job_id'].some(key=>typeof run[key]!=='string'||!run[key]||run[key].length>256))throw Error('Invalid recorded run identity.');
 if(!Number.isSafeInteger(run.pub_index)||run.pub_index<0||!Number.isSafeInteger(run.num_bits)||run.num_bits<1||run.num_bits>64||!Number.isSafeInteger(run.shots)||run.shots<1)throw Error('Invalid recorded shot or bit count.');
 if(!run.counts||Array.isArray(run.counts)||typeof run.counts!=='object'||!HEX.test(run.counts_sha256))throw Error('Invalid recorded count map or digest.');
 const entries=Object.entries(run.counts);
 if(!entries.length)throw Error('Empty recorded count map.');
 let shots=0;
 for(const [bits,count] of entries){
  if(!/^[01]+$/.test(bits)||bits.length!==run.num_bits||!Number.isSafeInteger(count)||count<0)throw Error('Invalid recorded outcome, bit width or count.');
  shots+=count;
  if(!Number.isSafeInteger(shots))throw Error('Unsafe recorded shot total.');
 }
 if(shots!==run.shots)throw Error('Recorded shot total mismatch.');
 if(sha256Hex(canonicalJson(run.counts))!==run.counts_sha256)throw Error('Recorded count digest mismatch.');
 return run;
}

export function expandRun(row){
 if(!row||typeof row.c!=='string'||!row.c)throw Error('Invalid compact recorded counts.');
 const counts={};
 for(const part of row.c.split(',')){
  const match=/^([01]+):(0|[1-9][0-9]*)$/.exec(part);
  if(!match||Object.hasOwn(counts,match[1]))throw Error('Invalid or duplicate compact outcome.');
  counts[match[1]]=Number(match[2]);
 }
 return validateRun({key:row.k,backend:row.b,job_id:row.j,pub_index:row.p,num_bits:row.n,shots:row.s,counts,counts_sha256:row.h});
}

/** The retained QVM receipt is a simulator source, separately and explicitly opted in. */
export function validateQvmReceipt(receipt){
 if(!receipt||receipt.schema!=='cosmos-stage015-prospective-free-qvm-triplets-v1'||receipt.source_class!==QVM_SOURCE_CLASS||receipt.public_rows_sha256!==QVM_SOURCE_SHA)throw Error('Unapproved Rigetti QVM simulator source.');
 if(!Array.isArray(receipt.scenario_records)||sha256Hex(canonicalJson(receipt.scenario_records))!==QVM_SOURCE_SHA)throw Error('Rigetti QVM scenario digest mismatch.');
 if(receipt.physical_hardware_jobs_permitted!==0||receipt.original_real_physical_measurements!==0||canonicalJson(receipt.backend_exact_allowlist)!==canonicalJson([QVM_TARGET])||receipt.total_simulated_shot_cap!==2048)throw Error('Rigetti QVM source boundary changed.');
 const batches=receipt.scenario_records.flatMap(row=>row.batches);
 for(const batch of batches){
  if(!HEX.test(batch.program_sha256)||batch.source!=='ACTUAL_AZURE_CLOUD_SIMULATOR'||canonicalJson(Object.keys(batch.counts).sort())!==canonicalJson(['00','01','10','11']))throw Error('Invalid Rigetti QVM batch evidence.');
  validateRun({key:batch.job_id,backend:batch.target,job_id:batch.job_id,pub_index:0,num_bits:2,shots:batch.shots,counts:batch.counts,counts_sha256:sha256Hex(canonicalJson(batch.counts))});
 }
 return expandQvmReceipt(receipt).map((run,index)=>validateRun({...run,qvm:{...run.qvm,program_sha256:batches[index].program_sha256}}));
}

async function fetchJson(path){
 const response=await fetch(path,{cache:'force-cache'});
 if(!response.ok)throw Error('Recorded seed source unavailable.');
 return response.json();
}

/** No argument retains the complete IBM gallery. QVM replay needs explicit opt-in. */
export async function loadSparkRuns({includeQvm=false}={}){
 const index=await fetchJson(SPARK_INDEX_PATH);
 if(index.schema!=='spark-beasts-public-seed-pack-index-v1'||!Array.isArray(index.shards))throw Error('Invalid recorded seed index.');
 const paths=[SPARK_BASE_PATH,...index.shards,REAL_FEZ_DRAGON_SOURCE_PATH];
 if(paths.some(path=>!approvedPath(path)))throw Error('Unapproved recorded seed path.');
 const tables=await Promise.all(paths.map(fetchJson));
 const byKey=new Map();
 for(const table of tables){
  if(!['spark-beasts-quantum-runs-compact-v1','spark-beasts-public-seed-shard-v1'].includes(table.schema)||!Array.isArray(table.runs))throw Error('Invalid recorded seed table.');
  for(const row of table.runs){
   const run=expandRun(row),previous=byKey.get(run.key);
   if(previous&&canonicalJson(previous)!==canonicalJson(run))throw Error('Conflicting recorded run key.');
   if(!previous)byKey.set(run.key,run);
  }
 }
 if(includeQvm){
  for(const run of validateQvmReceipt(await fetchJson(QVM_RECEIPT_PATH))){
   if(byKey.has(run.key))throw Error('Conflicting simulator run key.');
   byKey.set(run.key,run);
  }
 }
 return [...byKey.values()];
}
