import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {loadSparkRuns} from '../public/spark/runs.mjs';
import {buildGenome,BODIES} from '../public/spark/genome.mjs';
import {buildQbeast} from '../public/spark/qbeast.mjs';
import {simulateStable} from '../public/spark/signal.mjs';

const source=await readFile(new URL('../public/spark/app.mjs',import.meta.url),'utf8');
const start=source.indexOf('function starterEntries(){'),end=source.indexOf('/** Source-pinned recipes',start);
assert.ok(start>0&&end>start);
const originalFetch=globalThis.fetch;
let runs;
try{
 globalThis.fetch=async path=>Response.json(JSON.parse(await readFile(new URL('../public'+path,import.meta.url),'utf8')));
 runs=await loadSparkRuns({includeQvm:true,includeNewHardware:true});
}finally{globalThis.fetch=originalFetch;}
function gallery(rows){
 let calls=0;
 const context={runs:rows,starterCache:[],BODIES,simulateStable,buildGenome:(...args)=>{calls++;return buildGenome(...args);}};
 const entries=vm.runInNewContext(source.slice(start,end)+';starterEntries()',context);
 const snapshot=JSON.parse(JSON.stringify(entries.map(entry=>{const genome=buildGenome(entry.traits,rows.find(row=>row.key===entry.run),entry.user,10);return{recipe:entry,seed:genome.seed,id:buildQbeast(genome).profile.id,body:genome.body,island:genome.island};})));
 return {snapshot,calls};
}
const baselineUrl=new URL('./fixtures/spark-starter-gallery-d7d56557.json',import.meta.url);
// Captured before the repair from the exhaustive d7d56557 gallery, with the
// unchanged bd02fa22 seed archives. CI never regenerates these identities.
const baseline=JSON.parse(await readFile(baselineUrl,'utf8'));
test('starter gallery preserves every archived full recipe, seed and QBEAST while bounding startup work',()=>{
 const result=gallery(runs);assert.deepEqual(result.snapshot,baseline.full);
 assert.ok(result.calls<=256,'eager candidate builds must be bounded; actual '+result.calls);
 assert.equal(new Set(result.snapshot.map(row=>row.body)).size,BODIES.length);
 assert.ok(new Set(result.snapshot.map(row=>row.island)).size>=8);
});
test('partial archives exhaust the finite source and retain exact gallery order and identities',()=>{assert.deepEqual(gallery(runs.slice(0,1)).snapshot,baseline.partial);});
test('empty source produces no manufactured creature',()=>{assert.deepEqual(gallery([]).snapshot,baseline.empty);});
