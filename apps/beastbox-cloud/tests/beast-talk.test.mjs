import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {birth} from '../lib/companion-local.mjs';
import {adoptBeast,createSession} from '../lib/companion/session.mjs';
import {framePrompt,personaFrame,readTalkLog,talkPersona,talkToBeast,validOllamaUrl,writeTalkLog,MAX_LOG} from '../lib/companion/beast-talk.mjs';

const json=(value,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
const verified={provider:'rawrphos-local',model:'rawrphos-native',step:14000,guest_stateless:true,reply:' Hello keeper!'};
function sparkBeast(){const s=createSession();adoptBeast(s,birth('serene').genome,'Orbit');return s.beast;}

test('persona comes from the visitor\'s own Beast, then the Cage creature, then Zeref; it is deterministic',()=>{
 const beast=sparkBeast();
 const a=talkPersona({beast}),b=talkPersona({beast});
 assert.deepEqual(a,b);
 assert.equal(a.name,'Orbit');assert.equal(a.source,'spark');assert.match(a.key,/^spark:/);
 const cage=talkPersona({cage:{id:'bb-1',name:'Lumix',family:'aurora',temperament:{curiosity:.9,energy:.2,playfulness:.7,caution:.1,independence:.3}}});
 assert.equal(cage.name,'Lumix');assert.deepEqual(cage.traits,['curious','playful','independent']);
 const zeref=talkPersona({});
 assert.equal(zeref.name,'Zeref');assert.match(zeref.kind,/moon cat dragon/);
 assert.match(personaFrame(a),/You are Orbit/);
 assert.match(personaFrame(a),/not a person/);
});

test('framed prompt always keeps the keeper\'s words and fits the 700-character guest limit',()=>{
 const p=talkPersona({});
 const history=Array.from({length:10},(_,i)=>({role:i%2?'beast':'you',text:'line '+i+' '+'x'.repeat(200)}));
 const said='y'.repeat(400);
 const prompt=framePrompt(p,history,said);
 assert.ok(prompt.length<=700);
 assert.ok(prompt.endsWith('Keeper: '+said+'\nZeref:'));
 assert.match(framePrompt(p,[{role:'you',text:'hi'},{role:'beast',text:'purr'}],'how are you?'),/Keeper: hi\nZeref: purr\nKeeper: how are you\?/);
});

test('guest route sends one framed message and returns only a verified reply',async()=>{
 const calls=[];
 const result=await talkToBeast({text:'Hi!',persona:talkPersona({}),fetchImpl:async(url,init)=>{calls.push({url,init});return json(verified);}});
 assert.equal(result.ok,true);assert.equal(result.reply,'Hello keeper!');assert.equal(result.route,'guest-rawrphos');
 assert.equal(calls.length,1);assert.equal(calls[0].url,'/api/guest');
 const body=JSON.parse(calls[0].init.body);
 assert.deepEqual(Object.keys(body).sort(),['provider','text']);
 assert.equal(body.provider,'rawrphos-local');assert.match(body.text,/You are Zeref/);assert.match(body.text,/Keeper: Hi!/);
 assert.equal(calls[0].init.credentials,'same-origin');
});

test('every failure is an honest offline result with connect help and no reply text',async()=>{
 const cases=[
  [async()=>json({error:'This guest\'s daily quota is exhausted'},429),/resting.*quota/],
  [async()=>json({error:'Guest model host is not configured'},503),/offline right now/],
  [async()=>json({...verified,step:18000}),/no verified text|no verified reply/],
  [async()=>json({...verified,guest_stateless:false}),/no verified/],
  [async()=>{throw new TypeError('Failed to fetch');},/Couldn't reach the Beast Box server/],
 ];
 for(const [fetchImpl,pattern] of cases){
  const result=await talkToBeast({text:'hello',fetchImpl});
  assert.equal(result.ok,false);assert.equal('reply' in result,false);
  assert.match(result.error,pattern);assert.ok(result.help.length>=2);
  assert.doesNotMatch(result.error,/^Failed to fetch$/);
 }
});

test('local Ollama is loopback-only, carries the persona as system text, and explains missing models / blocked origins',async()=>{
 assert.equal(validOllamaUrl('http://127.0.0.1:11434'),true);
 assert.equal(validOllamaUrl('http://localhost:11434/'),true);
 assert.equal(validOllamaUrl('https://evil.example:11434'),false);
 assert.equal(validOllamaUrl('http://127.0.0.1:11434/api?x=1'),false);
 let sent=null;
 const ok=await talkToBeast({route:'local-ollama',text:'hi',persona:talkPersona({}),ollama:{url:'http://127.0.0.1:11434',model:'companion-glacecoil'},
  fetchImpl:async(url,init)=>{sent={url,body:JSON.parse(init.body)};return json({model:'companion-glacecoil',done:true,message:{role:'assistant',content:'rim? star crumb!'}});}});
 assert.equal(ok.ok,true);assert.equal(ok.model,'companion-glacecoil');
 assert.equal(sent.url,'http://127.0.0.1:11434/api/chat');
 assert.equal(sent.body.messages[0].role,'system');assert.match(sent.body.messages[0].content,/You are Zeref/);
 const missing=await talkToBeast({route:'local-ollama',text:'hi',fetchImpl:async()=>json({error:'model "companion-glacecoil" not found, try pulling it first'},404)});
 assert.match(missing.error,/not installed.*ollama pull/);
 const blocked=await talkToBeast({route:'local-ollama',text:'hi',fetchImpl:async()=>{throw new TypeError('Failed to fetch');}});
 assert.match(blocked.error,/Couldn't reach Ollama/);
 assert.ok(blocked.help.some(line=>/OLLAMA_ORIGINS=/.test(line)));
 const remote=await talkToBeast({route:'local-ollama',text:'hi',ollama:{url:'https://example.com'},fetchImpl:async()=>{throw Error('must not fetch');}});
 assert.equal(remote.ok,false);
});

test('own Hugging Face key requires explicit spend consent and goes through the BYOK guest route',async()=>{
 const key='hf_'+'a'.repeat(30);
 const refused=await talkToBeast({route:'hf-byok',text:'hi',hf:{key,spendConfirmed:false},fetchImpl:async()=>{throw Error('must not fetch');}});
 assert.equal(refused.ok,false);assert.match(refused.error,/charges/);
 let body=null;
 const ok=await talkToBeast({route:'hf-byok',text:'hi',hf:{key,model:'owner/model',spendConfirmed:true},fetchImpl:async(url,init)=>{body=JSON.parse(init.body);return json({provider:'huggingface-byok',model:'owner/model',reply:'hello!',guest_stateless:true});}});
 assert.equal(ok.ok,true);
 assert.deepEqual(Object.keys(body).sort(),['hf_key','model','provider','spend_confirmed','text']);
 assert.ok(body.text.length<=700);
});

test('chat log is per Beast, bounded, and survives a reload of storage',()=>{
 const store=new Map();const storage={getItem:k=>store.get(k)??null,setItem:(k,v)=>store.set(k,v)};
 const rows=Array.from({length:40},(_,i)=>({role:i%2?'beast':'you',text:'t'+i}));
 assert.equal(writeTalkLog(storage,'spark:a',rows),true);
 assert.equal(readTalkLog(storage,'spark:a').length,MAX_LOG);
 assert.deepEqual(readTalkLog(storage,'spark:b'),[]);
 storage.setItem('beastbox-talk-log-v1:bad','{not json');
 assert.deepEqual(readTalkLog(storage,'bad'),[]);
});

test('talk is reachable from Home, My Beast, Cage and Brain Bay; status route exposes no secrets',()=>{
 const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
 assert.match(read('app/page.tsx'),/href="\/beast-cage\/talk"/);
 assert.match(read('public/spark/index.html'),/href="\/beast-cage\/talk"/);
 assert.match(read('components/beast-cage-portal.tsx'),/href="\/beast-cage\/talk"/);
 assert.match(read('components/brain-bay-workshop.tsx'),/<BeastTalkPanel/);
 const status=read('app/api/talk/route.ts');
 assert.doesNotMatch(status,/BRIDGE_URL|BRIDGE_TOKEN|fetch\(/);
 assert.match(read('public/spark/app.mjs'),/guestModelTalk/);
});
