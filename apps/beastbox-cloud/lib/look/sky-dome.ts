// Gradient sky dome. The sun disc sits on the one-sun direction. Drift moves a veil, not the disc.
// Software GL uses the light gradient. A real GPU paints the Rayleigh / Henyey-Greenstein horizon.
import {hazeTint} from './haze.ts';
import {SKY_COL_GLSL,SKY_LABEL} from './sky-math.ts';
import {SUN_LABEL,sunTintFor} from './sun-tint.ts';
import type {MotionFrame} from './motion.ts';

export type SunSample={day?:number;dir?:number[];sky?:{zenith?:number[];horizon?:number[];starAlpha?:number};elevationDeg?:number};
export type RigSample={sunElevationDeg?:number;exposure?:number};
export {SKY_LABEL};

export function sunDiscDir(os:SunSample,rig:RigSample){
 const d=os?.dir?.length===3?os.dir:[0,1,0];
 const len=Math.hypot(d[0],d[1],d[2])||1;
 return {
  sunDir:[d[0]/len,d[1]/len,d[2]/len] as [number,number,number],
  elevationDeg:Number(rig?.sunElevationDeg ?? os?.elevationDeg ?? 0),
  exposure:Number(rig?.exposure ?? 0.85),
  zenith:os?.sky?.zenith||[.18,.4,.7],
  horizon:os?.sky?.horizon||[.62,.78,.9],
  starAlpha:Number(os?.sky?.starAlpha ?? 0),
  day:Number(os?.day ?? 0),
 };
}

const VERT=`varying vec3 vDir;varying vec3 vWorld;
void main(){vDir=normalize(position);vWorld=normalize(mat3(modelMatrix)*position);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`;
const FRAG_LITE=`uniform vec3 uSun,uZen,uHor,uBody;
uniform float uDay,uStar,uDrift,uMotion,uSpace;
varying vec3 vDir;varying vec3 vWorld;
float h31(vec3 p){p=fract(p*.1031);p+=dot(p,p.yzx+33.33);return fract((p.x+p.y)*p.z);}
void main(){
 vec3 d=normalize(vDir);
 vec3 w=normalize(vWorld);
 float e=d.y;
 float s=max(dot(d,normalize(uSun)),0.0);
 vec3 c;
 if(uSpace>0.5){
  float we=w.y;
  vec3 nadir=vec3(0.045,0.055,0.18);
  vec3 limb=vec3(0.14,0.18,0.46);
  vec3 zen=vec3(0.06,0.08,0.24);
  c=mix(nadir,mix(limb,zen,smoothstep(-0.15,0.85,we)),smoothstep(-0.55,0.65,we));
  float face=pow(clamp(dot(w,normalize(-cameraPosition)),0.0,1.0),2.2);
  c=mix(c,vec3(0.20,0.26,0.62),face*0.85);
  vec3 g=w*140.0;vec3 cell=floor(g);float h=h31(cell);
  float dd=length(g-(cell+vec3(0.5)));
  float tw=uMotion>.5?.75+.25*sin(uDrift*2.0+h*6.0):1.0;
  c+=vec3(.72,.82,1.0)*step(.9965,h)*smoothstep(.16,0.0,dd)*tw*.55*(1.0-smoothstep(.92,.995,s));
 }else{
  float veil=uMotion*sin(d.x*1.6+d.z*1.1+uDrift)*.07;
  c=mix(uHor,uZen,pow(clamp(e+veil,0.0,1.0),.45));
  float low=smoothstep(.38,-.08,e);
  float mid=smoothstep(.7,.16,e)*(1.0-low);
  c=mix(c,uHor,low*.35);
  c=mix(c,mix(uHor,uZen,.42),mid*.25);
  if(e<0.0)c=mix(uHor*.55,uHor*.22,smoothstep(0.0,-.25,e));
  float night=uStar*(1.0-uDay)*step(-.02,e);
  float cell=h31(floor(d*90.0));
  float tw=uMotion>.5?.82+.18*sin(uDrift*2.0+cell*6.0):1.0;
  c+=vec3(.75,.82,1.0)*night*step(.985,cell)*tw*.55;
 }
 float disc=smoothstep(.9976,.99945,s)*uDay;
 float glow=pow(s,28.0)*uDay;
 c+=uBody*(disc*3.6+glow*.55);
 gl_FragColor=vec4(c,1.0);
}`;
const FRAG=`uniform vec3 uSun,uZen,uHor,uBody;
uniform float uDay,uStar,uDrift,uMotion,uSpace;
varying vec3 vDir;varying vec3 vWorld;
float h31(vec3 p){p=fract(p*.1031);p+=dot(p,p.yzx+33.33);return fract((p.x+p.y)*p.z);}
${SKY_COL_GLSL}
void main(){
 vec3 d=normalize(vDir);
 vec3 w=normalize(vWorld);
 vec3 c;
 if(uSpace>0.5){
  float mu=clamp(dot(d,normalize(uSun)),-1.0,1.0);
  c=spaceAir(w);
  float face=pow(clamp(dot(w,normalize(-cameraPosition)),0.0,1.0),2.2);
  c=mix(c,vec3(0.20,0.26,0.62),face*0.85);
  c+=vec3(0.22,0.10,0.04)*pow(max(mu,0.0),4.0)*0.08*clamp(uDay,0.0,1.0);
  c+=spaceStars(w,uDrift,uMotion)*(1.0-smoothstep(0.92,0.995,mu));
  c=addDisc(c,mu,clamp(uDay,0.0,1.0),uBody,uDrift,uMotion);
 }else{
  c=skyCol(d,uHor,uZen,uBody,uSun,uDay,uDrift,uMotion);
  float night=uStar*(1.0-uDay)*step(-.02,d.y);
  float cell=h31(floor(d*90.0));
  float tw=uMotion>.5?.82+.18*sin(uDrift*2.0+cell*6.0):1.0;
  c+=vec3(.75,.82,1.0)*night*step(.985,cell)*tw*.55;
 }
 gl_FragColor=vec4(c,1.0);
}`;

export {rayleighPhase,hgPhase,skyColour,spaceSkyColour} from './sky-math.ts';

export function createSkyDome(THREE:typeof import('three'),os:SunSample,rig:RigSample,opts?:{lite?:boolean}){
 const disc=sunDiscDir(os,rig);
 const tint=sunTintFor(disc.elevationDeg);
 const U={
  uSun:{value:new THREE.Vector3(...disc.sunDir)},
  uZen:{value:new THREE.Color().setRGB(disc.zenith[0]||0,disc.zenith[1]||0,disc.zenith[2]||0)},
  uHor:{value:new THREE.Color().setRGB(disc.horizon[0]||0,disc.horizon[1]||0,disc.horizon[2]||0)},
  uBody:{value:new THREE.Color().setRGB(tint.rgb[0],tint.rgb[1],tint.rgb[2])},
  uDay:{value:disc.day},
  uStar:{value:disc.starAlpha},
  uDrift:{value:0},
  uMotion:{value:1},
  uSpace:{value:0},
 };
 const lite=!!opts?.lite;
 const mat=new THREE.ShaderMaterial({
  uniforms:U,vertexShader:VERT,fragmentShader:lite?FRAG_LITE:FRAG,
  side:THREE.BackSide,depthWrite:false,depthTest:false,fog:false,
 });
 // Inside the orbit camera's far plane (it floors at 400). A larger shell is clipped and the frame falls back to the flat clear colour.
 const dome=new THREE.Mesh(new THREE.SphereGeometry(280,lite?24:32,lite?14:18),mat);
 dome.name='genesis-sky';dome.frustumCulled=false;dome.renderOrder=-50;
 dome.userData.label=SKY_LABEL;
 dome.userData.sun=SUN_LABEL;
 dome.userData.lite=lite;
 return {dome,uniforms:U,disc,lite};
}

type SkyUniforms={
 uSun:{value:{set:(x:number,y:number,z:number)=>void}};
 uZen:{value:{setRGB:(r:number,g:number,b:number)=>void}};
 uHor:{value:{setRGB:(r:number,g:number,b:number)=>void}};
 uBody:{value:{setRGB:(r:number,g:number,b:number)=>void}};
 uDay:{value:number};
 uStar:{value:number};
 uDrift:{value:number};
 uMotion:{value:number};
 uSpace:{value:number};
};

export function syncSky(uniforms:SkyUniforms,os:SunSample,rig:RigSample,frame:MotionFrame,space=false){
 const disc=sunDiscDir(os,rig);
 uniforms.uSun.value.set(disc.sunDir[0],disc.sunDir[1],disc.sunDir[2]);
 const tint=hazeTint(disc.sunDir,disc.horizon,disc.zenith,frame.skyDrift);
 uniforms.uHor.value.setRGB(tint[0],tint[1],tint[2]);
 uniforms.uZen.value.setRGB(disc.zenith[0]||0,disc.zenith[1]||0,disc.zenith[2]||0);
 const body=sunTintFor(disc.elevationDeg);
 uniforms.uBody.value.setRGB(body.rgb[0],body.rgb[1],body.rgb[2]);
 uniforms.uDay.value=disc.day;
 uniforms.uStar.value=disc.starAlpha;
 uniforms.uDrift.value=frame.skyDrift;
 uniforms.uMotion.value=frame.reduced?0:1;
 uniforms.uSpace.value=space?1:0;
 return disc;
}
