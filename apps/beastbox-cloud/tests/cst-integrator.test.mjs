import test from 'node:test';import assert from 'node:assert/strict';import * as THREE from 'three';
import {seededRng,fnv1a,createCSTClock,lorenzStep,createCSTState,stepCSTState,motionParams,springStep,verletPoint,verletIntegrate,solveDistance,solveSphereCollision,coherenceFeedback,creatureMood,CST_GAIN,clampDt,genesisDrag} from '../lib/physics/cst-integrator.mjs';
import {createSpringChain,stepSpringChain,applyToBones} from '../lib/physics/spring-bones.mjs';
import {prng} from '../lib/companion/film-motion.mjs';import {rngFrom} from '../lib/pocket-sand.mjs';

test('one shared PRNG: film-motion and pocket-sand use the integrator rng (same sequence)',()=>{
 const a=seededRng('zeref'),b=prng('zeref'),c=rngFrom('zeref');
 for(let i=0;i<100;i++){const x=a();assert.equal(b(),x);assert.equal(c(),x);assert.ok(x>=0&&x<1);}
 // reference value pinned so the sequence can never drift silently
 assert.equal(fnv1a('a'),0xe40c292c);
});
test('fixed-step clock is frame-rate independent and deterministic',()=>{
 const run=frames=>{const c=createCSTClock({seed:'s',hz:120});let n=0;for(const f of frames)c.tick(f,()=>n++);return [n,c.t];};
 const [n60]=run(Array(60).fill(1/60)),[n30]=run(Array(30).fill(1/30));
 assert.equal(n60,120);assert.equal(n30,120);
 const c=createCSTClock({maxSubsteps:4});assert.equal(c.tick(5,()=>{}),4);assert.ok(c.acc<c.h);
});
test('Lorenz port stays on the bounded attractor and follows CST gains',()=>{
 const L={x:.1,y:.2,z:.3};for(let i=0;i<20000;i++)lorenzStep(L,.005,{arousal:.9,qe:.8});
 assert.ok(Math.abs(L.x)<40&&Math.abs(L.y)<60&&L.z>-1&&L.z<80,JSON.stringify(L));
 assert.equal(CST_GAIN.lorenzRho,.30);assert.equal(coherenceFeedback(.5,.75),.6);
 const m=creatureMood({resonance:1,coherence:0,curiosity:.3,avoid:.2,instability:.25,chaos:0});
 assert.deepEqual(m,{joy:.6,curiosity:.3,fear:.2,calm:.75,mischief:.12});
});
test('CST state is deterministic per seed and maps to motion params in range',()=>{
 const run=seed=>{const S=createCSTState(seed,{emotion:{arousal:.8}});for(let i=0;i<600;i++)stepCSTState(S,1/120);return motionParams(S);};
 assert.deepEqual(run('zeref'),run('zeref'));assert.notDeepEqual(run('zeref'),run('nyx'));
 const calm=createCSTState('a',{emotion:{arousal:.05}}),hyped=createCSTState('a',{emotion:{arousal:.95}});
 assert.ok(motionParams(hyped).stiffness>motionParams(calm).stiffness,'arousal → stiffness');
 const p=run('x');for(const k of ['stiffness','damping','turbulence'])assert.ok(Number.isFinite(p[k])&&p[k]>=0);
});
test('solvers: spring converges, verlet + distance keeps length, collision pushes out',()=>{
 const s={x:0,v:0};for(let i=0;i<2000;i++)springStep(s,1,90,9,1/120);assert.ok(Math.abs(s.x-1)<1e-3);
 const a=verletPoint(0,0,0,0),b=verletPoint(1,0,0);
 for(let i=0;i<500;i++){verletIntegrate([a,b],1/120,{acc:{x:0,y:-9.8,z:0}});for(let k=0;k<4;k++)solveDistance(a,b,1);}
 assert.ok(Math.abs(Math.hypot(b.x,b.y,b.z)-1)<1e-3);assert.ok(b.y<-.9,'hangs under gravity');
 const p={x:.1,y:0,z:0};assert.ok(solveSphereCollision(p,{x:0,y:0,z:0,r:.5}));assert.ok(Math.abs(p.x-.5)<1e-9);
 assert.equal(clampDt(1),.05);assert.equal(clampDt(-1),0);assert.equal(genesisDrag(0),1);
});
test('spring chain stays connected, is deterministic and settles to rest without wind',()=>{
 const rest=[0,1,2,3,4].map(i=>({x:0,y:-i*.2,z:0}));
 const mk=()=>{const ch=createSpringChain(rest,{name:'tail',gravity:0});const S=createCSTState('z');
  for(let i=0;i<400;i++){stepCSTState(S,1/120);stepSpringChain(ch,1/120,{mp:motionParams(S),t:i/120});}return ch;};
 const a=mk(),b=mk();assert.deepEqual(a.pts,b.pts);
 for(let i=1;i<a.pts.length;i++){const p=a.pts[i],q=a.pts[i-1];assert.ok(Math.abs(Math.hypot(p.x-q.x,p.y-q.y,p.z-q.z)-.2)<.02);}
 const ch=createSpringChain(rest,{gravity:0});for(let i=0;i<300;i++)stepSpringChain(ch,1/120);
 assert.ok(Math.abs(ch.pts[4].y+.8)<1e-3);
});
test('applyToBones rotates a THREE bone chain toward the simulated tip',()=>{
 const b0=new THREE.Bone(),b1=new THREE.Bone(),root=new THREE.Group();b1.position.y=1;b0.add(b1);root.add(b0);root.updateMatrixWorld(true);
 const ch=createSpringChain([{x:0,y:0,z:0},{x:0,y:1,z:0}]);ch.pts[1].x=1;ch.pts[1].y=0;applyToBones(THREE,ch,[b0,b1]);
 const w=new THREE.Vector3().setFromMatrixPosition(b1.matrixWorld);assert.ok(w.x>.99&&Math.abs(w.y)<1e-6);
});
