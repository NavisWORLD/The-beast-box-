// Pocket beach shoreline (Cory: the Cage, world and beach are one dimensional pocket). The beach is terrain the creatures roam,
// like the volcano island and the ocean, placed on a 'beach' cell of the world field and seeded (lwStream, no Math.random).
// PLACEHOLDER parts (sand crescent, tide line, palms) until Cosmo's beach landform GLB lands; drop
// /universe/livingworld/landforms/models/beach_shore_near.glb in and it replaces the placeholders automatically.
import {lwStream} from './living-world.mjs';
import {bendToSphere,LF} from './landforms-three';
type T=typeof import('three');type V3=import('three').Vector3;
export const BEACH_GLB=LF+'models/beach_shore_near.glb';
export function addBeachShore(THREE:T,scene:import('three').Scene,o:{seed:string;R:number;mpu:number;scale:number;n:V3;phone:boolean}){
 const group=new THREE.Group();group.name='beach-shore';scene.add(group);const k=o.mpu*o.scale;const r=lwStream(o.seed+':beach-shore');
 const n=o.n.clone().normalize();const t=new THREE.Vector3().crossVectors(Math.abs(n.y)<.95?new THREE.Vector3(0,1,0):new THREE.Vector3(1,0,0),n).normalize();const b=new THREE.Vector3().crossVectors(n,t).normalize();
 const v=new THREE.Vector3();const bend=(geo:import('three').BufferGeometry)=>{const P=geo.attributes.position;for(let i=0;i<P.count;i++){bendToSphere(THREE,n,t,b,o.R,k,P.getX(i),P.getY(i),P.getZ(i),v);P.setXYZ(i,v.x,v.y,v.z);}geo.computeVertexNormals();geo.computeBoundingSphere();return geo;};
 // flat crescent in metres (x,z), y up from sea level; the open side faces the sea
 const face=r()*Math.PI*2,arc=Math.PI*(0.9+r()*0.5),R0=24,R1=62,seg=o.phone?28:56;
 const crescent=(rIn:number,rOut:number,y:number,segs:number)=>{const pos:number[]=[],idx:number[]=[];
  for(let i=0;i<=segs;i++){const a=face-arc/2+arc*i/segs;for(const rr of [rIn,rOut])pos.push(Math.cos(a)*rr,y,Math.sin(a)*rr);if(i<segs){const q=i*2;idx.push(q,q+2,q+1,q+1,q+2,q+3);}}
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.setIndex(idx);return g;};
 const placeholder:import('three').Object3D[]=[];
 const sand=new THREE.Mesh(bend(crescent(R0,R1,1.2,seg)),new THREE.MeshStandardMaterial({color:0xf0d9a0,roughness:.95,metalness:0,side:THREE.DoubleSide}));sand.name='beach-sand';sand.receiveShadow=true;
 const tideMat=new THREE.MeshBasicMaterial({color:0xeaf6ff,transparent:true,opacity:.6,depthWrite:false,side:THREE.DoubleSide});
 const tide=new THREE.Mesh(bend(crescent(R1-1,R1+2.5,1.35,seg)),tideMat);tide.name='beach-tide';
 group.add(sand,tide);placeholder.push(sand,tide);
 // palms: seeded spots on the sand, leaning seaward
 const trunkG=new THREE.CylinderGeometry(.35,.6,9,6);trunkG.translate(0,4.5,0);const frondG=new THREE.ConeGeometry(.9,5,4);frondG.rotateX(Math.PI/2);frondG.translate(0,0,2.5);frondG.scale(1,.25,1);
 const trunkM=new THREE.MeshStandardMaterial({color:0x8a6a44,roughness:.9}),frondM=new THREE.MeshStandardMaterial({color:0x2f8a3e,roughness:.8});
 const nPalm=(o.phone?4:6)+Math.floor(r()*4);const up=new THREE.Vector3();
 for(let i=0;i<nPalm;i++){const a=face-arc/2+arc*(0.08+0.84*r()),rr=R0+4+r()*(R1-R0-14);const x=Math.cos(a)*rr,z=Math.sin(a)*rr;
  const palm=new THREE.Group();palm.name='beach-palm';const tr=new THREE.Mesh(trunkG,trunkM);tr.rotation.z=(r()-.5)*.5;tr.rotation.x=(r()-.5)*.5;palm.add(tr);
  const crown=new THREE.Group();crown.position.set(0,9,0).applyEuler(tr.rotation);for(let f=0;f<5;f++){const fr=new THREE.Mesh(frondG,frondM);fr.rotation.y=f*Math.PI*2/5+r();fr.rotation.x=.35;crown.add(fr);}palm.add(crown);
  bendToSphere(THREE,n,t,b,o.R,k,x,1.2,z,v);palm.position.copy(v);up.copy(v).normalize();palm.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),up);palm.scale.setScalar(k);
  palm.traverse((m:any)=>{if(m.isMesh)m.castShadow=true;});group.add(palm);placeholder.push(palm);}
 // swap-in: Cosmo's beach landform replaces the placeholders when the file exists
 let real=false;
 const ready=(async()=>{try{const h=await fetch(BEACH_GLB,{method:'HEAD'});if(!h.ok)return false;const {GLTFLoader}=await import('three/examples/jsm/loaders/GLTFLoader.js');const g:any=await new GLTFLoader().loadAsync(BEACH_GLB);g.scene.updateMatrixWorld(true);
  const root=new THREE.Group();g.scene.traverse((m:any)=>{if(!m.isMesh)return;const geo=m.geometry.clone();geo.applyMatrix4(m.matrixWorld);root.add(new THREE.Mesh(bend(geo),m.material));});
  group.add(root);for(const p of placeholder)p.visible=false;real=true;return true;}catch{return false;}})();
 const phase=r()*Math.PI*2;let clock=0;
 return {group,ready,center:()=>bendToSphere(THREE,n,t,b,o.R,k,0,1.2,0,new THREE.Vector3()),
  update(dt:number){clock+=dt;tideMat.opacity=.35+.3*(.5+.5*Math.sin(clock*.6+phase));},
  state:()=>({palms:nPalm,placeholder:!real,n:n.toArray().map(x=>+x.toFixed(3))})};
}
