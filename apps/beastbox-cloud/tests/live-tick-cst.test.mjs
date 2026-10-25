import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {liveBase,liveSecond,advanceChain,CHAIN_GENESIS,chainStep,usesCst,CST_MAX_SECONDS,CST_AMPLITUDE,LIVE_TICK_SCHEMA,LIVE_TICK_SCHEMA_CST,LIVE_LABELS} from '../lib/zeref/live-tick.mjs';
const diaryDefault={tick:124,xp:812,last_tick_at:'2026-10-25T14:00:00Z',signals:{resonance:88,curiosity:61.5,warmth:70,energy:50,memory:40},identity:{beast_id:'bb-test'},recent:[{xp_gain:12},{xp_gain:8},{xp_gain:10}]};
const diary=diaryDefault,E={engine:'cst'};
const T0=Date.parse(diary.last_tick_at),at=(b,s)=>liveSecond(b,T0+s*1000);

test('CST is OPT-IN: default is the hash wander; option or diary field enables it; no signals stays wander',()=>{
 assert.equal(liveBase(diary).engine,'wander');assert.equal(at(liveBase(diary),30).schema,LIVE_TICK_SCHEMA);assert.equal(liveBase({...diary,live_engine:'cst'}).engine,'cst');
 assert.equal(liveBase(diary,E).engine,'cst');assert.equal(liveBase({...diary,signals:{}},E).engine,'wander');
 assert.equal(liveBase(diary,{engine:'wander'}).engine,'wander');
 const x=at(liveBase(diary,E),30);assert.equal(x.schema,LIVE_TICK_SCHEMA_CST);assert.equal(x.engine,'cst');assert.equal(x.label,'SIMULATED');
 assert.match(x.cst.label,/SIMULATED/);assert.match(x.cst.label,/MODEL/);assert.match(LIVE_LABELS.live,/SIMULATED/);
});
test('fallback engine is the previous hash wander, bit for bit (pinned from origin/main before this change)',()=>{
 const b=liveBase(diary,{engine:'wander'});assert.equal(at(b,0).schema,LIVE_TICK_SCHEMA);
 const pin={0:{resonance:85.91,curiosity:63.95,warmth:67.28,energy:51.97,memory:39.9},1:{resonance:86.44,curiosity:63.42,warmth:67.61,energy:51.65,memory:40.23},
  59:{resonance:87.12,curiosity:62.74,warmth:71.32,energy:50.61,memory:41.28},3600:{resonance:88.85,curiosity:61.85,warmth:70.6,energy:49.35,memory:38.29},
  86400:{resonance:86.11,curiosity:59.33,warmth:72.48,energy:49.78,memory:39.88},2000000:{resonance:88.77,curiosity:60.96,warmth:70.65,energy:50.21,memory:41.04}};
 for(const [s,v] of Object.entries(pin))assert.deepEqual(at(b,+s).signals,v,'sec '+s);
 assert.equal(CHAIN_GENESIS(b),'6b91a9cb4e780f58ad56321cd10ace318ee59ab06660c57adf27974a06a58c71');
 assert.equal(advanceChain(b,CHAIN_GENESIS(b),0,300),'5e0114ed1ad749ca0dc29c45907df3ae77d2a0dfa1696e162ec164378988c428');
});
test('CST second N is always second N: fresh base, forward, backward and random access agree exactly',()=>{
 const b=liveBase(diary,E),fwd=[];for(let s=0;s<=400;s++)fwd.push(JSON.stringify(at(b,s)));
 for(const s of [400,0,250,3,399,17,250])assert.equal(JSON.stringify(at(b,s)),fwd[s],'sec '+s);
 for(const s of [0,1,99,400])assert.equal(JSON.stringify(at(liveBase(diary,E),s)),fwd[s]);
 assert.equal(advanceChain(b,CHAIN_GENESIS(b),0,400),advanceChain(liveBase(diary,E),advanceChain(liveBase(diary,E),CHAIN_GENESIS(b),0,150),151,400));
 assert.notEqual(CHAIN_GENESIS(b),CHAIN_GENESIS(liveBase(diary,{engine:'wander'})));
});
test('CST signals move every few seconds, stay within ±3 of recorded and in 0..100; second 0 offset is 0',()=>{
 const b=liveBase(diary,E);const seen={};let lo=1e9,hi=-1e9;
 for(let s=0;s<=1800;s++){const x=at(b,s);for(const [k,v] of Object.entries(x.signals)){(seen[k]??=new Set()).add(v);const d=v-diary.signals[k];lo=Math.min(lo,d);hi=Math.max(hi,d);assert.ok(Math.abs(d)<=CST_AMPLITUDE+.006&&v>=0&&v<=100);}}
 for(const k of Object.keys(diary.signals))assert.ok(seen[k].size>=20,k+' moved '+seen[k].size+' distinct values');
 for(const [k,v] of Object.entries(at(b,0).signals))assert.equal(v,diary.signals[k]);
 assert.ok(hi-lo>2,'overall swing '+(hi-lo));
});
test('different beasts and different recorded ticks give different CST trajectories',()=>{
 assert.notDeepEqual(at(liveBase(diary,E),300).signals,at(liveBase({...diary,identity:{beast_id:'other'}},E),300).signals);
 assert.notDeepEqual(at(liveBase(diary,E),300).signals,at(liveBase({...diary,tick:125},E),300).signals);
});
test('xp rule unchanged; past CST_MAX_SECONDS the engine falls back to the hash wander; catch-up of a day is bounded',()=>{
 const b=liveBase(diary,E),w=liveBase(diary,{engine:'wander'});assert.equal(at(b,500).xp_live,at(w,500).xp_live);
 assert.ok(usesCst(b,CST_MAX_SECONDS)&&!usesCst(b,CST_MAX_SECONDS+1));
 assert.deepEqual(at(b,CST_MAX_SECONDS+60).signals,at(w,CST_MAX_SECONDS+60).signals);assert.equal(at(b,CST_MAX_SECONDS+60).schema,LIVE_TICK_SCHEMA);
 const t=Date.now();at(liveBase(diary,E),CST_MAX_SECONDS);assert.ok(Date.now()-t<8000,'1 day catch-up ms '+(Date.now()-t));
});
test('engine source stays free of Math.random / clocks and states the Lorenz dt difference',()=>{
 const src=readFileSync(new URL('../lib/zeref/live-tick.mjs',import.meta.url),'utf8');
 assert.doesNotMatch(src.replace(/\/\*[^]*?\*\//g,''),/Math\.random|Date\.now|new Date|Math\.sin|Math\.exp|Math\.pow/);assert.match(src,/0\.035/);assert.match(src,/stepCSTState/);
});
