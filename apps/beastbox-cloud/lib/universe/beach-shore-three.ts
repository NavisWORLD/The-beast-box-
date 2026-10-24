// Pocket beach shoreline (Cory: the Cage, world and beach are one dimensional pocket). The beach is terrain the creatures roam,
// like the volcano island and the ocean, placed on a 'beach' cell of the world field and seeded (lwStream, no Math.random).
// PLACEHOLDER parts (sand crescent, tide line, palms) until Cosmo's beach landform GLB lands; drop
// /universe/livingworld/landforms/models/beach_shore_near.glb in and it replaces the placeholders automatically.
import {lwStream} from './living-world.mjs';
import {bendToSphere} from './landforms-three';
type T=typeof import('three');type V3=import('three').Vector3;
export const BEACH_DIR='/universe/livingworld/landforms/beach/models/';export const BEACH_GLB=BEACH_DIR+'beach_shore_near.glb';
export function addBeachShore(THREE:T,scene:import('three').Scene,o:{seed:string;R:number;mpu:number;scale:number;n:V3;phone:boolean;slotBiome?:(d:number[])=>string|null}){
 const group=new THREE.Group();group.name='beach-shore';scene.add(group);const k=o.mpu*o.scale;const r=lwStream(o.seed+':beach-shore');
 const n=o.n.clone().normalize();// local +Z (sea side) = the southward tangent, so the land side faces north toward the Cage (Studio's map: beach south)
 const b=new THREE.Vector3(0,-1,0).addScaledVector(n,n.y);if(b.lengthSq()<1e-6)b.set(1,0,0).addScaledVector(n,-n.x);b.normalize();const t=new THREE.Vector3().crossVectors(b,n).normalize();
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
 // Cosmo's beach v1: shore GLB at sea level (y=0 = ocean plane), palms from the zones in density_by_biome_beach, anchors read from the GLB
 let real=false;const anchors:Record<string,number[]>={};const paths:Record<string,number[][]>={};const slots:any[]=[];let palms=0;const mixers:any[]=[];
 const ready=(async()=>{try{const {GLTFLoader}=await import('three/examples/jsm/loaders/GLTFLoader.js');const L=new GLTFLoader();const g:any=await L.loadAsync(BEACH_GLB);g.scene.updateMatrixWorld(true);
  const root=new THREE.Group();root.name='beach-shore-glb';
  g.scene.traverse((m:any)=>{const nm=m.name||'';if(/^(shore_spawn|tide_line|place_slot_\d|creature_path_\d)$/.test(nm)){const w=new THREE.Vector3();m.getWorldPosition(w);anchors[nm]=[w.x,w.y,w.z];if(m.userData?.waypoints)paths[nm]=m.userData.waypoints;}
   if(!m.isMesh)return;const geo=m.geometry.clone();geo.applyMatrix4(m.matrixWorld);
   // dune z-fighting: lift dry sand 2 cm and give the neon contour lines a polygon offset so the berm never shimmers
   const mat=m.material.clone();if(/wire|violet|teal/.test(mat.name)){mat.polygonOffset=true;mat.polygonOffsetFactor=-2;mat.polygonOffsetUnits=-2;}
   const mesh=new THREE.Mesh(bend(geo),mat);mesh.name='beach-'+(mat.name||'part');mesh.receiveShadow=true;root.add(mesh);});
  group.add(root);for(const p of placeholder)p.visible=false;real=true;
  // palms: seeded spots 6-25 m inland of the tide line (local -Z), min spacing 5 m, from the three palm GLBs
  const kinds=await Promise.all(['palm_a','palm_b','palm_c'].map(async f=>{const pg:any=await L.loadAsync(BEACH_DIR+f+'.glb');return pg;}));
  const want=o.phone?7:14;const pts:number[][]=[];for(let i=0;i<want*30&&pts.length<want;i++){const x=(r()-.5)*96,zz=-(6+r()*19)-x*x/110;if(pts.every(p=>Math.hypot(p[0]-x,p[1]-zz)>=5))pts.push([x,zz]);}
  for(const [x,z] of pts){const pg=kinds[Math.floor(r()*3)];const p=pg.scene.clone(true);bendToSphere(THREE,n,t,b,o.R,k,x,0,z,v);p.position.copy(v);up.copy(v).normalize();
   p.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),up);p.rotateY(r()*Math.PI*2);p.scale.setScalar(k);p.traverse((m:any)=>{if(m.isMesh)m.castShadow=true;});group.add(p);palms++;
   if(pg.animations?.length){const mx=new THREE.AnimationMixer(p);const a=mx.clipAction(pg.animations[0]);a.time=r()*4;a.play();mixers.push(mx);}}
  // place_slot_0..3: filled from the world field (Azure-synced world data): the biome under each slot picks the prop
  const props:any={};for(const f of ['driftwood','tidepool_rock','shell_spiral']){props[f]=(await L.loadAsync(BEACH_DIR+f+'.glb')).scene;}
  for(let i=0;i<4;i++){const a=anchors['place_slot_'+i];if(!a)continue;bendToSphere(THREE,n,t,b,o.R,k,a[0],a[1],a[2],v);const d=v.clone().normalize().toArray();const biome=o.slotBiome?.(d)||null;
   const pick=biome==='beach'?'driftwood':/ocean|jelly/.test(biome||'')?'tidepool_rock':'shell_spiral';const p=props[pick].clone(true);p.position.copy(v);p.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),v.clone().normalize());p.scale.setScalar(k*(pick==='shell_spiral'?6:1));group.add(p);slots.push({slot:i,biome,prop:pick});}
  return true;}catch(e){(globalThis as any).__lwBeachErr=String(e);return false;}})();
 const toWorld=(p:number[])=>bendToSphere(THREE,n,t,b,o.R,k,p[0],p[1],p[2],new THREE.Vector3());
 const phase=r()*Math.PI*2;let clock=0;
 return {group,ready,center:()=>toWorld([0,0,-12]),anchor:(nm:string)=>anchors[nm]?toWorld(anchors[nm]):null,path:(nm:string)=>(paths[nm]||[]).map(toWorld),radius:70*k/o.R,
  update(dt:number){clock+=dt;for(const m of mixers)m.update(dt);tideMat.opacity=.35+.3*(.5+.5*Math.sin(clock*.6+phase));},
  state:()=>({palms:real?palms:nPalm,placeholder:!real,slots,anchors:Object.keys(anchors),n:n.toArray().map(x=>+x.toFixed(3))})};
}
