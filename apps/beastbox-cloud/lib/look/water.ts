// Water that exists only where the seeded land sits below the water line. Waves are SIMULATED.
import type {MotionFrame} from './motion.ts';

export const WATER_LABEL='Waves · SIMULATED';
export const FOAM_DEPTH=.4;

export function foamAmount(depth:number){
 if(!(depth>0)||depth>=FOAM_DEPTH)return 0;
 return 1-depth/FOAM_DEPTH;
}
/** Schlick fresnel. cosTheta is the angle between the normal and the view. */
export function fresnelSchlick(cosTheta:number,f0=.02){
 const c=Math.max(0,Math.min(1,cosTheta));
 return f0+(1-f0)*Math.pow(1-c,5);
}

const RES:Record<string,number>={LOW:36,MED:56,HIGH:80,GOD:96};

export function smooth01(e0:number,e1:number,v:number){
 const t=Math.max(0,Math.min(1,(v-e0)/((e1-e0)||1)));
 return t*t*(3-2*t);
}

/** Water surface that rises with distance, fit from height samples. The spawn pad stays at 0. */
export function shoreSurface(heightAt:(x:number,z:number)=>number){
 const ratios:number[]=[];
 for(let j=0;j<16;j++)for(let i=0;i<16;i++){
  const x=-96+(i/15)*192,z=-96+(j/15)*192;
  const s=smooth01(12,70,Math.hypot(x,z));
  if(s<.25)continue;
  ratios.push(heightAt(x,z)/s);
 }
 ratios.sort((a,b)=>a-b);
 const coeff=ratios.length?ratios[Math.min(ratios.length-1,Math.floor(ratios.length*.32))]:0;
 const at=(x:number,z:number)=>coeff*smooth01(12,70,Math.hypot(x,z));
 return {coeff,at};
}

export function buildWater(THREE:typeof import('three'),o:{
 heightAt:(x:number,z:number)=>number;
 waterLevel:number;
 tier?:string;
 span?:number;
 surface?:(x:number,z:number)=>number;
}){
 const n=RES[o.tier||'MED']||RES.MED;
 const span=o.span??80;
 const level=o.waterLevel;
 const yOf=o.surface||(()=>level);
 const pos:number[]=[];const depth:number[]=[];const idx:number[]=[];
 const at=(i:number,j:number)=>{
  const x=-span+(i/n)*span*2,z=-span+(j/n)*span*2;
  const y=yOf(x,z);
  return {x,y,z,d:y-o.heightAt(x,z)};
 };
 const id=(i:number,j:number)=>j*(n+1)+i;
 for(let j=0;j<=n;j++)for(let i=0;i<=n;i++){
  const p=at(i,j);
  pos.push(p.x,p.y,p.z);depth.push(p.d);
 }
 let wet=0,dry=0,foam=0;
 for(let j=0;j<n;j++)for(let i=0;i<n;i++){
  const a=id(i,j),b=id(i+1,j),c=id(i,j+1),d=id(i+1,j+1);
  const ds=[depth[a],depth[b],depth[c],depth[d]];
  const above=ds.filter(v=>v>0).length;
  if(above===0){dry++;continue;}
  wet++;
  if(ds.some(v=>foamAmount(v)>0))foam++;
  idx.push(a,b,c,b,d,c);
 }
 const geo=new THREE.BufferGeometry();
 geo.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));
 geo.setAttribute('aDepth',new THREE.Float32BufferAttribute(depth,1));
 geo.setIndex(idx);
 geo.computeVertexNormals();
 return {geometry:geo,wet,dry,foam,level,label:WATER_LABEL};
}

const VERT=`attribute float aDepth;
uniform float uTime,uMotion,uLevel;
varying float vDepth;varying vec3 vW;varying vec3 vN;
void main(){
 float shore=smoothstep(.4,0.0,aDepth);
 float wave=uMotion*(sin(position.x*.48+uTime*1.15)*.14+sin(position.z*.36-uTime*.82)*.1);
 float roll=uMotion*shore*sin(aDepth*5.5-uTime*2.1)*.16;
 vec3 p=position;p.y+=wave+roll;
 vec3 n=normalize(vec3(uMotion*-cos(position.x*.48+uTime*1.15)*.067,1.0,uMotion*-cos(position.z*.36-uTime*.82)*.036));
 vN=normalize(normalMatrix*n);vDepth=aDepth;
 vec4 w=modelMatrix*vec4(p,1.0);vW=w.xyz;
 gl_Position=projectionMatrix*viewMatrix*w;
}`;
const FRAG=`uniform vec3 uSun,uSky,uDeep;uniform float uDay;
varying float vDepth;varying vec3 vW;varying vec3 vN;
void main(){
 if(vDepth<=0.0)discard;
 vec3 N=normalize(vN);vec3 V=normalize(cameraPosition-vW);
 float fres=pow(1.0-max(dot(N,V),0.0),5.0);
 float t=smoothstep(0.0,1.6,vDepth);
 vec3 c=mix(vec3(.08,.55,.52),uDeep,t);
 c=mix(c,uSky,fres*.78);
 float glint=pow(max(dot(N,normalize(normalize(uSun)+V)),0.0),90.0)*uDay*step(0.0,uSun.y);
 c+=vec3(1.0,.95,.85)*glint*.9;
 float foam=smoothstep(.4,0.02,vDepth);
 c=mix(c,vec3(.9,.95,.96),foam*.82);
 float a=mix(.78,.92,fres)*(1.0-smoothstep(.0,.08,max(-vDepth,0.0)));
 c*=a;
 gl_FragColor=vec4(c,a);
}`;

export function createWaterMaterial(THREE:typeof import('three'),level:number){
 const uniforms={
  uTime:{value:0},uMotion:{value:1},uLevel:{value:level},
  uSun:{value:new THREE.Vector3(.3,.8,.2)},
  uSky:{value:new THREE.Color(.55,.72,.86)},
  uDeep:{value:new THREE.Color(.02,.12,.24)},
  uDay:{value:1},
 };
 const mat=new THREE.ShaderMaterial({
  uniforms,vertexShader:VERT,fragmentShader:FRAG,
  transparent:true,depthWrite:false,premultipliedAlpha:true,fog:false,
 });
 return {material:mat,uniforms};
}

export function syncWater(uniforms:{uTime:{value:number};uMotion:{value:number}},frame:MotionFrame){
 uniforms.uTime.value=frame.shoreRoll;
 uniforms.uMotion.value=frame.reduced?0:1;
}
