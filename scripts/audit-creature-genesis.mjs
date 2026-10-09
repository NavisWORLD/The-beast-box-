#!/usr/bin/env node
/** Offline, reproducible audit of retained inputs and deterministic game generation. */
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {readFileSync,writeFileSync,mkdirSync,rmSync} from 'node:fs';
import {resolve} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {inflateSync,gzipSync} from 'node:zlib';
import {canonicalJson,buildGenome,makeSeed,BODIES} from '../apps/beastbox-cloud/public/spark/genome.mjs';
import {renderBeast} from '../apps/beastbox-cloud/public/spark/draw.mjs';
import {Voice} from '../apps/beastbox-cloud/public/spark/voice.mjs';
import {buildQbeast} from '../apps/beastbox-cloud/public/spark/qbeast.mjs';
import {expandRun,validateQvmReceipt,SPARK_INDEX_PATH,SPARK_BASE_PATH,QVM_RECEIPT_PATH} from '../apps/beastbox-cloud/public/spark/runs.mjs';
import {ARCHIVE_RECIPES} from '../apps/beastbox-cloud/lib/companion/archive-menagerie.mjs';

export const BASE_REVISION='aab168e607e5b9a896ead547bfeb88ffc499ccff';
export const STAGE015_REVISION='cd5d9321cb30f5327d14bbdd3f71751b630d81a3';
const DEFAULT_ROOT=fileURLToPath(new URL('../',import.meta.url));
const PUBLIC_ROOT='apps/beastbox-cloud/public';
const OUTPUT='experiments/beast-awakens-001/genesis';
const MAX_EVIDENCE_BYTES=16*1024*1024;
const codePaths=[
 'scripts/audit-creature-genesis.mjs',
 ...['genome','engine','sha','draw','voice','qbeast','identity','runs','qvm-growth'].map(name=>`${PUBLIC_ROOT}/spark/${name}.mjs`),
 'apps/beastbox-cloud/lib/companion/archive-menagerie.mjs',
];
export const sha256=bytes=>createHash('sha256').update(bytes).digest('hex');
const hash=value=>sha256(canonicalJson(value));
const increment=(map,key)=>{map[key]=(map[key]||0)+1;};
const sortedObject=value=>Object.fromEntries(Object.entries(value).sort(([a],[b])=>a<b?-1:a>b?1:0));
const equalMaterial=(a,b)=>typeof a==='string'&&typeof b==='string'?a===b:Buffer.from(a).equals(Buffer.from(b));

/** Equal digests are equivalences only if their exact preimage bytes also agree. */
export class DigestTracker{
 constructor(){this.buckets=new Map();}
 add(digest,material,record){
  const previous=this.buckets.get(digest);
  if(previous){previous.records.push(record);if(!equalMaterial(previous.material,material))previous.conflict=true;}
  else this.buckets.set(digest,{material:typeof material==='string'?material:Buffer.from(material),records:[record],conflict:false});
 }
 groups(){return [...this.buckets].filter(([,value])=>value.records.length>1).map(([digest,value])=>({digest,records:value.records,conflictingMaterial:value.conflict}));}
 summary(){
  const groups=this.groups();
  return {uniqueDigests:this.buckets.size,repeatedDigestGroups:groups.length,repeatedRecords:groups.reduce((sum,group)=>sum+group.records.length,0),extraRecords:groups.reduce((sum,group)=>sum+group.records.length-1,0),identicalMaterialGroups:groups.filter(group=>!group.conflictingMaterial).length,conflictingMaterialGroups:groups.filter(group=>group.conflictingMaterial).length};
 }
}

function readSource(root,path){
 const bytes=readFileSync(resolve(root,path));
 return {bytes,data:JSON.parse(bytes),reference:{path,sha256:sha256(bytes),bytes:bytes.length}};
}
function runTotals(runs){
 const backend={},bits={};
 for(const run of runs){increment(backend,run.backend);increment(bits,String(run.num_bits));}
 return {rows:runs.length,uniqueJobs:new Set(runs.map(run=>`${run.backend}:${run.job_id}`)).size,shots:runs.reduce((sum,run)=>sum+run.shots,0),byBackend:sortedObject(backend),byNumBits:sortedObject(bits)};
}

/** Full real archive, retained gallery order, and a separate lexically sorted experiment input. */
export function loadGenesisSources({root=DEFAULT_ROOT}={}){
 root=root instanceof URL?fileURLToPath(root):resolve(root);
 const index=readSource(root,PUBLIC_ROOT+SPARK_INDEX_PATH);
 if(index.data.schema!=='spark-beasts-public-seed-pack-index-v1'||!Array.isArray(index.data.shards))throw Error('Invalid public seed index.');
 const archiveRuns=[],rowSources=new Map(),tables=[];
 for(const path of [SPARK_BASE_PATH,...index.data.shards]){
  if(!/^\/spark\/[a-z0-9-]+\.json$/.test(path))throw Error('Unapproved archive path.');
  const source=readSource(root,PUBLIC_ROOT+path);
  if(!['spark-beasts-quantum-runs-compact-v1','spark-beasts-public-seed-shard-v1'].includes(source.data.schema)||!Array.isArray(source.data.runs))throw Error('Invalid archive table.');
  const expanded=source.data.runs.map((row,rowIndex)=>{
   const run=expandRun(row);
   // Node crypto is independent of the browser SHA implementation used by expandRun.
   if(hash(run.counts)!==row.h)throw Error('Independent count digest mismatch.');
   if(rowSources.has(run.key))throw Error('Duplicate archive run key: '+run.key);
   rowSources.set(run.key,{path:source.reference.path,fileSha256:source.reference.sha256,rowIndex});
   return run;
  });
  archiveRuns.push(...expanded);
  tables.push({...source.reference,schema:source.data.schema,...runTotals(expanded),circuitPayloadsPublished:false,perJobCreationTimePublished:false});
 }
 const qvmSource=readSource(root,PUBLIC_ROOT+QVM_RECEIPT_PATH);
 const qvmRuns=validateQvmReceipt(qvmSource.data);
 if(hash(qvmSource.data.scenario_records)!==qvmSource.data.public_rows_sha256)throw Error('Independent QVM digest mismatch.');
 for(const row of qvmSource.data.scenario_records){
  const quil=`DECLARE ro BIT[2]\nRESET\nRX(${row.theta_rad.toFixed(12)}) 0\nCNOT 0 1\nMEASURE 0 ro[0]\nMEASURE 1 ro[1]\n`;
  if(row.batches.some(batch=>batch.program_sha256!==sha256(quil)))throw Error('QVM retained program commitment mismatch.');
 }
 const python=readFileSync(resolve(root,'spark-beasts/data/quantum_runs.compact.json'));
 const base=readFileSync(resolve(root,PUBLIC_ROOT+SPARK_BASE_PATH));
 const sources={
  schema:'beast-awakens-genesis-sources-v1',baselineRevision:BASE_REVISION,
  providerReauthenticated:false,newProviderJobs:0,newPhysicalMeasurements:0,
  index:{...index.reference,claimBoundary:index.data.claim_boundary,privacy:index.data.privacy,dedupe:index.data.dedupe},
  tables,archive:runTotals(archiveRuns),
  qvm:{...qvmSource.reference,...runTotals(qvmRuns),scenarioRecordsSha256:hash(qvmSource.data.scenario_records),sourceClass:qvmSource.data.source_class,physicalHardware:false,defaultGalleryIncluded:false,programCommitmentsReconstructed:24,phaseShots:sortedObject(qvmRuns.reduce((out,run)=>{out[run.qvm.phase]=(out[run.qvm.phase]||0)+run.shots;return out;},{}))},
  pythonBaseCopy:{path:'spark-beasts/data/quantum_runs.compact.json',sha256:sha256(python),byteEqualToPublicBase:base.equals(python)},
  generationCode:codePaths.map(path=>{const bytes=readFileSync(resolve(root,path));return {path,sha256:sha256(bytes),bytes:bytes.length};}),
  sourceOmissions:['No live IBM, Azure or Rigetti provider query was made.','The derived IBM seed pack omits raw circuits, per-job timestamps, user/account identifiers and original signal payloads.','Only separately retained receipt subsets can be traced to complete committed result bytes.','Procedural voice envelope hashes are not rendered PCM waveform hashes.'],
 };
 return {root,archiveRuns,sortedArchiveRuns:archiveRuns.slice().sort((a,b)=>a.key<b.key?-1:a.key>b.key?1:0),qvmRuns,rowSources,sources};
}

const phenotype=genome=>Object.fromEntries(Object.entries(genome).filter(([key])=>!['schema','seed','inputs','quantum','engine'].includes(key)));
const fixedUtterance=(genome,stage)=>Voice.utterance(genome.voice,stage,'neutral',0,{focus:0,calm:0,spark:0});

export function duplicateCountWitness(runs){
 const keys=['ibm_kingston:da680fk86m6s738vgm00#pub1','ibm_kingston:da69g1c6l22c73dm1mf0#pub29'];
 const [first,second]=keys.map(key=>runs.find(run=>run.key===key));
 if(!first||!second)throw Error('Retained duplicate-count witness unavailable.');
 const recipe={focus:40,calm:40,spark:40};
 const a=buildGenome(recipe,first,null,10),b=buildGenome(recipe,second,null,10);
 const normalized={...second,key:first.key,backend:first.backend,job_id:first.job_id,pub_index:first.pub_index,shots:first.shots};
 const c=buildGenome(recipe,normalized,null,10);
 return {runKeys:keys,traits:recipe,userId:null,bucket:10,countsSha256:hash(first.counts),sameRawCounts:canonicalJson(first.counts)===canonicalJson(second.counts),sameDyn12:canonicalJson(a.engine.dyn12)===canonicalJson(b.engine.dyn12),sameSeeds:a.seed===b.seed,samePhenotypes:canonicalJson(phenotype(a))===canonicalJson(phenotype(b)),sameStage2Pixels:Buffer.from(renderBeast(a,2,'open')).equals(Buffer.from(renderBeast(b,2,'open'))),normalizedMetadata:{description:'Same raw counts; backend/job/PUB/shots/run key set to the first record.',sameSeeds:a.seed===c.seed,samePhenotypes:canonicalJson(phenotype(a))===canonicalJson(phenotype(c)),sameStage2Pixels:Buffer.from(renderBeast(a,2,'open')).equals(Buffer.from(renderBeast(c,2,'open')))}};
}

/** Every archived row, actual existing page recipe, no saved or fabricated specimens. */
export function censusCreatures({archiveRuns,rowSources}){
 const names=['counts','seed','shortId','genome','phenotype','qbeastGenesis','qbeastSnapshot','dyn12','behavior','voiceParameters','spriteI','spriteII','spriteIII','utteranceI','utteranceII','utteranceIII'];
 const trackers=Object.fromEntries(names.map(name=>[name,new DigestTracker()]));
 const records=[],categories={},geneRanges={},failures=[];
 for(const [ordinal,run] of archiveRuns.entries()){
  try{
   const traits=ARCHIVE_RECIPES[ordinal%ARCHIVE_RECIPES.length];
   const genome=buildGenome(traits,run,null,10),snapshot=buildQbeast(genome);
   const [seed,seedMaterial]=makeSeed(genome.inputs.traits,run,null,10);
   if(seed!==genome.seed||hash(seedMaterial)!==seed)throw Error('Independent seed digest mismatch.');
   const material={counts:canonicalJson(run.counts),seed:canonicalJson(seedMaterial),shortId:seed,genome:canonicalJson(genome),phenotype:canonicalJson(phenotype(genome)),qbeastGenesis:canonicalJson({domain:'genesis',profile:snapshot.profile,public_state:snapshot.public_state,progress:snapshot.progress}),qbeastSnapshot:canonicalJson(Object.fromEntries(Object.entries(snapshot).filter(([key])=>key!=='digest'))),dyn12:canonicalJson(genome.engine.dyn12),behavior:canonicalJson(genome.behavior),voiceParameters:canonicalJson(genome.voice)};
   const hashes={};
   for(const name of ['counts','seed','genome','phenotype','dyn12','behavior','voiceParameters'])hashes[name]=sha256(material[name]);
   hashes.shortId=snapshot.profile.id;
   for(const name of ['qbeastGenesis','qbeastSnapshot'])hashes[name]=sha256('QBEAST1\0'+material[name]);
   if(hashes.qbeastGenesis!==snapshot.events[0].parent||hashes.qbeastSnapshot!==snapshot.digest)throw Error('Independent QBEAST digest mismatch.');
   for(const [stage,roman] of [[1,'I'],[2,'II'],[3,'III']]){
    material['sprite'+roman]=renderBeast(genome,stage,'open');
    hashes['sprite'+roman]=sha256(material['sprite'+roman]);
    material['utterance'+roman]=canonicalJson(fixedUtterance(genome,stage));
    hashes['utterance'+roman]=sha256(material['utterance'+roman]);
   }
   for(const name of names)trackers[name].add(hashes[name],material[name],run.key);
   const features={family:snapshot.profile.family,body:genome.body,island:genome.island,element:genome.element,ears:genome.ears,tail:genome.tail,wings:genome.wings,pattern:genome.pattern,pose:genome.pose,eyeStyle:genome.eye_style,mouth:genome.mouth,glow:genome.glow,facing:genome.facing,temperament:genome.temperament,gait:genome.behavior.gait,voiceStyle:genome.voice.style,voiceWave:genome.voice.wave};
   for(const [key,value] of Object.entries(features)){categories[key]??={};increment(categories[key],value);}
   for(const [key,values] of [['habit',genome.behavior.habits],['quirk',genome.behavior.quirks]])for(const value of values){categories[key]??={};increment(categories[key],value.name);}
   for(const [key,value] of Object.entries(genome.genes)){geneRanges[key]??={min:Infinity,max:-Infinity,values:new Set()};geneRanges[key].min=Math.min(geneRanges[key].min,value);geneRanges[key].max=Math.max(geneRanges[key].max,value);geneRanges[key].values.add(value);}
   const record={ordinal,source:rowSources.get(run.key),input:{runKey:run.key,expandedRunSha256:hash(run),countsSha256:run.counts_sha256,traits,userId:null,bucket:10},seed:genome.seed,profileId:snapshot.profile.id,features,hashes};
   record.recordSha256=hash(record);
   records.push(record);
  }catch(error){failures.push({ordinal,runKey:run.key,error:error.message});}
 }
 const summary={
  schema:'beast-awakens-genesis-census-v1',rows:archiveRuns.length,generated:records.length,failures:failures.length,failureRecords:failures,
  ordering:'Existing base-pack then shard order; page size 12, recipe ordinal modulo 3. This does not alter gallery ordering.',
  traitsRecipes:ARCHIVE_RECIPES,userId:null,bucket:10,stages:[1,2,3],eyes:'open',spriteFormat:'64x64 row-major RGBA Uint8ClampedArray, 16384 raw bytes; no PNG encoder',
  fixedVoice:{mood:'neutral',utteranceIndex:0,drive:{focus:0,calm:0,spark:0},stages:[1,2,3],renderedPcm:false},
  categories:Object.fromEntries(Object.entries(categories).map(([key,value])=>[key,sortedObject(value)])),
  geneRanges:Object.fromEntries(Object.entries(geneRanges).map(([key,value])=>[key,{min:value.min,max:value.max,distinctValues:value.values.size}])),
  expectedBodies:BODIES,expectedFamilies:['nebula','aurora','void','plasma','memory','signal','starlight'],
  digests:Object.fromEntries(Object.entries(trackers).map(([name,tracker])=>[name,tracker.summary()])),
  cohortSha256:hash(records.map(record=>record.recordSha256)),
  duplicateCountWitness:duplicateCountWitness(archiveRuns),
  claimBoundary:'Deterministic game/art morphology and procedural voice envelope census; no hardware execution, learned intelligence, evolutionary gain or quantum advantage is inferred.',
 };
 return {summary,records,countEquivalences:trackers.counts.groups(),digestConflicts:Object.fromEntries(Object.entries(trackers).map(([name,tracker])=>[name,tracker.groups().filter(group=>group.conflictingMaterial)]))};
}

/** Decode only the retained, explicitly typed one-byte-per-shot NumPy BitArrays. */
function retainedBitArrayCounts(result){
 const pubs=result?.__value__?.pub_results;
 if(result.__type__!=='PrimitiveResult'||!Array.isArray(pubs)||pubs.length!==1)throw Error('Unrecognized retained IBM result.');
 const bitarray=pubs[0]?.__value__?.data?.__value__?.fields?.c;
 if(bitarray?.__type__!=='BitArray'||bitarray.__value__.array?.__type__!=='ndarray')throw Error('Unrecognized retained BitArray.');
 const bits=bitarray.__value__.num_bits,npy=inflateSync(Buffer.from(bitarray.__value__.array.__value__,'base64'));
 if(!npy.subarray(0,6).equals(Buffer.from([0x93,0x4e,0x55,0x4d,0x50,0x59]))||npy[6]!==1||bits<1||bits>8)throw Error('Unsupported retained NumPy encoding.');
 const headerLength=npy.readUInt16LE(8),header=npy.subarray(10,10+headerLength).toString('ascii');
 const shape=/['"]shape['"]:\s*\((\d+),\s*1\s*\)/.exec(header);
 if(!shape||!header.includes("'descr': '|u1'")||!header.includes("'fortran_order': False"))throw Error('Unexpected retained NumPy shape.');
 const samples=npy.subarray(10+headerLength),counts={};
 if(samples.length!==Number(shape[1]))throw Error('Retained BitArray shot size mismatch.');
 for(const value of samples){if(value>=2**bits)throw Error('Retained BitArray overflow.');const key=value.toString(2).padStart(bits,'0');counts[key]=(counts[key]||0)+1;}
 return {counts,shots:samples.length,numBits:bits};
}

export function auditRetainedReceipts({root,archiveRuns}){
 const sourceRoot='experiments/zeref-origin-heart-001/source/ibm/';
 const manifest=readSource(root,sourceRoot+'source-manifest.json'),ibm=[];
 for(const job of manifest.data.jobs){
  const result=readSource(root,sourceRoot+`job-${job.job_id}-result.json`),info=readSource(root,sourceRoot+`job-${job.job_id}-info.json`);
  const decoded=retainedBitArrayCounts(result.data),run=archiveRuns.find(run=>run.backend===job.backend&&run.job_id===job.job_id&&run.pub_index===0);
  if(result.reference.sha256!==manifest.data.committed_result_sha256[job.job_id]||hash(result.data)!==manifest.data.canonical_result_sha256[job.job_id]||!run||hash(decoded.counts)!==run.counts_sha256||decoded.shots!==job.shots||info.data.status!=='Completed')throw Error('Retained IBM receipt mismatch.');
  ibm.push({jobId:job.job_id,backend:job.backend,sourceClass:job.source_class,status:info.data.status,created:info.data.created,result:result.reference,sanitizedInfo:info.reference,canonicalResultSha256:hash(result.data),countsSha256:hash(decoded.counts),shots:decoded.shots,numBits:decoded.numBits,archiveRunKey:run.key,rawResultVerified:true,providerReauthenticated:false,rawCircuitPublished:false,infoHashNote:'Committed info is a sanitized projection; raw_info_sha256 in the source manifest refers to the original unsanitized source.'});
 }
 const origin=readSource(root,'experiments/zeref-dad-son-001/evidence/ibm/fresh-marrakesh-origin-seed.json');
 const verification=readSource(root,'experiments/zeref-dad-son-001/evidence/ibm/fresh-marrakesh-verification.json');
 if(hash(origin.data.counts)!==origin.data.counts_sha256||Object.values(origin.data.counts).reduce((a,b)=>a+b,0)!==origin.data.shot_count)throw Error('Retained Marrakesh origin count mismatch.');
 const originRows=archiveRuns.filter(run=>run.job_id===origin.data.job_id);
 const witnessesPath='evidence/final-whole-organism-001/resource-source/historical-hardware-witnesses.jsonl';
 const witnessBytes=readFileSync(resolve(root,witnessesPath)),witnesses=witnessBytes.toString('utf8').trim().split('\n').map(line=>JSON.parse(line));
 const statuses=['evidence/final-whole-organism-001/resource-source/STATUS.json','evidence/final-whole-organism-001/ibm-path/STATUS.json'].map(path=>{const source=readSource(root,path);return {...source.reference,status:source.data};});
 const pinnedPaths=['evidence/stage015/azure-qvm-24-job-public-receipt.json','evidence/stage015/qwen-192-forecast-public-receipt.json','evidence/stage015/independent-audit.json'];
 const stage015=pinnedPaths.map(path=>{
  let bytes;
  try{bytes=execFileSync('git',['show',`${STAGE015_REVISION}:${path}`],{cwd:root,env:{...process.env,GIT_NO_LAZY_FETCH:'1'},timeout:10000,maxBuffer:4*1024*1024,stdio:['ignore','pipe','pipe']});}
  catch{return {revision:STAGE015_REVISION,path,availableAsGitObject:false,error:'Pinned object unavailable; no remote provider claim can be reauthenticated by this offline audit.'};}
   const data=JSON.parse(bytes),entry={revision:STAGE015_REVISION,path,sha256:sha256(bytes),bytes:bytes.length,availableAsGitObject:true,providerReauthenticated:false};
   if(path.includes('azure-qvm')){entry.sourceClass=data.source_class;entry.scenarioRecordsSha256=hash(data.scenario_records);entry.matchesCurrentPublicRows=entry.scenarioRecordsSha256==='7ef23c00005a2053d1fc830985330f4db322b3bf6144fd79fd1561d14c425599';if(!entry.matchesCurrentPublicRows)throw Error('Pinned QVM rows do not match.');}
   if(path.includes('qwen-192')){entry.completedModelGenerations=data.actual_model_generations_completed;entry.newQuantumJobs=data.new_azure_quantum_jobs;entry.modelWeightsUpdated=data.model_weights_updated;entry.model=data.model;entry.modelRevision=data.pinned_model_revision;entry.publicPromptDigest=data.public_prompt_digest;entry.retainedResults=data.cohort_arm_results_unranked;entry.classicalReference=data.explicit_classical_reference;entry.pairedUncertainty=data.predeclared_paired_uncertainty;}
   if(path.includes('independent-audit'))entry.audit=data;
   return entry;
 });
 return {providerReauthenticated:false,sourceManifest:manifest.reference,verifiedResultJobs:ibm,historicalMarrakeshOrigin:{source:origin.reference,verification:verification.reference,jobId:origin.data.job_id,backend:origin.data.backend,countsSha256:hash(origin.data.counts),shots:origin.data.shot_count,sourceClass:origin.data.source_class,created:null,archivedNow:true,providerReauthenticated:false,rawCircuitPublished:false,archiveRunKeys:originRows.map(run=>run.key),sameCountsInArchive:originRows.some(run=>run.counts_sha256===origin.data.counts_sha256),syntheticContinuationNewQuantumEntropy:verification.data.synthetic_continuation_new_quantum_entropy,waveformQuantumEntropy:origin.data.waveform_quantum_entropy},externalHardwareWitnesses:{path:witnessesPath,sha256:sha256(witnessBytes),count:witnesses.length,records:witnesses,rawResultsNotReauthenticatedHere:true},sealedPathStatuses:statuses,stage015};
}

export function encodeRecordArchive(records){
 const plain=Buffer.from(records.map(record=>canonicalJson(record)+'\n').join(''));
 if(plain.length>MAX_EVIDENCE_BYTES)throw Error('Decompressed record archive exceeds its byte bound.');
 const bytes=gzipSync(plain,{level:9,mtime:0});
 bytes.writeUInt32LE(0,4); // canonical gzip mtime; no host clock information
 bytes[9]=255; // OS unknown; remove a host-specific header byte
 return {bytes,recordCount:records.length,decompressedBytes:plain.length,decompressedSha256:sha256(plain)};
}

function evidenceFiles(sources,census){
 const sourceInventory={...sources.sources,retainedReceipts:auditRetainedReceipts(sources)};
 const json=value=>canonicalJson(value)+'\n';
 const recordArchive=encodeRecordArchive(census.records);
 const files=new Map([
  ['source-inventory.json',json(sourceInventory)],
  ['census-summary.json',json(census.summary)],
  ['creature-records.jsonl.gz',recordArchive.bytes],
  ['count-equivalences.json',json({schema:'beast-awakens-count-equivalences-v1',groups:census.countEquivalences,digestConflicts:census.digestConflicts})],
  ['qvm-inputs.json',json({schema:'beast-awakens-retained-simulator-inputs-v1',source:sources.sources.qvm,runs:sources.qvmRuns,claimBoundary:'24 retained simulator batches; no new cloud job and no physical QPU measurement.'})],
 ]);
 const entries=[...files].map(([path,bytes])=>({path,sha256:sha256(bytes),bytes:Buffer.byteLength(bytes),...(path.endsWith('.gz')?{encoding:'gzip',decompressedSha256:recordArchive.decompressedSha256,decompressedBytes:recordArchive.decompressedBytes,recordCount:recordArchive.recordCount,compression:{level:9,mtime:0,osByte:255,zlibVersion:process.versions.zlib}}:{})}));
 files.set('digest-manifest.json',json({schema:'beast-awakens-genesis-evidence-manifest-v1',baselineRevision:BASE_REVISION,cohortSha256:census.summary.cohortSha256,recordCount:census.records.length,files:entries,maxFileBytes:MAX_EVIDENCE_BYTES,manifestSelfHashExcluded:true}));
 for(const [path,bytes] of files)if(Buffer.byteLength(bytes)>MAX_EVIDENCE_BYTES)throw Error('Evidence byte bound exceeded: '+path);
 return files;
}

async function main(){
 const args=process.argv.slice(2),known=new Set(['--write','--check','--sources-only']);
 if(args.some(arg=>!known.has(arg))||args.length>1)throw Error('Usage: node scripts/audit-creature-genesis.mjs [--write | --check | --sources-only]');
 const sources=loadGenesisSources();
 if(args.includes('--sources-only')){console.log(JSON.stringify({archive:sources.sources.archive,qvm:sources.sources.qvm,providerReauthenticated:false}));return;}
 const census=censusCreatures(sources);
 if(census.summary.failures)throw Error('Genome generation failed for '+census.summary.failures+' rows.');
 if(args.includes('--write')||args.includes('--check')){
  const files=evidenceFiles(sources,census),out=resolve(sources.root,OUTPUT);
  if(args.includes('--write')){mkdirSync(out,{recursive:true});rmSync(resolve(out,'creature-records.jsonl'),{force:true});}
  for(const [path,content] of files){
   if(args.includes('--write'))writeFileSync(resolve(out,path),content);
   else if(!readFileSync(resolve(out,path)).equals(Buffer.from(content)))throw Error('Evidence reproduction mismatch: '+path);
  }
 }
 console.log(JSON.stringify({archive:sources.sources.archive,qvm:sources.sources.qvm,generated:census.summary.generated,failures:census.summary.failures,cohortSha256:census.summary.cohortSha256,digests:census.summary.digests,mode:args[0]||'summary',providerReauthenticated:false}));
}

if(process.argv[1]&&pathToFileURL(resolve(process.argv[1])).href===import.meta.url)main().catch(error=>{console.error(error.message);process.exitCode=1;});
