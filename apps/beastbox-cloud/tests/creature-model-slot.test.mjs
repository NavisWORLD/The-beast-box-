import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import {validateRig,resolveModelEntry,pickClipName,fitScale,roleFor,MODEL_SLOT_SCHEMA,CLIP_ROLES} from '../lib/creatures3d/creature-model-slot.mjs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const good={schema:MODEL_SLOT_SCHEMA,id:'art-x',height_m:.9,forward:'+Z',clips:{idle:'Idle',walk:'Walk'},sprite_fallback:'/a.webp',honesty:'Artist-made 3D model. Not a measured quantum phenotype.'};
test('a good rig validates and a bad one says why',()=>{
 assert.equal(validateRig(good,'art-x').ok,true);
 const bad=validateRig({...good,id:'other',height_m:0,forward:'up',clips:{dance:'x'},honesty:''},'art-x');
 assert.equal(bad.ok,false);for(const w of [/does not match/,/height_m/,/forward/,/unknown clip role/,/honesty/])assert.ok(bad.errors.some(e=>w.test(e)),String(w));
 assert.equal(validateRig(null,'x').ok,false);
});
test('the manifest lists only models whose files really exist and match',()=>{
 const m=JSON.parse(read('public/creatures3d/custom/manifest.json'));assert.equal(m.schema,MODEL_SLOT_SCHEMA);
 for(const [id,e] of Object.entries(m.models)){const buf=readFileSync(new URL('../public/creatures3d/custom/'+e.glb,import.meta.url));
  assert.equal(buf.byteLength,e.bytes,id);assert.equal(createHash('sha256').update(buf).digest('hex'),e.sha256,id);
  assert.equal(buf.subarray(0,4).toString(),'glTF',id);
  const rig=JSON.parse(read('public/creatures3d/custom/'+e.rig));assert.deepEqual(validateRig(rig,id),{ok:true,errors:[]},id);}
 assert.equal(resolveModelEntry(m,'art-x'),null);
});
test('manifest entries resolve to file names only, no path tricks',()=>{
 const m={models:{'art-x':{glb:'art-x.glb',rig:'art-x.rig.json',glb_low:'art-x_low.glb'},evil:{glb:'../../etc/x.glb'}}};
 const e=resolveModelEntry(m,'art-x');assert.equal(e.glb,'/creatures3d/custom/art-x.glb');assert.equal(e.glbLow,'/creatures3d/custom/art-x_low.glb');
 assert.equal(resolveModelEntry(m,'evil').glb,'/creatures3d/custom/evil.glb');
});
test('clip names map to roles by the rig first, then by name',()=>{
 assert.equal(pickClipName(['Idle','Walk'],'walk',{walk:'Walk'}),'Walk');
 assert.equal(pickClipName(['breathing','trot'],'idle'),'breathing');assert.equal(pickClipName(['trot'],'walk'),'trot');
 assert.equal(pickClipName(['x'],'sleep'),null);assert.deepEqual([...CLIP_ROLES],['idle','walk','sleep','happy','startle']);
});
test('fitScale and roleFor are deterministic and safe',()=>{
 assert.equal(fitScale(2,1),.5);assert.equal(fitScale(0,1),1);assert.equal(fitScale(NaN,1),1);
 assert.equal(roleFor({}),'idle');assert.equal(roleFor({speed:.5}),'walk');assert.equal(roleFor({sleep:.9,speed:1}),'sleep');assert.equal(roleFor({startle:.9}),'startle');assert.equal(roleFor({joy:.9}),'happy');
});
test('the module is pure: no clock, no random, no three import',()=>{
 const s=read('lib/creatures3d/creature-model-slot.mjs');assert.doesNotMatch(s,/Math\.random|Date\.now|new Date|performance\.now|from 'three'/);
});
test('the runtime keeps the sprite unless every step succeeds',()=>{
 const s=read('components/creature-model-slot.ts');assert.match(s,/validateRig\(rig0,id\)/);assert.match(s,/return null/);assert.match(s,/catch\(e\)/);
});
