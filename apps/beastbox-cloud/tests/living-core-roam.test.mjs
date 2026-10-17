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

test('universe roamers leave their home zone but stay inside the universe limit', async () => {
  const {createActor,stepActor,motionPersona}=await import('../lib/companion/film-motion.mjs');
  const {UNIVERSE_R}=await import('../lib/living-core/roam-brain.mjs');
  const a=createActor(motionPersona({id:'art-kairo'}),{x:2,z:0,radius:.9,seed:'u',universe:UNIVERSE_R});
  let far=0;for(let i=0;i<20000;i++){const p=stepActor(a,1/30,{});far=Math.max(far,Math.hypot(p.x-2,p.z));assert.ok(Math.hypot(p.x,p.z)<=UNIVERSE_R+1e-6);}
  assert.ok(far>3,'left home zone: '+far);
});

test('surface life: Lorenz chaos stays bounded and never repeats; heartbeat + spring are sane', async () => {
  const {lorenzStep,heartbeat,springStep}=await import('../lib/living-core/surface-math.mjs');
  const s=[1,1,20];const seen=new Set();for(let i=0;i<20000;i++){lorenzStep(s,1/240,.2);assert.ok(Math.abs(s[0])<60&&Math.abs(s[2])<80);if(i%500===0)seen.add(s.map(v=>v.toFixed(3)).join());}
  assert.equal(seen.size,40);
  let mx=0;for(let t=0;t<2;t+=.01)mx=Math.max(mx,heartbeat(t));assert.ok(mx>.9&&mx<=1);
  const sp={x:0,v:-1.4};for(let i=0;i<120;i++)springStep(sp,1/120);assert.ok(Math.abs(sp.x)<.02);
});

test('active Beast roams the universe when the Cage opts in', async () => {
  const {createLife,stepLife}=await import('../lib/creatures3d/life-brain.mjs');
  const L=createLife('bb-test');let mx=0;for(let i=0;i<30*240;i++){stepLife(L,1/30,{universe:30});mx=Math.max(mx,Math.hypot(L.x,L.z));}
  assert.ok(mx>8,'reached '+mx);assert.ok(mx<=30+1e-9);
});

test('gravity camera: dolly zoom keeps subject size while FOV widens 46→60', async () => {
  const src=(await import('node:fs')).readFileSync(new URL('../lib/living-core/gravity-camera.ts',import.meta.url),'utf8');
  assert.match(src,/FOV_BASE=46,FOV_WIDE=60/);
  const dolly=(d,a,b)=>d*Math.tan(a*Math.PI/360)/Math.tan(b*Math.PI/360);
  const d=dolly(10,46,60);assert.ok(d<10&&d>7);
  const cage=(await import('node:fs')).readFileSync(new URL('../components/cage-pocket-dimension.tsx',import.meta.url),'utf8');
  assert.match(cage,/density=\.012\*/);assert.match(cage,/dof:\(!low&&!soft&&!phoneGpu\)/);
});

test('music level is 0 until sound is unlocked and audible', async () => {
  const src=(await import('node:fs')).readFileSync(new URL('../lib/companion/beast-audio-engine.mjs',import.meta.url),'utf8');
  assert.match(src,/level\(\) \{\s*if \(!ctx \|\| !master \|\| !musicAudible\(\)\) return 0;/);
});
