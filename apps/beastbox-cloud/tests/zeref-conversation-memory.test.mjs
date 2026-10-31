import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {framePrompt,talkPersona,talkToBeast,MEMORY_TURNS,GUEST_LIMIT} from '../lib/companion/beast-talk.mjs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const H=[{role:'you',text:'You have one sun.'},{role:'beast',text:'One sun.'},{role:'you',text:'It lights everything.'},{role:'beast',text:'Bright.'},{role:'you',text:'Storms make the sky dark.'},{role:'beast',text:'Dark sky.'},{role:'you',text:'old line'},{role:'beast',text:'old reply'}];

test('framePrompt carries the last MEMORY_TURNS lines, oldest dropped first',()=>{
 assert.equal(MEMORY_TURNS,6);
 const p=framePrompt(talkPersona(),H.slice(0,6),'How many suns do you have?');
 assert.match(p,/Keeper: You have one sun\.\nZeref: One sun\.\nKeeper: It lights everything\./);
 assert.ok(p.endsWith('Keeper: How many suns do you have?\nZeref:'));
 const tight=framePrompt(talkPersona(),H,'q'.repeat(300),700);
 assert.ok(tight.length<=700);assert.ok(tight.endsWith('Keeper: '+'q'.repeat(300)+'\nZeref:'));
 const full=framePrompt(talkPersona(),H,'hi');assert.match(full,/Keeper: old line\nZeref: old reply\nKeeper: hi/);assert.doesNotMatch(full,/You have one sun/);
});

test('remember (on by default in the page) sends recent history to Zeref\'s own model only',async()=>{
 const bodies=[];
 const ok={provider:'rawrphos-local',model:'rawrphos-native',step:1,reply:'One.',checkpoint_sha256:'x'};
 const fetchImpl=async(url,init)=>{bodies.push(JSON.parse(init.body));return new Response(JSON.stringify(ok),{status:200,headers:{'content-type':'application/json'}});};
 await talkToBeast({text:'How many suns?',route:'guest-rawrphos',history:H.slice(0,2),remember:true,fetchImpl});
 assert.match(bodies[0].text,/Keeper: You have one sun\./);
 await talkToBeast({text:'How many suns?',route:'guest-rawrphos',history:H.slice(0,2),fetchImpl});
 assert.doesNotMatch(bodies[1].text,/You have one sun/); // no remember consent -> stays local
 const panel=read('components/beast-talk-panel.tsx');
 assert.match(panel,/const \[remember,setRemember\]=useState\(true\)/);
 assert.match(panel,/remember:persona\.source==='zeref'&&remember/);
});

test('class chat sends the last exchanges of its own thread and reports memory_turns',()=>{
 const r=read('app/api/classroom/route.ts');
 assert.match(r,/readClassThread\(cfg0,id\)/);
 assert.match(r,/slice\(-MEMORY_TURNS\)/);
 assert.match(r,/memory_turns:memory\.length/);
 assert.ok(GUEST_LIMIT>0);
});
