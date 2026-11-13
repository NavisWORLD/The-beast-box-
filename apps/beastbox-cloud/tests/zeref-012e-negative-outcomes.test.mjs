import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {runEpisode,buildDataset,SCHEMA,QBEAST} from '../../../scripts/zeref_012e_collision_dataset.mjs';
const root=fileURLToPath(new URL('../../../',import.meta.url));
const sha=s=>createHash('sha256').update(s).digest('hex');
let cached;
function fixture(){return cached??=buildDataset();}
test('existing pocket emits both blocked and successful canonical experiences without hidden map',()=>{
 const x=runEpisode({split:'train',index:0,policy:'greedy-frontier'});
 assert.equal(x.examples.length,40);
 assert.ok(x.proof.chain_head.length===64);
 assert.equal(x.proof.events,40);
 for(const e of x.examples){
  assert.equal(e.schema,SCHEMA);
  assert.equal(e.qbeast_id,QBEAST);
  assert.equal(e.source_class,'deterministic_pocket_simulation');
  assert.equal(e.native_game_progress,false);
  assert.equal(e.quantum_action_pair_verified,false);
  assert.equal(e.personal_user_data,false);
  assert.equal(e.labels_from_verified_outcome,true);
  assert.equal(e.source_record_sha256.length,64);
  if(e.eligible_unknown_rift_attempt){
   assert.equal(e.observation.neighbors[e.action].kind,'open');
   assert.equal(e.unseen_rift_collision,Number(e.observed_outcome==='rift'));
  }else assert.equal(e.unseen_rift_collision,0);
  assert.ok(!('rifts' in e.observation),'hidden rift oracle must not leak');
 }
});
test('train, validation and heldout layout IDs never overlap',()=>{
 const m=fixture().manifest;
 assert.deepEqual(Object.fromEntries(Object.entries(m.rows).map(([s,r])=>[s,r.layouts])),
   {train:32,validation:12,heldout:24});
 assert.deepEqual(Object.fromEntries(Object.entries(m.rows).map(([s,r])=>[s,r.episodes])),
   {train:96,validation:36,heldout:72});
 assert.equal(m.rows.train.records,3840);
 assert.equal(m.rows.validation.records,1440);
 assert.equal(m.rows.heldout.records,2880);
 const idSets=Object.fromEntries(Object.entries(m.evidence).map(([s,v])=>[s,new Set(v.episodes.map(x=>x.key))]));
 assert.equal(idSets.train.size,32);
 assert.equal(idSets.validation.size,12);
 assert.equal(idSets.heldout.size,24);
 for(const a of Object.keys(idSets))for(const b of Object.keys(idSets)){
  if(a!==b)assert.ok([...idSets[a]].every(k=>!idSets[b].has(k)));
 }
});
test('all split outputs and source code reproduce exact SHA-256s',()=>{
 const {manifest:m,contents:c}=fixture();
 for(const [name,info] of Object.entries(m.artifacts)){
  assert.equal(sha(c[name]),info.sha256);
  assert.equal(Buffer.byteLength(c[name]),info.bytes);
 }
 for(const [name,hash] of Object.entries(m.source_files_sha256)){
  assert.equal(sha(readFileSync(root+name)),hash);
 }
 assert.equal(m.verified_quantum_action_pairs,0);
 assert.equal(m.approved_Zeref_parent_modified,false);
 assert.equal(m.production_weights_modified,false);
 assert.equal(m.private_user_data_used,false);
});
test('collision positives are observed not created as reinforcement rewards or oracle estimates',()=>{
 const {manifest:m,contents:c}=fixture();
 for(const split of ['train','validation','heldout']){
  const rows=c[split+'.jsonl'].trim().split('\n').map(JSON.parse);
  const positives=rows.filter(x=>x.unseen_rift_collision===1);
  assert.equal(positives.length,m.rows[split].previously_hidden_rift_collisions);
  assert.ok(positives.length>0);
  assert.ok(positives.every(x=>x.observed_outcome==='rift'&&x.observed_reward===-1));
  assert.ok(rows.some(x=>x.observed_outcome==='new_cell'));
  assert.ok(rows.every(x=>x.source_record_sha256.length===64));
 }
});
