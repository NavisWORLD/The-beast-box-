// Gradient sky dome. The sun disc sits on the one-sun direction. Drift moves a veil, not the disc.
import {hazeTint} from './haze.ts';
import type {MotionFrame} from './motion.ts';

export type SunSample={day?:number;dir?:number[];sky?:{zenith?:number[];horizon?:number[];starAlpha?:number};elevationDeg?:number};
export type RigSample={sunElevationDeg?:number;exposure?:number};

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

const VERT=`varying vec3 vDir;
void main(){vDir=normalize(position);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`;
const FRAG=`uniform vec3 uSun,uZen,uHor;
uniform float uDay,uStar,uDrift,uMotion;
varying vec3 vDir;
float h31(vec3 p){p=fract(p*.1031);p+=dot(p,p.yzx+33.33);return fract((p.x+p.y)*p.z);}
void main(){
 vec3 d=normalize(vDir);
 float e=d.y;
 float veil=uMotion*sin(d.x*1.6+d.z*1.1+uDrift)*.07;
 vec3 c=mix(uHor,uZen,pow(clamp(e+veil,0.0,1.0),.45));
 float s=max(dot(d,normalize(uSun)),0.0);
 float disc=smoothstep(.9992,.9997,s)*uDay;
 float glow=pow(s,48.0)*uDay;
 c+=vec3(1.0,.93,.78)*(disc*1.4+glow*.35);
 float night=uStar*(1.0-uDay)*step(-.02,e);
 float cell=h31(floor(d*90.0));
 float tw=uMotion>.5?.82+.18*sin(uDrift*2.0+cell*6.0):1.0;
 c+=vec3(.75,.82,1.0)*night*step(.985,cell)*tw*.55;
 if(e<0.0)c=mix(uHor,uHor*.35,smoothstep(0.0,-.12,e));
 gl_FragColor=vec4(c,1.0);
}`;

export function createSkyDome(THREE:typeof import('three'),os:SunSample,rig:RigSample){
 const disc=sunDiscDir(os,rig);
 const U={
  uSun:{value:new THREE.Vector3(...disc.sunDir)},
  uZen:{value:new THREE.Color().setRGB(disc.zenith[0]||0,disc.zenith[1]||0,disc.zenith[2]||0)},
  uHor:{value:new THREE.Color().setRGB(disc.horizon[0]||0,disc.horizon[1]||0,disc.horizon[2]||0)},
  uDay:{value:disc.day},
  uStar:{value:disc.starAlpha},
  uDrift:{value:0},
  uMotion:{value:1},
 };
 const mat=new THREE.ShaderMaterial({
  uniforms:U,vertexShader:VERT,fragmentShader:FRAG,
  side:THREE.BackSide,depthWrite:false,depthTest:false,fog:false,
 });
 const dome=new THREE.Mesh(new THREE.SphereGeometry(720,32,18),mat);
 dome.name='genesis-sky';dome.frustumCulled=false;dome.renderOrder=-50;
 return {dome,uniforms:U,disc};
}

export function syncSky(uniforms:{uSun:{value:{set:(x:number,y:number,z:number)=>void}};uZen:{value:{setRGB:(r:number,g:number,b:number)=>void}};uHor:{value:{setRGB:(r:number,g:number,b:number)=>void}};uDay:{value:number};uStar:{value:number};uDrift:{value:number};uMotion:{value:number}},os:SunSample,rig:RigSample,frame:MotionFrame){
 const disc=sunDiscDir(os,rig);
 uniforms.uSun.value.set(disc.sunDir[0],disc.sunDir[1],disc.sunDir[2]);
 const tint=hazeTint(disc.sunDir,disc.horizon,disc.zenith,frame.skyDrift);
 uniforms.uHor.value.setRGB(tint[0],tint[1],tint[2]);
 uniforms.uZen.value.setRGB(disc.zenith[0]||0,disc.zenith[1]||0,disc.zenith[2]||0);
 uniforms.uDay.value=disc.day;
 uniforms.uStar.value=disc.starAlpha;
 uniforms.uDrift.value=frame.skyDrift;
 uniforms.uMotion.value=frame.reduced?0:1;
 return disc;
}
