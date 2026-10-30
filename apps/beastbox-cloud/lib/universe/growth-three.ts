// Growth nodes, three.js extras: shed-leaf particles (one Points per node) and the tap burst ring. Colours and sizes are Cosmo's growth tint
// pack (growth_tint.json shed_particles). Per-particle randoms come from lwStream (recorded-IBM seed), never Math.random; time comes from the
// caller's frame clock. Placement is SEEDED, growth speed rides the SIMULATED tick (Rigetti Bell simulator, not hardware).
import {shedRecipe} from './growth-view.mjs';
import {lwStream} from './living-world.mjs';
type T=typeof import('three');
const VS=`uniform float uT,uShed,uR,uPx,uRad,uH,uFall,uDrift,uLife,uSize,uMotion,uLift,uFade;uniform vec3 uC,uE1,uE2;uniform vec3 uCol[4];
attribute vec4 aS;varying vec3 vCol;varying float vA;
void main(){float vis=step(aS.w,uShed)*step(.5,uMotion);float life=uLife*(.7+.6*aS.z);float ph=fract(uT/life+aS.z*7.31);
 vec3 d=normalize(uC+(uE1*(aS.x*2.-1.)+uE2*(aS.y*2.-1.))*uRad);float hs=uH*(.5+.5*aS.y);float y=max(0.,hs-ph*uFall*life);
 float dr=sin(ph*6.2831+aS.z*9.)*uDrift;vec3 p=d*(uR+uLift+y)+uE1*dr+uE2*dr*.6;vec4 mv=viewMatrix*modelMatrix*vec4(p,1.);
 gl_Position=projectionMatrix*mv;gl_PointSize=vis*clamp(uSize*uPx/max(.05,-mv.z),1.5,12.0);int ci=int(floor(fract(aS.z*4.7+aS.x)*3.99));vCol=uCol[ci];vA=vis*(1.-smoothstep(1.-uFade,1.,ph));}`;
const BVS=`uniform float uAge,uR,uPx,uRad,uSize,uLift;uniform vec3 uC,uE1,uE2;uniform vec3 uCol[4];attribute vec4 aS;varying vec3 vCol;varying float vA;
void main(){float a=aS.x*6.2831;float rr=uAge*uRad*(.6+.5*aS.y);vec3 d=normalize(uC+(uE1*cos(a)+uE2*sin(a))*rr);float y=sin(min(1.,uAge/1.4)*3.14159)*uRad*.12*aS.z;
 vec4 mv=viewMatrix*modelMatrix*vec4(d*(uR+uLift+y),1.);gl_Position=projectionMatrix*mv;float vis=step(0.,uAge)*step(uAge,1.4);gl_PointSize=vis*clamp(uSize*uPx/max(.05,-mv.z),1.5,12.0);
 int ci=int(floor(aS.w*3.99));vCol=uCol[ci];vA=vis*(1.-smoothstep(.6,1.4,uAge));}`;
const FS=`varying vec3 vCol;varying float vA;uniform float uEm;void main(){vec2 q=gl_PointCoord-.5;float r=length(q);if(r>.5||vA<.01)discard;gl_FragColor=vec4(vCol*(1.+uEm),vA*(1.-r*1.2));
 #include <colorspace_fragment>
}`;
const basis=(THREE:T,c:import('three').Vector3)=>{const e1=new THREE.Vector3(0,1,0).cross(c);if(e1.lengthSq()<1e-6)e1.set(1,0,0);e1.normalize();const e2=new THREE.Vector3().crossVectors(c,e1).normalize();return {e1,e2};};
export type ShedOpts={seed:string;R:number;mpu:number;K:number;cellRad:number;lift:(d:import('three').Vector3)=>number};
export function createGrowthShed(THREE:T,parent:import('three').Object3D,nodes:any[],o:ShedOpts){
 const group=new THREE.Group();group.name='growth-shed';parent.add(group);const N=64;const items:any[]=[];
 const mk=(vs:string,u:any,seedKey:string,n:number)=>{const r=lwStream(o.seed+':growth-shed:'+seedKey);const g=new THREE.BufferGeometry();const aS=new Float32Array(n*4);for(let i=0;i<n*4;i++)aS[i]=r();// fixed 4 draws per particle
  g.setAttribute('aS',new THREE.BufferAttribute(aS,4));g.setAttribute('position',new THREE.BufferAttribute(new Float32Array(n*3),3));
  const m=new THREE.ShaderMaterial({vertexShader:vs,fragmentShader:FS,uniforms:u,transparent:true,depthWrite:false});const p=new THREE.Points(g,m);p.frustumCulled=false;p.renderOrder=3;group.add(p);return p;};
 for(const n of nodes){const rc=shedRecipe(n.kind);const a=n.lat*Math.PI/180,l=n.lon*Math.PI/180;const c=new THREE.Vector3(Math.cos(a)*Math.cos(l),Math.sin(a),Math.cos(a)*Math.sin(l));const {e1,e2}=basis(THREE,c);
  const cols=[0,1,2,3].map(i=>new THREE.Vector3(...rc.colors[i%rc.colors.length]));const mid=(r:number[])=>(r[0]+r[1])/2;const K=o.K*o.mpu;
  const cm=Math.max(1,n.spread)*o.cellRad;// territory radius (rad)
  const U:any={uT:{value:0},uShed:{value:0},uR:{value:o.R},uPx:{value:600},uRad:{value:cm*.7},uH:{value:(n.kind==='canopy'?3:n.kind==='shrub'?1.2:.5)*K*(n.kind==='canopy'?2.2:1)},uFall:{value:mid(rc.fall_speed_mps)*K},uDrift:{value:rc.drift_m*K},uLife:{value:mid(rc.lifetime_s)},uSize:{value:mid(rc.size_m)*K*2},uMotion:{value:1},uLift:{value:o.lift(c)},uFade:{value:rc.fadeOutLast},uC:{value:c},uE1:{value:e1},uE2:{value:e2},uCol:{value:cols},uEm:{value:rc.emissive}};
  const pts=mk(VS,U,n.id,N);
  const BU:any={uAge:{value:-1},uR:{value:o.R},uPx:{value:600},uRad:{value:cm*.5},uSize:{value:.07*K},uLift:{value:U.uLift.value},uC:{value:c},uE1:{value:e1},uE2:{value:e2},uCol:{value:cols},uEm:{value:rc.emissive}};
  const burst=mk(BVS,BU,n.id+':burst',24);items.push({id:n.id,U,BU,pts,burst});}
 return {group,items,
  /** per frame: t seconds (frame clock), px = pixels per world unit at distance 1, shed = {nodeId: 0..1}, motion on/off */
  update(t:number,px:number,shed:Record<string,number>,motion:boolean){for(const it of items){it.U.uT.value=t;it.U.uPx.value=px;it.BU.uPx.value=px;it.U.uShed.value=shed[it.id]||0;it.U.uMotion.value=motion?1:0;}},
  /** start the ring burst on a node (caller skips this under reduced motion) */
  burst(id:string,ageS:number){const it=items.find(x=>x.id===id);if(it)it.BU.uAge.value=ageS;},
  dispose(){parent.remove(group);for(const it of items){for(const p of [it.pts,it.burst]){p.geometry.dispose();p.material.dispose();}}}};
}
