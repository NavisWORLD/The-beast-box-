import test from 'node:test';import assert from 'node:assert/strict';
import {updateDeviceSession,selectedIdentity,recoverMirroredSession} from '../lib/companion/session-store.mjs';
import {createSession,adoptBeast,careAction,exportSession} from '../lib/companion/session.mjs';
import {SESSION_KEY} from '../public/spark/identity.mjs';
const setup=()=>{const data=new Map(),s=createSession();adoptBeast(s,{seed:'a'.repeat(64)},'Moss');data.set(SESSION_KEY,JSON.stringify(exportSession(s)));return {data,s,store:{getItem:k=>data.get(k)??null,setItem:(k,v)=>data.set(k,v)}};};
test('silent failed saves are not reported as success',()=>{
 const {s,store}=setup();store.setItem=()=>{};
 assert.throws(()=>updateDeviceSession(store,selectedIdentity(s),d=>careAction(d,'pet')),/confirm|read back/);
});
test('one complete device write retains metadata and new care',()=>{
 const {s,store,data}=setup();let writes=0;const set=store.setItem;store.setItem=(k,v)=>{writes++;set(k,v);};
 updateDeviceSession(store,selectedIdentity(s),d=>careAction(d,'pet'),{place:'shore',sensorLog:['off'],trail:{place:'shore'}});
 const saved=JSON.parse(data.get(SESSION_KEY));assert.equal(writes,1);assert.equal(saved.beast.xp,4);assert.equal(saved.place,'shore');
});
test('a mutation cannot overwrite a concurrent update even in a broken lock environment',()=>{
 const {s,store,data}=setup();
 assert.throws(()=>updateDeviceSession(store,selectedIdentity(s),d=>{careAction(d,'pet');const fresh=structuredClone(s);fresh.beast.xp=99;data.set(SESSION_KEY,JSON.stringify(exportSession(fresh)));}),/changed while/);
 assert.equal(JSON.parse(data.get(SESSION_KEY)).beast.xp,99);
});
test('a recovery mirror never replaces a newer local record',()=>{
 const {s,store}=setup();const old=exportSession(s);updateDeviceSession(store,selectedIdentity(s),d=>careAction(d,'pet'));
 const restored=recoverMirroredSession(store,old,new Map());assert.equal(restored.beast.xp,4);
});
test('an unsigned recovery mirror is confirmed before becoming the active record',()=>{
 const {s,store,data}=setup();data.clear();careAction(s,'pet');
 assert.equal(recoverMirroredSession(store,exportSession(s),new Map()).beast.xp,4);
 assert.equal(JSON.parse(data.get(SESSION_KEY)).beast.seed,s.beast.seed);
 data.clear();store.setItem=()=>{};assert.throws(()=>recoverMirroredSession(store,exportSession(s),new Map()),/confirm/);
});
