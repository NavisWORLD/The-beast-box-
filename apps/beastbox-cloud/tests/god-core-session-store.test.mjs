import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {buildGenome} from '../public/spark/genome.mjs';
import {selectSpark,readSparkSession,SESSION_KEY} from '../public/spark/identity.mjs';
import {updateDeviceSession,selectedIdentity} from '../lib/companion/session-store.mjs';
import {careAction,advanceCreature} from '../lib/companion/session.mjs';
const table=JSON.parse(fs.readFileSync(new URL('../public/spark/runs.json',import.meta.url)));
const row=table.runs[0], run={key:row.k,backend:row.b,job_id:row.j,pub_index:row.p,num_bits:row.n,shots:row.s,counts:Object.fromEntries(row.c.split(',').map(p=>{const[k,v]=p.split(':');return[k,+v]})),counts_sha256:row.h};
const gen=buildGenome({focus:30,calm:50,spark:80},run,'Sol',10);
const storage=()=>{const data=new Map();return {getItem:k=>data.get(k)??null,setItem:(k,v)=>data.set(k,v),removeItem:k=>data.delete(k)}};
test('care, autonomous tick, and metadata preserve one identity and each other',()=>{
 const store=storage();selectSpark(store,gen);
 const id=selectedIdentity(readSparkSession(store));
 updateDeviceSession(store,id,s=>careAction(s,'pet'),{place:'grove'});
 updateDeviceSession(store,id,s=>advanceCreature(s,{place:'grove'}),{place:'nest',sensorLog:['local']} );
 const final=readSparkSession(store);
 assert.equal(selectedIdentity(final),id);
 assert.equal(final.beast.xp,4);
 assert.equal(final.beast.behavior.tick,1);
 assert.equal(final.beast.behavior.memory.length,1);
 const raw=JSON.parse(store.getItem(SESSION_KEY));
 assert.equal(raw.place,'nest');assert.deepEqual(raw.sensorLog,['local']);
});
test('a stale tab cannot restore an older Beast on top of a new selection',()=>{
 const store=storage();selectSpark(store,gen);const old=selectedIdentity(readSparkSession(store));
 const other=buildGenome({focus:90,calm:10,spark:40},run,'Sol',10);
 selectSpark(store,other);const before=store.getItem(SESSION_KEY);
 assert.throws(()=>updateDeviceSession(store,old,s=>careAction(s,'pet')),/Another page changed/);
 assert.equal(store.getItem(SESSION_KEY),before);
});
test('a non-selection mutation cannot forge or silently change identity',()=>{
 const store=storage();selectSpark(store,gen);const id=selectedIdentity(readSparkSession(store));
 const before=store.getItem(SESSION_KEY);
 assert.throws(()=>updateDeviceSession(store,id,s=>{s.beast.seed='f'.repeat(64)}),/cannot replace|recipe mismatch/);
 assert.equal(store.getItem(SESSION_KEY),before);
});
