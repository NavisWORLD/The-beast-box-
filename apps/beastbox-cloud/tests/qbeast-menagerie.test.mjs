import test from 'node:test';
import assert from 'node:assert/strict';
import {ARCHIVE_RECIPES,archiveProvenance,makeArchiveMenagerie} from '../lib/companion/archive-menagerie.mjs';
const row=(key,backend='ibm_marrakesh')=>({key,backend,job_id:key.split(':').pop(),pub_index:0,num_bits:1,shots:4096,counts:{'0':2880,'1':1216},counts_sha256:'1'.repeat(64)});
test('archive labels do not promote simulator results into QPU claims',()=>{
 assert.equal(archiveProvenance('rigetti_qvm'),'SIMULATOR');
 assert.equal(archiveProvenance('ionq.simulator'),'SIMULATOR');
 assert.equal(archiveProvenance('ibm_marrakesh'),'RECORDED IBM COUNTS');
 assert.equal(archiveProvenance('unknown'),'RECORDED SEED DATA');
});
test('archive examples are deterministic, bounded and not given earned stats',()=>{
 const runs=Array.from({length:18},(_,i)=>row('ibm_marrakesh:archive-job-'+i));
 const a=makeArchiveMenagerie(runs,12),b=makeArchiveMenagerie(runs,12);
 assert.ok(a.length>0&&a.length<=12);
 assert.deepEqual(a.map(x=>x.id),b.map(x=>x.id));
 assert.equal(new Set(a.map(x=>x.id)).size,a.length);
 for(const item of a){
  assert.equal(item.sourceClass,'DERIVED PREVIEW');
  assert.equal(item.stage,1);
  assert.ok(item.genome.seed);
  assert.ok(item.countsHash);
  assert.ok(item.runKey.startsWith('ibm_marrakesh:'));
  assert.ok(!('xp' in item)&&!('bond' in item)&&!('owner' in item));
 }
 assert.ok(ARCHIVE_RECIPES.every(x=>Object.isFrozen(x)));
});
test('empty or malformed tables do not invent specimens',()=>{
 assert.deepEqual(makeArchiveMenagerie([],12),[]);
 assert.deepEqual(makeArchiveMenagerie([null,{key:'broken'}],12),[]);
 assert.deepEqual(makeArchiveMenagerie([row('ibm_foo:test')],0),[]);
});

test('every archived source row can be visited through sequential bounded pages',()=>{
 const runs=Array.from({length:30},(_,i)=>row('ibm_marrakesh:page-'+i));
 const chunks=[];
 for(let p=0;p<Math.ceil(runs.length/12);p++)chunks.push(...makeArchiveMenagerie(runs.slice(p*12,(p+1)*12),12));
 assert.equal(chunks.length,30);
 assert.equal(new Set(chunks.map(item=>item.runKey)).size,30);
 assert.equal(new Set(chunks.map(item=>item.id)).size,30);
});
