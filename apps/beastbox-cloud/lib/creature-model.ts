/**
 * One source for the live 3D character and downloadable GLB.
 * Render-only, deterministic cosmetic genome. No COSMOS data, authority or
 * model weights are ever used in geometry generation.
 */
import * as THREE from 'three';
import {type CreatureProfile, validCreature} from './creature-profile';

export type CompanionLook='nebula'|'aurora'|'starlight';
export type RigQuality='auto'|'low';
export type CreatureRig={
 group:THREE.Group; body:THREE.Mesh; bodyMaterial:THREE.MeshPhysicalMaterial;
 fins:THREE.Group[]; halo:THREE.Group; motes:THREE.Points;
 dispose:()=>void;
};
const COLORS:Record<CompanionLook,{base:number;lobe:number;petal:number;accent:number}>={
 nebula:{base:0xb395fa,lobe:0x8d68e9,petal:0x8ad6fa,accent:0xe9b8ff},
 aurora:{base:0x83dfdf,lobe:0x70b3e9,petal:0x8ff6e1,accent:0x9bf4f6},
 starlight:{base:0xf3dcff,lobe:0xdbb8ff,petal:0xffe0f4,accent:0xffd4f4}
};
export function creatureAppearance(profile:CreatureProfile|null|undefined,look:CompanionLook){
 // Never silently render an invalid profile's contents.
 if(!profile||!validCreature(profile)){
  return {look,hue:0,glow:.6,finCount:11,finLength:1,haloStyle:0,
   constellation:1729};
 }
 return {
  look:profile.baseLook,
  hue:profile.appearance.hueShift,
  glow:Math.max(.4,Math.min(1,profile.appearance.glow/100)),
  finCount:10+profile.appearance.finPattern,
  finLength:.87+profile.appearance.finPattern*.085,
  haloStyle:profile.appearance.haloPattern,
  constellation:profile.appearance.constellation
 };
}
function starGeometry(radius:number,inner:number){
 const shape=new THREE.Shape();
 for(let i=0;i<8;i++){
  const distance=i%2===0?radius:inner,angle=Math.PI/2-i*Math.PI/4;
  const x=Math.cos(angle)*distance,y=Math.sin(angle)*distance;
  if(i===0)shape.moveTo(x,y);else shape.lineTo(x,y);
 }
 shape.closePath();
 return new THREE.ExtrudeGeometry(shape,{
  depth:.048,bevelEnabled:true,bevelThickness:.02,bevelSize:.012,bevelSegments:2
 });
}
function galaxyTexture(config:ReturnType<typeof creatureAppearance>){
 // Generated locally, reproducibly, with no remote requests or private input.
 const canvas=document.createElement('canvas');canvas.width=512;canvas.height=256;
 const context=canvas.getContext('2d');
 if(!context)throw new Error('Canvas texture is not supported');
 const gradient=context.createRadialGradient(220,65,10,256,128,300);
 const palette=config.look==='aurora'?['#e5fff8','#78acc8']:
  config.look==='starlight'?['#fff5ff','#bd9cda']:['#ecd9ff','#9768df'];
 gradient.addColorStop(0,palette[0]);gradient.addColorStop(.42,palette[1]);
 gradient.addColorStop(.8,'#55488d');gradient.addColorStop(1,'#1b204a');
 context.fillStyle=gradient;context.fillRect(0,0,512,256);
 let state=(config.constellation^0xa7c61e35)>>>0;
 const random=()=>{state^=state<<13;state^=state>>>17;state^=state<<5;return(state>>>0)/4294967296;};
 for(let i=0;i<415;i++){
  const x=random()*512,y=random()*256,r=.24+random()*.85;
  context.fillStyle=i%11===0?'#ffd8f6':i%6===0?'#9bf4ff':'#f8f8ff';
  context.globalAlpha=.28+random()*.7;
  context.beginPath();context.arc(x,y,r,0,Math.PI*2);context.fill();
 }
 context.globalAlpha=1;
 const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;
 return texture;
}
export function createCreatureRig(
 profile:CreatureProfile|null|undefined,look:CompanionLook='nebula',quality:RigQuality='auto'
):CreatureRig{
 const g=creatureAppearance(profile,look);
 const tint=(color:number)=>{
  const value=new THREE.Color(color);
  value.offsetHSL(g.hue/360,0,0);
  return value;
 };
 const root=new THREE.Group();root.name='CosmicAvatar';
 const bodyMap=galaxyTexture(g);
 const bodyMaterial=new THREE.MeshPhysicalMaterial({
  map:bodyMap,color:tint(COLORS[g.look].base),metalness:.12,roughness:.26,
  clearcoat:.96,clearcoatRoughness:.14,emissive:tint(COLORS[g.look].base),
  emissiveIntensity:.12+g.glow*.17
 });
 const lobeMaterial=new THREE.MeshPhysicalMaterial({
  color:tint(COLORS[g.look].lobe),roughness:.24,metalness:.12,
  clearcoat:1,transparent:true,opacity:.90,emissive:tint(COLORS[g.look].lobe),
  emissiveIntensity:.12+g.glow*.12
 });
 const petalMaterial=new THREE.MeshPhysicalMaterial({
  color:tint(COLORS[g.look].petal),roughness:.21,metalness:.14,
  transparent:true,opacity:.88,clearcoat:1,side:THREE.DoubleSide,
  emissive:tint(COLORS[g.look].petal),emissiveIntensity:.13+g.glow*.18
 });
 const eyeMaterial=new THREE.MeshPhysicalMaterial({color:0x0a0f33,metalness:.16,roughness:.08,clearcoat:1});
 const highlight=new THREE.MeshBasicMaterial({color:0xffffff});
 const gold=new THREE.MeshPhysicalMaterial({color:0xffd88c,metalness:.48,roughness:.14,emissive:0xf7b75e,emissiveIntensity:.22});
 const smile=new THREE.MeshStandardMaterial({color:0x502158,roughness:.7});
 const blush=new THREE.MeshBasicMaterial({color:0xffa9d8,transparent:true,opacity:.45});
 const sphere=new THREE.SphereGeometry(1,quality==='low'?18:28,quality==='low'?14:22);
 const body=new THREE.Mesh(sphere,bodyMaterial);body.name='GalaxyBody';body.scale.set(1.06,.98,.76);root.add(body);
 const shape=new THREE.Shape();shape.moveTo(0,-.22);
 shape.bezierCurveTo(-.23,-.05,-.28,.25,0,.54);
 shape.bezierCurveTo(.28,.25,.23,-.05,0,-.22);
 const finGeometry=new THREE.ExtrudeGeometry(shape,{
  depth:.06,bevelEnabled:true,bevelSegments:2,steps:1,
  bevelSize:.035,bevelThickness:.035,curveSegments:8
 });
 const fins:THREE.Group[]=[];
 for(let i=0;i<g.finCount;i++){
  const angle=i*Math.PI*2/g.finCount;
  const lobe=new THREE.Mesh(sphere,lobeMaterial);
  lobe.position.set(Math.sin(angle)*.78,Math.cos(angle)*.72,.08);
  lobe.scale.set(.36,.42,.31);root.add(lobe);
  const pivot=new THREE.Group();pivot.name='Fin_'+i;
  pivot.position.set(Math.sin(angle)*.89,Math.cos(angle)*.8,-.11);
  pivot.rotation.z=-angle;
  const petal=new THREE.Mesh(finGeometry,petalMaterial);
  petal.scale.set(1.06,g.finLength*(i%3===0?1.15:.94),1);
  pivot.add(petal);root.add(pivot);fins.push(pivot);
 }
 const glintGeometry=starGeometry(.088,.028);
 for(const direction of [-1,1]){
  const x=direction*.35;
  const eye=new THREE.Mesh(sphere,eyeMaterial);
  eye.position.set(x,.105,.67);eye.scale.set(.19,.25,.115);root.add(eye);
  const star=new THREE.Mesh(glintGeometry,gold);
  star.position.set(x+.025,.15,.777);root.add(star);
  const glimmer=new THREE.Mesh(sphere,highlight);
  glimmer.position.set(x-.061,.205,.787);glimmer.scale.set(.029,.045,.012);root.add(glimmer);
  const cheek=new THREE.Mesh(sphere,blush);
  cheek.position.set(x*1.53,-.26,.67);cheek.scale.set(.16,.09,.017);root.add(cheek);
 }
 const smileCurve=new THREE.QuadraticBezierCurve3(
  new THREE.Vector3(-.13,-.27,.72),new THREE.Vector3(0,-.43,.82),
  new THREE.Vector3(.13,-.27,.72)
 );
 root.add(new THREE.Mesh(new THREE.TubeGeometry(smileCurve,12,.021,6,false),smile));
 const halo=new THREE.Group();halo.name='OrbitingHalo';
 halo.position.set(0,1.42,-.04);root.add(halo);
 const crown=new THREE.Mesh(starGeometry(.24,.067),gold);
 crown.position.set(0,.12,.13);halo.add(crown);
 const haloGeometry=new THREE.TorusGeometry(g.haloStyle===1?.39:.32,.013,7,48);
 for(let ring=0;ring<(g.haloStyle===2?2:1);ring++){
  const orbit=new THREE.Mesh(haloGeometry,gold);
  orbit.position.set(0,.1,0);orbit.rotation.set(.85+ring*.55,.23,-.17+ring*.36);
  orbit.scale.set(1,.5+ring*.16,1);halo.add(orbit);
 }
 const positions:number[]=[];let pointSeed=(g.constellation^0x1cd90b77)>>>0;
 const random=()=>{pointSeed^=pointSeed<<13;pointSeed^=pointSeed>>>17;pointSeed^=pointSeed<<5;return(pointSeed>>>0)/4294967296;};
 for(let i=0;i<(quality==='low'?28:78);i++){
  const a=random()*Math.PI*2,r=1.48+random()*.79;
  positions.push(Math.cos(a)*r,(random()-.5)*2.9,Math.sin(a)*.45-.5);
 }
 const pointsGeometry=new THREE.BufferGeometry();
 pointsGeometry.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));
 const pointsMaterial=new THREE.PointsMaterial({
  color:tint(COLORS[g.look].accent),size:.027,transparent:true,
  opacity:.72,sizeAttenuation:true
 });
 const motes=new THREE.Points(pointsGeometry,pointsMaterial);motes.name='ConstellationMotes';root.add(motes);
 let disposed=false;
 function dispose(){
  if(disposed)return;disposed=true;
  const geometries=new Set<THREE.BufferGeometry>(),materials=new Set<THREE.Material>();
  root.traverse(object=>{
   if(object instanceof THREE.Mesh || object instanceof THREE.Points){
    geometries.add(object.geometry);
    const m=object.material;
    (Array.isArray(m)?m:[m]).forEach(value=>materials.add(value));
   }
  });
  geometries.forEach(value=>value.dispose());
  materials.forEach(value=>value.dispose());bodyMap.dispose();
 }
 return {group:root,body,bodyMaterial,fins,halo,motes,dispose};
}
function poseClip(name:string,duration:number,height:number,rotation:number,haloSpin:number){
 const tracks:THREE.KeyframeTrack[]=[
  new THREE.VectorKeyframeTrack('CosmicAvatar.position',[0,duration/2,duration],
   [0,0,0, 0,height,0, 0,0,0]),
  new THREE.QuaternionKeyframeTrack('CosmicAvatar.quaternion',[0,duration/2,duration],(()=>{
   const q=(angle:number)=>new THREE.Quaternion().setFromEuler(new THREE.Euler(0,angle,0)).toArray();
   return [...q(0),...q(rotation),...q(0)];
  })()),
  new THREE.QuaternionKeyframeTrack('OrbitingHalo.quaternion',[0,duration/2,duration],(()=>{
   const q=(angle:number)=>new THREE.Quaternion().setFromEuler(new THREE.Euler(0,angle,0)).toArray();
   return [...q(0),...q(haloSpin),...q(0)];
  })())
 ];
 return new THREE.AnimationClip(name,duration,tracks);
}
export function creatureAnimationClips():THREE.AnimationClip[]{
 return [
  poseClip('idle',2.8,.10,.07,.24),
  poseClip('listening',1.3,.09,-.18,.18),
  poseClip('thinking',1.5,.12,.25,.36),
  poseClip('celebrating',.85,.24,.38,.85)
 ];
}
