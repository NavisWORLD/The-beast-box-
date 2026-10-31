// Cosmo's landforms v1 on the planet: the volcano island (bent to the planet's curve, moss/rock blended per vertex so the
// edge isn't a zigzag), sky (equirect + twinkling stars + sun corona) and sprite-sheet VFX (lava burst x2, embers,
// geyser plume, supernova). Schedules and placement come from seeded streams (lwStream), never an unseeded RNG.
import {lwStream} from './living-world.mjs';import {SKY_OCCLUDER,OCC_DECL,OCC_CULL} from './fp-volcano-sky.mjs';
type T=typeof import('three');type V3=import('three').Vector3;
export const LF='/universe/livingworld/landforms/';
export const ISLAND_ANCHORS:Record<string,[number,number,number]>={crater_center:[0,50.2,0],lava_source:[0,52,0],geyser_vent:[18.85,24.36,-28.3]};
/** bend a flat (x,y,z metres, y up, origin at sea level) point onto a sphere of radius R units around centre normal n */
export function bendToSphere(THREE:T,n:V3,t:V3,b:V3,R:number,k:number,x:number,y:number,z:number,out:V3){const hx=x*k,hz=z*k,d=Math.hypot(hx,hz);
 if(d<1e-9)return out.copy(n).multiplyScalar(R+y*k);const a=d/R;out.copy(t).multiplyScalar(hx/d).addScaledVector(b,hz/d).multiplyScalar(Math.sin(a)).addScaledVector(n,Math.cos(a)).normalize().multiplyScalar(R+y*k);return out;}
const smooth=(e0:number,e1:number,x:number)=>{const t=Math.max(0,Math.min(1,(x-e0)/(e1-e0)));return t*t*(3-2*t);};
export function sheet(THREE:T,url:string,{fps,loop,additive=true,cols=4,rows=4}:{fps:number;loop:boolean;additive?:boolean;cols?:number;rows?:number}){
 const tx=new THREE.TextureLoader().load(url);tx.colorSpace=THREE.SRGBColorSpace;tx.repeat.set(1/cols,1/rows);
 const sp=new THREE.Sprite(new THREE.SpriteMaterial({map:tx,transparent:true,depthWrite:false,blending:additive?THREE.AdditiveBlending:THREE.NormalBlending,fog:false}));sp.visible=loop;let age=loop?0:-1;
 const set=(f:number)=>{const c=f%cols,r=Math.floor(f/cols);tx.offset.set(c/cols,1-(r+1)/rows);};set(0);
 return {sp,play(){age=0;sp.visible=true;},get playing(){return age>=0;},update(dt:number){if(age<0)return;age+=dt;let f=Math.floor(age*fps);if(f>=cols*rows){if(loop){age=0;f=0;}else{age=-1;sp.visible=false;return;}}set(f);}};}

export function addVolcanoIsland(THREE:T,scene:import('three').Scene,o:{seed:string;R:number;mpu:number;scale:number;n:V3;phone:boolean}){
 const group=new THREE.Group();group.name='volcano-island';scene.add(group);const k=o.mpu*o.scale;
 const n=o.n.clone().normalize();const t=new THREE.Vector3().crossVectors(Math.abs(n.y)<.95?new THREE.Vector3(0,1,0):new THREE.Vector3(1,0,0),n).normalize();const b=new THREE.Vector3().crossVectors(n,t).normalize();
 const at=(p:[number,number,number])=>bendToSphere(THREE,n,t,b,o.R,k,p[0],p[1],p[2],new THREE.Vector3());
 const rock=new THREE.Color(),moss=new THREE.Color(),v=new THREE.Vector3();let near:any=null,far:any=null;
 const load=async(file:string)=>{const {GLTFLoader}=await import('three/examples/jsm/loaders/GLTFLoader.js');const g:any=await new GLTFLoader().loadAsync(LF+'models/'+file);g.scene.updateMatrixWorld(true);
  const mats:Record<string,any>={};g.scene.traverse((m:any)=>{if(m.isMesh)mats[m.material.name]=m.material;});if(mats.rock)rock.copy(mats.rock.color);if(mats.moss)moss.copy(mats.moss.color);
  const root=new THREE.Group();g.scene.traverse((m:any)=>{if(!m.isMesh)return;const geo=m.geometry.clone();geo.applyMatrix4(m.matrixWorld);const P=geo.attributes.position;const nm=m.material.name;
   // moss/rock: one per-vertex blend (height + a seeded-free value noise from position) on both materials, so the edge is soft
   const blend=nm==='moss'||nm==='rock';const col=blend?new Float32Array(P.count*3):null;
   for(let i=0;i<P.count;i++){const x=P.getX(i),y=P.getY(i),z=P.getZ(i);
    if(col){const nz=.5+.5*Math.sin(x*.37+z*.23)*Math.cos(z*.31-x*.17);const w=smooth(18,34,y+nz*8);const c=moss.clone().lerp(rock,w);col.set([c.r,c.g,c.b],i*3);}
    bendToSphere(THREE,n,t,b,o.R,k,x,y,z,v);P.setXYZ(i,v.x,v.y,v.z);}
   if(col)geo.setAttribute('color',new THREE.BufferAttribute(col,3));geo.computeVertexNormals();geo.computeBoundingSphere();
   let mat=m.material;if(col){mat=mat.clone();mat.vertexColors=true;mat.color.setRGB(1,1,1);}
   const mesh=new THREE.Mesh(geo,mat);mesh.name='island-'+nm;mesh.castShadow=nm!=='wire_teal'&&nm!=='wire_violet';mesh.receiveShadow=true;root.add(mesh);});
  return root;};
 const ready=(async()=>{far=await load('volcano_island_far.glb');group.add(far);near=await load('volcano_island_near.glb');group.add(near);return true;})();
 // VFX at the anchors (lava burst scaled x2 per the README)
 const unit=o.mpu*o.scale;const fx:any[]=[];const r=lwStream(o.seed+':island-fx');
 const burst=sheet(THREE,LF+'vfx/lava_burst_4x4_256.png',{fps:16,loop:false});burst.sp.scale.setScalar(36*unit*2);burst.sp.position.copy(at([0,58,0]));
 const embers=sheet(THREE,LF+'vfx/embers_4x4_256.png',{fps:12,loop:true});embers.sp.scale.setScalar(30*unit);embers.sp.position.copy(at([0,60,0]));
 const plume=sheet(THREE,LF+'vfx/geyser_plume_4x4_256.png',{fps:12,loop:false,additive:false});plume.sp.scale.setScalar(26*unit);plume.sp.position.copy(at([18.85,36,-28.3]));
 for(const f of [burst,embers,plume]){group.add(f.sp);fx.push(f);}
 let bursts=0;let nextBurst=2+r()*6,nextPlume=4+r()*8,clock=0;
 return {group,ready,anchor:(name:string)=>at(ISLAND_ANCHORS[name]||[0,0,0]),
  update(dt:number,camPos:V3){clock+=dt;if(clock>nextBurst){burst.play();bursts++;nextBurst=clock+6+r()*14;}if(clock>nextPlume){plume.play();nextPlume=clock+9+r()*12;}for(const f of fx)f.update(dt);
   // LOD: near within 400 m (scaled), far beyond (README)
   if(near&&far){const dM=camPos.distanceTo(at([0,0,0]))/o.mpu/o.scale;near.visible=dM<400;far.visible=!near.visible;}},
  state:()=>({bursts,near:!!near,far:!!far,nextBurst:+nextBurst.toFixed(2)})};
}

/** Cosmo's sky: equirect nebula sphere + 1,500 twinkling stars (positions match the webp) */
export function addCosmoSky(THREE:T,scene:import('three').Scene,{radius,phone}:{radius:number;phone:boolean}){
 const tx=new THREE.TextureLoader().load(LF+'sky/sky_equirect_4096x2048.webp');tx.colorSpace=THREE.SRGBColorSpace;
 const mat=new THREE.MeshBasicMaterial({map:tx,side:THREE.BackSide,depthWrite:false,fog:false,transparent:true,opacity:1,toneMapped:false});
 const dome=new THREE.Mesh(new THREE.SphereGeometry(radius,phone?48:64,phone?24:32),mat);dome.renderOrder=-10;scene.add(dome);
 const U:any={uT:{value:0},uA:{value:1},...SKY_OCCLUDER};let pts:any=null;
 fetch(LF+'sky/star_twinkle_points.json').then(r=>r.ok?r.json():null).then((j:any)=>{const arr=Array.isArray(j)?j:(j?.stars||j?.points||[]);if(!arr.length)return;
  const N=phone?Math.min(800,arr.length):arr.length;const P=new Float32Array(N*3),C=new Float32Array(N*3),A=new Float32Array(N*3);
  for(let i=0;i<N;i++){const s=arr[i];const d=s.dir;P.set([d[0]*radius*.97,d[1]*radius*.97,d[2]*radius*.97],i*3);const c=s.rgb||[1,1,1];const mx=Math.max(c[0],c[1],c[2])>1?255:1;C.set([c[0]/mx,c[1]/mx,c[2]/mx],i*3);A.set([s.mag??1,s.phase??0,s.rate_hz??.5],i*3);}
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(P,3));g.setAttribute('color',new THREE.BufferAttribute(C,3));g.setAttribute('aM',new THREE.BufferAttribute(A,3));
  pts=new THREE.Points(g,new THREE.ShaderMaterial({uniforms:U,transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,
   vertexShader:OCC_DECL+'attribute vec3 aM;attribute vec3 color;uniform float uT;varying vec3 vC;varying float vA;void main(){float tw=.7+.3*sin(uT*6.2832*aM.z+aM.y);float b=clamp(1.6-aM.x*.25,.2,1.6);vC=color;vA=tw;gl_PointSize=(1.5+2.5*b)*tw;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);'+OCC_CULL+'}',
   fragmentShader:'uniform float uA;varying vec3 vC;varying float vA;void main(){float d=length(gl_PointCoord-.5);if(d>.5)discard;gl_FragColor=vec4(vC*smoothstep(.5,0.,d)*vA*uA,1.);}'}));pts.renderOrder=-9;pts.frustumCulled=false;scene.add(pts);}).catch(()=>{});
 return {dome,update(t:number,night:number,center:V3){U.uT.value=t;mat.opacity=night;U.uA.value=night;dome.visible=night>.02;dome.position.copy(center);if(pts){pts.position.copy(center);pts.visible=night>.02;}}};
}
