// Presentation grass and trees. Placement is seeded. Sway is the wind and tree hooks.
// Nothing here writes beast, traveler, clock, or signal state.
import {stream01} from './seed.ts';
import {treeSway,windSway,type MotionFrame} from './motion.ts';

const GRASS:Record<string,number>={LOW:280,MED:480,HIGH:720,GOD:1000};
const TREES:Record<string,number>={LOW:16,MED:28,HIGH:40,GOD:56};

export function foliageCounts(tier:string){
 return {grass:GRASS[tier]||GRASS.MED,trees:TREES[tier]||TREES.MED};
}

const GRASS_VERT=`uniform float uPhase,uAmp;
varying float vY;
void main(){
 vec4 local=instanceMatrix*vec4(position,1.0);
 float lean=sin(uPhase+local.x*.2+local.z*.17)*uAmp;
 local.x+=lean*position.y*2.6;
 local.z+=lean*position.y*.7;
 vY=position.y;
 gl_Position=projectionMatrix*modelViewMatrix*local;
}`;
const GRASS_FRAG=`uniform float uDay;
varying float vY;
void main(){
 vec3 c=mix(vec3(.10,.24,.07),vec3(.34,.52,.16),clamp(vY/.42,0.0,1.0));
 c*=mix(.2,1.0,clamp(uDay,0.0,1.0));
 gl_FragColor=vec4(c,1.0);
}`;
const TREE_VERT=`uniform float uLean;
varying float vY;
void main(){
 vec3 p=position;
 p.x+=uLean*p.y*.55;
 p.z+=uLean*p.y*.22;
 vY=p.y;
 gl_Position=projectionMatrix*modelViewMatrix*instanceMatrix*vec4(p,1.0);
}`;
const TREE_FRAG=`uniform float uDay;
varying float vY;
void main(){
 vec3 trunk=vec3(.28,.16,.08),leaf=vec3(.08,.26,.1);
 vec3 c=mix(trunk,leaf,smoothstep(.35,1.1,vY));
 gl_FragColor=vec4(c*mix(.18,1.0,clamp(uDay,0.0,1.0)),1.0);
}`;

export function buildFoliage(THREE:typeof import('three'),o:{
 heightAt:(x:number,z:number)=>number;
 shoreAt?:(x:number,z:number)=>number;
 tier?:string;
 seed?:string;
}){
 const tier=o.tier||'MED';
 const n=foliageCounts(tier);
 const seed=o.seed||'genesis';
 const dry=(x:number,z:number)=>o.heightAt(x,z)>=(o.shoreAt?.(x,z)??0)-.02;
 const blade=new THREE.PlaneGeometry(.08,.42,1,3);blade.translate(0,.21,0);
 const crossed=blade.clone();crossed.rotateY(Math.PI/2);
 const pa=blade.attributes.position.array as Float32Array,pb=crossed.attributes.position.array as Float32Array;
 const pos=new Float32Array(pa.length+pb.length);pos.set(pa,0);pos.set(pb,pa.length);
 const ia=blade.index!.array as Uint16Array,ib=crossed.index!.array as Uint16Array,base=blade.attributes.position.count;
 const idx=new Uint16Array(ia.length+ib.length);idx.set(ia,0);
 for(let k=0;k<ib.length;k++)idx[ia.length+k]=ib[k]+base;
 const grassGeo=new THREE.BufferGeometry();
 grassGeo.setAttribute('position',new THREE.BufferAttribute(pos,3));
 grassGeo.setIndex(new THREE.BufferAttribute(idx,1));
 const grassMat=new THREE.ShaderMaterial({
  uniforms:{uPhase:{value:0},uAmp:{value:0},uDay:{value:1}},
  vertexShader:GRASS_VERT,fragmentShader:GRASS_FRAG,
  side:THREE.DoubleSide,fog:false,
 });
 const grass=new THREE.InstancedMesh(grassGeo,grassMat,n.grass);
 grass.name='genesis-grass';grass.frustumCulled=false;
 /* Cory Nov 12: the 5-sided cone read as a boxy pine. Now a round, tiered pine (three soft skirts on a short trunk, 12 sides, lathed), same height and footprint. */
 const treeGeo=new THREE.LatheGeometry([[0,0],[.045,0],[.045,.16],[.29,.2],[.25,.26],[.13,.46],[.23,.5],[.19,.56],[.09,.76],[.16,.8],[.12,.86],[.03,1.1],[0,1.15]].map(([x,y])=>new THREE.Vector2(x,y)),12);
 const treeMat=new THREE.ShaderMaterial({
  uniforms:{uLean:{value:0},uDay:{value:1}},
  vertexShader:TREE_VERT,fragmentShader:TREE_FRAG,fog:false,
 });
 const trees=new THREE.InstancedMesh(treeGeo,treeMat,n.trees);
 trees.name='genesis-trees';trees.frustumCulled=false;
 const m=new THREE.Matrix4(),p=new THREE.Vector3(),q=new THREE.Quaternion(),s=new THREE.Vector3();
 let gi=0;
 for(let i=0;i<n.grass*3&&gi<n.grass;i++){
  const r=12+stream01(seed+':grass:r:'+i)*46;
  const a=stream01(seed+':grass:a:'+i)*Math.PI*2;
  const x=Math.cos(a)*r,z=Math.sin(a)*r;
  if(!dry(x,z))continue;
  p.set(x,o.heightAt(x,z),z);
  q.setFromAxisAngle(new THREE.Vector3(0,1,0),stream01(seed+':grass:y:'+i)*Math.PI);
  const h=.75+stream01(seed+':grass:h:'+i)*.7;
  s.set(1,h,1);
  grass.setMatrixAt(gi,m.compose(p,q,s));
  gi++;
 }
 grass.count=gi;grass.instanceMatrix.needsUpdate=true;
 let ti=0;
 for(let i=0;i<n.trees*3&&ti<n.trees;i++){
  const r=22+stream01(seed+':tree:r:'+i)*120;
  const a=stream01(seed+':tree:a:'+i)*Math.PI*2;
  const x=Math.cos(a)*r,z=Math.sin(a)*r;
  if(!dry(x,z))continue;
  p.set(x,o.heightAt(x,z),z);
  q.identity();
  const h=.9+stream01(seed+':tree:h:'+i)*.8;
  s.set(h,h,h);
  trees.setMatrixAt(ti,m.compose(p,q,s));
  ti++;
 }
 trees.count=ti;trees.instanceMatrix.needsUpdate=true;
 return {grass,trees,counts:{grass:gi,trees:ti}};
}

/** Push the seeded wind and tree hooks into the drawable uniforms. */
export function syncFoliage(foliage:{grass:{material:any};trees:{material:any}},frame:MotionFrame){
 const g=foliage.grass.material.uniforms;
 const t=foliage.trees.material.uniforms;
 g.uPhase.value=frame.windPhase;
 g.uAmp.value=frame.windAmp;
 t.uLean.value=treeSway(frame);
 return {wind:windSway(frame,0,0),lean:t.uLean.value as number};
}
