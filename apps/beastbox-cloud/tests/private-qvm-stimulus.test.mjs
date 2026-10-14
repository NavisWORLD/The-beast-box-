import test from 'node:test';
import assert from 'node:assert/strict';
import {buildGenome,canonicalJson} from '../public/spark/genome.mjs';
import {buildQbeast} from '../public/spark/qbeast.mjs';
import {expandRun} from '../public/spark/runs.mjs';
import {readFileSync} from 'node:fs';
import {createSession,adoptBeast,exportSession,importSession,swapBrain} from '../lib/companion/session.mjs';
import {sha256Hex} from '../public/spark/sha.mjs';
import {applyPrivateQvmStimulus} from '../lib/companion/private-qvm-stimulus.mjs';
const owner='u_'+'1'.repeat(32),other='u_'+'2'.repeat(32);
const run=expandRun(JSON.parse(readFileSync(new URL('../public/spark/ibm-zeref-heart-sound-20261010.json',import.meta.url))).runs[0]);
function fixture(){
 const session=createSession(),genome=buildGenome({focus:80,calm:20,spark:100},run,'P-00000000000000000001',10);adoptBeast(session,genome);session.beast.qbeast=buildQbeast(genome);
 // Protocol fixture, not a claimed provider execution.
 const receipt={status:'RIGETTI_QVM_REMOTE',owner,beast_id:session.beast.qbeast.profile.id,target:'rigetti.sim.qvm',shots:256,job_id:'PROTOCOL-FIXTURE-ONLY',counts:{'000':128,'111':128}};receipt.receipt_hash=sha256Hex(canonicalJson(receipt));
 return {session,record:{owner,beastId:receipt.beast_id,profile:{provenance:{seed:genome.seed}},simulationReceipts:[receipt]}};
}
test('private simulator stimulus preserves identity, model and native authority and survives reload once',()=>{
 const {session,record}=fixture(),identity=canonicalJson(session.beast.qbeast),brain=session.brain;
 const result=applyPrivateQvmStimulus(session,record,owner);assert.equal(result.ok,true);assert.equal(result.duplicate,false);assert.equal(session.beast.behavior.tick,1);assert.equal(session.beast.behavior.events[0].place,'observatory');assert.equal(session.beast.brain,undefined);assert.equal(session.brain,brain);assert.equal(canonicalJson(session.beast.qbeast),identity);assert.equal(session.beast.stage,1);assert.equal(session.beast.xp,0);
 const loaded=importSession(exportSession(session));swapBrain(loaded,'local-pattern');const before=canonicalJson(exportSession(loaded));assert.equal(applyPrivateQvmStimulus(loaded,record,owner).duplicate,true);assert.equal(canonicalJson(exportSession(loaded)),before);
});
test('another owner or creature, altered receipt, and blocked execution cannot mutate behavior',()=>{
 for(const mutate of [r=>r.owner=other,r=>r.beastId='bb-other',r=>r.profile.provenance.seed='other',r=>r.simulationReceipts[0].counts['000']++]){const {session,record}=fixture(),before=canonicalJson(exportSession(session));mutate(record);assert.throws(()=>applyPrivateQvmStimulus(session,record,owner));assert.equal(canonicalJson(exportSession(session)),before);}
 const {session,record}=fixture(),before=canonicalJson(exportSession(session));record.simulationReceipts[0].status='BLOCKED_EXTERNAL';assert.equal(applyPrivateQvmStimulus(session,record,owner).blocked,true);assert.equal(canonicalJson(exportSession(session)),before);
});
