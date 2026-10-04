import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {buildGenome} from '../public/spark/genome.mjs';
import {buildQbeast,serializeQbeast} from '../public/spark/qbeast.mjs';
import {createSession,adoptBeast,careAction,finishTraining,exportSession} from '../lib/companion/session.mjs';
import {replaySpark,selectSpark,readSparkSession,saveSparkSession,SESSION_KEY,QBEAST_KEY} from '../public/spark/identity.mjs';
const table=JSON.parse(fs.readFileSync(new URL('../public/spark/runs.json',import.meta.url)));
const row=table.runs[0],run={key:row.k,backend:row.b,job_id:row.j,pub_index:row.p,num_bits:row.n,shots:row.s,counts:Object.fromEntries(row.c.split(',').map(p=>{const [k,v]=p.split(':');return [k,+v]})),counts_sha256:row.h};
const gen=buildGenome({focus:30,calm:50,spark:80},run,'Sol',10),snap=buildQbeast(gen);
const storage=()=>{const values=new Map();return {getItem:k=>values.get(k)??null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)}};
test('QBEAST recipe reproduces the exact renderer genome, no second identity',()=>{
 const restored=replaySpark(serializeQbeast(snap),new Map([[run.key,run]]));
 assert.deepEqual(restored.gen,gen);assert.equal(restored.snapshot.profile.id,snap.profile.id);
 const bad=structuredClone(snap);bad.profile.seed='f'.repeat(64);
 assert.throws(()=>replaySpark(JSON.stringify(bad),new Map([[run.key,run]])));
});
test('reimporting a public Spark file restores its exact identity and existing care',()=>{
 const store=storage();selectSpark(store,gen);const s=readSparkSession(store);careAction(s,'pet');saveSparkSession(store,s);
 const xp=s.beast.xp;selectSpark(store,buildGenome({focus:90,calm:10,spark:40},run,null,10));
 selectSpark(store,gen,{snapshot:snap});const restored=readSparkSession(store);
 assert.deepEqual(restored.beast.qbeast,snap);assert.equal(restored.beast.xp,xp);assert.deepEqual(restored.beast.genome,gen);
});
test('generate, care, switch creature, reopen keeps the original QBEAST and its care state',()=>{
 const store=storage();selectSpark(store,gen);let s=readSparkSession(store);
 const original=store.getItem(QBEAST_KEY);careAction(s,'pet');finishTraining(s,6);saveSparkSession(store,s);
 const xp=s.beast.xp,bond=s.beast.bond;
 const other=buildGenome({focus:90,calm:10,spark:40},run,null,10);selectSpark(store,other);assert.notEqual(readSparkSession(store).beast.seed,gen.seed);
 selectSpark(store,gen);s=readSparkSession(store);
 assert.equal(s.beast.xp,xp);assert.equal(s.beast.bond,bond);assert.equal(s.beast.qbeast.profile.id,snap.profile.id);assert.equal(store.getItem(QBEAST_KEY),original);
 for(let i=0;i<30;i++)finishTraining(s,6);
 assert.equal(s.beast.stage,1,'care XP must not grant earned GBA stages');
 assert.deepEqual(s.beast.qbeast.progress,{trust:0,bond:0,evolution_stage:0});
});
test('invalid active save and stale care writes do not erase a newer identity',()=>{
 const store=storage();selectSpark(store,gen);const stale=readSparkSession(store);
 const other=buildGenome({focus:80,calm:20,spark:10},run,null,10);selectSpark(store,other);
 assert.throws(()=>saveSparkSession(store,stale),/changed/);assert.equal(readSparkSession(store).beast.seed,other.seed);
 const before=store.getItem(SESSION_KEY);store.setItem(QBEAST_KEY,'broken');
 assert.throws(()=>selectSpark(store,gen));assert.equal(store.getItem(SESSION_KEY),before);
});
