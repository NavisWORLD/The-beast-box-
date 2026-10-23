// The Cage surface on any ground: Cosmo's ground cover + trees as InstancedMesh, wind-swayed, with the per-instance
// hash dissolve LOD from the README (clumps shrink to nothing before they fade, so nothing pops). Seeded streams only.
import {GROUND_ASSETS,TREE_KINDS,GRASS,LOD,plantGround,plantTrees} from './groundcover.mjs';
import {GC_MODELS,TREE_MODELS} from './surface-data.mjs';
// Alive props (Cosmo's aliveprops v1): same art, plus breathing rock cracks, humming crystals (brighter within 3 m of a
// creature), swaying mushrooms and flower heads turning to the sun (aFacing/uSunDir in object space). Per-instance aPhase/aLife
// come from lwStream (recorded-IBM seed), never an unseeded RNG. Each flower type's heads are merged into ONE InstancedMesh.
import {ALIVE_PROPS,aliveInstances,crossedPeak,nearness,sunFacing,easeFacing,angleBetween,CRYSTAL_RADIUS_M} from './alive-props.mjs';
const MAXC=16;
const ROT_UP=`mat3 rotUp(vec3 f){vec3 u=vec3(0.,1.,0.);float c=dot(u,f);if(c>.9999)return mat3(1.);vec3 ax=normalize(cross(u,f));float s=sqrt(max(0.,1.-c*c));float t=1.-c;
 return mat3(t*ax.x*ax.x+c,t*ax.x*ax.y+s*ax.z,t*ax.x*ax.z-s*ax.y, t*ax.x*ax.y-s*ax.z,t*ax.y*ax.y+c,t*ax.y*ax.z+s*ax.x, t*ax.x*ax.z+s*ax.y,t*ax.y*ax.z-s*ax.x,t*ax.z*ax.z+c);}`;
type Alive={kind:'rock'|'crystal'|'mushroom'|'head';part:'body'|'live';period:number};
type T=typeof import('three');type V3=import('three').Vector3;
export const SURFACE_ART='/universe/livingworld/';
export const ALIVE_ART=SURFACE_ART+'aliveprops/models/';
export type SurfaceOpts={seed:string;R:number;mpu:number;biomeAt:(d:number[])=>string;lift:(d:V3)=>number;tint:(biome:string)=>[number,number,number]|null;budget:number;size?:number};
type Slot={u:Record<string,{value:any}>};
function patch(THREE:T,mat:any,cfg:{h:number;near:number;far:number;inner:number;thin:number;wind:number;alive?:Alive},shared:any){
 const m=mat.clone();const al=cfg.alive;const U:any={uPeriod:{value:al?.period||1},uCreaturePos:shared.uCreaturePos,uCreatureCount:shared.uCreatureCount,uRadius:shared.uRadius,uMPU:shared.uMPU,uTime:shared.uTime,uH:{value:cfg.h},uNear:{value:cfg.near},uFar:{value:cfg.far},uIn:{value:cfg.inner},uThin:{value:cfg.thin},uWind:{value:cfg.wind}};
 const live=!!al&&al.part==='live',head=live&&al!.kind==='head',k=al?.kind;
 const aliveHead=!al?'':`uniform float uPeriod;uniform vec3 uCreaturePos[${MAXC}];uniform int uCreatureCount;uniform float uRadius;attribute float aPhase;attribute float aLife;varying float vGlow;\n`+(head?'attribute vec3 aFacing;attribute vec3 aPivot;\n'+ROT_UP+'\n':'');
 const aliveVS=!al?'':`
   float brA=.5-.5*cos(6.28318*(uTime/uPeriod+aPhase));float lifeA=.25+.75*aLife;vGlow=1.;`+(!live?'':
   k==='rock'?`transformed*=1.+.03*brA*lifeA;vGlow=mix(.35,1.,brA)*lifeA;`:
   k==='crystal'?`transformed.xz*=1.+.02*brA*lifeA;transformed.y*=1.+.045*brA*lifeA;
    vec3 wpC=(modelMatrix*instanceMatrix*vec4(0.,0.,0.,1.)).xyz;float nearC=0.;for(int i=0;i<${MAXC};i++){if(i>=uCreatureCount)break;nearC=max(nearC,1.-smoothstep(0.,uRadius,distance(wpC,uCreaturePos[i])));}
    vGlow=(.6+.4*brA)*(1.+1.5*nearC*nearC)*lifeA;`:
   k==='mushroom'?`{float ph=6.28318*(uTime/uPeriod+aPhase);float am=mix(.3,1.,aLife);float az=radians(3.5)*sin(ph)*am,ax=radians(2.)*sin(ph+1.3)*am;
    float cz=cos(az),sz=sin(az),cx=cos(ax),sx=sin(ax);vec3 q=transformed;q=vec3(q.x*cz-q.y*sz,q.x*sz+q.y*cz,q.z);q=vec3(q.x,q.y*cx-q.z*sx,q.y*sx+q.z*cx);transformed=q;}vGlow=mix(.6,1.,brA)*lifeA;`:
   `{float ph=6.28318*(uTime/uPeriod+aPhase);float am=mix(.3,1.,aLife);vec3 f=normalize(aFacing+vec3(sin(ph)*.05*am,0.,cos(ph*1.1)*.04*am));transformed=rotUp(f)*(transformed-aPivot)+aPivot;}vGlow=mix(.7,1.,brA)*lifeA;`);
 m.onBeforeCompile=(s:any)=>{Object.assign(s.uniforms,U);
  s.vertexShader='uniform float uMPU,uTime,uH,uNear,uFar,uIn,uThin,uWind;attribute float aHash;\n'+aliveHead+s.vertexShader.replace('#include <begin_vertex>',`#include <begin_vertex>`+aliveVS+`
   vec3 wp0=(modelMatrix*instanceMatrix*vec4(0.,0.,0.,1.)).xyz;float dM=distance(cameraPosition,wp0)/uMPU;
   float fs;if(uThin>.5){fs=aHash<.3?mix(1.,1.5,smoothstep(uNear*.8,uNear,dM))*clamp((mix(uNear,uFar,aHash/.3)-dM)/(uFar*.2),0.,1.):clamp((uNear-dM)/(uNear*.2),0.,1.);}
   else{float lim=mix(uNear,uFar,aHash);fs=clamp((lim-dM)/(lim*.2),0.,1.);}
   if(uIn>0.)fs*=clamp((dM-uIn*.8)/(uIn*.2),0.,1.);
   float hh=clamp(position.y/uH,0.,1.);float w=hh*hh*uWind*(sin(uTime*1.3+wp0.x*.21/uMPU+wp0.z*.17/uMPU)*.08+sin(uTime*3.1+wp0.x/uMPU)*.02);
   transformed.x+=w*uH*.15;transformed.z+=w*uH*.1;transformed*=fs;`);
  if(head)s.vertexShader=s.vertexShader.replace('#include <beginnormal_vertex>','#include <beginnormal_vertex>\n objectNormal=rotUp(normalize(aFacing))*objectNormal;');
  if(al)s.fragmentShader='varying float vGlow;\n'+s.fragmentShader.replace('#include <emissivemap_fragment>','#include <emissivemap_fragment>\n totalEmissiveRadiance*=vGlow;');};
 m.customProgramCacheKey=()=>'surf'+cfg.thin+(cfg.inner>0?'i':'')+(al?':'+al.kind+':'+al.part:'');return m;}
async function loadParts(url:string){const {GLTFLoader}=await import('three/examples/jsm/loaders/GLTFLoader.js');const g:any=await new GLTFLoader().loadAsync(url);g.scene.updateMatrixWorld(true);
 const parts:any[]=[];g.scene.traverse((o:any)=>{if(o.isMesh){const geo=o.geometry.clone();geo.morphAttributes={};geo.morphTargetsRelative=false;geo.applyMatrix4(o.matrixWorld);/* breathing is done in the shader; instanced meshes carry no morph targets */
  let n:any=o;while(n&&!/^(head(_\d+)?|crack_glow|crystal_body|mushroom_body)$/.test(n.name||''))n=n.parent;
  const e=n?n.matrixWorld.elements:null;parts.push({geo,mat:o.material,node:n?.name||null,pivot:e?[e[12],e[13],e[14]]:[0,0,0]});}});return parts;}
/** Flower heads -> one geometry (one group per material) with per-vertex aPivot, so all blooms of a type are ONE InstancedMesh. */
async function mergeHeads(THREE:T,heads:any[]){const {mergeGeometries}=await import('three/examples/jsm/utils/BufferGeometryUtils.js');
 const mats:any[]=[];const byMat:any[][]=[];
 for(const p of heads){const g=p.geo.index?p.geo.toNonIndexed():p.geo.clone();for(const k of Object.keys(g.attributes))if(!['position','normal'].includes(k))g.deleteAttribute(k);
  const n=g.attributes.position.count;const pv=new Float32Array(n*3);for(let i=0;i<n;i++){pv[i*3]=p.pivot[0];pv[i*3+1]=p.pivot[1];pv[i*3+2]=p.pivot[2];}g.setAttribute('aPivot',new THREE.BufferAttribute(pv,3));
  let mi=mats.indexOf(p.mat);if(mi<0){mats.push(p.mat);byMat.push([]);mi=mats.length-1;}byMat[mi].push(g);}
 const perMat=byMat.map(l=>l.length>1?mergeGeometries(l,false):l[0]);return {geo:mergeGeometries(perMat,true),mats};}
export function addCageSurface(THREE:T,parent:import('three').Object3D,o:SurfaceOpts){
 const group=new THREE.Group();group.name='cage-surface';parent.add(group);
 const shared={uMPU:{value:o.mpu},uTime:{value:0},uCreaturePos:{value:Array.from({length:MAXC},()=>new THREE.Vector3(1e9,1e9,1e9))},uCreatureCount:{value:0},uRadius:{value:CRYSTAL_RADIUS_M*o.mpu}};const aliveSets:any[]=[];const counts:Record<string,number>={};const meshes:any[]=[];
 const up=new THREE.Vector3(0,1,0),q=new THREE.Quaternion(),qy=new THREE.Quaternion(),m4=new THREE.Matrix4(),v=new THREE.Vector3(),sc=new THREE.Vector3(),col=new THREE.Color();
 const K=o.size??1;
 const build=(parts:any[],list:any[],cfg:any,brighten=false)=>{if(!list.length)return;for(const p of parts){const geo=p.geo.clone();const hs=new Float32Array(list.length);list.forEach((it:any,i:number)=>hs[i]=it.h);geo.setAttribute('aHash',new THREE.InstancedBufferAttribute(hs,1));
   let mat=p.mat;if(brighten&&/leaf/i.test(mat.name||'')){mat=mat.clone();mat.emissive=mat.color.clone().multiplyScalar(.45);mat.emissiveIntensity=1;mat.color.multiplyScalar(1.25);}
   const im=new THREE.InstancedMesh(geo,patch(THREE,mat,cfg,shared),list.length);im.frustumCulled=false;im.castShadow=false;im.receiveShadow=false;
   list.forEach((it:any,i:number)=>{v.set(it.dir[0],it.dir[1],it.dir[2]);q.setFromUnitVectors(up,v);qy.setFromAxisAngle(up,it.yaw);q.multiply(qy);const s=o.mpu*K*it.scale;
    m4.compose(v.clone().multiplyScalar(o.R+o.lift(v)),q,sc.set(s,s,s));im.setMatrixAt(i,m4);const t=o.tint(it.biome);col.setRGB(1,1,1);if(t)col.setRGB(.6+.4*t[0],.6+.4*t[1],.6+.4*t[2]);im.setColorAt(i,col);});
   im.instanceMatrix.needsUpdate=true;if(im.instanceColor)im.instanceColor.needsUpdate=true;group.add(im);meshes.push(im);}};
  const buildAlive=async(asset:string,parts:any[],list:any[],cfg:any)=>{const info=aliveInstances(o.seed,asset,list.length)!;const kind=(info.kind==='flower'?'head':info.kind) as Alive['kind'];
   const P=list.map((it:any)=>{const d=new THREE.Vector3(it.dir[0],it.dir[1],it.dir[2]);const qq=new THREE.Quaternion().setFromUnitVectors(up,d).multiply(new THREE.Quaternion().setFromAxisAngle(up,it.yaw));
    return {pos:d.clone().multiplyScalar(o.R+o.lift(d)),quat:qq,s:o.mpu*K*it.scale,inv:qq.clone().invert()};});
   const set:any={kind:info.kind,period:info.period,info,P,meshes:[],facing:null,near:new Float32Array(list.length)};
   const attach=(geo:any,mat:any,al:Alive)=>{geo.setAttribute('aHash',new THREE.InstancedBufferAttribute(Float32Array.from(list.map((it:any)=>it.h)),1));
    geo.setAttribute('aPhase',new THREE.InstancedBufferAttribute(info.phase,1));geo.setAttribute('aLife',new THREE.InstancedBufferAttribute(info.life,1));
    if(al.kind==='head'){if(!set.facing){set.facing=new Float32Array(list.length*3);for(let i=0;i<list.length;i++)set.facing[i*3+1]=1;}
     const fa=new THREE.InstancedBufferAttribute(set.facing,3);fa.setUsage(THREE.DynamicDrawUsage);geo.setAttribute('aFacing',fa);}
    const mats=Array.isArray(mat)?mat.map((m:any)=>patch(THREE,m,{...cfg,alive:al},shared)):patch(THREE,mat,{...cfg,alive:al},shared);
    const im=new THREE.InstancedMesh(geo,mats,list.length);im.frustumCulled=false;im.castShadow=false;im.receiveShadow=false;
    P.forEach((p:any,i:number)=>{m4.compose(p.pos,p.quat,sc.set(p.s,p.s,p.s));im.setMatrixAt(i,m4);const t=o.tint(list[i].biome);col.setRGB(1,1,1);if(t)col.setRGB(.6+.4*t[0],.6+.4*t[1],.6+.4*t[2]);im.setColorAt(i,col);});
    im.instanceMatrix.needsUpdate=true;if(im.instanceColor)im.instanceColor.needsUpdate=true;group.add(im);meshes.push(im);set.meshes.push(im);};
   const heads=parts.filter((p:any)=>/^head/.test(p.node||''));
   for(const p of parts){if(heads.includes(p))continue;attach(p.geo.clone(),p.mat,{kind,part:p.node?'live':'body',period:info.period});}
   if(heads.length){const mh=await mergeHeads(THREE,heads);attach(mh.geo,mh.mats,{kind:'head',part:'live',period:info.period});}
   aliveSets.push(set);};
 const Rm=o.R/o.mpu;
 const ready=(async()=>{
  const ground=plantGround({seed:o.seed,R:Rm,focus:[0,1,0],biomeAt:o.biomeAt,budget:o.budget,cellM:1,whole:true} as any) as Record<string,any[]>;
  await Promise.all(GROUND_ASSETS.map(async(a:string)=>{counts[a]=ground[a].length;if(!ground[a].length)return;const alive=!!(ALIVE_PROPS as any)[a];const h=(GC_MODELS as any)[a]?.h||.3;
   if(alive){try{const ap=await loadParts(ALIVE_ART+a+'_alive.glb');await buildAlive(a,ap,ground[a],{h,near:LOD.grassThin,far:LOD.props,inner:0,thin:0,wind:0});return;}catch{/* fall back to the still prop */}}
   const parts=await loadParts(SURFACE_ART+'groundcover/models/'+a+'.glb');
   build(parts,ground[a],GRASS.has(a)?{h,near:LOD.grassFull,far:LOD.grassThin,inner:0,thin:1,wind:1}:{h,near:LOD.grassThin,far:LOD.props,inner:0,thin:0,wind:a.startsWith('flower')?1:0});}));
  const trees=plantTrees({seed:o.seed,R:Rm,biomeAt:o.biomeAt,budget:Math.max(.5,o.budget)}) as Record<string,any[]>;
  await Promise.all(TREE_KINDS.map(async(k:string)=>{counts['tree:'+k]=trees[k].length;if(!trees[k].length)return;const giant=k==='giant_heartwood';const far=giant?LOD.giantFar:LOD.treeFar;
   const [nearP,farP]=await Promise.all([loadParts(SURFACE_ART+'trees/models/'+k+'_near.glb'),loadParts(SURFACE_ART+'trees/models/'+k+'_far.glb')]);const h=(TREE_MODELS as any)[k+'_near']?.h||3;const w=giant?.3:1;
   build(nearP,trees[k],{h,near:LOD.treeNear,far:LOD.treeNear,inner:0,thin:0,wind:w},k==='teal_round');build(farP,trees[k],{h,near:far,far:far,inner:LOD.treeNear,thin:0,wind:w},k==='teal_round');}));
  return counts;})();
 let tPrev=-1,tFlower=0,flowerAcc=0;const tmp=new THREE.Vector3();
 /** Optional ctx (sun dir world, creature directions on this planet, camera pos). Returns the REAL alive events seen this frame. */
 const update=(t:number,ctx?:{sunDir?:V3;creatures?:V3[];cam?:V3})=>{shared.uTime.value=t;const ev=new Set<string>();if(!ctx){tPrev=t;return [];}
  const cr=(ctx.creatures||[]).slice(0,MAXC).map(n=>{const d=n.clone().normalize();return d.multiplyScalar(o.R+o.lift(d));});
  shared.uCreatureCount.value=cr.length;cr.forEach((c,i)=>shared.uCreaturePos.value[i].copy(c));const crA=cr.map(c=>[c.x,c.y,c.z]);
  const seen=(p:V3,m:number)=>!!ctx.cam&&ctx.cam.distanceTo(p)/o.mpu<m;
  for(const set of aliveSets){
   if(set.kind==='rock'&&tPrev>=0){for(let i=0;i<set.P.length;i++)if(seen(set.P[i].pos,14)&&crossedPeak(tPrev,t,set.period,set.info.phase[i])){ev.add('rock_breathe');break;}}
   if(set.kind==='crystal'){for(let i=0;i<set.P.length;i++){const p=set.P[i].pos;const n=nearness([p.x,p.y,p.z],crA,CRYSTAL_RADIUS_M*o.mpu);const was=set.near[i];set.near[i]=n;if(was<.05&&n>.3&&seen(p,30))ev.add('crystal_hum');}}}
  if(ctx.sunDir&&t-tFlower>=.25){const dt=Math.min(1,t-tFlower);tFlower=t;let turned=0,cnt=0;
   for(const set of aliveSets){if(set.kind!=='flower'||!set.facing)continue;const F=set.facing;
    for(let i=0;i<set.P.length;i++){tmp.copy(ctx.sunDir).applyQuaternion(set.P[i].inv);const cur=[F[i*3],F[i*3+1],F[i*3+2]];
     const nx=easeFacing(cur,sunFacing([tmp.x,tmp.y,tmp.z],set.info.jitter.subarray(i*3,i*3+3)),dt);F[i*3]=nx[0];F[i*3+1]=nx[1];F[i*3+2]=nx[2];
     if(seen(set.P[i].pos,20)){cnt++;turned+=angleBetween(cur,nx);}}
    for(const im of set.meshes){const a=im.geometry.getAttribute('aFacing');if(a)a.needsUpdate=true;}}
   if(cnt>=3){flowerAcc+=turned/cnt;if(flowerAcc>.21){flowerAcc=0;ev.add('flower_turn');}}else flowerAcc=0;}
  tPrev=t;return [...ev];};
 const dispose=()=>{parent.remove(group);for(const m of meshes){m.geometry.dispose();(Array.isArray(m.material)?m.material:[m.material]).forEach((x:any)=>x.dispose());}};
 return {group,counts,ready,meshes,update,dispose};
}
