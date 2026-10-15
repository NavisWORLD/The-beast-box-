import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {talkToBeast} from '../lib/companion/beast-talk.mjs';
const ID='a'.repeat(32);
const res=(status,body)=>new Response(JSON.stringify(body),{status,headers:{'content-type':'application/json'}});
function fake(jobReplies,start={state:'queued',job_id:ID}){
 const seen=[];let i=0;
 const fetchImpl=async(url,opts)=>{seen.push(String(url));
  if(url==='/api/status')return res(200,{owner:true,backendReachable:true,providerKind:'rawrphos'});
  if(url==='/api/bridge/chat-start')return res(200,start);
  const [status,body]=jobReplies[Math.min(i++,jobReplies.length-1)];return res(status,body);};
 return {fetchImpl,seen};
}
const run=f=>talkToBeast({route:'connected-brain-bay',text:'hi',fetchImpl:f.fetchImpl});
test('poll uses the ?id= contract the bridge route validates',async()=>{
 const f=fake([[200,{state:'done',job_id:ID,response:'hello from the job'}]]);
 const r=await run(f);
 assert.ok(f.seen.some(u=>u==='/api/bridge/chat-job?id='+ID),f.seen.join(' '));
 assert.ok(!f.seen.some(u=>u.includes('job_id=')));
 assert.equal(r.ok,true);
});
test('route regex accepts exactly what the client sends',()=>{
 const route=readFileSync(new URL('../app/api/bridge/[endpoint]/route.ts',import.meta.url),'utf8');
 assert.match(route,/searchParams\.has\('id'\)/);
});
for(const state of ['failed','cancelled','expired']){
 test(`terminal job state ${state} ends with a readable failure`,async()=>{
  const r=await run(fake([[200,{state,job_id:ID}]]));assert.equal(r.ok,false);
 });
}
test('wrong-owner / expired job id (404) asks to resend',async()=>{
 const r=await run(fake([[404,{error:'not found'}]]));assert.equal(r.ok,false);assert.match(r.error,/another session or has expired/);
});
test('start without a valid job id fails without polling',async()=>{
 const f=fake([[200,{}]],{state:'queued',job_id:'bad'});const r=await run(f);
 assert.equal(r.ok,false);assert.ok(!f.seen.some(u=>u.includes('chat-job')));
});
test('a reply for another job id is not used',async()=>{
 const r=await run(fake([[200,{state:'done',job_id:'b'.repeat(32),reply:'x'}]]));assert.equal(r.ok,false);
});
