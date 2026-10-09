import test from 'node:test';
import assert from 'node:assert/strict';
import {birth} from '../lib/companion-local.mjs';
import {buildQbeast} from '../public/spark/qbeast.mjs';
import {adoptBeast,careAction,createSession,exportSession,importSession} from '../lib/companion/session.mjs';
import {rememberExchange} from '../lib/companion/adventure.mjs';
import {publicBrainProvider,runPublicBrain,setPublicBrain} from '../lib/companion/public-brain-bay.mjs';

function fixture(){
 const session=createSession();
 adoptBeast(session,birth('serene').genome,'Orbit');
 session.beast.qbeast=buildQbeast(session.beast.genome);
 session.beast.nativeStage=1;
 careAction(session,'pet');
 rememberExchange(session,'quiet star','quiet star shines');
 return session;
}
function state(session){
 return JSON.stringify({id:session.beast.qbeast.profile.id,qbeast:session.beast.qbeast,genome:session.beast.genome,xp:session.beast.xp,bond:session.beast.bond,stage:session.beast.stage,mind:session.mind});
}
function json(value,status=200){return new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});}

test('public brain swaps retain canonical identity, genesis, all growth and local mind across reload',()=>{
 const session=fixture(),before=state(session);
 assert.equal(publicBrainProvider(session),'local-mind');
 for(const provider of ['guest-rawrphos','loopback-ollama','local-mind']){
  assert.equal(setPublicBrain(session,provider).ok,true);
  assert.equal(state(session),before);
  assert.equal(publicBrainProvider(importSession(exportSession(session))),provider);
 }
 assert.throws(()=>setPublicBrain(session,'owner-bridge'),/public provider/);
 assert.equal(state(session),before);
 assert.equal(setPublicBrain(createSession(),'guest-rawrphos').ok,false);
});

test('pattern replies are deterministic, read-only, and never fetch a model',async()=>{
 const session=fixture(),before=JSON.stringify(exportSession(session));
 let calls=0;
 const fetcher=()=>{calls++;throw Error('no network allowed');};
 const a=await runPublicBrain(session,'quiet star',{fetcher,ollamaModel:'unused:latest'});
 const b=await runPublicBrain(session,'quiet star',{fetcher});
 assert.deepEqual(a,b);
 assert.equal(a.source,'local-mind');
 assert.equal(a.fallback,false);
 assert.match(a.label,/pattern/);
 assert.equal(calls,0);
 assert.equal(JSON.stringify(exportSession(session)),before);
});

test('guest sends only bounded explicit text and accepts only verified stateless native14K results',async()=>{
 const session=fixture();setPublicBrain(session,'guest-rawrphos');
 const before=JSON.stringify(exportSession(session)),calls=[];
 const result=await runPublicBrain(session,'a'.repeat(800),{fetcher:async(url,options)=>{
  calls.push({url,options});
  return json({provider:'rawrphos-local',model:'rawrphos-native',step:14000,guest_stateless:true,reply:'A verified checkpoint answer.'});
 }});
 assert.equal(result.source,'guest-rawrphos');
 assert.equal(result.fallback,false);
 assert.equal(calls.length,1);
 assert.equal(calls[0].url,'/api/guest');
 assert.deepEqual(JSON.parse(calls[0].options.body),{provider:'rawrphos-local',text:'a'.repeat(400)});
 assert.equal(calls[0].options.credentials,'same-origin');
 assert.equal(calls[0].options.redirect,'error');
 assert.equal(JSON.stringify(exportSession(session)),before);
});

test('failed, oversized and unverified guest responses dim the selected module with honestly labeled pattern fallback',async()=>{
 const session=fixture();setPublicBrain(session,'guest-rawrphos');
 const before=JSON.stringify(exportSession(session));
 const verified={provider:'rawrphos-local',model:'rawrphos-native',step:14000,guest_stateless:true,reply:'answer'};
 const replies=[json({error:'unavailable'},503),json({...verified,step:18000}),json({...verified,guest_stateless:false}),json({...verified,reply:''}),json({...verified,reply:'x'.repeat(6001)}),json({...verified,reply:'x'.repeat(40000)})];
 for(const response of replies){
  const result=await runPublicBrain(session,'quiet star',{fetcher:async()=>response});
  assert.equal(result.source,'local-mind');
  assert.equal(result.fallback,true);
  assert.equal(result.moduleReady,false);
  assert.match(result.label,/fallback.*not a model answer/);
  assert.ok(result.failure);
  assert.equal(publicBrainProvider(session),'guest-rawrphos');
  assert.equal(JSON.stringify(exportSession(session)),before);
 }
 const result=await runPublicBrain(session,'quiet star',{fetcher:async()=>{throw Error('offline');}});
 assert.equal(result.fallback,true);
});

test('loopback Ollama requires explicit selection and model tag; requests never carry identity, memory or credentials',async()=>{
 const session=fixture(),calls=[];
 const fetcher=async(url,options)=>{calls.push({url,options});return json({model:'tiny:latest',done:true,message:{content:'Actual local model text.'}});};
 await runPublicBrain(session,'quiet star',{fetcher,ollamaModel:'tiny:latest'});
 assert.equal(calls.length,0);
 setPublicBrain(session,'loopback-ollama');
 for(const ollamaModel of ['', 'https://example.com/model','model\nAuthorization']){
  const result=await runPublicBrain(session,'quiet star',{fetcher,ollamaModel});
  assert.equal(result.fallback,true);
 }
 assert.equal(calls.length,0);
 const result=await runPublicBrain(session,'quiet star',{fetcher,ollamaModel:'tiny:latest'});
 assert.equal(result.source,'loopback-ollama');
 assert.equal(calls.length,1);
 assert.equal(calls[0].url,'http://127.0.0.1:11434/api/chat');
 assert.equal(calls[0].options.credentials,'omit');
 assert.equal(calls[0].options.redirect,'error');
 assert.deepEqual(JSON.parse(calls[0].options.body),{model:'tiny:latest',stream:false,messages:[{role:'user',content:'quiet star'}],options:{num_predict:128,temperature:.3}});
});

test('absent Beast and blocked messages do not call guest inference',async()=>{
 let calls=0;const fetcher=async()=>{calls++;throw Error('unexpected');};
 assert.equal((await runPublicBrain(createSession(),'hello',{fetcher})).ok,false);
 const session=fixture();setPublicBrain(session,'guest-rawrphos');
 const result=await runPublicBrain(session,'this is porn',{fetcher});
 assert.equal(result.source,'local-mind');
 assert.equal(calls,0);
});
