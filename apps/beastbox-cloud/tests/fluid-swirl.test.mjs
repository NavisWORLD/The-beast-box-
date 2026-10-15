import test from 'node:test';import assert from 'node:assert/strict';
import {createFluid,stepFluid,divergence,flowParams,stormChaos,velocityAt} from '../lib/companion/fluid-swirl.mjs';
import {chshGameWorld} from '../lib/companion/chsh-game-world.mjs';
test('storm/chaos map to Reynolds and shear width monotonically',()=>{
 const a=flowParams({storm:0,chaos:0}),b=flowParams({storm:1,chaos:1});
 assert.ok(b.reynolds>a.reynolds);assert.ok(b.shearWidth<a.shearWidth);});
test('projection keeps the flow nearly divergence-free and finite',()=>{
 const f=createFluid(24,{storm:.8,chaos:.9,seed:3});for(let i=0;i<120;i++)stepFluid(f,1/30);
 assert.ok(divergence(f)<0.5,String(divergence(f)));const v=velocityAt(f,.3,.6);assert.ok(Number.isFinite(v.u)&&Number.isFinite(v.v));});
test('solver step is cheap enough for 60fps on phones (<2ms avg here)',()=>{
 const f=createFluid(24);const t=performance.now();for(let i=0;i<300;i++)stepFluid(f,1/30);assert.ok((performance.now()-t)/300<2);});
test('CHSH game wins grow biosphere and calm the storm; labelled honestly',()=>{
 const w=chshGameWorld({quantum:{win_rate:.84,standard_error:.011},classical_bound:.75});
 assert.equal(w.label,'CHSH game (Bell nonlocality)');assert.equal(w.loopholeFree,false);
 assert.ok(w.biosphereDelta>0&&w.stormDelta<0);assert.equal(chshGameWorld(null),null);
 const sc=stormChaos({joy:30,curiosity:50,fear:20,calm:40,mischief:20},w);assert.ok(sc.storm>=0&&sc.storm<=1);});
import {historyRows} from '../lib/companion/chsh-game-world.mjs';
test('history rows newest first with fallback to bundled shard',()=>{
 const r=historyRows({entries:[{date_utc:'20261015',job_id:'a',win_rate:.81,standard_error:.012},{date_utc:'20261016',job_id:'b',win_rate:.83,standard_error:.012}]});
 assert.equal(r[0].job,'b');assert.equal(r[1].date,'2026-10-15');
 assert.equal(historyRows(null,{date_utc:'20261015',job_id:'x',quantum:{win_rate:.8,standard_error:.01}}).length,1);});
