import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {lifeTransform,hopAt,hopSeconds,IDENTITY,RESIDENT_LIFE_KEY} from '../lib/universe/sprite-life.mjs';
import {SPRITE_LIFE,SPRITE_LIFE_SOURCE_SHA256} from '../lib/universe/sprite-life-data.mjs';
test('only the five residents are mapped; Zeref has no entry and gets the identity',()=>{
 assert.deepEqual(Object.keys(SPRITE_LIFE).sort(),['frost','kairo','kittenref','shardhowl','velvetcoil']);
 assert.ok(!('zeref' in SPRITE_LIFE)&&!('zeref64' in SPRITE_LIFE));assert.deepEqual(lifeTransform('zeref',{t:3,walk:1}),IDENTITY);
 assert.deepEqual(Object.values(RESIDENT_LIFE_KEY).sort(),['frost','kairo','kittenref','shardhowl','velvetcoil']);});
test('idle follows Cosmo formula and reduced motion is the identity',()=>{
 const L=SPRITE_LIFE.frost,t=1.1,f=2*Math.PI*(t/L.idle.period_s+L.idle.phase);const r=lifeTransform('frost',{t});
 assert.ok(Math.abs(r.sy-(1+L.idle.amp_y*Math.sin(f)))<1e-12);assert.ok(Math.abs(r.sx-(1-L.idle.amp_x*Math.sin(f)))<1e-12);
 assert.deepEqual(lifeTransform('frost',{t,walk:1,sleep:1,hopU:.4,reduced:true}),IDENTITY);});
test('walk bobs up, sleep curls, hop leaves the ground and returns',()=>{
 assert.ok(lifeTransform('kairo',{t:.1,walk:1}).dy<=0);const s=lifeTransform('kairo',{t:1,sleep:1});assert.ok(s.sx>1&&s.sy<1);
 let minDy=0;for(let u=0;u<1;u+=.02)minDy=Math.min(minDy,hopAt(SPRITE_LIFE.kairo,u).dy);assert.ok(minDy<-.1);assert.deepEqual(hopAt(SPRITE_LIFE.kairo,1),{sy:1,sx:1,dy:0});assert.ok(hopSeconds('kairo')>0);});
test('pure: no clock, no Math.random; data carries provenance',()=>{
 const m=readFileSync(new URL('../lib/universe/sprite-life.mjs',import.meta.url),'utf8').replace(/\/\*[\s\S]*?\*\//g,'');assert.ok(!/Math\.random|Date\.|performance\./.test(m));
 assert.match(SPRITE_LIFE_SOURCE_SHA256,/^[0-9a-f]{64}$/);assert.match(readFileSync(new URL('../lib/universe/sprite-life-data.mjs',import.meta.url),'utf8'),/SEEDED[\s\S]*SIMULATED/);});
test('living world wires it for residents only, with no voice lines added',()=>{const lw=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
 assert.match(lw,/lifeTransform\(lk,/);assert.match(lw,/RESIDENT_LIFE_KEY as any\)\[r\.name\]/);assert.ok(!/creature_voices/.test(lw));});
