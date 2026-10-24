import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {isPanGesture,worldPerPixel,panStep,clampPan,decayPan,centroid,keyPanPixels} from '../lib/universe/view-gestures.mjs';
const B={rx:1,ry:0,rz:0,ux:0,uy:1,uz:0,k:.01};
test('pan gestures: right drag, shift drag, two fingers; plain drag rotates',()=>{
 assert.ok(isPanGesture({button:2}));assert.ok(isPanGesture({shiftKey:true}));assert.ok(isPanGesture({pointers:2}));assert.ok(!isPanGesture({}));});
test('pan follows the finger and uses the camera basis',()=>{
 const p=panStep({x:0,y:0,z:0},B,100,0);assert.ok(Math.abs(p.x+1)<1e-12&&p.y===0);// finger right: camera target moves left, so the scene slides right
 const q=panStep({x:0,y:0,z:0},B,0,100);assert.ok(Math.abs(q.y-1)<1e-12);// finger down: the scene slides down
 const r=panStep({x:0,y:0,z:0},{rx:0,ry:0,rz:1,ux:0,uy:1,uz:0,k:.5},10,0);assert.ok(Math.abs(r.z+5)<1e-12&&r.x===0);});
test('clamp, decay, centroid, keys, perspective scale',()=>{
 const c=clampPan({x:30,y:40,z:0},5);assert.ok(Math.abs(Math.hypot(c.x,c.y)-5)<1e-12);assert.deepEqual(clampPan({x:1,y:0,z:0},5),{x:1,y:0,z:0});
 assert.ok(decayPan({x:10,y:0,z:0},.5).x<10&&decayPan({x:10,y:0,z:0},0).x===10);assert.deepEqual(centroid({x:0,y:0},{x:10,y:20}),{x:5,y:10});
 assert.deepEqual(keyPanPixels('ArrowLeft'),[40,0]);assert.equal(keyPanPixels('a'),null);assert.ok(Math.abs(worldPerPixel(90,10,200)-0.1)<1e-12);});
test('pure and wired into the cage pocket and /universe',()=>{
 const m=readFileSync(new URL('../lib/universe/view-gestures.mjs',import.meta.url),'utf8').split('\n').filter(l=>!l.trim().startsWith('//')).join('\n');assert.ok(!/Math\.random|Date\.|performance\./.test(m));
 for(const f of ['cage-pocket-dimension.tsx','universe-3d.tsx'])assert.match(readFileSync(new URL('../components/'+f,import.meta.url),'utf8'),/view-gestures/);});
