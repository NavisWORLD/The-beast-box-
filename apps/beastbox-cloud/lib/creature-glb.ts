'use client';
/**
 * Downloadable real geometry and animations. Only cosmetic game character
 * data enters this exporter. No COSMOS model, memory, telemetry, or tool calls.
 */
import {type CreatureProfile,validCreature} from './creature-profile';
import {createCreatureRig,creatureAnimationClips,type CompanionLook} from './creature-model';

export async function createCreatureGlb(
 profile:CreatureProfile|null,look:CompanionLook='nebula'
):Promise<Uint8Array>{
 if(profile&&!validCreature(profile))throw new Error('Invalid game character');
 const {GLTFExporter}=await import('three/examples/jsm/exporters/GLTFExporter.js');
 const rig=createCreatureRig(profile,look,'auto');
 try{
  // Animations target stable named geometry; GLB contains the geometry rather
  // than a link to a 2D video or a reference to an inaccessible model.
  const exported=await new GLTFExporter().parseAsync(rig.group,{
   binary:true,onlyVisible:true,trs:true,maxTextureSize:512,
   animations:creatureAnimationClips()
  });
  if(!(exported instanceof ArrayBuffer))throw new Error('GLB binary export unavailable');
  const result=new Uint8Array(exported);
  if(result.length<20||result[0]!==0x67||result[1]!==0x6c||
     result[2]!==0x54||result[3]!==0x46)
   throw new Error('Generated GLB failed its basic file signature');
  return result;
 }finally{rig.dispose();}
}
