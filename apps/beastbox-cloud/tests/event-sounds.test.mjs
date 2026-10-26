import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {detectEvents,initialState,recipe,noiseSamples,SOUND} from '../lib/universe/event-sounds.mjs';
const run=(frames)=>{let st=initialState(),out=[];for(const f of frames){const r=detectEvents(st,f);st=r.state;out.push(...r.events);}return out;};
const F=(tick,o={})=>({tick,boomPhase:'none',boomTerm:0,storm:0,grow:0.3,...o});
test('nothing sounds at load and a calm world is silent (no ambience)',()=>{assert.deepEqual(run([F(0,{storm:0.6,boomPhase:'flash',boomTerm:1,grow:0.9}),F(1,{storm:0.6,boomPhase:'flash',boomTerm:1,grow:0.9})]).map(e=>e.kind),[]);const calm=[];for(let t=0;t<400;t++)calm.push(F(t));assert.deepEqual(run(calm),[]);});
test('boom: a sound on the flash edge and on the shell edge only, magnitude is the engine sky term',()=>{
 const ev=run([F(0),F(10,{boomPhase:'flash',boomTerm:0.8}),F(11,{boomPhase:'flash',boomTerm:0.8}),F(30,{boomPhase:'shell',boomTerm:0.4}),F(90,{boomPhase:'fade',boomTerm:0.2}),F(150,{boomPhase:'remnant'})]);
 assert.deepEqual(ev.map(e=>e.kind),['boom','boom_shell']);assert.equal(ev[0].magnitude,0.8);assert.equal(ev[1].magnitude,0.4);
});
test('storm: one sound per upward edge crossing of the engine tension, rate-limited in engine ticks',()=>{
 const ev=run([F(0),F(10,{storm:0.3}),F(11,{storm:0.55}),F(60,{storm:0.55}),F(100,{storm:0.8}),F(130,{storm:0.1}),F(300,{storm:0.3})]);
 assert.deepEqual(ev.map(e=>[e.kind,e.tick]),[['storm',10],['storm',100],['storm',300]]);assert.ok(ev.every(e=>e.magnitude>0&&e.magnitude<=1));
});
test('growth: chimes when mean growth rises a step, not when it falls',()=>{
 const ev=run([F(0,{grow:0.30}),F(20,{grow:0.31}),F(40,{grow:0.33}),F(80,{grow:0.20}),F(120,{grow:0.15})]);assert.deepEqual(ev.map(e=>e.kind),['growth']);
});
test('every recipe is a bounded small sound; loudness grows with the engine magnitude and never passes the ceiling',()=>{
 for(const k of ['boom','boom_shell','storm','growth']){const lo=recipe(k,0.1),hi=recipe(k,1);const gain=r=>Math.max(...r.parts.map(p=>p.gain));assert.ok(gain(hi)>gain(lo));assert.ok(gain(hi)<=SOUND.maxGain);for(const p of hi.parts)assert.ok(p.dur<=2.5&&p.freq>20&&p.freq<2000);}
 assert.equal(recipe('ambient',1),null);
});
test('deterministic: two runs deep-equal, seeded noise, and the input channels are never mutated',()=>{
 const frames=[F(0),F(10,{boomPhase:'flash',boomTerm:0.7,storm:0.6,grow:0.4}),F(50,{storm:0.9,grow:0.5})];const s=JSON.stringify(frames);
 assert.deepEqual(run(frames),run(frames));assert.equal(JSON.stringify(frames),s);assert.deepEqual(noiseSamples(64,7),noiseSamples(64,7));assert.notDeepEqual(noiseSamples(64,7),noiseSamples(64,8));
});
test('no clock, no Math.random, no rAF in the module; the AudioContext is never created here',()=>{
 const src=fs.readFileSync(new URL('../lib/universe/event-sounds.mjs',import.meta.url),'utf8').replace(/^\s*\/\/.*$/gm,'');assert.ok(!/Math\.random|Date\.|performance\.now|requestAnimationFrame|AudioContext/.test(src));
});
test('the view wires it OFF by default: one toggle, AudioContext only inside the tap, events from engine channels, never in the render path before the toggle',()=>{
 const src=fs.readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
 assert.match(src,/const \[sndOn,setSndOn\]=useState\(false\)/);
 assert.match(src,/sndRef=useRef<any>\(\{on:false,ctx:null\}\)/);
 assert.equal((src.match(/new AC\(\)/g)||[]).length,1);
 const tapAt=src.indexOf('const toggleSound=');const acAt=src.indexOf('new AC()');assert.ok(tapAt>0&&acAt>tapAt&&acAt-tapAt<500);
 assert.ok(src.includes('evStep();'));assert.ok(/if\(!s\.on\|\|!s\.ctx\|\|!field\)\{evSt=null/.test(src));
 assert.equal((src.match(/data-lw-visual-life ref=\{hudVL\}\/>\{soundBtn\}/g)||[]).length,3);
 assert.ok(/detectEvents\(evSt,\{tick:field\.tick,boomPhase:vlBoom\?vlBoom\.phase:'none',boomTerm:vlBoom\?vlBoom\.skyTerm:0,storm:field\.storm/.test(src));
 const vlBlock=src.slice(src.indexOf('Visual Life Pass B6'));assert.ok(!/Math\.random/.test(vlBlock.slice(0,6000)));
});
