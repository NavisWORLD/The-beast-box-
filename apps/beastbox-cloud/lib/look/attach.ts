// Mount the Genesis look. Classic objects stay in the scene; they are hidden only while Genesis is selected.
// Motion reads the shared world clock. No second clock, no unseeded draws, no beast or traveler writes.
import {currentLook} from './look-mode.ts';
import {budgetFor,presentationTier,type Tier} from './tiers.ts';
import {buildTerrainLod} from './terrain-lod.ts';
import {createTerrainMaterial} from './terrain-material.ts';
import {buildWater,createWaterMaterial,shoreSurface,syncWater,WATER_LABEL} from './water.ts';
import {createSkyDome,syncSky,type SunSample} from './sky-dome.ts';
import {genesisPoints} from './speckle.ts';
import {CREATURE_MOTION,motionAt,presentationTick} from './motion.ts';
import {stream01} from './seed.ts';
import {currentWorldClock} from '../world/one-world-clock.mjs';
import {lightRigFor} from '../universe/sky-view.mjs';

export {WATER_LABEL,CREATURE_MOTION};

type Sun = SunSample & {dir?:number[]};
type Opts={
 seed?:string;
 tier?:string;
 phone?:boolean;
 softGL?:boolean;
 heightAt:(x:number,z:number)=>number;
 reduced?:()=>boolean;
 nowMs?:()=>number;
 readTick?:()=>number;
 getLook?:()=>string;
 getSun?:()=>Sun;
 camera?:()=>{position:{x:number;y:number;z:number}}|null;
 follow?:()=>{position:any;quaternion:any;visible?:boolean}|null;
 classicRoots?:()=>any[];
 renderer?:{getPixelRatio():number;setPixelRatio(n:number):void};
 sun?:{castShadow:boolean;shadow:{mapSize:{x:number;y:number;set:(w:number,h:number)=>void};map?:{dispose?:()=>void}|null}};
 dpr?:number;
};

function worldTick(read?:()=>number){
 if(read)return read();
 const u=currentWorldClock()?.get?.();
 return typeof u?.tick==='number'?u.tick:0;
}

function starField(THREE:typeof import('three'),seed:string){
 const n=280,p=new Float32Array(n*3),R=340;
 for(let i=0;i<n;i++){
  const z=stream01(seed+':star:z:'+i)*2-1;
  const a=stream01(seed+':star:a:'+i)*Math.PI*2;
  const s=Math.sqrt(Math.max(0,1-z*z));
  p[i*3]=s*Math.cos(a)*R;p[i*3+1]=z*R;p[i*3+2]=s*Math.sin(a)*R;
 }
 const g=new THREE.BufferGeometry();
 g.setAttribute('position',new THREE.Float32BufferAttribute(p,3));
 const mat=genesisPoints(THREE,0xd7e4ff,1.6);
 const pts=new THREE.Points(g,mat);
 pts.name='genesis-stars';pts.frustumCulled=false;
 return pts;
}

const WATER_SPAN:Record<string,number>={LOW:110,MED:170,HIGH:260,GOD:380};

export function attachGenesisLook(THREE:typeof import('three'),scene:{add:(o:any)=>void},opts:Opts){
 const group=new THREE.Group();group.name='genesis-look';
 const anchor=new THREE.Mesh(new THREE.PlaneGeometry(.001,.001),new THREE.MeshBasicMaterial({transparent:true,opacity:0,depthWrite:false}));
 anchor.name='genesis-anchor';anchor.frustumCulled=false;anchor.renderOrder=-100;
 scene.add(anchor);scene.add(group);
 let built=false,seenTick=0,changedAt=0,dprOn=false,classicDpr=1;
 let shadowSaved:{w:number;h:number;on:boolean}|null=null;
 let terrain:ReturnType<typeof createTerrainMaterial>|null=null;
 let water:ReturnType<typeof createWaterMaterial>|null=null;
 let sky:ReturnType<typeof createSkyDome>|null=null;
 let stars:ReturnType<typeof starField>|null=null;
 const tier:Tier=(opts.tier as Tier)||presentationTier(null,{phone:!!opts.phone,softGL:!!opts.softGL});
 const lightsBefore=()=>0;
 const sunV=new THREE.Vector3();
 const invQ=new THREE.Quaternion();

 function build(){
  if(built)return;
  built=true;
  const shore=shoreSurface(opts.heightAt);
  const lod=buildTerrainLod(THREE,{heightAt:opts.heightAt,tier,seed:opts.seed||'genesis',waterLevel:shore.coeff});
  terrain=createTerrainMaterial(THREE,shore.coeff);
  const mesh=new THREE.Mesh(lod.geometry,terrain.material);
  mesh.name='genesis-terrain';mesh.frustumCulled=false;group.add(mesh);
  const wet=buildWater(THREE,{heightAt:opts.heightAt,waterLevel:shore.coeff,surface:shore.at,tier,span:WATER_SPAN[tier]||170});
  water=createWaterMaterial(THREE,shore.coeff);
  const wmesh=new THREE.Mesh(wet.geometry,water.material);
  wmesh.name='genesis-water';wmesh.userData.label=WATER_LABEL;wmesh.frustumCulled=false;wmesh.renderOrder=2;group.add(wmesh);
  sky=createSkyDome(THREE,{dir:[0,1,0],day:1,sky:{zenith:[.2,.45,.75],horizon:[.62,.78,.9],starAlpha:0}},{sunElevationDeg:40,exposure:.85});
  group.add(sky.dome);
  stars=starField(THREE,opts.seed||'genesis');
  group.add(stars);
  group.userData.tris=lod.tris;
  group.userData.creature=CREATURE_MOTION;
 }

 function applyQuality(on:boolean){
  const r=opts.renderer,sun=opts.sun,cap=budgetFor(tier);
  if(r){
   if(on&&!dprOn){classicDpr=r.getPixelRatio();r.setPixelRatio(Math.min(opts.dpr??classicDpr,cap.dpr));dprOn=true;}
   else if(!on&&dprOn){r.setPixelRatio(classicDpr);dprOn=false;}
  }
  if(sun){
   if(on&&!shadowSaved){
    shadowSaved={w:sun.shadow.mapSize.x,h:sun.shadow.mapSize.y,on:sun.castShadow};
    if(cap.shadow<=0)sun.castShadow=false;
    else{sun.castShadow=true;sun.shadow.mapSize.set(cap.shadow,cap.shadow);sun.shadow.map?.dispose?.();}
   }else if(!on&&shadowSaved){
    sun.castShadow=shadowSaved.on;sun.shadow.mapSize.set(shadowSaved.w,shadowSaved.h);shadowSaved=null;
   }
  }
 }

 function sync(){
  const look=(opts.getLook?opts.getLook():currentLook())==='genesis';
  anchor.visible=true;
  if(!look){group.visible=false;applyQuality(false);return;}
  build();
  group.visible=true;
  applyQuality(true);
  const follow=opts.follow?.();
  // Orbit and the other non-ground views leave the classic ground hidden. Genesis is that ground's picture, so it stays hidden with it.
  if(follow&&follow.visible===false){group.visible=false;applyQuality(false);return;}
  for(const obj of opts.classicRoots?.()||[]){if(obj)obj.visible=false;}
  if(follow){group.position.copy(follow.position);group.quaternion.copy(follow.quaternion);}
  group.updateMatrixWorld();
  const cam=opts.camera?.();
  if(cam&&sky){sky.dome.position.set(cam.position.x,cam.position.y,cam.position.z);group.worldToLocal(sky.dome.position);}
  const reduced=!!opts.reduced?.();
  const now=opts.nowMs?.()??0;
  const tick=worldTick(opts.readTick);
  if(tick!==seenTick){seenTick=tick;changedAt=now;}
  const frame=motionAt(opts.seed||'genesis',presentationTick(tick,now,changedAt,reduced),reduced);
  const sun=opts.getSun?.()||{dir:[0,1,0],day:1,elevationDeg:45,sky:{zenith:[.18,.4,.7],horizon:[.62,.78,.9],starAlpha:0}};
  const rig=lightRigFor({day:sun.day??1,elevationDeg:sun.elevationDeg??0,sky:sun.sky});
  const d=sun.dir||[0,1,0];
  group.getWorldQuaternion(invQ).invert();
  sunV.set(d[0],d[1],d[2]).applyQuaternion(invQ);
  if(sky)syncSky(sky.uniforms,{...sun,dir:[sunV.x,sunV.y,sunV.z]},rig,frame);
  if(stars){(stars.material as {opacity:number}).opacity=reduced?+(sun.sky?.starAlpha||0):+(sun.sky?.starAlpha||0);}
  if(terrain){
   terrain.uniforms.uSun.value.copy(sunV);
   terrain.uniforms.uDay.value=sun.day??1;
   terrain.uniforms.uHazePhase.value=frame.hazePhase;
   terrain.uniforms.uMotion.value=frame.reduced?0:1;
   const tint=sky?sky.uniforms.uHor.value:null;
   if(tint)terrain.uniforms.uHaze.value.copy(tint);
  }
  if(water){
   syncWater(water.uniforms,frame);
   const d=sun.dir||[0,1,0];
   water.uniforms.uSun.value.set(d[0],d[1],d[2]);
   water.uniforms.uDay.value=sun.day??1;
   if(sky)water.uniforms.uSky.value.copy(sky.uniforms.uHor.value);
  }
  return frame;
 }
 anchor.onBeforeRender=()=>{sync();};
 return {
  anchor,group,tier,sync,creature:CREATURE_MOTION,lightsAdded:lightsBefore(),
  dispose(){
   anchor.onBeforeRender=()=>{};
   const host=scene as {remove?:(o:any)=>void};
   host.remove?.(anchor);host.remove?.(group);
   group.traverse((o:any)=>{o.geometry?.dispose?.();const m=o.material;if(Array.isArray(m))m.forEach((x:any)=>x.dispose?.());else m?.dispose?.();});
   anchor.geometry?.dispose?.();(anchor.material as {dispose?:()=>void})?.dispose?.();
  },
 };
}
