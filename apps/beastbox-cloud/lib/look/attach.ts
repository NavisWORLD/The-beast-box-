// Mount the Genesis look. Classic objects stay in the scene; they are hidden only while Genesis is selected.
// The anchor is the first scene child so that hide runs before the classic ground is drawn.
// Motion reads the shared world clock. No second clock, no unseeded draws, no beast or traveler writes.
import {currentLook,usesGenesisBase} from './look-mode.ts';
import {budgetFor,considerDrop,presentationTier,type Tier} from './tiers.ts';
import {buildTerrainLod} from './terrain-lod.ts';
import {createTerrainMaterial} from './terrain-material.ts';
import {buildWater,createWaterMaterial,shoreSurface,syncWater,WATER_LABEL} from './water.ts';
import {createSkyDome,syncSky,type SunSample} from './sky-dome.ts';
import {genesisPoints} from './speckle.ts';
import {buildFoliage,syncFoliage} from './foliage.ts';
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
 getTier?:()=>string;
 onTier?:(tier:string)=>void;
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

const WATER_SPAN:Record<string,number>={LOW:140,MED:220,HIGH:340,GOD:480};

export function attachGenesisLook(THREE:typeof import('three'),scene:{add:(o:any)=>void;children?:any[]},opts:Opts){
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
 let foliage:ReturnType<typeof buildFoliage>|null=null;
 let pick:Tier=(opts.tier as Tier)||presentationTier(null,{phone:!!opts.phone,softGL:!!opts.softGL});
 let live:Tier=pick;
  const frames:number[]=[];
 let lastNow=0;
 const concealed=new Map<any,boolean>();
 const lightsBefore=()=>0;
 const sunV=new THREE.Vector3();
 const invQ=new THREE.Quaternion();

 function lead(){
  const list=scene.children;
  if(!list)return;
  const i=list.indexOf(anchor);
  if(i>0){list.splice(i,1);list.unshift(anchor);}
 }
 lead();

 function disposeObject(o:any){
  o.geometry?.dispose?.();
  const m=o.material;
  if(Array.isArray(m))m.forEach((x:any)=>x.dispose?.());
  else m?.dispose?.();
 }
 function invalidate(){
  built=false;
  for(const o of [...group.children]){group.remove(o);disposeObject(o);}
  terrain=null;water=null;sky=null;stars=null;foliage=null;
 }

 function build(){
  if(built)return;
  built=true;
  const shore=shoreSurface(opts.heightAt,opts.seed||'genesis');
  const lod=buildTerrainLod(THREE,{heightAt:opts.heightAt,tier:live,seed:opts.seed||'genesis',waterLevel:shore.coeff});
  terrain=createTerrainMaterial(THREE,shore.coeff);
  const mesh=new THREE.Mesh(lod.geometry,terrain.material);
  mesh.name='genesis-terrain';mesh.frustumCulled=false;mesh.renderOrder=-8;group.add(mesh);
  const wet=buildWater(THREE,{heightAt:opts.heightAt,waterLevel:shore.coeff,surface:shore.at,tier:live,span:WATER_SPAN[live]||220});
  water=createWaterMaterial(THREE,shore.coeff);
  const wmesh=new THREE.Mesh(wet.geometry,water.material);
  wmesh.name='genesis-water';wmesh.userData.label=WATER_LABEL;wmesh.frustumCulled=false;wmesh.renderOrder=2;group.add(wmesh);
  foliage=buildFoliage(THREE,{heightAt:opts.heightAt,shoreAt:shore.at,tier:live,seed:opts.seed||'genesis'});
  group.add(foliage.grass);group.add(foliage.trees);
  sky=createSkyDome(THREE,{dir:[0,1,0],day:1,sky:{zenith:[.2,.45,.75],horizon:[.62,.78,.9],starAlpha:0}},{sunElevationDeg:40,exposure:.85});
  group.add(sky.dome);
  stars=starField(THREE,opts.seed||'genesis');
  group.add(stars);
  group.userData.tris=lod.tris;
  group.userData.creature=CREATURE_MOTION;
  group.userData.tier=live;
 }

 function concealClassic(){
  for(const obj of opts.classicRoots?.()||[]){
   if(!obj)continue;
   if(!concealed.has(obj))concealed.set(obj,obj.visible!==false);
   obj.visible=false;
  }
 }
 function revealClassic(){
  for(const [obj,vis] of concealed)obj.visible=vis;
  concealed.clear();
 }

 function applyQuality(on:boolean){
  const r=opts.renderer,sun=opts.sun,cap=budgetFor(live);
  if(r){
   if(on&&!dprOn){classicDpr=r.getPixelRatio();r.setPixelRatio(Math.min(opts.dpr??classicDpr,cap.dpr));dprOn=true;}
   else if(!on&&dprOn){r.setPixelRatio(classicDpr);dprOn=false;}
  }
  if(sun){
   if(on&&!shadowSaved){
    shadowSaved={w:sun.shadow.mapSize.x,h:sun.shadow.mapSize.y,on:sun.castShadow};
    if(cap.shadow<=0)sun.castShadow=false;
    else{sun.castShadow=true;sun.shadow.mapSize.set(cap.shadow,cap.shadow);sun.shadow.map?.dispose?.();}
   }else if(on&&shadowSaved&&sun.shadow.mapSize.x!==cap.shadow){
    if(cap.shadow<=0)sun.castShadow=false;
    else{sun.castShadow=true;sun.shadow.mapSize.set(cap.shadow,cap.shadow);sun.shadow.map?.dispose?.();}
   }else if(!on&&shadowSaved){
    sun.castShadow=shadowSaved.on;sun.shadow.mapSize.set(shadowSaved.w,shadowSaved.h);shadowSaved=null;
   }
  }
 }

 function sampleFrames(now:number){
  if(lastNow>0){
   const dt=now-lastNow;
   if(dt>0&&dt<250)frames.push(dt);
  }
  lastNow=now;
  const step=considerDrop(live,pick,frames);
  if(!step.consumed)return;
  frames.length=0;
  if(step.tier!==live){
   live=step.tier;pick=live;
   if(dprOn&&opts.renderer)opts.renderer.setPixelRatio(Math.min(opts.dpr??classicDpr,budgetFor(live).dpr));
   opts.onTier?.(live);invalidate();
  }
 }

 function sync(){
  lead();
  const chosen=(opts.getTier?.()||pick) as Tier;
  if(chosen!==pick){
   pick=chosen;live=chosen;
   if(dprOn&&opts.renderer)opts.renderer.setPixelRatio(Math.min(opts.dpr??classicDpr,budgetFor(live).dpr));
   invalidate();
  }
  const look=usesGenesisBase(opts.getLook?opts.getLook():currentLook()); // Park draws this same ground, then grades it (lib/look/park.ts)
  anchor.visible=true;
  if(!look){group.visible=false;applyQuality(false);revealClassic();return;}
  build();
  group.visible=true;
  applyQuality(true);
  const follow=opts.follow?.();
  // Orbit and the other non-ground views leave the classic ground hidden. Genesis is that ground's picture, so it stays hidden with it.
  if(follow&&follow.visible===false){group.visible=false;applyQuality(false);revealClassic();return;}
  concealClassic();
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
  if(stars){(stars.material as {opacity:number}).opacity=+(sun.sky?.starAlpha||0);}
  if(terrain){
   terrain.uniforms.uSun.value.copy(sunV);
   terrain.uniforms.uDay.value=sun.day??1;
   terrain.uniforms.uHazePhase.value=frame.hazePhase;
   terrain.uniforms.uZen.value.setRGB(sun.sky?.zenith?.[0]??.16,sun.sky?.zenith?.[1]??.36,sun.sky?.zenith?.[2]??.64);
   terrain.uniforms.uMotion.value=frame.reduced?0:1;
   const tint=sky?sky.uniforms.uHor.value:null;
   if(tint)terrain.uniforms.uHaze.value.copy(tint);
  }
  if(water){
   syncWater(water.uniforms,frame);
   const wd=sun.dir||[0,1,0];
   water.uniforms.uSun.value.set(wd[0],wd[1],wd[2]);
   water.uniforms.uDay.value=sun.day??1;
   if(sky)water.uniforms.uSky.value.copy(sky.uniforms.uHor.value);
  }
  if(foliage){
   syncFoliage(foliage,frame);
   const day=sun.day??1;
   foliage.grass.material.uniforms.uDay.value=day;
   foliage.trees.material.uniforms.uDay.value=day;
  }
  sampleFrames(now);
  return frame;
 }
 anchor.onBeforeRender=()=>{sync();};
 return {
  anchor,group,get tier(){return live;},sync,creature:CREATURE_MOTION,lightsAdded:lightsBefore(),
  dispose(){
   anchor.onBeforeRender=()=>{};
   const host=scene as {remove?:(o:any)=>void};
   host.remove?.(anchor);host.remove?.(group);
   group.traverse((o:any)=>disposeObject(o));
   anchor.geometry?.dispose?.();(anchor.material as {dispose?:()=>void})?.dispose?.();
  },
 };
}
