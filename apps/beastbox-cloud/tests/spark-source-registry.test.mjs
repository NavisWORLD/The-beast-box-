import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import * as registry from '../public/spark/runs.mjs';
import {buildGenome} from '../public/spark/genome.mjs';
import {buildQbeast,serializeQbeast} from '../public/spark/qbeast.mjs';
import {replaySpark} from '../public/spark/identity.mjs';

const read=path=>JSON.parse(readFileSync(new URL('../public'+path,import.meta.url),'utf8'));
const sha=text=>createHash('sha256').update(text).digest('hex');
const compact=()=>({k:'ibm_example:test',b:'ibm_example',j:'test',p:0,n:1,s:4,c:'0:3,1:1',h:sha('{"0":3,"1":1}')});
const receipt=()=>read('/spark/rigetti-qvm-sim.json');
function localFetch(t,transform=value=>value){
 t.mock.method(globalThis,'fetch',async path=>new Response(JSON.stringify(transform(read(path),path)),{status:200}));
}

test('count integrity rejects changed digests, shots and malformed compact outcomes',()=>{
 assert.deepEqual(registry.expandRun(compact()).counts,{'0':3,'1':1});
 for(const change of [
  {h:'0'.repeat(64)},{s:5},{c:'0:3,1:-1'},{c:'0:3,1:1.5'},
  {c:'0:3,0:1'},{c:'00:3,1:1'},{c:'x:3,1:1'},
  {c:'0:9007199254740992,1:1'},{n:0},{p:-1},{s:0},
 ])assert.throws(()=>registry.expandRun({...compact(),...change}));
});

test('a declared QVM digest cannot substitute for hashing the retained scenario records',()=>{
 assert.equal(typeof registry.validateQvmReceipt,'function');
 const valid=registry.validateQvmReceipt(receipt());
 assert.equal(valid.length,24);
 assert.equal(valid.reduce((sum,run)=>sum+run.shots,0),2048);
 assert.ok(valid.every(run=>run.backend==='rigetti.sim.qvm'&&run.qvm.program_sha256.length===64));
 const edited=receipt();
 edited.scenario_records[0].theta_rad+=0.001;
 assert.throws(()=>registry.validateQvmReceipt(edited),/digest/i);
 const fractional=receipt();
 fractional.scenario_records[0].batches[0].counts['00']=61.9;
 assert.throws(()=>registry.validateQvmReceipt(fractional));
 const hardware=receipt();hardware.physical_hardware_jobs_permitted=1;
 assert.throws(()=>registry.validateQvmReceipt(hardware));
});

test('the default registry retains every published IBM row in existing gallery order',async t=>{
 localFetch(t);
 const runs=await registry.loadSparkRuns();
 const index=read('/spark/user-seeds-20261004.json');
 const expected=['/spark/runs.json',...index.shards].flatMap(path=>read(path).runs.map(row=>row.k));
 assert.equal(runs.length,5676);
 assert.deepEqual(runs.map(run=>run.key),expected);
 assert.ok(runs.every(run=>run.backend.startsWith('ibm_')));
});

test('explicit simulator opt-in enables replay without changing the default gallery',async t=>{
 localFetch(t);
 const runs=await registry.loadSparkRuns({includeQvm:true});
 assert.equal(runs.length,5700);
 assert.equal(runs.filter(run=>run.backend==='rigetti.sim.qvm').length,24);
 const run=runs.find(run=>run.backend==='rigetti.sim.qvm');
 const genome=buildGenome({focus:40,calm:40,spark:40},run,null,10);
 const loaded=replaySpark(serializeQbeast(buildQbeast(genome)),new Map(runs.map(row=>[row.key,row])));
 assert.equal(loaded.gen.seed,genome.seed);
 assert.equal((await registry.loadSparkRuns()).length,5676);
});

test('conflicting rows sharing a run key are rejected instead of silently replacing source evidence',async t=>{
 localFetch(t,(table,path)=>{
  if(path!=='/spark/user-seeds-20261004-1.json')return table;
  const conflicting=structuredClone(read('/spark/runs.json').runs[0]);
  conflicting.j='another-job';
  return {...table,runs:[conflicting,...table.runs]};
 });
 await assert.rejects(registry.loadSparkRuns(),/conflict/i);
});
