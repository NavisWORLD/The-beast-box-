/** Read-only pinned-source audit. --fetch downloads public files; never executes HF code. */
import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {canonicalJson} from '../apps/beastbox-cloud/public/spark/genome.mjs';
import {loadGenesisSources} from './audit-creature-genesis.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const sha=b=>createHash('sha256').update(b).digest('hex');
const manifestPath=resolve(ROOT,'experiments/hf-genesis-001/source-manifest.json');
export async function auditHuggingFace({sourceDir='/tmp/beast-hf-qc67',fetchSources=false}={}){
 const manifest=JSON.parse(readFileSync(manifestPath));
 if(manifest.repository!=='phera-ra/QC67_cosmo'||manifest.revision!=='b414724c627300c41b099dcc6853766d08fd27a4')throw Error('Unexpected source pin.');
 const files=[];
 for(const file of manifest.files){
  if(!/^[a-zA-Z0-9_.\/-]+$/.test(file.path)||file.path.includes('..')||file.error)throw Error('Unapproved source path.');
  const path=resolve(sourceDir,file.path);
  if(fetchSources&&!existsSync(path)){
   const response=await fetch(`https://huggingface.co/${manifest.repository}/resolve/${manifest.revision}/${file.path}`,{signal:AbortSignal.timeout(30000)});
   if(!response.ok)throw Error(`Public source unavailable: ${file.path}`);
   const bytes=Buffer.from(await response.arrayBuffer());if(bytes.length>5*1024*1024)throw Error('Source exceeds size bound.');
   mkdirSync(dirname(path),{recursive:true});writeFileSync(path,bytes);
  }
  const bytes=readFileSync(path);if(bytes.length!==file.bytes||sha(bytes)!==file.sha256)throw Error(`Pinned source integrity failed: ${file.path}`);
  files.push({path:file.path,bytes:file.bytes,sha256:file.sha256,verified:true});
 }
 const data=readFileSync(resolve(sourceDir,'data/quantum_measurements_public.jsonl'));
 const published=JSON.parse(readFileSync(resolve(sourceDir,'data/quantum_measurements_manifest.json')));
 if(data.length!==published.output.bytes||sha(data)!==published.output.sha256)throw Error('Archive manifest mismatch.');
 const rows=data.toString('utf8').trim().split('\n').map(line=>JSON.parse(line));
 const allowed=new Set(['schema','record_index','timestamp','provider_class','provider','backend','job_id','counts','total_shots']);
 const classes={},shots={},jobs={},widths={},errors=[];
 const {archiveRuns,qvmRuns}=loadGenesisSources({root:ROOT});
 const repoJobs=new Set(archiveRuns.map(r=>r.job_id)),repoDigests=new Set(archiveRuns.map(r=>r.counts_sha256));
 const repoPairs=new Set([...archiveRuns,...qvmRuns].map(r=>r.job_id+':'+r.counts_sha256));
 let sharedJobs=0,sharedCounts=0,sharedJobCounts=0;
 for(const r of rows){
  if(r.schema!=='cosmos.public-quantum-record.v1'||Object.keys(r).some(k=>!allowed.has(k)))throw Error('Public projection contains unapproved fields.');
  const entries=Object.entries(r.counts||{}),width=new Set(entries.map(([bits])=>bits.length));
  const valid=entries.length>0&&width.size===1&&entries.every(([bits,n])=>/^[01]+$/.test(bits)&&Number.isSafeInteger(n)&&n>=0)&&Number.isSafeInteger(r.total_shots)&&r.total_shots>0&&entries.reduce((a,[,n])=>a+n,0)===r.total_shots;
  if(!valid)errors.push(r.record_index);
  if(!['measured_quantum_hardware','classical_simulator','legacy_unlabelled'].includes(r.provider_class))throw Error('Unknown provenance category.');
  if(r.provider_class==='measured_quantum_hardware'&&(!/^ibm_/.test(r.backend||'')||typeof r.job_id!=='string'||!r.job_id))throw Error('Hardware-labelled record lacks retained backend/job metadata.');
  if(r.provider_class==='classical_simulator'&&r.backend!=='rigetti.sim.qvm')throw Error('Simulator target boundary changed.');
  classes[r.provider_class]=(classes[r.provider_class]||0)+1;shots[r.provider_class]=(shots[r.provider_class]||0)+r.total_shots;
  (jobs[r.provider_class]??=new Set()).add(r.job_id||'(missing)');const n=[...width][0];widths[n]=(widths[n]||0)+1;
  const digest=sha(canonicalJson(r.counts));if(repoJobs.has(r.job_id))sharedJobs++;if(repoDigests.has(digest))sharedCounts++;if(repoPairs.has(r.job_id+':'+digest))sharedJobCounts++;
 }
 if(errors.length)throw Error('Invalid public count records: '+errors.join(','));
 for(const [key,value] of Object.entries(published.summary.records_by_provider_class))if(classes[key]!==value||shots[key]!==published.summary.samples_by_provider_class[key])throw Error('Published class totals mismatch.');
 const pool=JSON.parse(readFileSync(resolve(sourceDir,'data/seed.json'))).values;
 const arithmetic=pool.every((v,i)=>Math.abs(v-(.1+i*.0001))<1e-12);
 return {schema:'beastbox-hf-source-audit-v1',repository:manifest.repository,revision:manifest.revision,files,
  archive:{sha256:sha(data),bytes:data.length,records:rows.length,classes,shots,totalShots:Object.values(shots).reduce((a,b)=>a+b,0),uniqueJobs:Object.fromEntries(Object.entries(jobs).map(([k,v])=>[k,v.size])),bitWidths:widths,shotMismatches:0,privateFieldsPresent:false,providerReauthenticated:false},
  overlap:{existingIBMRows:archiveRuns.length,existingQvmRows:qvmRuns.length,hfRowsWithMatchingIBMJob:sharedJobs,hfRowsWithMatchingIBMCountDigest:sharedCounts,hfRowsWithMatchingJobAndCounts:sharedJobCounts,note:'Count collisions or common labels do not by themselves attest a circuit or hardware job.'},
  storedHeartPool:{values:pool.length,first:pool[0],last:pool.at(-1),arithmeticSequence:arithmetic,step:arithmetic?.0001:null,classification:'DETERMINISTIC EXAMPLE POOL; no measurement receipt attached to this file',newQuantumMeasurements:false},
  boundaries:['Integrity is checked against pinned public artifacts; hardware execution is not independently re-attested.','877 legacy unlabelled records remain outside hardware attribution.','The two Azure Rigetti QVM records are SIMULATOR.','Original Python code is not executed or installed in the browser.','Stored identities and histories are not adopted as a user QBEAST.','No cloud-heart jobs, camera requests, raw microphone uploads, credentials or model training are started.']};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const index=process.argv.indexOf('--source-dir'),sourceDir=index>=0?process.argv[index+1]:undefined;
 const report=await auditHuggingFace({sourceDir,fetchSources:process.argv.includes('--fetch')});
 const text=JSON.stringify(report,null,2)+'\n',path=resolve(ROOT,'experiments/hf-genesis-001/source-audit.json');
 if(process.argv.includes('--write'))writeFileSync(path,text);
 if(process.argv.includes('--check')&&readFileSync(path,'utf8')!==text)throw Error('Pinned source audit does not reproduce.');
 console.log(JSON.stringify({records:report.archive.records,classes:report.archive.classes,shots:report.archive.shots,overlap:report.overlap,sha256:sha(text)}));
}
