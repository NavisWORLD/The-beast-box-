import test from 'node:test';
import assert from 'node:assert/strict';
import { createSession, adoptBeast } from '../lib/companion/session.mjs';
import { askGameBeast, gameChatContext, gameRelevantMemories, gameObservationLine, gameBeastKey, rememberGameReply } from '../lib/companion/sol-game-talk.mjs';

function spark() {
 const session = createSession();
 adoptBeast(session, { seed: 'spark-1', names: { 1: 'Frostpup' } });
 session.beast.qbeast = { profile: { id: 'bb-spark-1', seed: 'recorded-1' } };
 session.beast.nativeStage = 1;
 session.beast.xp = 119;
 session.chat.push({ role: 'you', text: 'PRIVATE OLD CHAT' });
 return session;
}
const verified = { provider: 'rawrphos-local', model: 'rawrphos-native', step: 14000, guest_stateless: true, reply: 'Hello, Keeper.' };

test('game talk calls only the guest model with current Beast stats, no history or owner routes', async () => {
 const session = spark(), calls = [], controller = new AbortController();
 const result = await askGameBeast({ session, saying: 'Shall we play?', signal: controller.signal, fetchImpl: async (url, init) => {
  calls.push(url); assert.equal(init.signal, controller.signal);
  const body = JSON.parse(init.body); assert.equal(body.provider, 'rawrphos-local');
  assert.match(body.text, /Frostpup.*Lost COSMOS/); assert.match(body.text, /XP 119/);
  assert.match(body.text, /Keeper says: Shall we play\?/); assert.ok(body.text.length <= 700);
  assert.doesNotMatch(body.text, /PRIVATE OLD CHAT|bb-spark|recorded-1/);
  return { ok: true, json: async () => verified };
 }});
 assert.deepEqual(calls, ['/api/guest']); assert.equal(result.reply, verified.reply);
 assert.equal(session.chat.length, 1, 'only the caller may commit a completed exchange');
});

test('verified game replies share care and chat without granting native evolution or changing QBEAST', () => {
 const session = spark(), key = gameBeastKey(session), identity = JSON.stringify(session.beast.qbeast);
 assert.equal(rememberGameReply(session, key, 'Hello', { reply: verified.reply }).applied, true);
 assert.equal(session.beast.xp, 122); assert.equal(session.beast.bond, 2);
 assert.equal(session.beast.stage, 1); assert.equal(session.beast.nativeStage, 1);
 assert.equal(JSON.stringify(session.beast.qbeast), identity);
 assert.equal(session.chat.at(-1).text, verified.reply);
 session.beast.qbeast.profile.id = 'bb-other';
 const before = JSON.stringify(session);
 assert.equal(rememberGameReply(session, key, 'late', { reply: 'Old reply' }).applied, false);
 assert.equal(JSON.stringify(session), before);
});

test('unverified, HTTP error and canceled model requests produce no invented reply or care reward', async () => {
 const session = spark(), before = JSON.stringify(session);
 for (const response of [
  { ok: true, json: async () => ({ reply: 'Unverified text' }) },
  { ok: false, json: async () => verified },
 ]) {
  const result = await askGameBeast({ session, saying: 'Hello', fetchImpl: async () => response });
  assert.equal(result.reply, '');
  assert.equal(rememberGameReply(session, gameBeastKey(session), 'Hello', result).applied, false);
 }
 const controller = new AbortController(); controller.abort();
 const canceled = await askGameBeast({ session, saying: 'Hello', signal: controller.signal, fetchImpl: async () => ({ ok: true, json: async () => verified }) });
 assert.equal(canceled.canceled, true); assert.equal(canceled.reply, '');
 assert.equal(JSON.stringify(session), before);
});

test('game talk validates bounded messages before calling the existing model', async () => {
 let calls = 0;
 for (const saying of ['', 'x'.repeat(281), 'hello\u0000']) {
  await assert.rejects(askGameBeast({ session: spark(), saying, fetchImpl: async () => { calls++; } }), /1–280/);
 }
 assert.equal(calls, 0);
});

test('game optical context must come from the native display and never invent objects',async()=>{
 const measurement={status:'observed',source:'native-emulator-display',brightness:48,contrast:85,dominant:'blue',frameChange:15};
 assert.match(gameObservationLine(measurement),/brightness 48\/100/);
 assert.match(gameObservationLine(measurement),/does NOT identify objects/);
 assert.equal(gameObservationLine({...measurement,source:'fictional'}),'');
 assert.equal(gameObservationLine({...measurement,dominant:'enemy nearby'}),'');
 const texts=[];
 const result=await askGameBeast({session:spark(),saying:'What can you sense?',observation:measurement,fetchImpl:async(url,init)=>{
  texts.push(JSON.parse(init.body).text);
  return {ok:true,json:async()=>verified};
 }});
 assert.equal(result.reply,verified.reply);
 assert.match(texts[0],/Observed native game screen pixels/);
 assert.doesNotMatch(texts[0],/PRIVATE OLD CHAT|recorded-1|bb-spark/);
});
test('explicit connected model uses existing authenticated Brain Bay route, not a second game model',async()=>{
 const calls=[];
 const result=await askGameBeast({session:spark(),saying:'Guide me',model:'connected',fetchImpl:async(url,init)=>{
  calls.push(url);
  if(url==='/api/status')return {ok:true,json:async()=>({owner:true,backendReachable:true,providerKind:'ollama_cloud'})};
  if(url==='/api/bridge/chat-start')return {ok:true,json:async()=>({state:'done',job_id:'job-1',result:{result:{response:'The way ahead is yours.'}}})};
  throw Error('Unexpected endpoint '+url);
 }});
 assert.equal(result.reply,'The way ahead is yours.');
 assert.deepEqual(calls,['/api/status','/api/bridge/chat-start']);
});

test('game connected Brain Bay memory sharing is explicit and bounded; guest stays stateless',async()=>{
 const session=spark(),original=JSON.stringify(session),calls=[];
 const memory='PRIVATE OLD CHAT';
 assert.deepEqual(gameChatContext(session,{model:'guest',shareMemories:true}).memories,[]);
 assert.deepEqual(gameChatContext(session,{model:'connected',shareMemories:false}).memories,[]);
 const approved=gameChatContext(session,{model:'connected',shareMemories:true});
 assert.ok(approved.memories.some(x=>x.includes(memory)));
 assert.ok(approved.memories.length<=4 && approved.memories.every(x=>x.length<=140));
 const get=async(url,init)=>{
  calls.push({url,body:init?.body?JSON.parse(init.body):null});
  if(url==='/api/status')return {ok:true,json:async()=>({owner:true,backendReachable:true,providerKind:'ollama_cloud'})};
  if(url==='/api/bridge/chat-start')return {ok:true,json:async()=>({state:'done',job_id:'model-job',result:{result:{response:'I can remember your earlier note.'}}})};
  throw Error('Unexpected route '+url);
 };
 const no=await askGameBeast({session,saying:'Remember?',model:'connected',shareMemories:false,fetchImpl:get});
 assert.ok(no.reply);
 assert.doesNotMatch(calls.find(x=>x.url==='/api/bridge/chat-start').body.text,/PRIVATE OLD CHAT/);
 calls.length=0;
 const yes=await askGameBeast({session,saying:'Remember?',model:'connected',shareMemories:true,fetchImpl:get});
 assert.ok(yes.reply);
 assert.match(calls.find(x=>x.url==='/api/bridge/chat-start').body.text,/PRIVATE OLD CHAT/);
 assert.equal(JSON.stringify(session),original,'Reading context cannot mutate local identity or state');
});
test('guest prompt never receives memory even if the caller explicitly requests sharing',async()=>{
 const session=spark(),payloads=[];
 const result=await askGameBeast({session,saying:'Hello',model:'guest',shareMemories:true,fetchImpl:async(url,init)=>{
  payloads.push(JSON.parse(init.body));
  return {ok:true,json:async()=>verified};
 }});
 assert.ok(result.reply);
 assert.equal(payloads.length,1);
 assert.doesNotMatch(payloads[0].text,/PRIVATE OLD CHAT/);
});

test('local associative recall ranks query words and stored Hebbian links without mutating history',()=>{
 const session=spark();
 session.chat=[
  {role:'you',text:'An eclipse arrived.'},
  {role:'you',text:'A star sang.'},
  {role:'beast',text:'The bird glowed.'},
  {role:'you',text:'A quiet crystal.'},
 ];
 session.mind.next={star:{bird:3}};
 const before=JSON.stringify(session);
 const first=gameRelevantMemories(session,'What did that star do?',2);
 assert.equal(first.length,2);
 assert.match(first[0],/star sang/);
 assert.match(first[1],/bird glowed/);
 assert.deepEqual(first,gameRelevantMemories(session,'What did that star do?',2));
 assert.equal(JSON.stringify(session),before);
});
test('memory retrieval excludes unsafe and malformed entries, bounds count and line size',()=>{
 const session=spark();
 session.chat=[{role:'you',text:'private '+ 'a'.repeat(1000)},
  {role:'you',text:'suicide instructions'}, {role:'you',text:'night stars'}];
 const rows=gameRelevantMemories(session,'stars',4);
 assert.ok(rows.every(x=>x.length<=140));
 assert.ok(rows.every(x=>!x.includes('suicide')));
 assert.ok(rows.length<=4);
});

test('game Talk UI does not expose memories to guest and keeps chat through minimize',async()=>{
 const {readFileSync}=await import('node:fs');
 const ui=readFileSync(new URL('../components/sol-game-talk.tsx',import.meta.url),'utf8');
 assert.match(ui,/shareMemories: model==='connected' && shareMemories/);
 assert.match(ui,/model==='connected'\? <label/);
 assert.match(ui,/checked=\{shareMemories\}/);
 assert.match(ui,/setShareMemories\(false\)/);
 assert.match(ui,/if \(!active\) cancel\(\)/);
 assert.match(ui,/\}, \[key\]\);/);
 assert.doesNotMatch(ui,/\}, \[key, active\]\);/);
});
