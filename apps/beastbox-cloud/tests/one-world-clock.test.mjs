import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {grow} from '../lib/universe/tiny-universe.mjs';
import {allStorms} from '../lib/universe/seeded-storms.mjs';
import {createWorldClock,oneWorldClock,currentWorldClock,worldClockCount,ONE_WORLD_KEY} from '../lib/world/one-world-clock.mjs';
const genesis=JSON.parse(fs.readFileSync(new URL('../public/universe/tiny-universe-genesis.json',import.meta.url),'utf8'));
const mem=()=>{const m=new Map();return {getItem:k=>m.has(k)?m.get(k):null,setItem:(k,v)=>m.set(k,String(v))};};
const manual=()=>({setTimer:()=>1,clearTimer:()=>{}});
const src=f=>fs.readFileSync(new URL('../'+f,import.meta.url),'utf8');
test('exactly one world clock per page: repeated calls (route changes, remounts) return the same instance',()=>{
 const before=worldClockCount();
 const a=oneWorldClock({genesis,grow,storage:mem(),...manual()});const b=oneWorldClock({genesis,grow,storage:mem(),...manual()});const c=oneWorldClock();
 assert.equal(a,b);assert.equal(a,c);assert.equal(currentWorldClock(),a);assert.equal(worldClockCount()-before,1);
 a.stop();
});
test('every view reads the same tick and the same storm count (no more Storms 20 vs 19)',()=>{
 const clk=createWorldClock({genesis,grow,storage:mem(),...manual()});
 const views={tiny:null,orbit:null,world:null};
 for(const k of Object.keys(views))clk.subscribe(u=>{views[k]=u;});
 for(let i=0;i<300;i++){clk.step();const counts=Object.values(views).map(u=>allStorms(u).length),ticks=Object.values(views).map(u=>u.tick);
  assert.equal(new Set(counts).size,1);assert.equal(new Set(ticks).size,1);}
 assert.equal(views.tiny.tick,300);
});
test('deterministic: same genesis -> same universe at the same tick (seeded, no Math.random)',()=>{
 const a=createWorldClock({genesis,grow,...manual()}),b=createWorldClock({genesis,grow,...manual()});
 for(let i=0;i<50;i++){a.step();b.step();}assert.deepEqual(a.get(),b.get());
 assert.doesNotMatch(src('lib/world/one-world-clock.mjs'),/Math\.random/);
});
test('the one clock is the single writer of lw:universe and resumes it only for the same seed/schema',()=>{
 const s=mem();const a=createWorldClock({genesis,grow,storage:s,...manual()});for(let i=0;i<5;i++)a.step();
 assert.equal(JSON.parse(s.getItem(ONE_WORLD_KEY)).tick,5);
 const b=createWorldClock({genesis,grow,storage:s,...manual()});assert.equal(b.get().tick,5);
 const s2=mem();s2.setItem(ONE_WORLD_KEY,JSON.stringify({...genesis,seed:'other',tick:99}));assert.equal(createWorldClock({genesis,grow,storage:s2,...manual()}).get().tick,genesis.tick);
});
test('only one interval runs, and pause stops growth without forking state',()=>{
 let timers=0;const clk=createWorldClock({genesis,grow,setTimer:()=>++timers,clearTimer:()=>{}});clk.start();clk.start();assert.equal(timers,1);
 clk.setPaused(true);const t=clk.get().tick;clk.step();assert.equal(clk.get().tick,t);
});
test('wiring: root layout mounts the provider once; pages run no private grow() loop',()=>{
 const lay=src('app/layout.tsx');assert.equal((lay.match(/<OneWorldProvider\/>/g)||[]).length,1);
 const tiny=src('components/tiny-universe-view.tsx');assert.doesNotMatch(tiny,/\bgrow\(/);assert.doesNotMatch(tiny,/setInterval/);assert.match(tiny,/useOneWorld\(/);
 const lw=src('components/living-world.tsx');assert.match(lw,/oneClock\.get\(\)/);assert.match(lw,/storms:allStorms\(u\)\.length/);
 assert.match(lw,/if\(!\(oneClock&&!VISIT\)\)lwStore\.setItem\('lw:universe'/);
 const u3=src('components/universe-3d.tsx');assert.match(u3,/allStorms\(u\)/);
});
