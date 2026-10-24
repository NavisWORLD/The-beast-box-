// Landscapes, VIEW layer (SEEDED). Draws the seeded places from lib/universe/seeded-landscapes.mjs: a terrain-following pad, a play ring with
// four ticks, a shelter, rim trees, seats and crystal lamps. Cosmo's look pack (landscape-look-data.mjs) supplies colours; the ENGINE supplies
// every position, size and mode. Nothing here draws a random number or reads a clock (time arrives as the frame's `t`). All art is existing GLBs.
// Honest limits: the pad FOLLOWS the terrain (it cannot flatten the GPU terrain), and the rim blend is colour/alpha only, so there is never a cliff.
import {landscapeSlots,landscapeAnchors,landscapeMode,nightT,lampLevel,LANDSCAPE,pointAt,dirOf,homeLandscapeId,landscapeGoal,angleBetween} from './seeded-landscapes.mjs';
import {nightFactor} from './genesis-sun.mjs';
import {lwStream} from './living-world.mjs';
import {LANDSCAPE_LOOK as LOOK} from './landscape-look-data.mjs';
import {SURFACE_ART,ALIVE_ART} from './surface-three';
type T=typeof import('three');type V3=import('three').Vector3;
const TAU=Math.PI*2;
/** Pad and ring ride a little above the sampled height so the (coarser) GPU terrain mesh never swallows them. World units (0.294 u = 1 m). */
const PAD_LIFT=0.12,RING_LIFT=0.16,HMAX_M=0.9;
const sstep=(a:number,b:number,x:number)=>{const t=Math.min(1,Math.max(0,(x-a)/(b-a)));return t*t*(3-2*t);};
/** pure per-vertex hash in [0,1) (no RNG): same pad, same grain, every load */
export const padHash=(i:number,j:number)=>{const s=Math.sin(i*12.9898+j*78.233)*43758.5453;return s-Math.floor(s);};
/** pad colour at pad-fraction f (Cosmo's rim_lerp: pad to 0.70, rim 0.70-0.88, rim_outer 0.88-1.00); returns rgb linear + alpha */
export function padFrac(f:number){return {toRim:sstep(LOOK.pad.rim_lerp.r_frac_pad_end,LOOK.pad.rim_lerp.r_frac_rim_mid,f),toOuter:sstep(LOOK.pad.rim_lerp.r_frac_rim_mid,LOOK.pad.rim_lerp.r_frac_edge,f),alpha:1-sstep(LOOK.pad.rim_lerp.r_frac_rim_mid,LOOK.pad.rim_lerp.r_frac_edge,f)*1};}
const glbCache=new Map<string,Promise<any>>();
async function loadGLB(url:string){if(!glbCache.has(url))glbCache.set(url,(async()=>{const {GLTFLoader}=await import('three/examples/jsm/loaders/GLTFLoader.js');const g:any=await new GLTFLoader().loadAsync(url);return g.scene;})());return glbCache.get(url)!;}
const TREE_BY_KIND:Record<string,string[]>={court:['olive_meadow_near','teal_round_near'],grove:['teal_round_near','giant_heartwood_near'],sun_court:['olive_meadow_near','olive_meadow_near'],shore_camp:['teal_conifer_near','olive_meadow_near'],shrine:['crystal_leaf_near','purple_glow_near'],garden:['purple_glow_near','olive_meadow_near']};
const TREE_H:Record<string,number>={olive_meadow_near:3.183,teal_round_near:2.845,teal_conifer_near:3.1,crystal_leaf_near:2.213,purple_glow_near:2.49,giant_heartwood_near:11.182};
export type LandscapeEnv={sunDir:V3;storm:number;hasLife:boolean;cam:V3;reduced:boolean};
export type LandscapeOpts={landscapes:any[];R:number;mpu:number;hAt:(v:V3)=>number;phone:boolean;seed:string};
export function addLandscapes(THREE:T,parent:import('three').Object3D,o:LandscapeOpts){
 const {R,mpu,hAt}=o;const root=new THREE.Group();root.name='landscapes';parent.add(root);
 const tmp=new THREE.Vector3(),tn=new THREE.Vector3(),tq=new THREE.Quaternion(),UP=new THREE.Vector3(0,1,0);
 const sp=(d:number[],lift:number,out=new THREE.Vector3())=>{tn.set(d[0],d[1],d[2]).normalize();return out.copy(tn).multiplyScalar(R+hAt(tn)+lift);};
 // Decal surfaces ride the HIGHEST height within ~0.9 m (the GPU terrain mesh is coarser than the height map and would otherwise swallow them in the dips).
 const q1=new THREE.Vector3(),q2=new THREE.Vector3(),q3=new THREE.Vector3();
 const spMax=(d:number[],lift:number,out=new THREE.Vector3())=>{tn.set(d[0],d[1],d[2]).normalize();q1.set(-tn.z,0,tn.x);if(q1.lengthSq()<1e-6)q1.set(1,0,0);q1.normalize();q2.copy(tn).cross(q1);const e=HMAX_M/LANDSCAPE.worldRadiusM;
  let h=hAt(tn);for(const [a,b] of [[1,0],[-1,0],[0,1],[0,-1]]){q3.copy(tn).addScaledVector(q1,a*e).addScaledVector(q2,b*e).normalize();h=Math.max(h,hAt(q3));}
  return out.copy(tn).multiplyScalar(R+h+lift);};
 const col=(hex:string)=>new THREE.Color(hex);
 const items:any[]=[];
 for(const ls of o.landscapes){
  const key=ls.dry&&ls.kind==='court'?'court_dry':ls.kind;const pad=LOOK.pad.by_kind[key]||LOOK.pad.by_kind[ls.kind];const rcfg=LOOK.ring.by_kind[key]||LOOK.ring.by_kind[ls.kind];
  const n=dirOf(ls.lat,ls.lon);const rad=ls.radiusM/LANDSCAPE.worldRadiusM;
  const group=new THREE.Group();group.name='landscape:'+ls.id;root.add(group);const detail=new THREE.Group();group.add(detail);
  // ---- pad: polar grid, vertices on the terrain; colour/alpha follow rim_lerp in LINEAR light (THREE.Color holds linear values)
  const RN=12,SN=40;const pos=new Float32Array(((RN+1)*SN)*3),colv=new Float32Array(((RN+1)*SN)*4),idx:number[]=[];
  const cb=col(pad.base),cd=col(pad.detail),cr=col(pad.rim),co=col(pad.rim_outer),c=new THREE.Color();
  for(let ri=0;ri<=RN;ri++){const f=ri/RN;const pf=padFrac(f);for(let si=0;si<SN;si++){const k=ri*SN+si;const d=ri===0?n:pointAt(n,si/SN*TAU,f*rad);spMax(d,PAD_LIFT,tmp);pos[k*3]=tmp.x;pos[k*3+1]=tmp.y;pos[k*3+2]=tmp.z;
    c.copy(cb).lerp(cd,padHash(ri,si)*LOOK.pad.detail_noise.amount*(1-pf.toRim));c.lerp(cr,pf.toRim);c.lerp(co,pf.toOuter);colv[k*4]=c.r;colv[k*4+1]=c.g;colv[k*4+2]=c.b;colv[k*4+3]=pf.alpha;}}
  for(let ri=0;ri<RN;ri++)for(let si=0;si<SN;si++){const a=ri*SN+si,b=ri*SN+(si+1)%SN,a2=(ri+1)*SN+si,b2=(ri+1)*SN+(si+1)%SN;idx.push(a,a2,b,b,a2,b2);}
  const pg=new THREE.BufferGeometry();pg.setAttribute('position',new THREE.BufferAttribute(pos,3));pg.setAttribute('color',new THREE.BufferAttribute(colv,4));pg.setIndex(idx);
  const padMat=new THREE.MeshBasicMaterial({vertexColors:true,transparent:true,depthWrite:false,side:THREE.DoubleSide,polygonOffset:true,polygonOffsetFactor:-2,polygonOffsetUnits:-2,fog:false});
  const padMesh=new THREE.Mesh(pg,padMat);padMesh.renderOrder=2;padMesh.frustumCulled=false;group.add(padMesh);
  // ---- play ring (inner + outer) and four ticks N/E/S/W (view-layer decal; terrain-following ribbons)
  const rp:number[]=[],rc:number[]=[],ri2:number[]=[];const hw=(LOOK.ring.ring_width_m/2)/LANDSCAPE.worldRadiusM;const ringC=col(rcfg.ring),tickC=(rcfg.ticks as string[]).map(col);
  const pushQ=(pa:number[],pb:number[],cc:any,a:number)=>{const base=rp.length/3;for(const d of [pa,pb]){spMax(d,RING_LIFT,tmp);rp.push(tmp.x,tmp.y,tmp.z);rc.push(cc.r,cc.g,cc.b,a);}return base;};
  const strip=(pts:number[][][],cc:any,a:number,close:boolean)=>{let prev=-1,first=-1;for(const [pa,pb] of pts){const b=pushQ(pa,pb,cc,a);if(prev>=0)ri2.push(prev,prev+1,b,prev+1,b+1,b);else first=b;prev=b;}if(close&&first>=0&&prev>=0)ri2.push(prev,prev+1,first,prev+1,first+1,first);};
  const ringPts=(fr:number)=>Array.from({length:49},(_,i)=>{const b=i/48*TAU;return [pointAt(n,b,Math.max(1e-4,fr*rad-hw)),pointAt(n,b,fr*rad+hw)];});
  const rIn=LOOK.ring.inner_ring_radius_frac,rOut=LOOK.ring.outer_ring_radius_frac;
  strip(ringPts(rIn).slice(0,48),ringC,1,true);strip(ringPts(rOut).slice(0,48),ringC,1,true);
  for(let k=0;k<4;k++){const b=ls.yaw+k*Math.PI/2;const pts=Array.from({length:7},(_,i)=>{const dd=(rIn+(rOut-rIn)*i/6)*rad;const dl=hw/Math.max(dd,1e-3);return [pointAt(n,b-dl,dd),pointAt(n,b+dl,dd)];});strip(pts,tickC[k],LOOK.ring.tick_alpha_mul,false);}
  const rg=new THREE.BufferGeometry();rg.setAttribute('position',new THREE.Float32BufferAttribute(rp,3));rg.setAttribute('color',new THREE.Float32BufferAttribute(rc,4));rg.setIndex(ri2);
  const ringMat=new THREE.MeshBasicMaterial({vertexColors:true,transparent:true,depthWrite:false,side:THREE.DoubleSide,polygonOffset:true,polygonOffsetFactor:-4,polygonOffsetUnits:-4,fog:false});
  const ringMesh=new THREE.Mesh(rg,ringMat);ringMesh.renderOrder=3;ringMesh.frustumCulled=false;detail.add(ringMesh);
  const it:any={ls,n:new THREE.Vector3(n[0],n[1],n[2]),group,detail,padMat,ringMat,pad,lamps:[] as any[],mode:'gather',stormSm:0,stormOn:false,storm_t:0,night_t:0,lampLevel:0,far:false,pieces:0,ready:false,
   cb,cd,pos:sp(landscapeAnchors(ls).lamp,0.9*mpu)};
  // ---- pieces: existing GLBs placed by engine slots (shelter canopy + boulders, rim trees, seats, crystal lamps)
  const put=async(url:string,d:number[],scale:number,yaw:number,into:any,lampMat=false)=>{try{const src=await loadGLB(url);const m=src.clone(true);
    if(lampMat){m.traverse((x:any)=>{if(x.isMesh&&x.material){x.material=x.material.clone();const e=x.material.emissive?x.material.emissive.clone().multiplyScalar(x.material.emissiveIntensity??1):new THREE.Color(0);x.material.emissiveIntensity=1;it.lamps.push({mat:x.material,base:e});}});}
    const p=sp(d,0);m.position.copy(p);tn.copy(p).normalize();tq.setFromUnitVectors(UP,tn);m.quaternion.copy(tq);m.rotateY(yaw);m.scale.setScalar(scale);into.add(m);it.pieces++;}catch(e){/* missing art: skip the piece, the pad still reads */}};
  const slots=landscapeSlots(ls);const an=landscapeAnchors(ls);const tk=TREE_BY_KIND[ls.kind]||TREE_BY_KIND.court;const jy=(i:number)=>ls.yaw*3+i*2.4;
  const tasks:Promise<void>[]=[];
  if(ls.slots.shelter==='canopy'){// a canopy tree with two boulders at its foot
   tasks.push(put(SURFACE_ART+'trees/models/'+tk[0]+'.glb',an.shelter,mpu*1.5,jy(0),group));
   tasks.push(put(ALIVE_ART+'rock_boulder_alive.glb',pointAt(an.shelter,ls.yaw+0.9,0.12*rad),mpu*1.7,jy(1),group));
   tasks.push(put(ALIVE_ART+'rock_boulder_alive.glb',pointAt(an.shelter,ls.yaw-1.1,0.1*rad),mpu*1.3,jy(2),group));
  }else{// stones: four boulders in a horseshoe, no canopy
   for(let i=0;i<4;i++)tasks.push(put(ALIVE_ART+'rock_boulder_alive.glb',pointAt(an.shelter,ls.yaw+(i-1.5)*0.9,0.14*rad),mpu*(2.2+0.4*(i%2)),jy(i),group));
  }
  slots.trees.forEach((d:number[],i:number)=>{const nm=tk[i%tk.length];tasks.push(put(SURFACE_ART+'trees/models/'+nm+'.glb',d,mpu*(0.85+0.3*padHash(ls.lat+i,ls.lon)),jy(3+i),detail));});
  slots.seats.forEach((d:number[],i:number)=>{tasks.push(put(ALIVE_ART+'rock_boulder_alive.glb',d,mpu*1.05,jy(8+i),detail));});
  const LAMPS=['crystal_spire_alive','crystal_cluster_alive','crystal_small_alive'];
  slots.lamps.forEach((d:number[],i:number)=>{tasks.push(put(ALIVE_ART+LAMPS[i%3]+'.glb',d,mpu*1.8,jy(14+i),detail,true));});
  Promise.all(tasks).then(()=>{it.ready=true;});
  // ---- rain (the storm beat): seeded streaks over the pad radius only, none inside the sheltered zone, additive, fading with storm_t. Caps 220 desktop / 90 phone. No new weather system.
  {const RS=LOOK.rain,cap=o.phone?RS.max_instances_phone:RS.max_instances_desktop;const cnt=Math.min(cap,Math.round(RS.density_per_m2_of_pad*Math.PI*ls.radiusM*ls.radiusM));const rr=lwStream(o.seed+':rain:'+ls.id);
   const cull=RS.sheltered_zone.cull_radius_frac_of_pad;const drops:any[]=[];const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.BufferAttribute(new Float32Array(cnt*6),3));
   for(let i=0;i<cnt;i++){const f=cull+(1-cull)*Math.sqrt(rr());const d=pointAt(n,rr()*TAU,f*rad);const S=spMax(d,0,new THREE.Vector3());const up=S.clone().normalize();const sl=new THREE.Vector3().crossVectors(up,UP);if(sl.lengthSq()<1e-6)sl.set(1,0,0);sl.normalize();
    drops.push({S,up,sl,ph:rr(),len:RS.length_m[0]+(RS.length_m[1]-RS.length_m[0])*rr()});}
   const mat=new THREE.LineBasicMaterial({color:new THREE.Color(RS.color_day),transparent:true,opacity:0,depthWrite:false,blending:THREE.AdditiveBlending});
   const lines=new THREE.LineSegments(geo,mat);lines.frustumCulled=false;lines.visible=false;lines.name='rain:'+ls.id;group.add(lines);it.rain={drops,geo,mat,lines,count:cnt,cull};}
  items.push(it);
 }
 // ---- at most 2 real point lights per planet (phone: none, emissive-only), assigned to the nearest lit landscapes each frame
 const lights:any[]=[];if(!o.phone)for(let i=0;i<2;i++){const l=new THREE.PointLight(0xffb35a,0,9*mpu*3,2);root.add(l);lights.push(l);}
 const cPad=new THREE.Color(),cDay=new THREE.Color(),tmpC=new THREE.Color();
 const native=col(LOOK.lamp.crystal_native.native_emissive_hex);
 const snapshot=()=>items.map(it=>({id:it.ls.id,name:it.ls.name,kind:it.ls.kind,mode:it.mode,storm_t:+it.storm_t.toFixed(3),night_t:+it.night_t.toFixed(3),lamp:+it.lampLevel.toFixed(3),far:it.far,pieces:it.pieces,ready:it.ready,rain:it.rain?(it.rain.lines.visible?it.rain.count:0):0,label:it.ls.home_exception?'Home world · place SEEDED':'SEEDED'}));
 function update(t:number,dt:number,env:LandscapeEnv){
  const lit:any[]=[];
  for(const it of items){
   const ins=it.n.dot(env.sunDir);
   // storm weight: time-smoothed (in 1.5 s, out 3.5 s) with hysteresis 0.45/0.55 so a flickering tension never pops the mode
   const tau=env.storm>it.stormSm?LOOK.crossfade.mode_weight_smoothing_s.storm_in:LOOK.crossfade.mode_weight_smoothing_s.storm_out;it.stormSm+=(env.storm-it.stormSm)*(1-Math.exp(-dt/Math.max(0.05,tau)));
   if(!it.stormOn&&it.stormSm>0.55)it.stormOn=true;else if(it.stormOn&&it.stormSm<0.45)it.stormOn=false;
   it.storm_t=sstep(0.40,0.60,it.stormSm);it.night_t=nightT(ins);
   it.mode=landscapeMode(it.ls,{ins,storm:it.stormOn?1:0,hasLife:env.hasLife});
   // pad grade: golden dusk, then the night grade, then the wet grade (all mix in linear light)
   const p=it.pad;cDay.copy(it.cb);cPad.copy(it.cb);const dw=LOOK.crossfade.golden_dusk.max_mix*Math.exp(-Math.pow((ins-LOOK.crossfade.golden_dusk.peak_ins)/LOOK.crossfade.golden_dusk.width,2));
   cPad.lerp(tmpC.set(LOOK.crossfade.golden_dusk.tint),dw);cPad.lerp(tmpC.set(p.night.base),it.night_t);cPad.lerp(tmpC.set(p.moisture_darken.wet_base),it.storm_t*(1-it.night_t*0.5));if(it.mode==='empty')cPad.lerp(tmpC.set(p.by_mode.empty),1);
   it.padMat.color.setRGB(Math.min(2,cPad.r/Math.max(1e-3,cDay.r)),Math.min(2,cPad.g/Math.max(1e-3,cDay.g)),Math.min(2,cPad.b/Math.max(1e-3,cDay.b)));
   // ring alpha by mode (gather<->sleep by night_t, shelter by storm_t, empty on its own)
   const A=LOOK.ring.alpha_by_mode;let a=A.gather+(A.sleep-A.gather)*it.night_t;a+=(A.shelter-a)*it.storm_t;if(it.mode==='empty')a=A.empty;it.ringMat.opacity=a;
   // rain streaks follow storm_t (already time-smoothed 1.5 s in / 3.5 s out); wet only while the mode is the storm shelter
   if(it.rain){const RS=LOOK.rain,R_=it.rain;const on=it.storm_t>0.01&&!it.far&&it.mode!=='empty';R_.lines.visible=on;
    if(on){const al=RS.alpha_range[0]+(RS.alpha_range[1]-RS.alpha_range[0])*0.5,aln=RS.alpha_range_night[0]+(RS.alpha_range_night[1]-RS.alpha_range_night[0])*0.5;R_.mat.opacity=it.storm_t*(al+(aln-al)*it.night_t);R_.mat.color.set(RS.color_day).lerp(tmpC.set(RS.color_night),it.night_t);
     const H=RS.height_above_pad_m,v=RS.fall_speed_m_s*(env.reduced?0.3:1),tn_=Math.tan(RS.slant_deg*Math.PI/180);const a=R_.geo.attributes.position.array as Float32Array;
     R_.drops.forEach((d:any,k:number)=>{const y=H-((t*v+d.ph*H)%H);const y2=y+d.len;a[k*6]=d.S.x+d.up.x*y*mpu;a[k*6+1]=d.S.y+d.up.y*y*mpu;a[k*6+2]=d.S.z+d.up.z*y*mpu;
      const s2=y2*mpu;a[k*6+3]=d.S.x+d.up.x*s2+d.sl.x*(y2-y)*tn_*mpu;a[k*6+4]=d.S.y+d.up.y*s2+d.sl.y*(y2-y)*tn_*mpu;a[k*6+5]=d.S.z+d.up.z*s2+d.sl.z*(y2-y)*tn_*mpu;});
     R_.geo.attributes.position.needsUpdate=true;}}
   // far LOD: pad + shelter only (rim trees, seats, lamps and ring drop)
   const d=env.cam.distanceTo(it.pos);it.far=d>LOOK_FAR_M*mpu;it.detail.visible=!it.far;
   // lamps: spec s4 emissive = lin(hex) x peak x nightFactor x lifeVolume x mode factor, with the documented storm deviation inside lampLevel()
   const nf=nightFactor(ins);const LIFE=0.6;const lvl=lampLevel({nightFactor:nf,storm_t:it.storm_t,lifeVolume:LIFE,mode:it.mode});it.lampLevel=lvl;
   const lm=LOOK.lamp;const hex=lm.by_mode[it.mode]?.emissive_hex||'#2B2140';const wm=lm.warm_mix_by_mode[it.mode]??0;const fl=env.reduced?0:lm.point_light.flicker.amp*Math.sin(TAU*(t/lm.point_light.flicker.period_s));
   tmpC.copy(native).lerp(new THREE.Color(hex),wm).multiplyScalar(lm.peak_linear*lvl*(1+fl));
   for(const L of it.lamps){L.mat.emissive.copy(L.base).add(tmpC);}
   if(lvl>0.02&&!it.far)lit.push({it,d,lvl,hex});
  }
  lit.sort((a,b)=>a.d-b.d);
  lights.forEach((l,i)=>{const e=lit[i];if(!e){l.intensity=0;return;}const pl=LOOK.lamp.point_light;l.position.copy(e.it.pos);l.color.set(pl.color[e.it.mode]||'#FFB35A');
   l.distance=Math.min(9,Math.max(5,0.9*e.it.ls.radiusM))*mpu;const pm=Math.max(0.05,LANDSCAPE.mix[e.it.mode]||0.05);l.intensity=(pl.intensity[e.it.mode]||0)*(e.lvl/pm)*mpu*mpu*4;});
 }

 /** The roam goal for one resident right now (null when its home place is empty or not here). */
 const goalCache:Record<string,any>={};
 function goalFor(key:string,seed:string){const it=items.find(x=>x.ls.id===homeLandscapeId(seed,key,items.map(y=>y.ls)));if(!it)return null;const ck=it.ls.id+'|'+key+'|'+it.mode;if(!(ck in goalCache))goalCache[ck]=landscapeGoal(it.ls,it.mode,key,seed);const g=goalCache[ck];return g?{...g,mode:it.mode,id:it.ls.id}:null;}
 /** A tap on the ground (unit direction): the landscape whose pad it falls inside, else null. */
 function tapAt(d:number[]){for(const it of items){const rad=it.ls.radiusM/LANDSCAPE.worldRadiusM;if(angleBetween(it.n.toArray(),d)<=rad*1.05)return it.ls;}return null;}
 /** Mode of a landscape now (for notices and zoom lines). */
 const modeOf=(id:string)=>items.find(x=>x.ls.id===id)?.mode??null;
 const LOOK_FAR_M=90;
 /** Test/inspection camera: hover `up` metres over the first landscape's play anchor and `back` metres behind it (bearing `by`), looking at the ring centre. Only used when asked (window.__lwLandCam). */
 function inspectCam(camera:any,c:{up:number;back:number;by?:number}){const it=items[0];if(!it)return;const ls=it.ls;const rad=ls.radiusM/LANDSCAPE.worldRadiusM;const dd=pointAt(dirOf(ls.lat,ls.lon),ls.yaw+(c.by||0),Math.min(1.2,c.back/LANDSCAPE.worldRadiusM));
  const base=sp(dirOf(ls.lat,ls.lon),0);const nrm=base.clone().normalize();const cp=sp(dd,c.up*mpu);camera.position.copy(cp);camera.up.copy(nrm);camera.lookAt(base);camera.near=0.02;camera.updateProjectionMatrix();void rad;}
 return {update,items,snapshot,inspectCam,goalFor,tapAt,modeOf,group:root,dispose(){root.traverse((x:any)=>{x.geometry?.dispose?.();});parent.remove(root);}};
}
