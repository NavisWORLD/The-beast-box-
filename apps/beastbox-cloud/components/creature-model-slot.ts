/**
 * Runtime for the creature model slot. loadCreatureModel(THREE, id) resolves to null unless the manifest
 * lists the id AND its rig json validates AND the GLB loads, so the caller keeps its sprite (or sculpted body)
 * in every other case. On success it returns a root scaled to the rig's real height, a drive() that plays the
 * rig's clips from speed/mood, and dispose(). It never invents motion: a model with no clips just stands.
 */
import {MODEL_SLOT_BASE,resolveModelEntry,validateRig,pickClipName,fitScale,roleFor,CLIP_ROLES,withinBudget,budgetFor} from '../lib/creatures3d/creature-model-slot.mjs';
import {isNodeRig,nodeRigPose,applyActionMultipliers,ROLE_TO_ACTION} from '../lib/creatures3d/node-rig.mjs';
type Three=typeof import('three');
let manifestP:Promise<any>|null=null;
const getManifest=(base:string)=>manifestP||(manifestP=fetch(base+'manifest.json').then(r=>r.ok?r.json():null).catch(()=>null));
export type SlotLife={speed?:number;sleep?:number;startle?:number;joy?:number};
export type SlotModel={root:any;id:string;role:()=>string;honesty:string;rig:any;drive:(dt:number,life?:SlotLife)=>void;dispose:()=>void};
/** Test seam: the manifest cache is per page; tests reset it. */
export function _resetModelSlot(){manifestP=null;}
export type SlotOpts={low?:boolean;targetH?:number;base?:string;phone?:boolean;variant?:string;loadGltf?:null|((url:string)=>Promise<any>)};
/** phone: true keeps heavy and over-budget models out (the sprite stays); variant picks a species entry from the manifest (wisps). */
export async function loadCreatureModel(THREE:Three,id:string,{low=false,targetH=1,base=MODEL_SLOT_BASE,phone=false,variant='',loadGltf=null}:SlotOpts={}):Promise<SlotModel|null>{
 try{
  const entry=resolveModelEntry(await getManifest(base),id,base);if(!entry)return null;
  if(phone&&entry.tier==='heavy'){return null;}
  if(!withinBudget({bytes:entry.bytes,tris:entry.tris},phone)){console.warn('creature-model-slot: '+id+' is over the '+(phone?'phone':'device')+' size budget, keeping the sprite');return null;}
  const rig0=await fetch(entry.rig).then(r=>r.ok?r.json():null).catch(()=>null);
  const v=validateRig(rig0,id);if(!v.ok){console.warn('creature-model-slot: rig rejected for '+id+': '+v.errors.join('; '));return null;}
  const vr=variant&&entry.variants?entry.variants[variant]||null:null;
  const rig=vr&&isNodeRig(rig0)?applyActionMultipliers(rig0,vr.action_multipliers||{}):rig0;
  const load=loadGltf||(async(url:string)=>{const buf=await fetch(url).then(r=>r.ok?r.arrayBuffer():null);if(!buf)throw new Error('model download failed');
   if(buf.byteLength>budgetFor(phone).bytes)throw new Error('model is '+buf.byteLength+' bytes, over the '+budgetFor(phone).bytes+' budget');
   const {GLTFLoader}=await import('three/examples/jsm/loaders/GLTFLoader.js');const {MeshoptDecoder}=await import('three/examples/jsm/libs/meshopt_decoder.module.js');const l=new GLTFLoader();l.setMeshoptDecoder(MeshoptDecoder);return l.parseAsync(buf,url.slice(0,url.lastIndexOf('/')+1));});
  const gltf=await load(low&&entry.glbLow?entry.glbLow:entry.glb);const model=gltf.scene;model.name='slot-'+id;
  const holder=new THREE.Group();holder.name='slot-holder-'+id;holder.add(model);
  const bb=new THREE.Box3().setFromObject(model);const measured=bb.max.y-bb.min.y;
  // The rig states the real height; the measured box is only used to put the feet on y=0 and to scale to the caller's target.
  const k=fitScale(Number.isFinite(measured)&&measured>1e-6?measured:rig.height_m,targetH);
  model.scale.multiplyScalar(k);model.position.y=-(Number.isFinite(bb.min.y)?bb.min.y:0)*k;
  model.traverse((o:any)=>{if(o.isMesh){o.castShadow=true;o.frustumCulled=false;}});
  if(vr&&vr.materials)model.traverse((o:any)=>{if(!o.isMesh)return;for(const m of (Array.isArray(o.material)?o.material:[o.material])){const ov=m&&vr.materials[m.name];if(!ov)continue;
   if(ov.baseColorFactor)m.color.setRGB(ov.baseColorFactor[0],ov.baseColorFactor[1],ov.baseColorFactor[2],THREE.LinearSRGBColorSpace);
   if(ov.emissiveFactor)m.emissive.setRGB(ov.emissiveFactor[0],ov.emissiveFactor[1],ov.emissiveFactor[2],THREE.LinearSRGBColorSpace);
   if(Number.isFinite(ov.emissive_intensity))m.emissiveIntensity=ov.emissive_intensity;}});
  const dispose=()=>{mixer?.stopAllAction();model.traverse((o:any)=>{if(o.isMesh){o.geometry?.dispose();(Array.isArray(o.material)?o.material:[o.material]).forEach((m:any)=>{m?.map?.dispose?.();m?.dispose?.();});}});};
  let mixer:any=null;let curRole='idle';
  if(isNodeRig(rig)){
   // Light chars3d model: no baked clips. Node transforms are driven from the rig json (idle, blink, walk, hop, wave, sleep).
   const N:Record<string,any>={},REST:Record<string,any>={};
   model.traverse((o:any)=>{if(o.name&&!N[o.name]){N[o.name]=o;REST[o.name]={p:o.position.clone(),q:o.quaternion.clone(),s:o.scale.clone()};}});
   let t=0,act='idle',w=1,sleepT=0;const qa=new THREE.Quaternion(),ax=new THREE.Vector3();const sleepEnter=(rig.actions.sleep&&rig.actions.sleep.enter_s)||1.4;
   return {root:holder,id,rig,honesty:rig.honesty,role:()=>curRole,
    drive(dt,life={}){curRole=roleFor(life);const want=(ROLE_TO_ACTION as any)[curRole]||'idle';if(want!==act){act=want;w=0;sleepT=0;}
     t+=Math.max(0,Math.min(dt,.25));w=Math.min(1,w+dt/.25);if(act==='sleep')sleepT+=dt;
     const pose=nodeRigPose(rig,t,{action:act,w,sleepK:sleepT/sleepEnter});
     for(const name in N){const n=N[name],r=REST[name];n.position.copy(r.p);n.quaternion.copy(r.q);n.scale.copy(r.s);}
     for(const name in pose.nodes){const n=N[name];if(!n)continue;const d=pose.nodes[name],r=REST[name];
      n.position.set(r.p.x+d.p[0],r.p.y+d.p[1],r.p.z+d.p[2]);for(const [a,rad] of d.r){ax.set(a[0],a[1],a[2]);qa.setFromAxisAngle(ax,rad);n.quaternion.multiply(qa);}
      n.scale.set(r.s.x*d.s[0],r.s.y*d.s[1],r.s.z*d.s[2]);}},dispose};
  }
  const names=(gltf.animations||[]).map((c:any)=>c.name);mixer=names.length?new THREE.AnimationMixer(model):null;
  const acts:Record<string,any>={};if(mixer)for(const role of CLIP_ROLES){const n=pickClipName(names,role,rig.clips||{});if(n){const c=gltf.animations.find((x:any)=>x.name===n);if(c)acts[role]=mixer.clipAction(c);}}
  let cur='';
  const play=(role:string)=>{const a=acts[role]||acts.idle;if(!a||cur===role)return;const prev=acts[cur]||null;cur=role;a.reset().fadeIn(.25).play();if(prev&&prev!==a)prev.fadeOut(.25);};
  return {root:holder,id,rig,honesty:rig.honesty,role:()=>curRole,
   drive(dt,life={}){curRole=roleFor(life);if(mixer){play(curRole);mixer.update(dt);}},dispose};
 }catch(e){console.warn('creature-model-slot: '+id+' failed, keeping the sprite',e);return null;}
}
