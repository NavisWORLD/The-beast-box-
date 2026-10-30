// GENESIS X flashes, VIEW layer (SEEDED looks on SIMULATED signals): storm lightning (a capped sky veil + a jagged bolt that blooms a little),
// and spark-tick shimmer motes around the beast (never bloom). All timing comes from lib/universe/flashes.mjs on the engine clock; nothing here
// draws a random number. No light is added: the one sun stays the only light. ABSENT signal = nothing drawn.
import {lightningAt,stormCount,boltPath,shimmerAt,flashTier,FLASH_LABEL} from './flashes.mjs';
import {FLASH_PACK as P} from './flashes-data.mjs';
type T=typeof import('three');type V3=import('three').Vector3;
export type FlashEnv={engineT:number|null;field:any;cam:V3;center:V3;reduced:boolean;night:number};
export function addFlashes(THREE:T,scene:import('three').Object3D,o:{seed:string;planet:string;tier:string;phone:boolean}){
 const sf=P.lightning.sky_flash.colour.linear,bc=P.lightning.bolt.colour.linear,sc=P.spark_shimmer.burst.colour.linear;
 const veilM=new THREE.MeshBasicMaterial({color:new THREE.Color(sf[0],sf[1],sf[2]),transparent:true,opacity:0,blending:THREE.AdditiveBlending,depthWrite:false,side:THREE.BackSide,fog:false,toneMapped:false});
 const veil=new THREE.Mesh(new THREE.SphereGeometry(200,24,12),veilM);veil.visible=false;veil.frustumCulled=false;veil.renderOrder=-8;scene.add(veil);
 const N=P.lightning.bolt.segments;const bg=new THREE.BufferGeometry();bg.setAttribute('position',new THREE.BufferAttribute(new Float32Array((N+1)*3),3));
 const boltM=new THREE.LineBasicMaterial({color:new THREE.Color(bc[0],bc[1],bc[2]),transparent:true,opacity:1,blending:THREE.AdditiveBlending,depthWrite:false,fog:false,toneMapped:false});
 const bolt=new THREE.Line(bg,boltM);bolt.visible=false;bolt.frustumCulled=false;scene.add(bolt);
 const nM=flashTier(o.tier).shimmer_particles|0;const sg=new THREE.BufferGeometry();sg.setAttribute('position',new THREE.BufferAttribute(new Float32Array(Math.max(1,nM)*3),3));
 const shM=new THREE.PointsMaterial({color:new THREE.Color(sc[0],sc[1],sc[2]),size:2,sizeAttenuation:false,transparent:true,opacity:0,blending:THREE.AdditiveBlending,depthWrite:false,fog:false,toneMapped:false});
 const motes=new THREE.Points(sg,shM);motes.visible=false;motes.frustumCulled=false;scene.add(motes);
 let burst:number|null=null,lastSeed=-1;const up=new THREE.Vector3(),e1=new THREE.Vector3(),e2=new THREE.Vector3(),tmp=new THREE.Vector3();let snap:any={label:FLASH_LABEL,lightning:'ABSENT',shimmer:'ABSENT'};
 function update(env:FlashEnv){
  const storms=stormCount(env.field);const t=env.engineT;
  const L=t==null?{sky:0,bolt:0,boltSeed:0,glow:0,strikes:0,label:'ABSENT'}:lightningAt(o.seed,o.planet,t,storms,o.tier,env.reduced);
  const sky=Math.min(P.safety.sky_flash_max_delta_lum,L.sky+L.glow*P.safety.sky_flash_max_delta_lum);veil.visible=sky>1e-4;veilM.opacity=sky;veil.position.copy(env.cam);
  up.copy(env.center).normalize();
  if(L.bolt>0){if(L.boltSeed!==lastSeed){lastSeed=L.boltSeed;const a=L.boltSeed*Math.PI*2;e1.set(1,0,0);if(Math.abs(up.x)>.9)e1.set(0,0,1);e1.addScaledVector(up,-e1.dot(up)).normalize();e2.crossVectors(up,e1);
    const dir=e1.clone().multiplyScalar(Math.cos(a)).addScaledVector(e2,Math.sin(a));const side=dir.clone().cross(up).normalize();const arr=bg.attributes.position.array as Float32Array;const D=150;
    boltPath(L.boltSeed).forEach(([x,y],i)=>{tmp.copy(dir).multiplyScalar(D).addScaledVector(side,x*D*.25).addScaledVector(up,(.03+.42*y)*D);arr[i*3]=tmp.x;arr[i*3+1]=tmp.y;arr[i*3+2]=tmp.z;});bg.attributes.position.needsUpdate=true;}
   bolt.position.copy(env.cam);boltM.color.setRGB(bc[0]*L.bolt,bc[1]*L.bolt,bc[2]*L.bolt);bolt.visible=true;}else bolt.visible=false;
  const tick=env.field&&isFinite(env.field.tick)?env.field.tick+(env.field.clock?.alpha||0):null;const S=shimmerAt(tick,burst,o.tier,env.reduced);burst=S.burstTick;
  if(S.on&&nM>0){const arr=sg.attributes.position.array as Float32Array;e1.set(1,0,0);if(Math.abs(up.x)>.9)e1.set(0,0,1);e1.addScaledVector(up,-e1.dot(up)).normalize();e2.crossVectors(up,e1);
   const age=1-S.level/P.spark_shimmer.burst.peak_lum;const rise=.6*(.5/1.7)*(1-Math.pow(1-age,2));for(let i=0;i<nM;i++){const a=i/nM*Math.PI*2;const r=.35+.08*Math.sin(i*2.399);
    tmp.copy(env.center).addScaledVector(e1,Math.cos(a)*r).addScaledVector(e2,Math.sin(a)*r).addScaledVector(up,.05+rise*(.6+.4*Math.sin(i*1.7)));arr[i*3]=tmp.x;arr[i*3+1]=tmp.y;arr[i*3+2]=tmp.z;}
   sg.attributes.position.needsUpdate=true;shM.opacity=S.level;motes.visible=true;}else motes.visible=false;
  snap={label:FLASH_LABEL,tier:o.tier,storms,lightning:L.label,sky:+sky.toFixed(4),bolt:+L.bolt.toFixed(3),strikes:L.strikes,shimmer:S.label,shimmerOn:S.on,reduced:env.reduced};
 }
 return {update,snapshot:()=>snap,dispose(){for(const m of [veil,bolt,motes]){scene.remove(m);(m as any).geometry.dispose();}}};
}
