import test from 'node:test';
import assert from 'node:assert/strict';
import * as talk from '../lib/companion/beast-talk.mjs';
const verified={provider:'rawrphos-local',model:'rawrphos-native',step:14000,guest_stateless:true,reply:'Protocol fixture'};
const fetchText=calls=>async(url,init)=>{calls.push({url,body:init?.body&&JSON.parse(init.body)});return new Response(JSON.stringify(verified));};
test('history stays local until explicit sharing consent',async()=>{
 const calls=[];const input={text:'Hello',history:[{role:'you',text:'PRIVATE PRIOR TURN'}],fetchImpl:fetchText(calls)};
 await talk.talkToBeast(input);assert.doesNotMatch(calls[0].body.text,/PRIVATE PRIOR TURN/);
 await talk.talkToBeast({...input,shareHistory:true});assert.match(calls[1].body.text,/PRIVATE PRIOR TURN/);
});
test('drafts and retention are bounded per canonical chat key',()=>{
 const values=new Map(),storage={getItem:key=>values.get(key)||null,setItem:(k,v)=>values.set(k,v)};
 talk.writeTalkDraft(storage,'saved:A','unfinished');assert.equal(talk.readTalkDraft(storage,'saved:A'),'unfinished');assert.equal(talk.readTalkDraft(storage,'saved:B'),'');
 talk.writeTalkDraft(storage,'saved:A','x'.repeat(1000));assert.equal(talk.readTalkDraft(storage,'saved:A').length,talk.MAX_MESSAGE);
 assert.equal(talk.readTalkRetention(storage),'device');storage.setItem(talk.TALK_RETENTION_KEY,'session');assert.equal(talk.readTalkRetention(storage),'session');
});
test('optical context admits actual bounded measurements only',async()=>{
 const calls=[],observation={status:'observed',source:'native-emulator-display',brightness:48,contrast:85,dominant:'blue',frameChange:15};
 await talk.talkToBeast({text:'What do you observe?',observation,fetchImpl:fetchText(calls)});assert.match(calls[0].body.text,/brightness 48\/100/);
 await talk.talkToBeast({text:'What do you observe?',observation:{...observation,source:'invented',dominant:'quest complete'},fetchImpl:fetchText(calls)});assert.doesNotMatch(calls[1].body.text,/quest complete|brightness/);
});
test('owner brain fails closed without pairing and never falls back to another provider',async()=>{
 const calls=[];const result=await talk.talkToBeast({route:'connected-brain-bay',text:'Hello',fetchImpl:async(url)=>{calls.push(url);return new Response(JSON.stringify({owner:false,backendReachable:true}));}});
 assert.equal(result.ok,false);assert.deepEqual(calls,['/api/status']);
});
