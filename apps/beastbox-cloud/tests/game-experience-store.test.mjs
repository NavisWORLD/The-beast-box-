import test from 'node:test';import assert from 'node:assert/strict';
import {recordGameExperience} from '../lib/cosmos/cosmos-store.mjs';
// In-memory Azure Blob stand-in behind global fetch (same REST surface azure-blob.mjs calls).
function fakeBlob(){const m=new Map();let n=0;
 globalThis.fetch=async(url,{method='GET',body,headers={}}={})=>{const name=decodeURIComponent(new URL(url).pathname.split('/').slice(2).join('/'));
  const h=k=>headers[k]??headers[k.toLowerCase()];
  if(method==='GET'){const v=m.get(name);return v?new Response(v.text,{status:200,headers:{etag:v.etag}}):new Response('',{status:404});}
  if(method==='PUT'){if(url.includes('restype=container'))return new Response('',{status:201});const v=m.get(name);
   if(h('If-None-Match')==='*'&&v)return new Response('',{status:409});if(h('If-Match')&&(!v||v.etag!==h('If-Match')))return new Response('',{status:412});
   const etag='"e'+(++n)+'"';m.set(name,{text:String(body),etag});return new Response('',{status:201,headers:{etag}});}
  return new Response('',{status:400});};return m;}
const cfg={mode:'sas',containerUrl:'https://acct.blob.core.windows.net/c',sas:'sv=x'};
test('V12.3: game experience persists to the registered beast ecosystem, chained, de-duplicated',async()=>{
 const m=fakeBlob();const e={beast_id:'bb-deada969',cst_steps:100,heartbeats:8,mood:{joy:.5}};
 let r=await recordGameExperience(cfg,e);assert.equal(r.persisted,false);assert.match(r.reason,/not registered/);
 m.set('beasts/bb-deada969/profile.json',{text:'{"id":"bb-deada969"}',etag:'"p"'});
 r=await recordGameExperience(cfg,e);assert.equal(r.persisted,true);assert.equal(r.count,1);
 r=await recordGameExperience(cfg,e);assert.equal(r.duplicate,true);
 r=await recordGameExperience(cfg,{...e,cst_steps:200});assert.equal(r.count,2);
 const lines=m.get('beasts/bb-deada969/game-experience.jsonl').text.trim().split('\n').map(JSON.parse);
 assert.equal(lines[1].prev,lines[0].hash);assert.equal(JSON.parse(m.get('beasts/bb-deada969/game-latest.json').text).cst_steps,200);});
