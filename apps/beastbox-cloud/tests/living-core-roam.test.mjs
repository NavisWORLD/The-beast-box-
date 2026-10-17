import test from 'node:test';import assert from 'node:assert/strict';
import {reactToWords,nextGoal,rng,SPOTS,addCreation,MAX_CREATIONS,constructPoints,hopPose,flap,baseMood,loadCreations,saveCreations} from '../lib/living-core/roam-brain.mjs';
import {CREATURES,RESIDENT_LC} from '../lib/living-core/creatures.js';
test('chat words drive mood and creations',()=>{assert.equal(reactToWords('I love you').emotion,'happy');assert.equal(reactToWords('I love you').shape,'heart');assert.equal(reactToWords('why is that?').emotion,'curious');assert.equal(reactToWords('time to sleep').emotion,'sleepy');assert.equal(reactToWords('').emotion,null);});
test('goals: sleepy goes to nap moss, curious to a library',()=>{const r=rng(3);assert.equal(nextGoal(r,'sleepy').id,'nap-moss');assert.equal(nextGoal(r,'curious').kind,'library');assert.equal(SPOTS.filter(s=>s.kind==='library').length,3);});
test('creations persist capped',()=>{let l=[];for(let i=0;i<20;i++)l=addCreation(l,{shape:'star',x:i,z:0,seed:i});assert.equal(l.length,MAX_CREATIONS);assert.equal(l.at(-1).x,19);
 const m=new Map();const s={getItem:k=>m.get(k)??null,setItem:(k,v)=>m.set(k,v)};saveCreations(s,'bb-x',l);assert.equal(loadCreations(s,'bb-x').length,MAX_CREATIONS);});
test('construct points finite',()=>{for(const sh of ['spiral','ring','star','heart','helix','bloom']){const p=constructPoints(sh,7,64);assert.ok(p.every(Number.isFinite));}});
test('motion bible: squash .82 stretch 1.18, 35% downstroke',()=>{assert.ok(Math.abs(hopPose(.5).sy-1.18)<1e-9);assert.ok(Math.abs(hopPose(0).sy-.82)<1e-9);assert.equal(flap(0),1);assert.ok(Math.abs(flap(.35/1.1)+1)<1e-9);});
test('mood from beast state',()=>{assert.equal(baseMood({emotions:{joy:.9,calm:.1}},'idle'),'happy');assert.equal(baseMood(null,'sleeping'),'sleepy');});
test('every universe resident has a living-core config with one final block',()=>{for(const [id,c] of Object.entries(RESIDENT_LC)){assert.ok(CREATURES[c],id);assert.ok(CREATURES[c].src.endsWith('.png'));assert.ok((CREATURES[c].opts.eyes||[]).length>0,id);}});
import {readFileSync} from 'node:fs';
test('cage residents use living-core first, legacy GLB/hull/sprite as fallback',()=>{const s=readFileSync(new URL('../components/pocket-residents.ts',import.meta.url),'utf8');assert.match(s,/getLivingCore\(THREE,lcName\)/);assert.match(s,/catch\(\(\)=>legacy\(\)\)/);assert.match(s,/stepLivingCore/);
 for(const id of ['art-frostmitt','art-nyxbean','art-kairo','art-velvetcoil','art-shardhowl'])assert.ok(RESIDENT_LC[id],id);});
import {buildSynapseNet,fireStep,channelValues,EMO_VIBE} from '../lib/living-core/synapse-net.mjs';
test('synapse net: 12 CST channel families, wired, firing scales with excitation',()=>{const n=400,p=new Float32Array(n*3),q=new Float32Array(n*3);for(let i=0;i<n;i++){const a=i*2.4,b=Math.acos(1-2*(i+.5)/n);p[i*3]=Math.sin(b)*Math.cos(a);p[i*3+1]=Math.cos(b);p[i*3+2]=Math.sin(b)*Math.sin(a);q.set([p[i*3],p[i*3+1],p[i*3+2]],i*3);}
 const net=buildSynapseNet(p,q,n,{perChannel:6});assert.equal(net.count,72);assert.equal(new Set(net.ch).size,12);assert.ok(net.edges.length>=72);
 const v=channelValues({ch:{valence:.8,arousal:.6,coherence:.5}});assert.equal(v.length,12);
 const a=new Float32Array(12),b=new Float32Array(12);let fa=0,fb=0;for(let i=0;i<200;i++){fa+=fireStep(a,v,.05,0).length;fb+=fireStep(b,v,.05,1).length;}assert.ok(fb>fa*2);assert.ok(EMO_VIBE.scared.hz>EMO_VIBE.sleepy.hz);});
