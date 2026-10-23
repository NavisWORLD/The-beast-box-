// The Cage surface on any ground: Cosmo's ground cover + trees as InstancedMesh, wind-swayed, with the per-instance
// hash dissolve LOD from the README (clumps shrink to nothing before they fade, so nothing pops). Seeded streams only.
import {GROUND_ASSETS,TREE_KINDS,GRASS,LOD,plantGround,plantTrees} from './groundcover.mjs';
import {GC_MODELS,TREE_MODELS} from './surface-data.mjs';
type T=typeof import('three');type V3=import('three').Vector3;
export const SURFACE_ART='/universe/livingworld/';
export type SurfaceOpts={seed:string;R:number;mpu:number;biomeAt:(d:number[])=>string;lift:(d:V3)=>number;tint:(biome:string)=>[number,number,number]|null;budget:number;size?:number};
type Slot={u:Record<string,{value:any}>};
function patch(THREE:T,mat:any,cfg:{h:number;near:number;far:number;inner:number;thin:number;wind:number},shared:any){
 const m=mat.clone();const U={uMPU:shared.uMPU,uTime:shared.uTime,uH:{value:cfg.h},uNear:{value:cfg.near},uFar:{value:cfg.far},uIn:{value:cfg.inner},uThin:{value:cfg.thin},uWind:{value:cfg.wind}};
 m.onBeforeCompile=(s:any)=>{Object.assign(s.uniforms,U);
  s.vertexShader='uniform float uMPU,uTime,uH,uNear,uFar,uIn,uThin,uWind;attribute float aHash;\n'+s.vertexShader.replace('#include <begin_vertex>',`#include <begin_vertex>
   vec3 wp0=(modelMatrix*instanceMatrix*vec4(0.,0.,0.,1.)).xyz;float dM=distance(cameraPosition,wp0)/uMPU;
   float fs;if(uThin>.5){fs=aHash<.3?mix(1.,1.5,smoothstep(uNear*.8,uNear,dM))*clamp((mix(uNear,uFar,aHash/.3)-dM)/(uFar*.2),0.,1.):clamp((uNear-dM)/(uNear*.2),0.,1.);}
   else{float lim=mix(uNear,uFar,aHash);fs=clamp((lim-dM)/(lim*.2),0.,1.);}
   if(uIn>0.)fs*=clamp((dM-uIn*.8)/(uIn*.2),0.,1.);
   float hh=clamp(position.y/uH,0.,1.);float w=hh*hh*uWind*(sin(uTime*1.3+wp0.x*.21/uMPU+wp0.z*.17/uMPU)*.08+sin(uTime*3.1+wp0.x/uMPU)*.02);
   transformed.x+=w*uH*.15;transformed.z+=w*uH*.1;transformed*=fs;`);};
 m.customProgramCacheKey=()=>'surf'+cfg.thin+(cfg.inner>0?'i':'');return m;}
async function loadParts(url:string){const {GLTFLoader}=await import('three/examples/jsm/loaders/GLTFLoader.js');const g:any=await new GLTFLoader().loadAsync(url);g.scene.updateMatrixWorld(true);
 const parts:any[]=[];g.scene.traverse((o:any)=>{if(o.isMesh){const geo=o.geometry.clone();geo.applyMatrix4(o.matrixWorld);parts.push({geo,mat:o.material});}});return parts;}
export function addCageSurface(THREE:T,parent:import('three').Object3D,o:SurfaceOpts){
 const group=new THREE.Group();group.name='cage-surface';parent.add(group);
 const shared={uMPU:{value:o.mpu},uTime:{value:0}};const counts:Record<string,number>={};const meshes:any[]=[];
 const up=new THREE.Vector3(0,1,0),q=new THREE.Quaternion(),qy=new THREE.Quaternion(),m4=new THREE.Matrix4(),v=new THREE.Vector3(),sc=new THREE.Vector3(),col=new THREE.Color();
 const K=o.size??1;
 const build=(parts:any[],list:any[],cfg:any,brighten=false)=>{if(!list.length)return;for(const p of parts){const geo=p.geo.clone();const hs=new Float32Array(list.length);list.forEach((it:any,i:number)=>hs[i]=it.h);geo.setAttribute('aHash',new THREE.InstancedBufferAttribute(hs,1));
   let mat=p.mat;if(brighten&&/leaf/i.test(mat.name||'')){mat=mat.clone();mat.emissive=mat.color.clone().multiplyScalar(.45);mat.emissiveIntensity=1;mat.color.multiplyScalar(1.25);}
   const im=new THREE.InstancedMesh(geo,patch(THREE,mat,cfg,shared),list.length);im.frustumCulled=false;im.castShadow=false;im.receiveShadow=false;
   list.forEach((it:any,i:number)=>{v.set(it.dir[0],it.dir[1],it.dir[2]);q.setFromUnitVectors(up,v);qy.setFromAxisAngle(up,it.yaw);q.multiply(qy);const s=o.mpu*K*it.scale;
    m4.compose(v.clone().multiplyScalar(o.R+o.lift(v)),q,sc.set(s,s,s));im.setMatrixAt(i,m4);const t=o.tint(it.biome);col.setRGB(1,1,1);if(t)col.setRGB(.6+.4*t[0],.6+.4*t[1],.6+.4*t[2]);im.setColorAt(i,col);});
   im.instanceMatrix.needsUpdate=true;if(im.instanceColor)im.instanceColor.needsUpdate=true;group.add(im);meshes.push(im);}};
 const Rm=o.R/o.mpu;
 const ready=(async()=>{
  const ground=plantGround({seed:o.seed,R:Rm,focus:[0,1,0],biomeAt:o.biomeAt,budget:o.budget,cellM:1,whole:true} as any) as Record<string,any[]>;
  await Promise.all(GROUND_ASSETS.map(async(a:string)=>{counts[a]=ground[a].length;if(!ground[a].length)return;const parts=await loadParts(SURFACE_ART+'groundcover/models/'+a+'.glb');const h=(GC_MODELS as any)[a]?.h||.3;
   build(parts,ground[a],GRASS.has(a)?{h,near:LOD.grassFull,far:LOD.grassThin,inner:0,thin:1,wind:1}:{h,near:LOD.grassThin,far:LOD.props,inner:0,thin:0,wind:a.startsWith('flower')?1:0});}));
  const trees=plantTrees({seed:o.seed,R:Rm,biomeAt:o.biomeAt,budget:Math.max(.5,o.budget)}) as Record<string,any[]>;
  await Promise.all(TREE_KINDS.map(async(k:string)=>{counts['tree:'+k]=trees[k].length;if(!trees[k].length)return;const giant=k==='giant_heartwood';const far=giant?LOD.giantFar:LOD.treeFar;
   const [nearP,farP]=await Promise.all([loadParts(SURFACE_ART+'trees/models/'+k+'_near.glb'),loadParts(SURFACE_ART+'trees/models/'+k+'_far.glb')]);const h=(TREE_MODELS as any)[k+'_near']?.h||3;const w=giant?.3:1;
   build(nearP,trees[k],{h,near:LOD.treeNear,far:LOD.treeNear,inner:0,thin:0,wind:w},k==='teal_round');build(farP,trees[k],{h,near:far,far:far,inner:LOD.treeNear,thin:0,wind:w},k==='teal_round');}));
  return counts;})();
 return {group,counts,ready,meshes,update(t:number){shared.uTime.value=t;},dispose(){parent.remove(group);for(const m of meshes){m.geometry.dispose();m.material.dispose();}}};
}
