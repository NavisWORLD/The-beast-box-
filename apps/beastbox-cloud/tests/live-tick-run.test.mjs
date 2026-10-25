import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {runLiveTickLoop} from '../lib/zeref/live-tick-run.mjs';
import {liveBase,advanceChain,CHAIN_GENESIS} from '../lib/zeref/live-tick.mjs';
const diary={tick:124,xp:2520,last_tick_at:'2026-10-25T14:22:42.670Z',signals:{energy:88,signal:49,memory:100,resonance:86},identity:{beast_id:'bb-test'},recent:[{xp_gain:10}]};
const T0=Date.parse(diary.last_tick_at);
function rig(startMs,{head=null,state=diary}={}){let t=startMs;const out={batches:[],commits:0,head,sleeps:0};
 const io={readDiary:()=>out.state||state,readHead:()=>out.head,refresh:async()=>{},writeBatch:b=>{out.batches.push(b);out.head=b.head;},commit:async()=>{out.commits++;return true;}};
 const clock={now:()=>t,sleep:async ms=>{out.sleeps++;t+=ms;}};return {io,clock,out,at:()=>t};}
test('advances every second for hours with a fake clock, committing in BATCHES not per second',async()=>{
 const r=rig(T0+5000);const res=await runLiveTickLoop({io:r.io,clock:r.clock,runSeconds:3*3600,batchSeconds:600});
 assert.equal(res.ok,true);assert.ok(r.out.sleeps>=10700,'ticks every second: '+r.out.sleeps);assert.ok(r.out.commits>=18&&r.out.commits<=20,'batched commits '+r.out.commits);assert.ok(r.out.commits<r.out.sleeps/500);
 const b=liveBase(diary),last=r.out.batches.at(-1);const sec=Math.floor((r.at()-b.last_tick_at_ms)/1000);assert.equal(last.head.last_sec,sec);
 assert.equal(last.head.chain,advanceChain(b,CHAIN_GENESIS(b),0,sec),'in-run chain equals the pure per-second chain');
 assert.ok(r.out.batches.every(x=>x.entry.label==='SIMULATED'&&/^[a-f0-9]{64}$/.test(x.entry.hash)));
 for(let i=1;i<r.out.batches.length;i++)assert.equal(r.out.batches[i].entry.prev,r.out.batches[i-1].entry.hash);});
test('handoff: the next run continues the chain and recomputes the gap seconds (never stops)',async()=>{
 const a=rig(T0+1000);await runLiveTickLoop({io:a.io,clock:a.clock,runSeconds:900,batchSeconds:600});
 const gapStart=a.at();const b=rig(gapStart+300000,{head:a.out.head});await runLiveTickLoop({io:b.io,clock:b.clock,runSeconds:600,batchSeconds:600});
 const base=liveBase(diary),sec=Math.floor((b.at()-base.last_tick_at_ms)/1000);assert.equal(b.out.head.last_sec,sec);assert.equal(b.out.head.chain,advanceChain(base,CHAIN_GENESIS(base),0,sec));});
test('a NEW recorded tick is picked up at the next batch; the old segment is closed first',async()=>{
 const r=rig(T0+100000);let calls=0;r.io.readDiary=()=>{calls++;return r.at()>T0+2000000?{...diary,tick:125,last_tick_at:new Date(T0+1900000).toISOString()}:diary;};
 await runLiveTickLoop({io:r.io,clock:r.clock,runSeconds:3000,batchSeconds:600});const ticks=new Set(r.out.batches.map(x=>x.snapshot.recorded_tick));assert.deepEqual([...ticks].sort(),[124,125]);});
test('no recorded tick -> does nothing (never invents state)',async()=>{const r=rig(T0);r.io.readDiary=()=>({tick:1});const res=await runLiveTickLoop({io:r.io,clock:r.clock,runSeconds:100});assert.equal(res.ok,false);assert.equal(r.out.commits,0);});
test('workflow: chained + watchdog, batch commits, read-only on the recorded diary branch, no secrets',()=>{const y=readFileSync(new URL('../../../.github/workflows/zeref-live-tick-loop.yml',import.meta.url),'utf8');
 assert.match(y,/schedule:\n    - cron:/);assert.match(y,/workflow_dispatch/);assert.match(y,/group: zeref-live-tick-loop/);assert.match(y,/gh workflow run zeref-live-tick-loop\.yml/);assert.match(y,/zeref-live-tick-run\.mjs diary live "\$RUN_SECONDS" 600/);
 assert.doesNotMatch(y,/secrets\.(?!github)/);assert.doesNotMatch(y,/push[^\n]*zeref-diary\b(?!-)/);assert.match(y,/deploymentEnabled":false/);assert.match(y,/SIMULATED/);
 const s=readFileSync(new URL('../scripts/zeref-live-tick-run.mjs',import.meta.url),'utf8');assert.doesNotMatch(s,/origin','HEAD:zeref-diary/);});
test('engine/orchestrator never use Math.random',()=>{for(const f of ['../lib/zeref/live-tick-run.mjs','../lib/zeref/live-tick.mjs'])assert.doesNotMatch(readFileSync(new URL(f,import.meta.url),'utf8').replace(/\/\*[^]*?\*\//g,''),/Math\.random/);});
