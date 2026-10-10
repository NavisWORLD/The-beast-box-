import test from 'node:test';
import assert from 'node:assert/strict';
import {parseModelGameAction,proposeGuidedGameAction,MAX_GUIDED_STEPS,GUIDED_BUTTON_MS} from '../lib/companion/guided-game.mjs';
import {createSession,adoptBeast} from '../lib/companion/session.mjs';

function creature() {
 const session=createSession();adoptBeast(session,{seed:'source-real-1',names:{1:'Wisp'}});
 session.beast.qbeast={profile:{id:'bb-new-measured-1'}};
 return session;
}
const observation={status:'observed',source:'native-emulator-display',brightness:52,contrast:78,dominant:'blue',frameChange:12};
const payload={provider:'rawrphos-local',model:'rawrphos-native',step:14000,guest_stateless:true};
test('strict model text cannot smuggle extra commands, JSON tools, or START/SELECT',()=>{
 for(const bad of ['ACTION: UP\\nACTION: A','ACTION: START','ACTION: SELECT','I will move. ACTION: UP','action: LEFT','ACTION: UP; DROP','', ' '.repeat(100)]){
  assert.equal(parseModelGameAction(bad).ok,false,bad);
 }
 for(const action of ['UP','DOWN','LEFT','RIGHT','A','B','WAIT'])assert.equal(parseModelGameAction('ACTION: '+action).ok,true);
 assert.equal(parseModelGameAction('ACTION: WAIT').button,null);
 assert.equal(MAX_GUIDED_STEPS,3);
 assert.ok(GUIDED_BUTTON_MS<=200);
});
test('no actual frame means no model request, no invented movement',async()=>{
 let calls=0;
 const result=await proposeGuidedGameAction({session:creature(),observation:null,fetchImpl:async()=>{calls++;return {ok:true,json:async()=>({...payload,reply:'ACTION: A'})}}});
 assert.equal(result.ok,false);assert.equal(calls,0);
});
test('actual native pixels and matching QBEAST reach guest model with no saved memories or invented objects',async()=>{
 const s=creature();s.chat.push({role:'you',text:'PRIVATE KEYSTONE MEMORY'});
 const calls=[];
 const result=await proposeGuidedGameAction({session:s,observation,fetchImpl:async(url,init)=>{
  calls.push([url,JSON.parse(init.body).text]);
  return {ok:true,json:async()=>({...payload,reply:'ACTION: RIGHT'})};
 }});
 assert.equal(result.ok,true);
 assert.equal(result.button,'right');
 assert.equal(calls[0][0],'/api/guest');
 assert.match(calls[0][1],/Observed native game screen pixels/);
 assert.doesNotMatch(calls[0][1],/PRIVATE KEYSTONE MEMORY|recognizes enemies|bb-new-measured-1/);
});
test('rawrphos incoherent outputs never turn into physical game input',async()=>{
 const r=await proposeGuidedGameAction({session:creature(),observation,fetchImpl:async()=>({ok:true,json:async()=>({...payload,reply:'I see a monster! move up!'})})});
 assert.equal(r.ok,false);assert.match(r.reason,/valid single ACTION/);
});
test('missing or canceled native inference remains inert',async()=>{
 const abort=new AbortController();abort.abort();let calls=0;
 const stopped=await proposeGuidedGameAction({session:creature(),observation,signal:abort.signal,fetchImpl:async()=>{calls++;}});
 assert.equal(stopped.ok,false);assert.equal(calls,0);
 const missing=await proposeGuidedGameAction({session:creature(),observation,fetchImpl:async()=>({ok:true,json:async()=>({reply:'ACTION: UP'})})});
 assert.equal(missing.ok,false);
});
