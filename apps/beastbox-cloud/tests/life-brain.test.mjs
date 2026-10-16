import test from 'node:test';import assert from 'node:assert/strict';
import {createLife,stepLife,pokeLife,modeWeights,POCKET_RADIUS} from '../lib/creatures3d/life-brain.mjs';
const env=(o={})=>({mood:{joy:.6,curiosity:.6,fear:.1,calm:.6,mischief:.4},night:.5,rain:0,flowers:[{x:1,z:1}],fireflies:[{x:-1,y:.8,z:0}],residents:[{x:2,z:-1}],cam:{x:0,z:9},...o});
const run=(seed,n,e)=>{const L=createLife(seed);for(let i=0;i<n;i++)stepLife(L,1/30,e);return L;};
test('life is deterministic per seed',()=>{const a=run('bb-1',3000,env()),b=run('bb-1',3000,env());assert.deepEqual([a.x,a.z,a.mode,a.history],[b.x,b.z,b.mode,b.history]);
 const c=run('bb-2',3000,env());assert.notDeepEqual([a.x,a.z],[c.x,c.z]);});
test('it lives its own life: varied modes, mostly not facing the camera, stays in the pocket',()=>{const L=createLife('bb-3');let cam=0,n=0,maxR=0;const seen=new Set();
 for(let i=0;i<30*240;i++){stepLife(L,1/30,env());seen.add(L.mode);if(L.lookCam>.5)cam++;n++;maxR=Math.max(maxR,Math.hypot(L.x,L.z));}
 assert.ok(seen.size>=4,[...seen].join());assert.ok(cam/n<.2,'camera share '+cam/n);assert.ok(maxR<=POCKET_RADIUS+1e-9);});
test('rain sends it to shelter; poke with joy makes it approach',()=>{const L=createLife('bb-4');stepLife(L,1/30,env({rain:.8}));assert.equal(L.mode,'shelter');
 const M=createLife('bb-5');pokeLife(M,{joy:.8,fear:.1});stepLife(M,1/30,env());assert.equal(M.mode,'approach');assert.equal(M.attn.kind,'camera');});
test('treats get eaten',()=>{const L=createLife('bb-6',{x:0,z:0});let eaten=null;const treats=[{x:.6,z:.2,id:'t1'}];for(let i=0;i<600&&!eaten;i++)stepLife(L,1/30,env({treats,onEat:id=>{eaten=id;}}));assert.equal(eaten,'t1');});
test('night + mischief favours chasing fireflies; storms forbid it',()=>{const L=createLife('x');const w=modeWeights(L,env({night:1,mood:{joy:.5,curiosity:.5,fear:0,calm:.5,mischief:1}}));assert.ok(w.chase>w.glance);assert.equal(modeWeights(L,env({rain:.9})).chase,0);});
