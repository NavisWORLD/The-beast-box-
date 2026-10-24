// "The engine carries the sky", PR 1: the sun is stepped ENGINE state (sunAngle/sunDir/dayLength on the world field).
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {createWorldField,stepWorldField} from '../lib/universe/world-field.mjs';
import {DAY_LENGTH_TICKS,sunDirAt,sunFromElevation,nightFactor} from '../lib/universe/genesis-sun.mjs';
const init=n=>({id:Math.abs(n[0])>.7?'deep_ocean':'grassland',h:Math.abs(n[0])>.7?-.2:.2});
const mk=(seed='s')=>createWorldField({seed,W:16,H:8,initial:init});
const ins=F=>{const out=[];for(let k=0;k<F.N;k++)out.push(F.temp[k]);return out;};
test('the world gains sun fields; existing fields are untouched',()=>{
 const F=mk();for(const k of ['sunAngle','sunDir','dayLength','tick','storm','temp','moist','S','clock'])assert.ok(k in F,k);
 assert.equal(F.dayLength,DAY_LENGTH_TICKS);assert.ok(Math.abs(Math.hypot(...F.sunDir)-1)<1e-9);
});
test('same seed + same tick count = identical sun fields and per-cell state, twice',()=>{
 const a=mk(),b=mk();for(let i=0;i<500;i++){stepWorldField(a,1);stepWorldField(b,1);}
 assert.equal(a.tick,b.tick);assert.equal(a.sunAngle,b.sunAngle);assert.deepEqual(a.sunDir,b.sunDir);assert.deepEqual([...a.temp],[...b.temp]);assert.deepEqual([...a.moist],[...b.moist]);
});
test('the sun advances 2pi/dayLength per engine tick and returns after one full day',()=>{
  const F=mk();const a0=F.sunAngle,t0=F.tick;stepWorldField(F,1);const n=F.tick-t0;const d=((F.sunAngle-a0)%(2*Math.PI)+2*Math.PI)%(2*Math.PI);assert.ok(n>0);assert.ok(Math.abs(d-n*2*Math.PI/F.dayLength)<1e-9);
 const G=mk();const g0=G.tick,s0=G.sunAngle;while(G.tick-g0<G.dayLength)stepWorldField(G,1);assert.ok(Math.abs(((G.sunAngle-s0+Math.PI)%(2*Math.PI)+2*Math.PI)%(2*Math.PI)-Math.PI)<1e-6);
});
test('the engine sun equals the view geometry (x=cos a, y=.35 sin(a/2+1), z=sin a) at the same angle',()=>{
 const F=mk();for(let i=0;i<37;i++)stepWorldField(F,1);const a=F.sunAngle;const v=[Math.cos(a),.35*Math.sin(a*.5+1),Math.sin(a)];const l=Math.hypot(...v);
 F.sunDir.forEach((x,i)=>assert.ok(Math.abs(x-v[i]/l)<1e-12));
});
test('an explicit sun is still an OVERRIDE: different insolation',()=>{
 const a=mk(),b=mk();for(let i=0;i<200;i++){stepWorldField(a,1);stepWorldField(b,1,{sun:[0,1,0]});}
 assert.equal(a.tick,b.tick);assert.notDeepEqual([...a.temp],[...b.temp]);// the override really drives insolation
});
test('the sun phase is seeded from the recorded counts only (different seed, different phase; no clock)',()=>{
 assert.notEqual(mk('a').sunAngle,mk('b').sunAngle);assert.equal(mk('a').sunAngle,mk('a').sunAngle);
 const src=readFileSync(new URL('../lib/universe/world-field.mjs',import.meta.url),'utf8');assert.ok(!/Math\.random|Date\.now|performance\.now|new Date/.test(src));
});
test('night factor over a full engine day: day, dusk and night all occur; endpoints 0 and 1',()=>{
 const n=[1,0,0];let lo=1,hi=0;for(let i=0;i<DAY_LENGTH_TICKS;i+=8){const s=sunDirAt(i/DAY_LENGTH_TICKS*2*Math.PI);const f=nightFactor(n[0]*s[0]+n[1]*s[1]+n[2]*s[2]);lo=Math.min(lo,f);hi=Math.max(hi,f);}
 assert.equal(lo,0);assert.equal(hi,1);
});
test('pen port: sunFromElevation is the three.js spherical conversion (zenith up, horizon flat)',()=>{
 const z=sunFromElevation(90);assert.ok(Math.abs(z[1]-1)<1e-12);const h=sunFromElevation(0);assert.ok(Math.abs(h[1])<1e-12);assert.ok(Math.abs(Math.hypot(...sunFromElevation(25))-1)<1e-12);
 const src=readFileSync(new URL('../lib/universe/genesis-sun.mjs',import.meta.url),'utf8');assert.ok(src.includes('54f58cbedb0d002c5cc62d908a810446ee0142c303a443a80e2aaab135ced694'));
});
