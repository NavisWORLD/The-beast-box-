import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {buildCorpus,featuresFromCounts,featureRow,splitIbmRuns,FEATURE_LABELS} from '../../../scripts/prepare_rawrphos_quantum_conditioning.mjs';
import {expandRun} from '../public/spark/runs.mjs';

const sha=x=>createHash('sha256').update(x).digest('hex');
let memo=null;
function corpus(){return memo??=buildCorpus();}
function records(rows){return rows.trim().split('\n').filter(Boolean).map(JSON.parse);}

test('actual published IBM inventory and 24 simulator batches are independently classified',()=>{
 const {manifest,contents}=corpus();
 assert.equal(manifest.snapshots.archive.rows,5676);
 assert.equal(manifest.snapshots.archive.uniqueJobs,267);
 assert.equal(manifest.snapshots.archive.shots,25576380);
 assert.ok(manifest.snapshots.additional_recorded_ibm.rows>=20);
 assert.ok(manifest.snapshots.additional_recorded_ibm.jobs>=10);
 assert.equal(manifest.snapshots.qvm_simulator.rows,24);
 assert.equal(manifest.snapshots.qvm_simulator.shots,2048);
 assert.equal(manifest.model_weights_updated,false);
 assert.equal(manifest.provider_jobs_submitted,0);
 assert.equal(manifest.owner_private_training_data_imported,false);
 const ibm=['train','validation','test'].flatMap(s=>records(contents['ibm-'+s+'.jsonl']));
 const sim=records(contents['rigetti-qvm-simulator-held-separate.jsonl']);
 assert.equal(ibm.length,manifest.snapshots.combined_ibm.rows);
 assert.ok(ibm.every(r=>r.source_class==='RECORDED_IBM_HARDWARE'&&r.role==='STATE_CONDITIONING_ONLY'));
 assert.ok(sim.every(r=>r.source_class==='RECORDED_AZURE_RIGETTI_QVM_SIMULATOR'&&r.split==='simulator_separate'));
 assert.equal(new Set(ibm.map(r=>r.run_key)).size,ibm.length);
 assert.equal(new Set(sim.map(r=>r.run_key)).size,sim.length);
 assert.ok(ibm.every(r=>r.features.length===12&&r.features.every(x=>Number.isFinite(x)&&x>=0&&x<=1)));
 assert.ok([...ibm,...sim].every(r=>r.action_label===null&&r.reward_label===null&&r.dialogue_target===null));
});
test('no IBM job and no identical count digest spans train/validation/test',()=>{
 const {contents}=corpus(),jobs=new Map(),counts=new Map();
 for(const split of ['train','validation','test']){
  for(const r of records(contents['ibm-'+split+'.jsonl'])){
   const job=r.backend+':'+r.job_id;
   for(const [table,key] of [[jobs,job],[counts,r.counts_sha256]]){
    assert.ok(!table.has(key)||table.get(key)===split,'Train/test leakage: '+key);
    table.set(key,split);
   }
  }
 }
});
test('byte digests reproduce, stable source references, and no personal conversation or secrets',()=>{
 const {manifest,contents}=corpus();
 for(const [name,ref] of Object.entries(manifest.exports)){
  assert.equal(sha(Buffer.from(contents[name])),ref.sha256);
  assert.equal(Buffer.byteLength(contents[name]),ref.bytes);
 }
 for(const source of manifest.source_files){
  const root=fileURLToPath(new URL('../../../',import.meta.url));
  assert.equal(sha(readFileSync(root+source.path)),source.sha256);
 }
 assert.doesNotMatch(JSON.stringify(manifest),/BEASTBOX_CLOUD_AUTH_SECRET|hf_[A-Za-z0-9]{30}|AKIA[0-9A-Z]{16}/);
});
test('known numerical feature proportions and tamper rejection do not relabel outcomes',()=>{
 const run={num_bits:2,shots:10,counts:{'00':5,'01':1,'10':1,'11':3}};
 const f=featuresFromCounts(run);
 assert.equal(f.length,FEATURE_LABELS.length);
 assert.deepEqual(f.slice(0,5),[.4,.4,0,0,0]);
 assert.equal(f[6],.8); // even parity: 00 and 11
 assert.equal(f[10],.5);assert.equal(f[11],.3);
 const good={k:'fake',b:'ibm_fez',j:'job',p:0,n:2,s:10,c:'00:5,01:1,10:1,11:3',h:'0'.repeat(64)};
 assert.throws(()=>expandRun(good),/digest/i);
});
test('splitter rejects leakage by pinning full jobs and identical distributions',()=>{
 const fixture=[
  {key:'x',backend:'ibm_fez',job_id:'a',counts_sha256:'1'.repeat(64)},
  {key:'y',backend:'ibm_fez',job_id:'a',counts_sha256:'2'.repeat(64)},
  {key:'z',backend:'ibm_fez',job_id:'b',counts_sha256:'2'.repeat(64)},
 ];
 const labels=splitIbmRuns(fixture);
 assert.equal(labels.get('x'),labels.get('y'));
 assert.equal(labels.get('y'),labels.get('z'));
});
