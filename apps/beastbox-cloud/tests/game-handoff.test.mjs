import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {buildGenome} from '../public/spark/genome.mjs';
import {buildQbeast,serializeQbeast} from '../public/spark/qbeast.mjs';
import {buildSave,profileFromBeastJson,MAILBOX_OFFSET} from '../lib/companion/lcx1.mjs';
const {createGameHandoff}=await import('../lib/companion/game-handoff.mjs');
const row=JSON.parse(readFileSync(new URL('../public/spark/runs.json',import.meta.url))).runs[0];
const run={key:row.k,backend:row.b,job_id:row.j,pub_index:row.p,num_bits:row.n,shots:row.s,counts_sha256:row.h,counts:Object.fromEntries(row.c.split(',').map(p=>{const[k,v]=p.split(':');return[k,+v]}))};
function creature(traits={focus:30,calm:50,spark:80}){const genome=buildGenome(traits,run,'Sol',10);return{genome,seed:genome.seed,qbeast:buildQbeast(genome)}}
function native(beast){return Buffer.from(buildSave(profileFromBeastJson(beast.qbeast.profile,beast.genome.inputs.traits))).toString('base64')}
test('a first handoff carries the exact public QBEAST without invented native progress',()=>{
 const beast=creature(),before=structuredClone(beast),handoff=createGameHandoff(beast);
 assert.deepEqual(handoff,{type:'sol-spark-qbeast',text:serializeQbeast(beast.qbeast)});
 assert.deepEqual(beast,before);
});
test('the saved native mailbox is retained byte for byte from either supported state location',()=>{
 const beast=creature(),saved=native(beast);
 for(const state of [{game:{native_save:saved}},{localGrowth:{qbeast_id:beast.qbeast.profile.id,seed:beast.seed,game:{native_save:saved}}}]){
  const input={...beast,...state},before=structuredClone(input);
  assert.equal(createGameHandoff(input).native_save,saved);assert.deepEqual(input,before);
 }
});
test('corrupt, wrong-identity, invalid-size and empty saved batteries fail closed',()=>{
 const beast=creature(),other=creature({focus:90,calm:10,spark:10});
 const damaged=Buffer.from(native(beast),'base64');damaged[MAILBOX_OFFSET+10]^=1;
 for(const saved of [null,'',native(other),damaged.toString('base64'),'a'.repeat(43692),'not-a-save'])assert.throws(()=>createGameHandoff({...beast,game:{native_save:saved}}));
 assert.throws(()=>createGameHandoff({...beast,seed:other.seed}),/identity|seed/i);
 assert.throws(()=>createGameHandoff({...beast,genome:{...beast.genome,seed:other.seed}}),/identity|seed/i);
 assert.throws(()=>createGameHandoff({...beast,localGrowth:{qbeast_id:other.qbeast.profile.id,seed:beast.seed,game:{native_save:native(beast)}}}),/identity/i);
});
test('conflicting supported save locations require recovery instead of silently choosing one',()=>{
 const beast=creature(),saved=native(beast);
 assert.throws(()=>createGameHandoff({...beast,game:{native_save:saved},localGrowth:{game:{native_save:'invalid'}}}),/conflict/i);
 assert.equal(createGameHandoff({...beast,game:{native_save:saved},localGrowth:{game:{native_save:saved}}}).native_save,saved);
});
test('a quarantined portable journey remains separate from a verified native handoff',()=>{
 const beast=creature();beast.journeyNative={status:'unsigned-unverified',game:{native_save:native(beast)}};
 assert.equal(Object.hasOwn(createGameHandoff(beast),'native_save'),false);
});
