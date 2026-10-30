// The Cage surface on any ground: Cosmo's ground cover + trees as InstancedMesh, wind-swayed, with the per-instance
// hash dissolve LOD from the README (clumps shrink to nothing before they fade, so nothing pops). Seeded streams only.
import {GROUND_ASSETS,TREE_KINDS,GRASS,LOD,plantGround,plantTrees} from './groundcover.mjs';
import {GC_MODELS,TREE_MODELS} from './surface-data.mjs';
// Alive props (Cosmo's aliveprops v1): same art, plus breathing rock cracks, humming crystals (brighter within 3 m of a
// creature), swaying mushrooms and flower heads turning to the sun (aFacing/uSunDir in object space). Per-instance aPhase/aLife
// come from lwStream (recorded-IBM seed), never an unseeded RNG. Each flower type's heads are merged into ONE InstancedMesh.
import {ALIVE_PROPS,aliveInstances,crossedPeak,nearness,sunFacing,easeFacing,angleBetween,CRYSTAL_RADIUS_M} from './alive-props.mjs';
import {emissiveTintLinear,GROWTH_LAYER,TINT_STRENGTH,instanceGrowth,tapNode,tapNoticeKey,tapBounce,tapGlow,leanAffinity,fruitOffsets,fruitPalette,fruitDensity,CANOPY_SPILL,LEAN_MAX_DEG,TAP_MS} from './growth-view.mjs';
import {GROWTH,NODE_STAGES,growthCellAt} from './seeded-growth-nodes.mjs';
import {createGrowthShed} from './growth-three';
const MAXC=16;
const ROT_UP=`mat3 rotUp(vec3 f){vec3 u=vec3(0.,1.,0.);float c=dot(u,f);if(c>.9999)return mat3(1.);vec3 ax=normalize(cross(u,f));float s=sqrt(max(0.,1.-c*c));float t=1.-c;
 return mat3(t*ax.x*ax.x+c,t*ax.x*ax.y+s*ax.z,t*ax.x*ax.z-s*ax.y, t*ax.x*ax.y-s*ax.z,t*ax.y*ax.y+c,t*ax.y*ax.z+s*ax.x, t*ax.x*ax.z+s*ax.y,t*ax.y*ax.z-s*ax.x,t*ax.z*ax.z+c);}`;
type Alive={kind:'rock'|'crystal'|'mushroom'|'head';part:'body'|'live';period:number};
type T=typeof import('three');type V3=import('three').Vector3;
export const SURFACE_ART='/universe/livingworld/';
export const ALIVE_ART=SURFACE_ART+'aliveprops/models/';
export type GrowthOpts={nodes:any[];tick:number;cellRad:number;treeRM?:number};
export type SurfaceOpts={growth?:GrowthOpts;seed:string;R:number;mpu:number;biomeAt:(d:number[])=>string;lift:(d:V3)=>number;tint:(biome:string)=>[number,number,number]|null;budget:number;size?:number};
type Slot={u:Record<string,{value:any}>};
/** First person (target 36): trees within this many metres of the eye shrink away so no canopy fills the phone frame (SEEDED look value, like #709's resident clear). */
export const FP_TREE_CLEAR_M=16;
function patch(THREE:T,mat:any,cfg:{h:number;near:number;far:number;inner:number;thin:number;wind:number;alive?:Alive;gl?:boolean},shared:any){
 const m=mat.clone();const al=cfg.alive;const U:any={uPeriod:{value:al?.period||1},uCreaturePos:shared.uCreaturePos,uCreatureCount:shared.uCreatureCount,uRadius:shared.uRadius,uMPU:shared.uMPU,uTime:shared.uTime,uH:{value:cfg.h},uNear:{value:cfg.near},uFar:{value:cfg.far},uIn:{value:cfg.inner},uThin:{value:cfg.thin},uWind:{value:cfg.wind},uGT:{value:cfg.gl?TINT_STRENGTH(mat.name||''):0}};const fpG=cfg.thin===1||/blade|tip/i.test(mat.name||'');if(fpG)U.uFp36=shared.uFp36; /* target 36: near grass layer only */const fpT=(cfg as any).fpc>0;if(fpT&&!fpG){U.uFp36=shared.uFp36;U.uFpC={value:(cfg as any).fpc};} /* target 36: trees step out of the near first-person frame (SEEDED clear radius, metres) */
 const gl=!!cfg.gl;if(gl)for(const k of ['uGBeast','uGWind','uGTurb','uGShiver','uGMotion','uGStorm','uGPulseC','uGPulseA','uGGlow','uGLean','uGEm'])U[k]=shared[k];
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
 const GV=`
   float gS=1.;vGc=vec3(1.);vGm=0.;vGd=0.;vGe=vec3(0.);
   float gk=floor(aGa.w+.001);float gf=mod(gk,3.);float gst=floor(gk/3.);float gei=floor(aGc.w);float aGl=(aGc.w-gei)/.99;
   if(gf>.5){gS=aGa.x;float ph=aHash*6.2831;float hh2=hh;float swg=(sin(uTime*1.7+ph)*.6+sin(uTime*2.9+ph*1.7)*.4*uGTurb)*uGMotion;
    transformed.x+=uGWind.x*swg*hh2*hh2*uH*.12;transformed.z+=uGWind.y*swg*hh2*hh2*uH*.12;
    if(gf>1.5){float sv=sin(uTime*31.+ph*3.)*uGShiver*uGMotion;transformed.x+=sv*hh2*uH*.025;transformed.z+=sv*cos(ph)*hh2*uH*.02;}
    vec3 lo=transpose(mat3(instanceMatrix))*(uGBeast-wp0);lo.y=0.;float ll=length(lo);if(ll>1e-4&&aGl>0.){lo/=ll;float lm=tan(uGLean)*aGl*uGMotion*hh2*hh2*uH;transformed.x+=lo.x*lm;transformed.z+=lo.z*lm;}
    float pc=dot(normalize(wp0),uGPulseC.xyz);float pin=smoothstep(cos(uGPulseC.w),1.,pc);gS*=1.+uGPulseA*pin;
    vGc=aGc.xyz;vGm=aGa.y*uGT;vGd=min(.3,aGa.z+uGStorm*.22*step(1.5,gf))*step(.001,uGT);vGe=(uGEm[int(gst)]*(gei*.001)+aGc.xyz*uGGlow*pin)*step(.001,uGT);}
   `;
 m.onBeforeCompile=(s:any)=>{Object.assign(s.uniforms,U);
  s.vertexShader='uniform float uMPU,uTime,uH,uNear,uFar,uIn,uThin,uWind,uGT;attribute float aHash;\n'+(gl?'uniform vec2 uGWind;uniform float uGTurb,uGShiver,uGMotion,uGStorm,uGPulseA,uGGlow,uGLean;uniform vec4 uGPulseC;uniform vec3 uGBeast;uniform vec3 uGEm[6];attribute vec4 aGa;attribute vec4 aGc;varying vec3 vGc,vGe;varying float vGm,vGd;\n':'')+aliveHead+s.vertexShader.replace('#include <begin_vertex>',`#include <begin_vertex>`+aliveVS+`
   vec3 wp0=(modelMatrix*instanceMatrix*vec4(0.,0.,0.,1.)).xyz;float dM=distance(cameraPosition,wp0)/uMPU;
   float fs;if(uThin>.5){fs=aHash<.3?mix(1.,1.5,smoothstep(uNear*.8,uNear,dM))*clamp((mix(uNear,uFar,aHash/.3)-dM)/(uFar*.2),0.,1.):clamp((uNear-dM)/(uNear*.2),0.,1.);}
   else{float lim=mix(uNear,uFar,aHash);fs=clamp((lim-dM)/(lim*.2),0.,1.);}
   if(uIn>0.)fs*=clamp((dM-uIn*.8)/(uIn*.2),0.,1.);
   float hh=clamp(position.y/uH,0.,1.);float w=hh*hh*uWind*(sin(uTime*1.3+wp0.x*.21/uMPU+wp0.z*.17/uMPU)*.08+sin(uTime*3.1+wp0.x/uMPU)*.02);
   transformed.x+=w*uH*.15;transformed.z+=w*uH*.1;${gl?GV:'float gS=1.;'}transformed*=fs*gS;`+(fpT&&!fpG?`transformed*=mix(1.,smoothstep(uFpC*.75,uFpC,dM),uFp36);`:''));
  if(fpT&&!fpG)s.vertexShader='uniform float uFp36,uFpC;\n'+s.vertexShader;
  if(head)s.vertexShader=s.vertexShader.replace('#include <beginnormal_vertex>','#include <beginnormal_vertex>\n objectNormal=rotUp(normalize(aFacing))*objectNormal;');
  if(fpG)s.fragmentShader='uniform float uFp36;\n'+s.fragmentShader.replace('#include <color_fragment>','#include <color_fragment>\n {float lu=clamp(dot(diffuseColor.rgb,vec3(.2126,.7152,.0722))*1.6,0.,1.);vec3 m36=mix(vec3(.026,.105,.011),mix(vec3(.073,.262,.023),vec3(.262,.527,.069),smoothstep(.45,1.,lu)),smoothstep(0.,.5,lu));diffuseColor.rgb=mix(diffuseColor.rgb,m36,uFp36);}').replace('#include <emissivemap_fragment>','#include <emissivemap_fragment>\n totalEmissiveRadiance=mix(totalEmissiveRadiance,vec3(.012,.035,.006)*dot(totalEmissiveRadiance,vec3(.333)),uFp36);'); /* first person (target 36): the tip glow (teal #89FFED / lilac #CBA0FF emissive) fades to a faint green, so the lit colour comes from the one sun, not the glow */ /* first person (target 36): near grass goes lush green (MEADOW36 #2C5A1C/#4C8C2A/#8CC04A in linear), no lilac/teal; shading stays the one sun's light. Off (0) in the Cage and orbit. */
  if(al)s.fragmentShader='varying float vGlow;\n'+s.fragmentShader.replace('#include <emissivemap_fragment>','#include <emissivemap_fragment>\n totalEmissiveRadiance*=vGlow;');
  // growth tint: blend the base colour toward the stage tint in LINEAR light (never multiply), then desaturate, then add the small emissive boost
  if(gl)s.fragmentShader='varying vec3 vGc,vGe;varying float vGm,vGd;\n'+s.fragmentShader.replace('#include <color_fragment>','#include <color_fragment>\n diffuseColor.rgb=mix(diffuseColor.rgb,vGc,clamp(vGm,0.,1.));{float lu=dot(diffuseColor.rgb,vec3(.2126,.7152,.0722));diffuseColor.rgb=mix(diffuseColor.rgb,vec3(lu),vGd);}').replace('#include <emissivemap_fragment>','#include <emissivemap_fragment>\n totalEmissiveRadiance+=vGe;');};
 m.customProgramCacheKey=()=>'surf'+(fpG?'F':'')+(fpT&&!fpG?'T':'')+(gl?'G':'')+cfg.thin+(cfg.inner>0?'i':'')+(al?':'+al.kind+':'+al.part:'');return m;}
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
 const shared:any={uGBeast:{value:new THREE.Vector3(1e9,1e9,1e9)},uGWind:{value:new THREE.Vector2(0,0)},uGTurb:{value:0},uGShiver:{value:0},uGMotion:{value:1},uGStorm:{value:0},uGPulseC:{value:new THREE.Vector4(0,1,0,.2)},uGPulseA:{value:0},uGGlow:{value:0},uGLean:{value:LEAN_MAX_DEG*Math.PI/180},uGEm:{value:NODE_STAGES.map((st:string)=>new THREE.Vector3(...(emissiveTintLinear(st) as [number,number,number])))},uMPU:{value:o.mpu},uTime:{value:0},uCreaturePos:{value:Array.from({length:MAXC},()=>new THREE.Vector3(1e9,1e9,1e9))},uCreatureCount:{value:0},uRadius:{value:CRYSTAL_RADIUS_M*o.mpu},uFp36:{value:0}};const aliveSets:any[]=[];const counts:Record<string,number>={};const meshes:any[]=[];
 const up=new THREE.Vector3(0,1,0),q=new THREE.Quaternion(),qy=new THREE.Quaternion(),m4=new THREE.Matrix4(),v=new THREE.Vector3(),sc=new THREE.Vector3(),col=new THREE.Color();
 const K=o.size??1;
 // ---- growth nodes (SEEDED placement, SIMULATED tick): per-instance attributes only on lists that touch a territory, so with no nodes nothing here runs
 const GR=o.growth,recs:any[]=[];let gNodes:any[]=GR?.nodes||[],gTick=GR?.tick??0;const Rm0=o.R/o.mpu;
 const unitLL=(n:any)=>{const a=n.lat*Math.PI/180,l=n.lon*Math.PI/180;return [Math.cos(a)*Math.cos(l),Math.sin(a),Math.cos(a)*Math.sin(l)];};
 const mkRec=(key:string,list:any[],h:number)=>{const layer=(GROWTH_LAYER as any)[key];if(!GR||!layer||!list.length)return null;
  const nd=gNodes.map((n:any)=>({n,c:unitLL(n),cos:Math.cos(Math.min(Math.PI,n.spread*GROWTH.rim*GR.cellRad))}));const idx:number[]=[];
  list.forEach((it:any,i:number)=>{if(nd.some(q=>q.c[0]*it.dir[0]+q.c[1]*it.dir[1]+q.c[2]*it.dir[2]>=q.cos))idx.push(i);});
  if(!idx.length)return null;const n=list.length,A=new Float32Array(n*4),C=new Float32Array(n*4),L=new Float32Array(n);
  for(let i=0;i<n;i++){A[i*4]=1;C[i*4]=C[i*4+1]=C[i*4+2]=1;}
  for(const i of idx)A[i*4+3]=layer==='shrub'||layer==='canopy'?2:1;// +3*stage index added in apply()
  if(layer==='canopy'||layer==='shrub'){// canopy spill: at gold a crown reaches 1.06, so trunks in the territory move outward by 0.05 of the crown radius
   for(const i of idx){const it=list[i];let best:any=null,bd=-2;for(const q of nd){const d=q.c[0]*it.dir[0]+q.c[1]*it.dir[1]+q.c[2]*it.dir[2];if(d>bd){bd=d;best=q;}}
    if(!best)continue;const crownM=.4*h*it.scale*K;const sh=CANOPY_SPILL.trunk_offset_of_crown_radius*crownM/Rm0;const c=best.c;const dd=bd;
    const t=[it.dir[0]-c[0]*dd,it.dir[1]-c[1]*dd,it.dir[2]-c[2]*dd];const tl=Math.hypot(t[0],t[1],t[2]);if(tl<1e-6)continue;
    const v=[it.dir[0]+t[0]/tl*sh,it.dir[1]+t[1]/tl*sh,it.dir[2]+t[2]/tl*sh];const vl=Math.hypot(v[0],v[1],v[2]);list[i]={...it,dir:[v[0]/vl,v[1]/vl,v[2]/vl]};}}
  const r:any={key,layer,list,idx,A,C,L,flag:Uint8Array.from(A.filter((_:number,j:number)=>j%4===3)),attrs:[] as any[],h,fruit:null};recs.push(r);return r;};
 const growAttrs=(geo:any,r:any)=>{const mk=(arr:Float32Array,k:number,dyn=false)=>{const a=new THREE.InstancedBufferAttribute(arr,k);if(dyn)a.setUsage(THREE.DynamicDrawUsage);r.attrs.push(a);return a;};
  geo.setAttribute('aGa',mk(r.A,4,true));geo.setAttribute('aGc',mk(r.C,4,true));};
 const build=(parts:any[],list:any[],cfg0:any,brighten=false,rec:any=null)=>{if(!list.length)return;const cfg=rec?{...cfg0,gl:true}:cfg0;for(const p of parts){const geo=p.geo.clone();if(rec)growAttrs(geo,rec);const hs=new Float32Array(list.length);list.forEach((it:any,i:number)=>hs[i]=it.h);geo.setAttribute('aHash',new THREE.InstancedBufferAttribute(hs,1));
   let mat=p.mat;if(brighten&&/leaf/i.test(mat.name||'')){mat=mat.clone();mat.emissive=mat.color.clone().multiplyScalar(.12);mat.emissiveIntensity=1; /* FIX_NOTES 43c74d3: the .45 emissive + x1.25 boost clipped leaf tips to white in daylight */}
   const im=new THREE.InstancedMesh(geo,patch(THREE,mat,cfg,shared),list.length);im.frustumCulled=false;im.castShadow=false;im.receiveShadow=false;
   list.forEach((it:any,i:number)=>{v.set(it.dir[0],it.dir[1],it.dir[2]);q.setFromUnitVectors(up,v);qy.setFromAxisAngle(up,it.yaw);q.multiply(qy);const s=o.mpu*K*it.scale;
    m4.compose(v.clone().multiplyScalar(o.R+o.lift(v)),q,sc.set(s,s,s));im.setMatrixAt(i,m4);const t=o.tint(it.biome);col.setRGB(1,1,1);if(t)col.setRGB(t[0],t[1],t[2]); /* pack grass tint, no lift toward white (it read as frost) */im.setColorAt(i,col);});
   im.instanceMatrix.needsUpdate=true;if(im.instanceColor)im.instanceColor.needsUpdate=true;group.add(im);meshes.push(im);}};
  const buildAlive=async(asset:string,parts:any[],list:any[],cfg0:any,rec:any=null)=>{const cfg=rec?{...cfg0,gl:true}:cfg0;const info=aliveInstances(o.seed,asset,list.length)!;const kind=(info.kind==='flower'?'head':info.kind) as Alive['kind'];
   const P=list.map((it:any)=>{const d=new THREE.Vector3(it.dir[0],it.dir[1],it.dir[2]);const qq=new THREE.Quaternion().setFromUnitVectors(up,d).multiply(new THREE.Quaternion().setFromAxisAngle(up,it.yaw));
    return {pos:d.clone().multiplyScalar(o.R+o.lift(d)),quat:qq,s:o.mpu*K*it.scale,inv:qq.clone().invert()};});
   const set:any={kind:info.kind,period:info.period,info,P,meshes:[],facing:null,near:new Float32Array(list.length)};
   const attach=(geo:any,mat:any,al:Alive)=>{if(rec)growAttrs(geo,rec);geo.setAttribute('aHash',new THREE.InstancedBufferAttribute(Float32Array.from(list.map((it:any)=>it.h)),1));
    geo.setAttribute('aPhase',new THREE.InstancedBufferAttribute(info.phase,1));geo.setAttribute('aLife',new THREE.InstancedBufferAttribute(info.life,1));
    if(al.kind==='head'){if(!set.facing){set.facing=new Float32Array(list.length*3);for(let i=0;i<list.length;i++)set.facing[i*3+1]=1;}
     const fa=new THREE.InstancedBufferAttribute(set.facing,3);fa.setUsage(THREE.DynamicDrawUsage);geo.setAttribute('aFacing',fa);}
    const mats=Array.isArray(mat)?mat.map((m:any)=>patch(THREE,m,{...cfg,alive:al},shared)):patch(THREE,mat,{...cfg,alive:al},shared);
    const im=new THREE.InstancedMesh(geo,mats,list.length);im.frustumCulled=false;im.castShadow=false;im.receiveShadow=false;
    P.forEach((p:any,i:number)=>{m4.compose(p.pos,p.quat,sc.set(p.s,p.s,p.s));im.setMatrixAt(i,m4);const t=o.tint(list[i].biome);col.setRGB(1,1,1);if(t)col.setRGB(t[0],t[1],t[2]);im.setColorAt(i,col);});
    im.instanceMatrix.needsUpdate=true;if(im.instanceColor)im.instanceColor.needsUpdate=true;group.add(im);meshes.push(im);set.meshes.push(im);};
   const heads=parts.filter((p:any)=>/^head/.test(p.node||''));
   for(const p of parts){if(heads.includes(p))continue;attach(p.geo.clone(),p.mat,{kind,part:p.node?'live':'body',period:info.period});}
   if(heads.length){const mh=await mergeHeads(THREE,heads);attach(mh.geo,mh.mats,{kind:'head',part:'live',period:info.period});}
   aliveSets.push(set);};
 const Rm=o.R/o.mpu;
 const ready=(async()=>{
  const ground=plantGround({seed:o.seed,R:Rm,focus:[0,1,0],biomeAt:o.biomeAt,budget:o.budget,cellM:1,whole:true} as any) as Record<string,any[]>;
  await Promise.all(GROUND_ASSETS.map(async(a:string)=>{counts[a]=ground[a].length;if(!ground[a].length)return;const alive=!!(ALIVE_PROPS as any)[a];const h=(GC_MODELS as any)[a]?.h||.3;const rec=mkRec(a,ground[a],h);
   if(alive){try{const ap=await loadParts(ALIVE_ART+a+'_alive.glb');await buildAlive(a,ap,ground[a],{h,near:LOD.grassThin,far:LOD.props,inner:0,thin:0,wind:0},rec);return;}catch{/* fall back to the still prop */}}
   const parts=await loadParts(SURFACE_ART+'groundcover/models/'+a+'.glb');
   build(parts,ground[a],GRASS.has(a)?{h,near:LOD.grassFull,far:LOD.grassThin,inner:0,thin:1,wind:1}:{h,near:LOD.grassThin,far:LOD.props,inner:0,thin:0,wind:a.startsWith('flower')?1:0},false,rec);}));
  const trees=plantTrees({seed:o.seed,R:Rm,biomeAt:o.biomeAt,budget:Math.max(.5,o.budget)}) as Record<string,any[]>;
  await Promise.all(TREE_KINDS.map(async(k:string)=>{counts['tree:'+k]=trees[k].length;if(!trees[k].length)return;const giant=k==='giant_heartwood';const far=giant?LOD.giantFar:LOD.treeFar;
   const [nearP,farP]=await Promise.all([loadParts(SURFACE_ART+'trees/models/'+k+'_near.glb'),loadParts(SURFACE_ART+'trees/models/'+k+'_far.glb')]);const h=(TREE_MODELS as any)[k+'_near']?.h||3;const w=giant?.3:1;const rec=mkRec('tree:'+k,trees[k],h);
   build(nearP,trees[k],{h,near:LOD.treeNear,far:LOD.treeNear,inner:0,thin:0,wind:w,fpc:FP_TREE_CLEAR_M},k==='teal_round',rec);build(farP,trees[k],{h,near:far,far:far,inner:LOD.treeNear,thin:0,wind:w,fpc:FP_TREE_CLEAR_M},k==='teal_round',rec);}));
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
 const G_API=(()=>{if(!GR)return null;
  const pal=fruitPalette();let fruitMesh:any=null;const fruitTrees:any[]=[];let shed:any=null;let pulse:any=null;let tLean=-1;const tapState={t0:-1e9,node:null as any,glowOn:false};
  const nodeById=()=>Object.fromEntries(gNodes.map((n:any)=>[n.id,n]));
  const initFruit=()=>{if(fruitMesh)return;const trs=recs.filter(r=>r.layer==='shrub'||r.layer==='canopy');let total=0;for(const r of trs)total+=r.idx.length;if(!total)return;
   const per=6,cap=Math.min(total,260);const off=fruitOffsets(o.seed,cap,per);let used=0;
   const geo=new THREE.IcosahedronGeometry(.5,0);const mat=new THREE.MeshStandardMaterial({color:0xffffff,roughness:.45,emissive:new THREE.Color(0x9a2a44),emissiveIntensity:pal.emissive});
   fruitMesh=new THREE.InstancedMesh(geo,mat,cap*per);fruitMesh.frustumCulled=false;fruitMesh.name='growth-fruit';fruitMesh.count=0;group.add(fruitMesh);meshes.push(fruitMesh);
   const c=new THREE.Color();
   for(const r of trs){for(const i of r.idx){if(used>=cap)break;const it=r.list[i];const d=new THREE.Vector3(it.dir[0],it.dir[1],it.dir[2]);const q=new THREE.Quaternion().setFromUnitVectors(up,d);
     fruitTrees.push({rec:r,i,it,d,q,base:used*per,pos:d.clone().multiplyScalar(o.R+o.lift(d)),Hw:r.h*it.scale*K*o.mpu});
     for(let k=0;k<per;k++){const w=off[(used*per+k)*5+3];const p=w<pal.weights[0]?0:w<pal.weights[0]+pal.weights[1]?1:2;c.setRGB(pal.colors[p][0],pal.colors[p][1],pal.colors[p][2]);fruitMesh.setColorAt(used*per+k,c);}
     used++;}}
   fruitMesh.userData={off,per};};
  const updFruit=(storm:number)=>{initFruit();if(!fruitMesh)return;const {off,per}=fruitMesh.userData;const m=new THREE.Matrix4(),p=new THREE.Vector3(),sc=new THREE.Vector3(),qq=new THREE.Quaternion();
   for(let ti=0;ti<fruitTrees.length;ti++){const ft=fruitTrees[ti];const st=instanceGrowth(gNodes,gTick,ft.it.dir,ft.rec.layer,ft.it.biome,{cellRad:GR.cellRad});const dens=st.fruit;
    for(let k=0;k<per;k++){const base=(ti*per+k)*5;const thr=off[base+4];const on=dens>0&&thr<dens;const sz=on?(pal.sizeM[0]+(pal.sizeM[1]-pal.sizeM[0])*((off[base+3]*13)%1))*o.mpu*K*1.6:0;
     const cr=.4*ft.Hw*st.scale;p.set(off[base]*cr,off[base+1]*ft.Hw*st.scale,off[base+2]*cr).applyQuaternion(ft.q).add(ft.pos);sc.set(sz,sz,sz);m.compose(p,qq.identity(),sc);fruitMesh.setMatrixAt(ft.base+k,m);}}
   fruitMesh.count=fruitTrees.length*per;fruitMesh.instanceMatrix.needsUpdate=true;if(fruitMesh.instanceColor)fruitMesh.instanceColor.needsUpdate=true;};
  const apply=()=>{for(const r of recs){for(const i of r.idx){const it=r.list[i];const st=instanceGrowth(gNodes,gTick,it.dir,r.layer,it.biome,{cellRad:GR.cellRad});
    const fl=r.flag[i],si=st.hit?Math.max(0,NODE_STAGES.indexOf(st.stage as any)):0,tt=emissiveTintLinear(st.stage as any),ch=tt[0]>=tt[1]&&tt[0]>=tt[2]?0:tt[1]>=tt[2]?1:2,ea=tt[ch]>0?Math.min(.15,st.emissive[ch]/tt[ch]):0,ei=Math.round(ea*1000);
    r.A[i*4]=st.scale;r.A[i*4+1]=st.mix;r.A[i*4+2]=st.hit&&st.scarred?.15:0;r.A[i*4+3]=fl+3*si;r.C[i*4]=st.rgb[0];r.C[i*4+1]=st.rgb[1];r.C[i*4+2]=st.rgb[2];r.C[i*4+3]=ei+(r.L[i]||0)*.99;}
   for(const a of r.attrs)a.needsUpdate=true;}
   updFruit(0);};
  return {apply,updFruit,tapState,nodeById,get shed(){return shed;},set shed(v:any){shed=v;},get pulse(){return pulse;},set pulse(v:any){pulse=v;},get tLean(){return tLean;},set tLean(v:number){tLean=v;}};})();
 const setGrowth=(nodes:any[],tick:number)=>{if(!G_API)return;gNodes=nodes;gTick=tick;ready.then(()=>{G_API.apply();if(!G_API.shed&&gNodes.length){G_API.shed=createGrowthShed(THREE,group,gNodes,{seed:o.seed,R:o.R,mpu:o.mpu,K,cellRad:GR!.cellRad,lift:o.lift});}});};
 /** Per frame. t seconds (frame clock); wind/storm/turbulence come from the world field (motionParams / F.storm); reduced = reduced-motion preference. */
 const growthFrame=(f:{t:number;wind:[number,number];turb:number;storm:number;reduced:boolean;beast?:V3|null;px:number;nowMs:number})=>{if(!G_API)return;
  const U=shared;const mo=f.reduced?0:1;U.uGMotion.value=mo;U.uGWind.value.set(Math.max(-1.5,Math.min(1.5,f.wind[0])),Math.max(-1.5,Math.min(1.5,f.wind[1])));U.uGTurb.value=Math.max(0,Math.min(1.5,f.turb));
  U.uGShiver.value=f.storm>.5?(f.storm-.5)*2:0;U.uGStorm.value=Math.max(0,Math.min(1,f.storm));
  const age=f.nowMs-G_API.tapState.t0;const tn=G_API.tapState.node;
  if(tn&&age<TAP_MS*1.5){const c=unitLL(tn);U.uGPulseC.value.set(c[0],c[1],c[2],Math.min(.9,tn.spread*GR!.cellRad*.8));U.uGPulseA.value=tapBounce(age,f.reduced);U.uGGlow.value=tapGlow(age)*.08;}else{U.uGPulseA.value=0;U.uGGlow.value=0;}
  if(f.beast){U.uGBeast.value.copy(f.beast);if(f.t-G_API.tLean>.25){G_API.tLean=f.t;const bd=f.beast.clone().normalize();
   for(const r of recs){const L=r.L;for(const i of r.idx){const d=r.list[i].dir;const cs=Math.max(-1,Math.min(1,d[0]*bd.x+d[1]*bd.y+d[2]*bd.z));const distM=Math.acos(cs)*Rm0;const la=distM<6?leanAffinity(distM):0;L[i]=la;r.C[i*4+3]=Math.floor(r.C[i*4+3])+la*.99;}
    for(const a of r.attrs)if(a.itemSize===4&&a.array===r.C)a.needsUpdate=true;}}}
  const sh:Record<string,number>={};for(const n of gNodes)sh[n.id]=n.shed||0;if(G_API.shed){G_API.shed.update(f.t,f.px,sh,!f.reduced);const bage=f.reduced?-1:age/1000;if(tn&&(tn.stage==='bloom'||tn.stage==='gold'))G_API.shed.burst(tn.id,bage>=0&&bage<=1.4?bage:-1);else for(const it of G_API.shed.items)it.BU.uAge.value=-1;}};
 /** Tap on the ground at world direction `dir` (unit, planet frame). Returns the Emeth notice key and node when it hit a node's territory; starts the bounce + burst (view state only). */
 const tapGrowth=(dir:number[],nowMs:number)=>{if(!G_API)return null;const hit=tapNode(gNodes,gTick,dir,{cellRad:GR!.cellRad});if(!hit)return null;G_API.tapState.t0=nowMs;G_API.tapState.node=hit.node;
  return {key:tapNoticeKey(hit.cell),stage:hit.cell.stage,node:hit.node,scarred:hit.cell.scarred};};
 const growthInfo=()=>({enabled:!!GR,tick:gTick,nodes:gNodes.map((n:any)=>({id:n.id,kind:n.kind,lat:n.lat,lon:n.lon,stage:n.stage,x:n.x,scale:n.scale,shed:n.shed,label:n.label,view_snapped:n.view_snapped})),lists:recs.map(r=>({key:r.key,layer:r.layer,inTerritory:r.idx.length,of:r.list.length})),fruit:G_API?(recs.length?true:false):false});
 const dispose=()=>{G_API?.shed?.dispose();parent.remove(group);for(const m of meshes){m.geometry.dispose();(Array.isArray(m.material)?m.material:[m.material]).forEach((x:any)=>x.dispose());}};
 const setFirstPerson=(k:number)=>{shared.uFp36.value=Math.max(0,Math.min(1,k));};
 return {group,counts,ready,meshes,update,dispose,setGrowth,growthFrame,tapGrowth,growthInfo,setFirstPerson};
}
