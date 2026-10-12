import test from 'node:test';
import assert from 'node:assert/strict';
import {makeRecord,verifyStream,trainingEligible,diaryEntryRecords,qvmReceiptRecord,ibmRecordedRecord,ORIGINS,recordHash} from '../lib/zeref/experience-record.mjs';
import {BASELINES,createGridEnv,metrics,notePolicyOutcome,observe,restoreEnv,snapshotEnv,stepEnv} from '../lib/zeref/pocket-grid-env.mjs';

const D='23b4e2d6f736cf25f32242d0910d18df6939c3a89b1b50efecb83e94161363ad';
const base={qbeast_id:'bb-deada969',origin:'deterministic_pocket_simulation',observation:{cell:1},action:{key:'UP'},outcome:{kind:'new_cell',observed:true},
 reward:{kind:'computed_reward',value:1,rule:'r'}};

test('origins are a closed list and simulations never claim game progress',()=>{
 assert.deepEqual([...ORIGINS],['live_browser','original_native_rom','deterministic_pocket_simulation','azure_rigetti_qvm_simulation','ibm_recorded_historical']);
 const r=makeRecord(base);assert.equal(r.simulated,true);assert.equal(r.real_game_progress,false);
 assert.throws(()=>makeRecord({...base,origin:'native_rom_maybe'}));
 const forged={...r,real_game_progress:true};forged.hash=recordHash(forged);
 assert.equal(verifyStream([forged]).reason,'simulation-claims-game-progress');
});

test('quantum and recorded IBM records are state inputs, never actions or training targets',()=>{
 assert.throws(()=>makeRecord({...base,origin:'azure_rigetti_qvm_simulation'}),/state input/);
 const q=qvmReceiptRecord({kind:'rigetti-qvm-simulated',target:'rigetti.sim.qvm',shots:256,counts:{'101':200,'000':56},circuit_params:{},job_id:'j',counts_sha256:'a'.repeat(64)},{qbeast_id:'bb-7f9c2a03'});
 const i=ibmRecordedRecord({job_id:'db4q484vf2bc73cuuuag',backend:'ibm_fez'},{qbeast_id:'bb-deada969'});
 assert.equal(q.simulated,true);assert.equal(i.simulated,false);
 assert.equal(trainingEligible(q,{identity:'bb-7f9c2a03'}).ok,false);
 assert.equal(trainingEligible(i,{identity:'bb-deada969'}).ok,false);
});

test('consent: private scopes need explicit owner approval of that scope',()=>{
 const mic=makeRecord({...base,origin:'live_browser',consent:{scope:'microphone',owner_approved:false}});
 assert.equal(trainingEligible(mic,{identity:'bb-deada969'}).ok,false);
 const ok=makeRecord({...base,origin:'live_browser',consent:{scope:'microphone',owner_approved:true}});
 assert.equal(trainingEligible(ok,{identity:'bb-deada969'}).ok,false,'approved flag alone is not enough');
 assert.equal(trainingEligible(ok,{identity:'bb-deada969',approvedScopes:['microphone']}).ok,true);
 assert.throws(()=>makeRecord({...base,reward:{kind:'human_feedback',value:1}}),/owner approval/);
});

test('identities stay separate until an APPROVED association exists',()=>{
 const moon=makeRecord({...base,qbeast_id:'bb-7f9c2a03'});
 assert.equal(trainingEligible(moon,{identity:'bb-deada969'}).ok,false);
 assert.equal(trainingEligible(moon,{identity:'bb-deada969',approvedAssociations:[{subject:'bb-7f9c2a03',object:'bb-deada969',status:'PROPOSED_NOT_APPROVED'}]}).ok,false);
 assert.equal(trainingEligible(moon,{identity:'bb-deada969',approvedAssociations:[{subject:'bb-7f9c2a03',object:'bb-deada969',status:'APPROVED'}]}).ok,true);
});

test('hash chain detects tampering',()=>{
 const a=makeRecord(base),b=makeRecord({...base,prev:a.hash});
 assert.equal(verifyStream([a,b]).ok,true);
 const t={...b,reward:{...b.reward,value:.9}};assert.equal(verifyStream([a,t]).reason,'hash');
 assert.equal(verifyStream([b]).reason,'chain');
});

test('diary entries bridge without copying thought text and keep narrative provenance',()=>{
 const entry={beast_id:'bb-7f9c2a03',tick:1,hash:'f'.repeat(64),signals:{energy:90},place:'Rift Gate',thought:{text:'secret words',by:'deterministic-template'},
  learning:{new_cells:3,moves_succeeded:4,moves_blocked:1,goals:{explore:2},cells_visited:5,known_rifts:1,favorite_spot:'Rift Gate'},
  growth_source:{kind:'rigetti-qvm-simulated',target:'rigetti.sim.qvm',shots:256,counts:{'101':256},circuit_params:{},job_id:'j',counts_sha256:'b'.repeat(64)}};
 const rs=diaryEntryRecords(entry);
 assert.equal(rs.length,2);assert.equal(verifyStream(rs).ok,true);
 assert.ok(!JSON.stringify(rs).includes('secret words'));
 assert.ok(rs[1].labels.some(l=>l.value==='narrative:deterministic_template'));
 assert.equal(rs[0].origin,'azure_rigetti_qvm_simulation');
});

test('grid env uses the site pocket layout, hides unlearned rifts and is replay-identical after save/reload',()=>{
 const e=createGridEnv({digest:D,key:'t0',qbeast_id:'bb-deada969'});
 assert.equal(e.rifts.length,3);
 const o=observe(e);assert.ok(!JSON.stringify(o).includes('rift-known'));
 for(let i=0;i<12;i++){const r=stepEnv(e,BASELINES['greedy-frontier'](e),{policy:'g'});notePolicyOutcome(e,r.outcome);}
 const snap=snapshotEnv(e),f=restoreEnv(snap);
 const a=[],b=[];
 for(let i=0;i<12;i++){a.push(stepEnv(e,BASELINES['greedy-frontier'](e),{policy:'g'}).record.hash);b.push(stepEnv(f,BASELINES['greedy-frontier'](f),{policy:'g'}).record.hash);}
 assert.deepEqual(a,b);
});

test('baselines are measurable and the pocket-learner baseline is the site policy (better than random)',()=>{
 const m={};
 for(const pol of Object.keys(BASELINES)){let c=0;for(let i=0;i<8;i++){const e=createGridEnv({digest:D,key:'b'+i,qbeast_id:'bb-deada969'});
  while(!e.done){const r=stepEnv(e,BASELINES[pol](e),{policy:pol});notePolicyOutcome(e,r.outcome);}c+=metrics(e).cells_visited;}m[pol]=c/8;}
 assert.ok(m['pocket-learner']>m.random);assert.ok(m['greedy-frontier']>=m['pocket-learner']);
});
