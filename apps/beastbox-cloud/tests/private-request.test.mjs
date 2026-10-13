import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import ts from 'typescript';
import * as origin from '../lib/cosmos/private-origin.mjs';
function moduleAt(path,dependencies){const source=readFileSync(new URL(path,import.meta.url),'utf8'),code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText,module={exports:{}};new Function('require','module','exports','process',code)(key=>{if(!(key in dependencies))throw Error('Unexpected dependency '+key);return dependencies[key];},module,module.exports,{env:{}});return module.exports;}
const api=moduleAt('../lib/cosmos/private-api.ts',{'next/headers':{},'./azure-blob.mjs':{},'./private-owner.mjs':{},'./private-memory.mjs':{},'./private-origin.mjs':origin});
const request=body=>new Request('https://fixture.invalid/api/cosmos/private/beasts/bb-a1234567',{method:'PUT',headers:{host:'fixture.invalid',origin:'https://fixture.invalid','Content-Type':'application/json'},body:JSON.stringify(body)});
test('transport preserves a complete 32KB battery envelope while retaining strict small-message limits',async()=>{
 // Transport fixture only: these zeros are not a valid game save or earned progress.
 const body={action:{kind:'game-checkpoint',nativeSave:Buffer.alloc(32768).toString('base64')},expectedOwner:'u_'+'a'.repeat(32),eventId:'test-battery',version:1};
 assert.deepEqual(await api.privateBody(request(body)),body);
 await assert.rejects(api.privateBody(request({action:{kind:'memory',text:'x'.repeat(34000)}})),error=>error.status===413);
 await assert.rejects(api.privateBody(request({action:{kind:'game-checkpoint',nativeSave:'x'.repeat(66000)}})),error=>error.status===413);
});
test('a captured owner and seed are required preconditions, never authority',()=>{
 const owner='u_'+'a'.repeat(32),other='u_'+'b'.repeat(32);
 assert.equal(typeof api.privatePrecondition,'function');
 assert.doesNotThrow(()=>api.privatePrecondition(owner,{expectedOwner:owner,expectedSeed:'seed-a'},'seed-a'));
 for(const body of [{},{expectedOwner:other},{expectedOwner:owner,expectedSeed:'seed-b'}])assert.throws(()=>api.privatePrecondition(owner,body,'seed-a'),error=>error.status===409);
});
test('owner switching before a PUT or DELETE fails before touching either private world',async()=>{
 const owner='u_'+'a'.repeat(32),other='u_'+'b'.repeat(32);let touched=0;
 const boundApi={...api,privateContext:async()=>({subject:other,store:{read:async()=>{touched++;return{record:{identity:{seed:'seed-a'}}};},update:async()=>{touched++;},remove:async()=>{touched++;}}})};
 const route=moduleAt('../app/api/cosmos/private/beasts/[id]/route.ts',{'@/lib/cosmos/private-api':boundApi});
 for(const method of ['PUT','DELETE']){const response=await route[method](request({expectedOwner:owner,expectedSeed:'seed-a',action:{kind:'conversation-exchange'},eventId:'test-exchange',version:1}),{params:Promise.resolve({id:'bb-a1234567'})});assert.equal(response.status,409);}
 assert.equal(touched,0);
});
