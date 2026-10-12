#!/usr/bin/env node
/**
 * JSON-lines bridge so the Python RAWRPHOS experiment drives the SAME pocket
 * rules the site uses (no Python re-implementation). One request per line:
 *  {"op":"reset","key":"...","digest":"...","qbeast_id":"bb-...","max_steps":40,"traits":{...},"energy":65}
 *  {"op":"suggest","policy":"random|pocket-learner|greedy-frontier"}
 *  {"op":"step","action":"UP","policy":"name","labels":[...]}
 *  {"op":"snapshot"} / {"op":"restore","snapshot":{...}} / {"op":"metrics"}
 */
import readline from 'node:readline';
import {BASELINES,createGridEnv,metrics,notePolicyOutcome,observe,restoreEnv,snapshotEnv,stepEnv} from '../lib/zeref/pocket-grid-env.mjs';
let env=null;
const rl=readline.createInterface({input:process.stdin});
const send=o=>process.stdout.write(JSON.stringify(o)+'\n');
rl.on('line',line=>{
 if(!line.trim())return;
 try{
  const m=JSON.parse(line);
  if(m.op==='reset'){env=createGridEnv({digest:m.digest,key:m.key,qbeast_id:m.qbeast_id,maxSteps:m.max_steps||40,traits:m.traits,energy:m.energy??65});send({ok:true,obs:observe(env),rifts_hidden:true});}
  else if(m.op==='suggest'){const f=BASELINES[m.policy];if(!f)throw Error('unknown policy');send({ok:true,action:f(env)});}
  else if(m.op==='step'){const r=stepEnv(env,m.action,{policy:m.policy||'unknown',labels:m.labels||[]});notePolicyOutcome(env,r.outcome);send({ok:true,...r});}
  else if(m.op==='snapshot')send({ok:true,snapshot:snapshotEnv(env)});
  else if(m.op==='restore'){env=restoreEnv(m.snapshot);send({ok:true,obs:observe(env)});}
  else if(m.op==='metrics')send({ok:true,metrics:metrics(env),done:env.done});
  else throw Error('unknown op');
 }catch(err){send({ok:false,error:String(err.message||err)});}
});
