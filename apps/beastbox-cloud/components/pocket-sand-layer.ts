import {createSandField,sandBudget} from '../lib/pocket-sand.mjs';
import {createLoop,stepLoop,loopWellWeights} from '../lib/loop/loop-chain.mjs';
/** Opt-in (default off): the loop's SEEDED well weights tilt the sand. A consented environment tilt always wins. */
export const LOOP_WORLD_KEY='beastbox-loop-world-v1';
type Three=typeof import('three');
/** Cosmic sand + fluid (Cory's Genesis Engine physics) as an additive pocket layer. */
export function addPocketSand(THREE:Three,scene:import('three').Scene,{seed,low,reduced}:{seed:string;low:boolean;reduced:boolean}){
 const count=sandBudget({width:window.innerWidth,low,reduced,cores:navigator.hardwareConcurrency||4});
 const field=createSandField({seed,count});
 const geom=new THREE.BufferGeometry();
 geom.setAttribute('position',new THREE.BufferAttribute(field.pos,3));
 const colors=new Float32Array(count*3),c=new THREE.Color();
 for(let i=0;i<count;i++){c.setHSL(field.kind[i]?.52+((i*37)%100)/900:.74+((i*53)%100)/700,field.kind[i]?.85:.55,field.kind[i]?.62:.55);colors.set([c.r,c.g,c.b],i*3);}
 geom.setAttribute('color',new THREE.BufferAttribute(colors,3));
 const dot=document.createElement('canvas');dot.width=dot.height=32;const g=dot.getContext('2d');
 if(g){const r=g.createRadialGradient(16,16,0,16,16,16);r.addColorStop(0,'rgba(255,255,255,1)');r.addColorStop(.35,'rgba(255,255,255,.55)');r.addColorStop(1,'rgba(255,255,255,0)');g.fillStyle=r;g.fillRect(0,0,32,32);}
 const map=new THREE.CanvasTexture(dot);
 const points=new THREE.Points(geom,new THREE.PointsMaterial({size:low?.11:.085,map,vertexColors:true,transparent:true,opacity:.85,depthWrite:false,blending:THREE.AdditiveBlending,sizeAttenuation:true}));
 points.name='pocket-sand';scene.add(points);
 let acc=0,loop:ReturnType<typeof createLoop>|null=null,lt=0,ownTilt=false;
 try{if(localStorage.getItem(LOOP_WORLD_KEY)==='on')fetch('/spark/zeref-bio-spark.json').then(r=>r.json()).then(j=>{loop=createLoop({seed:j.heart_seed_v9_sha256});}).catch(()=>{});}catch{/* off */}
 const update=(dt:number,disturbers:{x:number;z:number;r:number;s:number}[])=>{
  if(reduced)return; // reduced motion: the field stays still
  if(loop){lt+=dt;while(lt>=1){lt-=1;loop=stepLoop(loop,{});if(!field.environment||ownTilt){field.setEnvironment(loopWellWeights(loop));ownTilt=true;}}}
  acc+=dt;if(low&&acc<1/30)return;const step=acc;acc=0;
  field.step(step,disturbers);(geom.attributes.position as import('three').BufferAttribute).needsUpdate=true;
 };
 return {field,update,count,loopMoments:()=>loop?loop.moments:[],dispose:()=>map.dispose()};
}
