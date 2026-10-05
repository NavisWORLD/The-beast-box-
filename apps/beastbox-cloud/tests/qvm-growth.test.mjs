import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import test from "node:test";
import {createSession,adoptBeast} from "../lib/companion/session.mjs";
import {deriveQvmGrowth,nextQvmGrowth} from "../lib/companion/qvm-growth.mjs";

const receipt=JSON.parse(readFileSync(new URL("../public/spark/rigetti-qvm-growth.json",import.meta.url),"utf8"));

test("archived Rigetti growth uses simulator history only and is deterministic",()=>{
 assert.equal(receipt.source_class,"NEW_AZURE_CLOUD_QVM_SIMULATION_NOT_QPU");
 assert.equal(receipt.backend_exact_allowlist[0],"rigetti.sim.qvm");
 assert.equal(receipt.physical_hardware_jobs_permitted,0);
 assert.equal(receipt.cloud_model_api_calls_permitted,0);
 assert.equal(receipt.scenario_records.length,8);
 const first=receipt.scenario_records[0];
 const a=deriveQvmGrowth(first),b=deriveQvmGrowth(structuredClone(first));
 assert.deepEqual(a,b);
 assert.equal(a.ok,true);
 assert.equal(a.source,"ARCHIVED_AZURE_RIGETTI_QVM_SIMULATOR");
 assert.equal(a.jobs.length,2);
 assert.deepEqual(a.jobs,first.batches.filter(row=>row.phase==="history_a"||row.phase==="history_b").map(row=>row.job_id));
 const changed=structuredClone(first);
 changed.batches.find(row=>row.phase==="future_held_out").counts={"00":0,"11":128};
 assert.deepEqual(deriveQvmGrowth(changed),a,"held-out future batch must not drive game growth");
});

test("eight archived simulator scenarios grow one Beast once each and preserve provenance",()=>{
 const session=createSession();
 adoptBeast(session,{seed:"rigetti-beast",names:{1:"Pulsekin",2:"Pulserex",3:"Pulsetitan"}},"Pulsekin");
 const pulses=[];
 for(let i=0;i<8;i++){
  const result=nextQvmGrowth(session,receipt);
  assert.equal(result.ok,true);
  assert.equal(result.scenario,i+1);
  assert.equal(result.used,i+1);
  assert.equal(result.total,8);
  pulses.push(result);
 }
 assert.equal(session.beast.qvm_growth.length,8);
 assert.equal(new Set(session.beast.qvm_growth.map(row=>row.scenario)).size,8);
 assert.equal(session.beast.qvm_growth.every(row=>row.source==="ARCHIVED_AZURE_RIGETTI_QVM_SIMULATOR"),true);
 assert.equal(session.beast.qvm_growth.every(row=>row.jobs.length===2),true);
 assert.ok(session.beast.xp>=120,"the complete archived sequence should be enough to reach stage III");
 assert.equal(session.beast.stage,3);
 const replay=nextQvmGrowth(session,receipt);
 assert.equal(replay.ok,false);
 assert.equal(replay.complete,true);
 assert.equal(session.beast.qvm_growth.length,8);
 assert.ok(pulses.some(row=>row.evolved));
});
