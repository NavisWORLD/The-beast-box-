// Alive props + One Mind threads: seeded (no Math.random), Emeth's lines only, fired only through the gate on real events.
import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {aliveInstances,crossedPeak,nearness,sunFacing,ALIVE_EVENTS,aliveLine,createAliveGate,threadFade,threadBrightness,creatureHome,ALIVE_PROPS} from '../lib/universe/alive-props.mjs';
const LINES=JSON.parse(fs.readFileSync(new URL('../lib/universe/data/living_world_lines.json',import.meta.url),'utf8')).alive_at_volumes;
test('instances are seeded and deterministic',()=>{const a=aliveInstances('s1','crystal_small',20),b=aliveInstances('s1','crystal_small',20),c=aliveInstances('s2','crystal_small',20);
 assert.deepEqual([...a.phase],[...b.phase]);assert.notDeepEqual([...a.phase],[...c.phase]);for(const l of a.life)assert.ok(l>=0&&l<=1);assert.equal(aliveInstances('s','nope',3),null);});
test('every alive event has an Emeth pool and lines come only from it, by seed',()=>{for(const k of ALIVE_EVENTS){assert.ok(LINES[k]?.length,k);
 const l=aliveLine(k,'seed',1);assert.ok(LINES[k].includes(l));assert.equal(aliveLine(k,'seed',1),l);}assert.equal(aliveLine('made_up','s',1),null);});
test('gate fires only known events and rate-limits',()=>{const g=createAliveGate({perKind:90,global:12});assert.throws(()=>g.fire('not_an_event','s',0));
 const f=g.fire('rock_breathe','s',100);assert.ok(f&&LINES.rock_breathe.includes(f.line));assert.equal(g.fire('rock_breathe','s',101),null);assert.equal(g.fire('crystal_hum','s',105),null);assert.ok(g.fire('crystal_hum','s',113));});
test('real-event detectors',()=>{assert.equal(crossedPeak(0,0,4,0),false);let hits=0;for(let t=0;t<40;t+=.5)if(crossedPeak(t,t+.5,4,0))hits++;assert.equal(hits,10);
 assert.equal(nearness([0,0,0],[[10,0,0]],3),0);assert.ok(nearness([0,0,0],[[1,0,0]],3)>0);assert.deepEqual(sunFacing([0,-1,0],[0,0,0]),[0,1,0]);
 const f=sunFacing([1,.01,0],[0,0,0]);assert.ok(Math.acos(f[1])<=Math.PI/3+1e-6);});
test('threads fade in only when pulled back; brightness from real tick times',()=>{assert.equal(threadFade(100),0);assert.equal(threadFade(2000),1);
 const now=Date.parse('2026-10-23T12:00:00Z');assert.ok(threadBrightness({last_tick_at:'2026-10-23T11:59:00Z'},now).b>threadBrightness({last_tick_at:'2026-10-20T12:00:00Z'},now).b);
 assert.equal(threadBrightness({},now).b,.12);assert.equal(creatureHome('s','a',[{id:'p'},{id:'q'}]),creatureHome('s','a',[{id:'p'},{id:'q'}]));});
test('no Math.random in alive code',()=>{for(const f of ['../lib/universe/alive-props.mjs','../lib/universe/surface-three.ts','../components/universe-3d.tsx','../app/api/cosmos/activity/route.ts'])
 assert.ok(!/Math\.random\s*\(/.test(fs.readFileSync(new URL(f,import.meta.url),'utf8')),f);assert.ok(Object.keys(ALIVE_PROPS).length>=9);});
