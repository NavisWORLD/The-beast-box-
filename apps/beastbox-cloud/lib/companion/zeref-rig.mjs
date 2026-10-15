/**
 * ZEREF TRUE-3D RIG — an artistic dimensional representation of the black
 * moon-cat/dragon companion, built from real geometry inside the existing
 * Three.js renderer. This is an artistic representation, not a newly
 * measured quantum phenotype.
 *
 * Design: buildZerefRig(THREE) constructs a THREE.Group from primitive
 * geometries (ellipsoid body, head, horned ears, thin wing planes, segmented
 * tail, crescent gem, star eyes) with genuine front/side/back volume.
 * poseZerefRig(rig, frame) applies a lib/zeref/zeref-mind.mjs frameFor()
 * pose using the same channel names as the SVG renderer, so the existing
 * mind drives both renderers without a second behavior system.
 *
 * The THREE module is injected so unit tests can run against a stub.
 */

export const ZEREF_RIG_SCHEMA='beastbox-zeref-rig-v1';
export const ZEREF_COLORS=Object.freeze({
 body:0x14101f,
 belly:0x241b3a,
 accent:0x8b5cf6,
 glow:0xb69cff,
 eye:0xf4efff,
 pupil:0x2a1650,
});

/** Frame channels are SVG pixels/degrees; this scales them into world units. */
export const RIG_WORLD_SCALE=0.02;
const deg=d=>Number.isFinite(d)?d*Math.PI/180:0;

function part(mesh,name){
 mesh.name=name;
 return mesh;
}

export function buildZerefRig(THREE){
 const bodyMat=new THREE.MeshStandardMaterial({color:ZEREF_COLORS.body,roughness:.55,metalness:.25,emissive:ZEREF_COLORS.accent,emissiveIntensity:.12});
 const bellyMat=new THREE.MeshStandardMaterial({color:ZEREF_COLORS.belly,roughness:.6,metalness:.15,emissive:ZEREF_COLORS.accent,emissiveIntensity:.08});
 const accentMat=new THREE.MeshStandardMaterial({color:ZEREF_COLORS.accent,roughness:.35,metalness:.4,emissive:ZEREF_COLORS.accent,emissiveIntensity:.5});
 const eyeMat=new THREE.MeshStandardMaterial({color:ZEREF_COLORS.eye,roughness:.15,metalness:.1,emissive:ZEREF_COLORS.glow,emissiveIntensity:.9});
 const pupilMat=new THREE.MeshStandardMaterial({color:ZEREF_COLORS.pupil,roughness:.3,metalness:.2,emissive:ZEREF_COLORS.accent,emissiveIntensity:.6});
 const group=new THREE.Group();
 group.name='zeref-root';

 const body=part(new THREE.Mesh(new THREE.SphereGeometry(.62,28,22),bodyMat),'body');
 body.scale.set(1,.92,.86);
 body.position.y=.1;
 const belly=part(new THREE.Mesh(new THREE.SphereGeometry(.5,24,18),bellyMat),'belly');
 belly.scale.set(.78,.8,.62);
 belly.position.set(0,.02,.3);

 const headG=new THREE.Group();headG.name='head';headG.position.set(0,.86,.18);
 const head=part(new THREE.Mesh(new THREE.SphereGeometry(.44,26,20),bodyMat),'skull');
 headG.add(head);
 const muzzle=part(new THREE.Mesh(new THREE.SphereGeometry(.2,18,14),bellyMat),'muzzle');
 muzzle.position.set(0,-.14,.34);muzzle.scale.set(1.1,.7,.8);
 headG.add(muzzle);
 const earGeo=new THREE.ConeGeometry(.13,.42,10);
 const earL=part(new THREE.Mesh(earGeo,bodyMat),'earL');
 earL.position.set(-.3,.42,-.02);earL.rotation.z=.38;
 const earR=part(new THREE.Mesh(earGeo.clone(),bodyMat),'earR');
 earR.position.set(.3,.42,-.02);earR.rotation.z=-.38;
 const earTipGeo=new THREE.ConeGeometry(.06,.16,8);
 const earTipL=part(new THREE.Mesh(earTipGeo,accentMat),'earTipL');
 earTipL.position.y=.26;earL.add(earTipL);
 const earTipR=part(new THREE.Mesh(earTipGeo,accentMat),'earTipR');
 earTipR.position.y=.26;earR.add(earTipR);
 headG.add(earL,earR);
 const eyeGeo=new THREE.SphereGeometry(.115,16,12);
 const eyeL=part(new THREE.Mesh(eyeGeo,eyeMat),'eyeL');
 eyeL.position.set(-.17,.05,.36);eyeL.scale.set(1,1.25,.55);
 const eyeR=part(new THREE.Mesh(eyeGeo,eyeMat),'eyeR');
 eyeR.position.set(.17,.05,.36);eyeR.scale.set(1,1.25,.55);
 const pupilGeo=new THREE.SphereGeometry(.05,12,10);
 const pupilL=part(new THREE.Mesh(pupilGeo,pupilMat),'pupilL');
 pupilL.position.set(0,.01,.09);eyeL.add(pupilL);
 const pupilR=part(new THREE.Mesh(pupilGeo,pupilMat),'pupilR');
 pupilR.position.set(0,.01,.09);eyeR.add(pupilR);
 headG.add(eyeL,eyeR);

 const wingGeo=new THREE.BoxGeometry(.08,.7,.44);
 const wingL=part(new THREE.Mesh(wingGeo,bellyMat),'wingL');
 wingL.position.set(-.62,.42,-.18);wingL.rotation.z=.5;
 const wingR=part(new THREE.Mesh(wingGeo,bellyMat),'wingR');
 wingR.position.set(.62,.42,-.18);wingR.rotation.z=-.5;

 const tailRoot=new THREE.Group();tailRoot.name='tail';tailRoot.position.set(0,.12,-.5);
 const tailSegs=[];
 let parent=tailRoot;
 for(let i=0;i<3;i++){
  const seg=part(new THREE.Mesh(new THREE.SphereGeometry(.16-i*.035,14,12),i===2?accentMat:bodyMat),`tailSeg${i}`);
  seg.position.set(0,.1+i*.05,-.22);
  seg.scale.set(1,1,1.6);
  parent.add(seg);parent=seg;tailSegs.push(seg);
 }

 const gem=part(new THREE.Mesh(new THREE.OctahedronGeometry(.11,0),accentMat),'gem');
 gem.position.set(0,.62,.5);
 const halo=part(new THREE.Mesh(new THREE.TorusGeometry(.5,.028,10,40),accentMat),'halo');
 halo.position.set(0,.1,-.1);halo.rotation.x=Math.PI/2.4;
 halo.visible=false;

 const pawGeo=new THREE.SphereGeometry(.15,12,10);
 const pawL=part(new THREE.Mesh(pawGeo,bellyMat),'pawL');
 pawL.position.set(-.3,-.5,.28);
 const pawR=part(new THREE.Mesh(pawGeo,bellyMat),'pawR');
 pawR.position.set(.3,-.5,.28);

 group.add(body,belly,headG,wingL,wingR,tailRoot,gem,halo,pawL,pawR);
 const parts={body,belly,headG,earL,earR,eyeL,eyeR,wingL,wingR,tailRoot,tailSegs,gem,halo,pawL,pawR};
 const base={bodySY:body.scale.y,bodySX:body.scale.x};
 return {schema:ZEREF_RIG_SCHEMA,group,parts,base,materials:{bodyMat,bellyMat,accentMat,eyeMat,pupilMat}};
}

/**
 * Pose the rig from a zeref-mind frameFor() frame. Channel names match the
 * SVG renderer (floatX/floatY/rot/headRot/earL/wingL/tail/glow/ring/charge,
 * gaze, lids) so one mind drives both renderers.
 */
export function poseZerefRig(rig,frame={}){
 const {group,parts,base,materials}=rig;
 const num=(v,d=0)=>Number.isFinite(Number(v))?Number(v):d;
 group.position.x=num(frame.floatX)*RIG_WORLD_SCALE;
 group.position.y=num(frame.floatY)*-RIG_WORLD_SCALE;
 group.rotation.z=deg(num(frame.rot));
 group.rotation.y=deg(num(frame.face)===0?0:(num(frame.face)<0?-18:0));
 parts.body.scale.y=base.bodySY*num(frame.bodySY,1);
 parts.body.scale.x=base.bodySX*num(frame.bodySX,1);
 parts.headG.rotation.z=deg(num(frame.headRot));
 parts.headG.position.y=.86+num(frame.headY)*-RIG_WORLD_SCALE;
 parts.earL.rotation.x=deg(num(frame.earL));
 parts.earR.rotation.x=deg(num(frame.earR));
 parts.wingL.rotation.z=.5+deg(num(frame.wingL));
 parts.wingR.rotation.z=-.5-deg(num(frame.wingR));
 parts.tailRoot.rotation.y=deg(num(frame.tail));
 parts.tailSegs.forEach((seg,i)=>{seg.rotation.y=deg(num(frame.tail))*(.6+i*.25);});
 parts.eyeL.position.x=-.17+num(frame.gazeX)*.05;
 parts.eyeR.position.x=.17+num(frame.gazeX)*.05;
 parts.eyeL.position.y=.05+num(frame.gazeY)*-.04;
 parts.eyeR.position.y=.05+num(frame.gazeY)*-.04;
 const lid=num(frame.lid,0);
 parts.eyeL.scale.y=1.25*(1-Math.min(.85,Math.max(0,lid)));
 parts.eyeR.scale.y=1.25*(1-Math.min(.85,Math.max(0,lid)));
 parts.pawL.position.y=-.5+num(frame.pawL)*.3;
 parts.pawR.position.y=-.5+num(frame.pawR)*.3;
 parts.halo.visible=num(frame.ring)>0.02||num(frame.charge)>0.02;
 const haloScale=1+Math.max(num(frame.ring),num(frame.charge))*.8;
 parts.halo.scale.set(haloScale,haloScale,haloScale);
 materials.accentMat.emissiveIntensity=.5+num(frame.glow)*.9+num(frame.charge)*1.4;
 parts.gem.rotation.y+=.02+num(frame.glow)*.05;
 return rig;
}

export function disposeZerefRig(rig){
 rig.group.traverse(node=>{
  if(node.geometry&&typeof node.geometry.dispose==='function')node.geometry.dispose();
 });
 for(const mat of Object.values(rig.materials))if(mat&&typeof mat.dispose==='function')mat.dispose();
}

/** Structural assertions shared by tests and future geometry inspection. */
export function inspectZerefRig(rig){
 const meshes=[];
 rig.group.traverse(node=>{if(node.isMesh||node.geometry)meshes.push(node.name||'(unnamed)');});
 return {
  schema:rig.schema,
  meshCount:meshes.length,
  meshes,
  hasVolume:meshes.includes('body')&&meshes.includes('skull')&&meshes.some(n=>n.startsWith('tailSeg')),
  hasWings:meshes.includes('wingL')&&meshes.includes('wingR'),
  hasEyes:meshes.includes('eyeL')&&meshes.includes('eyeR'),
 };
}
