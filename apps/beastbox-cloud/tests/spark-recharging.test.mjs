import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {talkToBeast,talkPersona} from '../lib/companion/beast-talk.mjs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const json=(value,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
const SPARK={fired:true,tick:3,at:1762200000,label:'SIMULATED synaptic event: the message was received and its spark recorded on the guest\'s own ledger; the model answers when the window opens'};

test('a 429 carrying a spark receipt is a recharging pause, not an outage',async()=>{
 const result=await talkToBeast({text:'Hi!',persona:talkPersona({}),fetchImpl:async()=>json({error:'Slow down a little; retry in a minute',spark:SPARK,retry_after_seconds:42},429)});
 assert.equal(result.ok,false);assert.equal(result.status,429);assert.equal(result.recharging,true);
 assert.deepEqual(result.spark,{tick:3,at:1762200000});assert.equal(result.retryAfterMs,42000);
 assert.equal(result.error,'Synapse recharging · your spark landed');assert.deepEqual(result.help,[]);
 assert.doesNotMatch(result.error,/resting|offline/i);
});

test('a spark 429 without retry_after_seconds defaults to a 30s window',async()=>{
 const result=await talkToBeast({text:'Hi!',persona:talkPersona({}),fetchImpl:async()=>json({error:'Local guest model is busy; retry in a moment',spark:{...SPARK,tick:1}},429)});
 assert.equal(result.recharging,true);assert.equal(result.retryAfterMs,30000);assert.equal(result.spark.tick,1);
});

test('a 429 without a spark keeps the old resting wording; a 503 stays offline',async()=>{
 const resting=await talkToBeast({text:'Hi!',persona:talkPersona({}),fetchImpl:async()=>json({error:'usage limit reached'},429)});
 assert.equal(resting.recharging,undefined);assert.match(resting.error,/resting/);
 const down=await talkToBeast({text:'Hi!',persona:talkPersona({}),fetchImpl:async()=>json({error:'Guest model host is not configured'},503)});
 assert.equal(down.recharging,undefined);assert.match(down.error,/offline right now/);
});

test('the BFF passes a strictly shaped spark receipt and retry window through',()=>{
 const route=read('app/api/guest/route.ts');
 assert.match(route,/spark\.fired===true/);assert.match(route,/retry_after_seconds/);
 assert.match(route,/Spark on receipt/);
});

test('the popup holds messages in a queue and never calls a recharging pause offline',()=>{
 const popup=read('public/spark/chat-popup.mjs');
 assert.match(popup,/outbox\.push\(\{text\}\)/);assert.match(popup,/async function drain\(\)/);
 assert.match(popup,/result\.recharging/);assert.match(popup,/Synapse recharging · your spark landed/);
 assert.doesNotMatch(popup,/is resting, try again/);
});

test('the bridge records the spark on the guest ledger and answers with the receipt',()=>{
 const bridge=read('../../beastbox/guest_local.py');
 assert.match(bridge,/def record_guest_spark/);assert.match(bridge,/guest_spark/);
 assert.match(bridge,/retry_after_seconds/);assert.match(bridge,/SIMULATED synaptic event/);
 const owner=read('bridge/owner_bridge.py');
 assert.match(owner,/record_guest_spark/);
});
