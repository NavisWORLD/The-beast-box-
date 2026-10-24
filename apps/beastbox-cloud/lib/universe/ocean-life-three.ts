// Ocean life renderer for the pocket world, using Cosmo's ocean-life art pack v1 (public/universe/livingworld/oceanlife).
// Where and how many: ocean-life.mjs, seeded from the recorded IBM genesis seed (lwStream), so it stays SEEDED, not recorded.
// Rendering: fish, jellies and seabirds are one InstancedMesh per species and material (the pack's static *_far.glb, 35-66 tris); whales, mantas
// and turtles are skinned *_near.glb clones with their own AnimationMixer that swap to the static far model past the pack's LOD distance.
// Not used: the pack's GLSL chunks (never compiled by Cosmo), the sprite sheets and the billboard atlas (they are for the planet/orbit scale).
// The sea is opaque here, so every animal rides at the surface; the pack's depth band is kept on the school (school.depth) but not drawn.
import {oceanLife,memberAt,headingAt,surfacing,planktonGlow} from './ocean-life.mjs';
import {OCEAN_SPECIES} from './ocean-species.mjs';
type T=typeof import('three');
const SPC:Record<string,any>=OCEAN_SPECIES as any;
const BASE='/universe/livingworld/oceanlife/models/';
const SKINNED=new Set(['whale','manta','turtle']);
const CLIP:Record<string,string>={whale:'tail_swim',manta:'glide',turtle:'paddle'};
export function addOceanLife(THREE:T,scene:import('three').Scene,o:{seed:string;R:number;mpu:number;isWater:(n:number[])=>boolean|string|null;phone:boolean;life?:number}){
 const data=oceanLife(o.seed,o.isWater,{life:(o.life??1)*(o.phone?.6:1),plankton:o.phone?160:320,R:o.R,mpu:o.mpu});
 const group=new THREE.Group();group.name='ocean-life';scene.add(group);const R=o.R,m=o.mpu;
 const dot=(()=>{const c=document.createElement('canvas');c.width=c.height=32;const g=c.getContext('2d')!;const gr=g.createRadialGradient(16,16,0,16,16,16);gr.addColorStop(0,'rgba(255,255,255,1)');gr.addColorStop(.4,'rgba(255,255,255,.55)');gr.addColorStop(1,'rgba(255,255,255,0)');g.fillStyle=gr;g.fillRect(0,0,32,32);return new THREE.CanvasTexture(c);})();
 const nP=data.plankton.length;const pp=new Float32Array(nP*3),pc=new Float32Array(nP*3);data.plankton.forEach((p,i)=>{pp.set([p.n[0]*(R+.01),p.n[1]*(R+.01),p.n[2]*(R+.01)],i*3);});
 const pg=new THREE.BufferGeometry();pg.setAttribute('position',new THREE.BufferAttribute(pp,3));pg.setAttribute('color',new THREE.BufferAttribute(pc,3));
 const plank=new THREE.Points(pg,new THREE.PointsMaterial({map:dot,vertexColors:true,size:.16,sizeAttenuation:true,transparent:true,blending:THREE.AdditiveBlending,depthWrite:false}));plank.frustumCulled=false;group.add(plank);
 const bySp=new Map<string,any[]>();for(const s of data.schools){if(!bySp.has(s.species))bySp.set(s.species,[]);bySp.get(s.species)!.push(s);}
 const counts:Record<string,number>={};for(const [sp,ss] of bySp)counts[sp]=ss.reduce((a:number,s:any)=>a+s.count,0);
 const V=(a:number[])=>new THREE.Vector3(a[0],a[1],a[2]);const mx=new THREE.Matrix4(),q=new THREE.Quaternion(),pos=new THREE.Vector3(),sc3=new THREE.Vector3(),yaw=new THREE.Quaternion(),yAxis=new THREE.Vector3(0,0,1);
 const mats:any[]=[];let loaded=0,failed:string|null=null,lastT=-1;
 // tier 1: instanced static models
 type Inst={sp:string;meshes:any[];schools:any[]};const insts:Inst[]=[];
 // tier 2: skinned clones
 type Skin={sp:string;school:any;idx:number;near:any;far:any;mixer:any;dist:number};const skins:Skin[]=[];
 const camV=new THREE.Vector3();const world=new THREE.Vector3();
 const spout=(()=>{const wh=(bySp.get('whale')||[]);const spN=14;return wh.map(()=>{const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(new Float32Array(spN*3),3));const p=new THREE.Points(g,new THREE.PointsMaterial({map:dot,color:0xeaf8ff,size:.12,sizeAttenuation:true,transparent:true,opacity:0,depthWrite:false}));p.frustumCulled=false;group.add(p);return {p,spN};});})();
 const ready=(async()=>{try{
  const [{GLTFLoader},{clone}]=await Promise.all([import('three/examples/jsm/loaders/GLTFLoader.js'),import('three/examples/jsm/utils/SkeletonUtils.js')]);const L=new GLTFLoader();
  const load=(f:string)=>L.loadAsync(BASE+f);
  for(const [sp,ss] of bySp){const total=counts[sp];
   if(!SKINNED.has(sp)){const g:any=await load(sp+'_far.glb');const meshes:any[]=[];g.scene.traverse((c:any)=>{if(!c.isMesh)return;const im=new THREE.InstancedMesh(c.geometry,c.material,total);im.frustumCulled=false;im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);im.userData.baseM=c.matrixWorld?c.matrixWorld.clone():new THREE.Matrix4();c.updateWorldMatrix(true,false);im.userData.baseM=c.matrixWorld.clone();group.add(im);meshes.push(im);mats.push(c.material);});insts.push({sp,meshes,schools:ss});}
   else{const [gn,gf]:any[]=await Promise.all([load(sp+'_near.glb'),load(sp+'_far.glb')]);gn.scene.traverse((c:any)=>{if(c.material)mats.push(c.material);});
    let idx=0;for(const s of ss)for(let i=0;i<s.count;i++){const near=clone(gn.scene),far=clone(gf.scene);near.frustumCulled=false;far.visible=false;near.traverse((c:any)=>{c.frustumCulled=false;});far.traverse((c:any)=>{c.frustumCulled=false;});
     const mixer=new THREE.AnimationMixer(near);const clip=gn.animations.find((a:any)=>a.name===CLIP[sp])||gn.animations[0];if(clip){const a=mixer.clipAction(clip);a.time=(s.phase/(Math.PI*2)+i*.37)%1*clip.duration;a.play();}
     group.add(near,far);skins.push({sp,school:s,idx:i,near,far,mixer,dist:0});idx++;}}
   loaded++;}
 }catch(e){failed=String(e);(window as any).__lwOceanErr=failed;}})();
 function basis(n:any,hv:any,yawA=0){const xv=new THREE.Vector3().crossVectors(n,hv).normalize();mx.makeBasis(xv,n,hv);q.setFromRotationMatrix(mx);if(yawA){yaw.setFromAxisAngle(n,yawA);q.premultiply(yaw);}}
 function place(obj:any,n:any,hv:any,lift:number,scale:number,yawA=0){const zv=hv.clone();const xv=new THREE.Vector3().crossVectors(n,zv).normalize();mx.makeBasis(xv,n,zv);q.setFromRotationMatrix(mx);if(yawA){yaw.setFromAxisAngle(n,yawA);q.premultiply(yaw);}obj.quaternion.copy(q);obj.position.copy(n).multiplyScalar(R+lift);obj.scale.setScalar(scale);}
 function update(t:number,s:{night:number;camPos?:import('three').Vector3}){
  const dt=lastT<0?0:Math.min(.1,Math.max(0,t-lastT));lastT=t;const night=Math.max(0,Math.min(1,s.night));
  for(const mt of mats){if(mt&&'emissiveIntensity' in mt)mt.emissiveIntensity=.45+.9*night;}
  // tier 1
  for(const it of insts){const sp=SPC[it.sp];const hz=1/(sp.clips.swim??sp.clips.pulse??sp.clips.flap??1.2);let k=0;
   for(const sc of it.schools)for(let i=0;i<sc.count;i++){const p=memberAt(sc,i,t),h=headingAt(sc,i,t);const n=V(p),hv=V(h);const ph=sc.phase+i*1.7;
    const bob=it.sp==='seabird'?.002*Math.sin(t*1.1+ph):.004+.003*Math.sin(t*2.2+ph);
    basis(n,hv,.28*Math.sin(t*Math.PI*2*hz+ph));
    const sCl=m*(1+.06*Math.sin(ph*3.1));pos.copy(n).multiplyScalar(R+bob);sc3.setScalar(sCl);mx.compose(pos,q,sc3);
    for(const im of it.meshes){const bm=im.userData.baseM as any;const tmp=mx.clone().multiply(bm);im.setMatrixAt(k,tmp);}k++;}
   for(const im of it.meshes)im.instanceMatrix.needsUpdate=true;}
  // tier 2
  const cam=s.camPos;let wi=0;
  for(const sk of skins){const sc=sk.school,i=sk.idx,sp=SPC[sk.sp];const p=memberAt(sc,i,t),h=headingAt(sc,i,t);const n=V(p),hv=V(h);
   let lift=.005;if(sk.sp==='whale'){const su=surfacing(sc,t);const hh=sp.size_m*m*.1;lift=-hh+su*hh*1.2+.01*Math.sin(t*.6+i);}
   else if(sk.sp==='manta')lift=.004+.003*Math.sin(t*.8+sc.phase+i);else if(sk.sp==='turtle')lift=.003;
   const dist=cam?cam.distanceTo(world.copy(n).multiplyScalar(R))/m:0;sk.dist=dist;const useFar=!!cam&&dist>sp.lod_near_to_far_m;
   const obj=useFar?sk.far:sk.near;sk.near.visible=!useFar;sk.far.visible=useFar;place(obj,n,hv,lift,m);if(!useFar){obj.position.copy(n).multiplyScalar(R+lift);}
   if(sk.mixer&&!useFar){const cr=Math.max(.3,Math.min(2.5,Math.abs(sc.speed)*Math.max(.5,sc.radius*R/m)/Math.max(.1,sp.cruise_mps)));sk.mixer.update(dt*cr);}
   if(sk.sp==='whale'&&spout[wi]){const su=surfacing(sc,t);const g=spout[wi++];const pa=g.p.geometry.attributes.position as any;const base=n.clone().multiplyScalar(R+sp.size_m*m*.12).addScaledVector(hv,sp.size_m*m*.27);
    for(let qd=0;qd<g.spN;qd++){const f=qd/g.spN;const rise=su*(.15+.5*f)*sp.size_m*m*.5;const sp2=su*Math.sin(qd*2.4+t*4)*.05*sp.size_m*m;pa.setXYZ(qd,base.x+n.x*rise+hv.x*sp2,base.y+n.y*rise+hv.y*sp2,base.z+n.z*rise+hv.z*sp2);}pa.needsUpdate=true;(g.p.material as any).opacity=Math.min(.85,su*1.2);}}
  const pcA=pg.attributes.color as any;let lit=0;for(let i=0;i<nP;i++){const gl=planktonGlow(data.plankton[i].p,t,s.night);if(gl>.05)lit++;pc[i*3]=.2*gl;pc[i*3+1]=1*gl;pc[i*3+2]=.78*gl;}pcA.needsUpdate=true;near=lit;}
 let near=0;
 /** Nearest ocean life to a unit-sphere point: kind for creature_notices (fish / whale surfacing) and distance in metres. */
 function nearest(n:number[],t:number){let best:{kind:string;species:string;m:number}|null=null;const a=V(n);for(const sc of data.schools){const p=memberAt(sc,0,t);const d=Math.acos(Math.max(-1,Math.min(1,a.x*p[0]+a.y*p[1]+a.z*p[2])))*R/m;
   const kind=sc.kind==='whale'?(surfacing(sc,t)>.5?'whale':'whale_deep'):sc.kind==='fish'?'fish':sc.kind;if(!best||d<best.m)best={kind,species:sc.species,m:d};}return best;}
 /** True when open water is within `rad` radians of n (a shoreline). */
 function shoreNear(n:number[],rad=.07){const a=V(n);const up=Math.abs(a.y)>.95?new THREE.Vector3(1,0,0):new THREE.Vector3(0,1,0);const e1=new THREE.Vector3().crossVectors(up,a).normalize(),e2=new THREE.Vector3().crossVectors(a,e1);for(let k=0;k<8;k++){const ang=k*Math.PI/4;const v=a.clone().addScaledVector(e1,Math.cos(ang)*rad).addScaledVector(e2,Math.sin(ang)*rad).normalize();if(o.isWater([v.x,v.y,v.z]))return true;}return false;}
 /** Camera framing for one school at time t: member 0's unit position and heading, the species, its size in units and the school radius in units. */
 function view(sc:any,t:number){const sp=SPC[sc.species];return {n:memberAt(sc,0,t),h:headingAt(sc,0,t),species:sc.species,kind:sc.kind,sizeU:sp.size_m*m,radiusU:sc.radius*R,sizeM:sp.size_m};}
 return {data,group,update,nearest,shoreNear,view,ready,state:()=>({label:data.label,pack:'Cosmo ocean-life pack v1',species:{...counts},schools:data.schools.length,fish:(counts.fish_a||0)+(counts.fish_b||0)+(counts.fish_c||0),rays:counts.manta||0,whales:counts.whale||0,plankton:nP,lit:near,loadedSpecies:loaded,instanced:insts.reduce((a,it)=>a+it.meshes.length,0),skinned:skins.length,failed}),
  dispose:()=>{scene.remove(group);pg.dispose();dot.dispose();for(const it of insts)for(const im of it.meshes)im.dispose();for(const sk of skins)sk.mixer.stopAllAction();}};}
