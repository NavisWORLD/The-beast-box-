import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import {nodeRigPose,blinkClosure,applyActionMultipliers,validateNodeRig,isNodeRig,ROLE_TO_ACTION,NODE_ACTIONS} from '../lib/creatures3d/node-rig.mjs';
import {withinBudget,budgetFor,deviceTier,heavyAllowed,resolveModelEntry,validateRig,roleFor,MODEL_BUDGET} from '../lib/creatures3d/creature-model-slot.mjs';
const C=new URL('../public/creatures3d/custom/',import.meta.url);
const man=JSON.parse(readFileSync(new URL('manifest.json',C),'utf8'));
const rigOf=id=>JSON.parse(readFileSync(new URL(man.models[id].rig,C),'utf8'));
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const IDS=['art-kairo','art-frostmitt','art-nyxbean','art-velvetcoil','art-shardhowl','kitten','zeref64','wisp_nebula','wisp_aurora','wisp_starlight'];
test('all ten light models are listed, light, and inside the phone budget',()=>{
 assert.deepEqual(Object.keys(man.models).sort(),[...IDS].sort());
 for(const id of IDS){const e=resolveModelEntry(man,id);assert.equal(e.tier,'light',id);assert.ok(withinBudget({bytes:e.bytes,tris:e.tris},true),id+' fits a phone');}
 assert.ok(!man.models.zeref&&!man.models['art-zeref'],'Zeref art is not in the pack');
});
test('the budget keeps heavy models off phones and does not trust an unknown size',()=>{
 assert.equal(withinBudget({bytes:2990224,tris:44278},true),false);//res_kairo
 assert.equal(withinBudget({bytes:468636,tris:33546},true),false);//res_shardhowl, small file but heavy
 assert.equal(withinBudget({bytes:2990224,tris:44278},false),true);
 assert.equal(withinBudget({},true),false);assert.equal(withinBudget({},false),true);
 assert.equal(budgetFor(true),MODEL_BUDGET.phone);
 assert.equal(deviceTier({phone:true,deviceMemory:16,cores:16}),'light');assert.equal(deviceTier({phone:false,deviceMemory:8,cores:8}),'heavy');assert.equal(deviceTier({phone:false,deviceMemory:2,cores:8}),'light');
 assert.equal(heavyAllowed({phone:true}),false);assert.equal(heavyAllowed({phone:false}),true);
});
test('every rig validates as a slot rig and as a node rig, with the honesty line',()=>{
 for(const id of IDS){const r=rigOf(id);assert.ok(isNodeRig(r),id);assert.deepEqual(validateRig(r,id),{ok:true,errors:[]},id);assert.deepEqual(validateNodeRig(r),[],id);
  assert.match(r.honesty,/Artistic 3D model/);assert.match(r.honesty,/SEEDED/);assert.match(r.honesty,/Not a measured quantum phenotype/);
  for(const a of NODE_ACTIONS)assert.ok(r.actions[a],id+' has '+a);assert.ok(r.actions.blink,id+' blink');}
});
test('at rest the pose is neutral and the pose is deterministic',()=>{
 const r=rigOf('kitten');const p=nodeRigPose(r,0,{action:'idle'});
 assert.deepEqual(nodeRigPose(r,1.234,{action:'walk',w:1}),nodeRigPose(r,1.234,{action:'walk',w:1}));
 assert.ok(Math.abs(p.nodes[r.root].s[1]-1)<.04);assert.equal(p.eye,0);
 const w0=nodeRigPose(r,.3,{action:'hop',w:0});assert.equal(w0.nodes[r.root].p[1],0);
});
test('each action drives the nodes the rig maps',()=>{
 const r=rigOf('kitten'),H=r.height_m;
 const hop=nodeRigPose(r,r.actions.hop.period_s*.5,{action:'hop'});assert.ok(Math.abs(hop.nodes[r.root].p[1]-r.actions.hop.height_frac*H)<1e-9,'hop peak is height_frac*H');
 const wave=nodeRigPose(r,r.actions.wave.period_s*.5,{action:'wave'});const arm=wave.nodes.arm_R.r.reduce((a,[ax,rad])=>a+ax[2]*rad,0);assert.ok(arm<-1.5,'arm_R raised (negative Z, up and out)');
 const walk=nodeRigPose(r,r.actions.walk.period_s*.25,{action:'walk'});assert.ok(walk.nodes[r.root].p[1]>0);assert.ok(walk.nodes.arm_L.r.length>0);
 const sl=nodeRigPose(r,1,{action:'sleep',sleepK:1});assert.ok(sl.eye>=1-1e-9);assert.ok(Math.abs(sl.nodes.eye_L.s[1]-r.eyes.closed_scale_y)<1e-9);assert.ok(sl.nodes.head.r.length>0);
 const sw=nodeRigPose(r,1,{action:'sleep',sleepK:0});assert.ok(sw.nodes[r.root].s[1]>.9);
 assert.deepEqual(ROLE_TO_ACTION,{idle:'idle',walk:'walk',happy:'wave',startle:'hop',sleep:'sleep'});
 assert.equal(ROLE_TO_ACTION[roleFor({sleep:1})],'sleep');assert.equal(ROLE_TO_ACTION[roleFor({speed:.5})],'walk');
});
test('blink closes at the SEEDED event times only',()=>{
 const b=rigOf('kitten').actions.blink;assert.equal(blinkClosure(b,0.5),0);
 const e=b.events[0];assert.equal(blinkClosure(b,e+b.close_s+b.hold_s/2),1);assert.equal(blinkClosure(b,e+b.close_s+b.hold_s+b.open_s+.01),0);
 assert.equal(blinkClosure(b,e+b.loop_s+b.close_s+.01),1);assert.equal(blinkClosure(null,1),0);
});
test('wisp species variants bend the family rig and carry their colours as data',()=>{
 const f=rigOf('wisp_starlight'),v=man.models.wisp_starlight.variants;assert.deepEqual(Object.keys(v).sort(),['MEMORY','PLASMA','STARLIGHT']);
 const fast=applyActionMultipliers(f,v.PLASMA.action_multipliers);assert.ok(fast.actions.idle.period_s<f.actions.idle.period_s);assert.equal(f.actions.idle.period_s,rigOf('wisp_starlight').actions.idle.period_s,'input not mutated');
 assert.deepEqual(Object.keys(man.models.wisp_nebula.variants).sort(),['NEBULA','VOID']);assert.deepEqual(Object.keys(man.models.wisp_aurora.variants).sort(),['AURORA','SIGNAL']);
 for(const s of Object.values(v))assert.ok(s.materials.wisp_glow.emissiveFactor);
});
test('the module is pure, the runtime budget-checks, and the world puts heavy first only on strong devices',()=>{
 const m=read('lib/creatures3d/node-rig.mjs');assert.doesNotMatch(m,/Math\.random|Date\.now|new Date|performance\.now|from 'three'/);
 const s=read('components/creature-model-slot.ts');assert.match(s,/withinBudget\(/);assert.match(s,/buf\.byteLength>budgetFor\(phone\)\.bytes/);assert.doesNotMatch(s,/withinBudget\(\{bytes:buf/);assert.match(s,/over the .* size budget/);assert.match(s,/tier==='heavy'/);assert.match(s,/nodeRigPose\(/);
 const w=read('components/living-world.tsx');assert.match(w,/heavyAllowed\(/);assert.match(w,/loadCreatureModel\(THREE,art\.id,\{low:phone,phone,/);
});
