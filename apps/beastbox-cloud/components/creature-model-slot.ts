/**
 * Runtime for the creature model slot. loadCreatureModel(THREE, id) resolves to null unless the manifest
 * lists the id AND its rig json validates AND the GLB loads, so the caller keeps its sprite (or sculpted body)
 * in every other case. On success it returns a root scaled to the rig's real height, a drive() that plays the
 * rig's clips from speed/mood, and dispose(). It never invents motion: a model with no clips just stands.
 */
import {MODEL_SLOT_BASE,resolveModelEntry,validateRig,pickClipName,fitScale,roleFor,CLIP_ROLES} from '../lib/creatures3d/creature-model-slot.mjs';
type Three=typeof import('three');
let manifestP:Promise<any>|null=null;
const getManifest=(base:string)=>manifestP||(manifestP=fetch(base+'manifest.json').then(r=>r.ok?r.json():null).catch(()=>null));
export type SlotLife={speed?:number;sleep?:number;startle?:number;joy?:number};
export type SlotModel={root:any;id:string;role:()=>string;honesty:string;rig:any;drive:(dt:number,life?:SlotLife)=>void;dispose:()=>void};
/** Test seam: the manifest cache is per page; tests reset it. */
export function _resetModelSlot(){manifestP=null;}
export async function loadCreatureModel(THREE:Three,id:string,{low=false,targetH=1,base=MODEL_SLOT_BASE,loadGltf=null as null|((url:string)=>Promise<any>)}={}):Promise<SlotModel|null>{
 try{
  const entry=resolveModelEntry(await getManifest(base),id,base);if(!entry)return null;
  const rig=await fetch(entry.rig).then(r=>r.ok?r.json():null).catch(()=>null);
  const v=validateRig(rig,id);if(!v.ok){console.warn('creature-model-slot: rig rejected for '+id+': '+v.errors.join('; '));return null;}
  const load=loadGltf||(async(url:string)=>{const {GLTFLoader}=await import('three/examples/jsm/loaders/GLTFLoader.js');const {MeshoptDecoder}=await import('three/examples/jsm/libs/meshopt_decoder.module.js');const l=new GLTFLoader();l.setMeshoptDecoder(MeshoptDecoder);return l.loadAsync(url);});
  const gltf=await load(low&&entry.glbLow?entry.glbLow:entry.glb);const model=gltf.scene;model.name='slot-'+id;
  const holder=new THREE.Group();holder.name='slot-holder-'+id;holder.add(model);
  const bb=new THREE.Box3().setFromObject(model);const measured=bb.max.y-bb.min.y;
  // The rig states the real height; the measured box is only used to put the feet on y=0 and to scale to the caller's target.
  const k=fitScale(Number.isFinite(measured)&&measured>1e-6?measured:rig.height_m,targetH);
  model.scale.multiplyScalar(k);model.position.y=-(Number.isFinite(bb.min.y)?bb.min.y:0)*k;
  model.traverse((o:any)=>{if(o.isMesh){o.castShadow=true;o.frustumCulled=false;}});
  const names=(gltf.animations||[]).map((c:any)=>c.name);const mixer=names.length?new THREE.AnimationMixer(model):null;
  const acts:Record<string,any>={};if(mixer)for(const role of CLIP_ROLES){const n=pickClipName(names,role,rig.clips||{});if(n){const c=gltf.animations.find((x:any)=>x.name===n);if(c)acts[role]=mixer.clipAction(c);}}
  let cur='';let curRole='idle';
  const play=(role:string)=>{const a=acts[role]||acts.idle;if(!a||cur===role)return;const prev=acts[cur]||null;cur=role;a.reset().fadeIn(.25).play();if(prev&&prev!==a)prev.fadeOut(.25);};
  const dispose=()=>{mixer?.stopAllAction();model.traverse((o:any)=>{if(o.isMesh){o.geometry?.dispose();(Array.isArray(o.material)?o.material:[o.material]).forEach((m:any)=>{m?.map?.dispose?.();m?.dispose?.();});}});};
  return {root:holder,id,rig,honesty:rig.honesty,role:()=>curRole,
   drive(dt,life={}){curRole=roleFor(life);if(mixer){play(curRole);mixer.update(dt);}},dispose};
 }catch(e){console.warn('creature-model-slot: '+id+' failed, keeping the sprite',e);return null;}
}
