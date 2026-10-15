import test from 'node:test';
import assert from 'node:assert/strict';
import {ZEREF_RIG_SCHEMA,ZEREF_COLORS,buildZerefRig,poseZerefRig,disposeZerefRig,inspectZerefRig} from '../lib/companion/zeref-rig.mjs';
import {createMind,frameFor,stepMind,forceBehavior} from '../lib/zeref/zeref-mind.mjs';

/** Minimal THREE stub: only the surface the rig builder touches. */
function stubThree(){
 class Vec{
  constructor(){this.x=0;this.y=0;this.z=0;}
  set(x,y,z){this.x=x;this.y=y;this.z=z;return this;}
 }
 class Obj{
  constructor(){this.children=[];this.position=new Vec();this.rotation={x:0,y:0,z:0};this.scale=new Vec();this.scale.set(1,1,1);this.visible=true;this.name='';}
  add(...kids){this.children.push(...kids);return this;}
  traverse(fn){fn(this);for(const k of this.children)k.traverse(fn);}
 }
 class Group extends Obj{}
 class Mesh extends Obj{
  constructor(geometry=null,material=null){super();this.geometry=geometry;this.material=material;this.isMesh=true;}
 }
 const geo=()=>class{constructor(){this.disposed=false;this.cloned=false;}clone(){const c=new (this.constructor)();c.cloned=true;return c;}dispose(){this.disposed=true;}};
 const mat=()=>class{constructor(p={}){Object.assign(this,p);this.disposed=false;}dispose(){this.disposed=true;}};
 return {
  Group,Mesh,
  SphereGeometry:geo(),ConeGeometry:geo(),BoxGeometry:geo(),OctahedronGeometry:geo(),TorusGeometry:geo(),
  MeshStandardMaterial:mat(),MeshBasicMaterial:mat(),
 };
}

const frame=over=>({floatX:0,floatY:0,rot:0,face:1,bodySX:1,bodySY:1,headRot:0,headY:0,earL:0,earR:0,wingL:0,wingR:0,tail:0,gazeX:0,gazeY:0,lid:0,pawL:0,pawR:0,glow:.35,ring:0,charge:0,...over});

test('rig builds genuine multi-part geometry with front/side/back volume',()=>{
 const rig=buildZerefRig(stubThree());
 assert.equal(rig.schema,ZEREF_RIG_SCHEMA);
 const report=inspectZerefRig(rig);
 assert.ok(report.meshCount>=15,`expected >=15 meshes, got ${report.meshCount}`);
 assert.equal(report.hasVolume,true);
 assert.equal(report.hasWings,true);
 assert.equal(report.hasEyes,true);
 assert.ok(report.meshes.includes('tailSeg2'));
 assert.equal(ZEREF_COLORS.body,0x14101f);
 assert.equal(ZEREF_COLORS.accent,0x8b5cf6);
});

test('posing changes transforms from mind frames; reduced frames stay near rest',()=>{
 const THREE=stubThree();
 const rig=buildZerefRig(THREE);
 const m=createMind({});
 forceBehavior(m,'pounce');
 for(let i=0;i<10;i++)stepMind(m,.1);
 const f=frameFor(m);
 poseZerefRig(rig,frame(f));
 assert.notEqual(rig.group.position.y,0);
 assert.ok(rig.parts.wingL.rotation.z>.5||rig.parts.wingR.rotation.z<-.5);
 const rest=buildZerefRig(THREE);
 const calm=createMind({reduced:true});
 poseZerefRig(rest,frame(frameFor(calm)));
 assert.ok(rest.group.position.x===0);
 assert.ok(rest.group.position.y===0);
});

test('charge and hover reveal the halo; lids narrow the star eyes',()=>{
 const rig=buildZerefRig(stubThree());
 assert.equal(rig.parts.halo.visible,false);
 poseZerefRig(rig,frame({charge:.8,glow:1}));
 assert.equal(rig.parts.halo.visible,true);
 assert.ok(rig.parts.halo.scale.x>1);
 poseZerefRig(rig,frame({lid:1}));
 assert.ok(rig.parts.eyeL.scale.y<1.25);
});

test('dispose releases every geometry and material without throwing',()=>{
 const THREE=stubThree();
 const rig=buildZerefRig(THREE);
 const geos=[];
 rig.group.traverse(n=>{if(n.geometry)geos.push(n.geometry);});
 assert.ok(geos.length>0);
 assert.doesNotThrow(()=>disposeZerefRig(rig));
 for(const g of geos)assert.equal(g.disposed,true);
 for(const mat of Object.values(rig.materials))assert.equal(mat.disposed,true);
});
