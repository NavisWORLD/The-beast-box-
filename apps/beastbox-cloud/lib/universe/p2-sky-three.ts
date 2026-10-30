// P2 sky layers for the first-person view: a cloud + aurora shell and rain streaks. All motion is driven by the caller's world clock t
// and the p2SkyAt() state (one sun, spark ticks, storm). Rain drop placement uses a seeded hash, no random calls.
type T=typeof import('three');
import {DITHER_GLSL} from './one-world-look';
const NOISE='float h21(vec2 p){p=fract(p*vec2(123.34,456.21));p+=dot(p,p+45.32);return fract(p.x*p.y);}float vn(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(h21(i),h21(i+vec2(1,0)),f.x),mix(h21(i+vec2(0,1)),h21(i+vec2(1,1)),f.x),f.y);}float fbm(vec2 p){float a=.5,s=0.0;for(int i=0;i<5;i++){s+=a*vn(p);p=p*2.02+vec2(3.1,1.7);a*=.5;}return s;}';
const TO_SRGB='vec3 toS(vec3 c){c=max(c,0.0);return mix(c*12.92,1.055*pow(c,vec3(1.0/2.4))-.055,step(.0031308,c));}';
const hash=(i:number)=>{let h=(i+1)*0x9E3779B1>>>0;h^=h>>>16;h=Math.imul(h,0x85EBCA6B)>>>0;h^=h>>>13;h=Math.imul(h,0xC2B2AE35)>>>0;h^=h>>>16;return (h>>>0)/4294967296;};
export function addP2Sky(THREE:T,scene:import('three').Object3D,phone:boolean){
 const U={uUp:{value:new THREE.Vector3(0,1,0)},uSun:{value:new THREE.Vector3(0,1,0)},uT:{value:0},uCover:{value:.3},uLit:{value:1},uDark:{value:0},uAur:{value:0},uSunCol:{value:new THREE.Color('#FFF0DB')},uHor:{value:new THREE.Color()}};
 const m=new THREE.ShaderMaterial({uniforms:U,side:THREE.BackSide,transparent:true,depthWrite:false,depthTest:false,fog:false,toneMapped:false,
  vertexShader:'varying vec3 vD;void main(){vD=normalize(position);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
  fragmentShader:`uniform vec3 uUp,uSun,uSunCol,uHor;uniform float uT,uCover,uLit,uDark,uAur;varying vec3 vD;${NOISE}${TO_SRGB}${DITHER_GLSL}
  void main(){vec3 d=normalize(vD);vec3 up=normalize(uUp);float e=dot(d,up);if(e<-.02)discard;
   vec3 ax=normalize(abs(up.y)<.9?cross(up,vec3(0,1,0)):cross(up,vec3(1,0,0)));vec3 az=cross(up,ax);
   vec2 p=vec2(dot(d,ax),dot(d,az))/max(.08,e+.12); /* project onto a flat cloud deck */
   float n=fbm(p*1.6+vec2(uT*.006,uT*.002));float c=smoothstep(1.0-uCover,1.0-uCover+.28,n)*smoothstep(-.02,.12,e);
   float s=max(0.0,dot(d,normalize(uSun)));vec3 lit=mix(vec3(.62,.66,.74),vec3(1.0),uLit)*mix(1.0,.55,uDark);vec3 col=mix(lit*(.35+.65*uLit),uSunCol,pow(s,8.0)*.5*uLit);
   col=mix(col,uHor,.25*(1.0-e));col*=1.0-.6*uDark*c;
   float a=c*mix(.85,.97,uDark);
   /* aurora: night only, a soft curtain band driven by spark ticks (SIMULATED) */
   float band=exp(-pow((e-.2-.05*sin(p.x*1.3+uT*.05))/.09,2.0));float cur=.6+.4*sin(p.x*7.0+uT*.11+fbm(p*2.0)*4.0);
   vec3 au=mix(vec3(.2,1.0,.6),vec3(.55,.35,1.0),smoothstep(.25,.5,e))*band*cur*uAur;
   vec3 o=col*a+au*(1.0-a);float oa=max(a,clamp(length(au)*1.4,0.0,1.0)*.85);
   gl_FragColor=vec4(dith(toS(o/max(oa,.001))),oa);} /* step 1: dithered, no bands in the soft cloud edges */`});
 const shell=new THREE.Mesh(new THREE.SphereGeometry(280,48,24),m);shell.renderOrder=-15;shell.frustumCulled=false;shell.visible=false;scene.add(shell);
 // rain: seeded streaks in a 30 x 30 x 20 unit box around the eye, falling on the clock t
 const N=phone?700:1800;const pos=new Float32Array(N*6);const base:number[]=[];for(let i=0;i<N;i++)base.push(hash(i*3)*30-15,hash(i*3+1)*20,hash(i*3+2)*30-15);
 const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.BufferAttribute(pos,3));
 const rm=new THREE.LineBasicMaterial({color:0xaec4dd,transparent:true,opacity:0,depthWrite:false,fog:false});const rain=new THREE.LineSegments(geo,rm);rain.frustumCulled=false;rain.visible=false;scene.add(rain);
 return {shell,rain,update(on:boolean,eye:import('three').Vector3,up:import('three').Vector3,sun:import('three').Vector3,hor:number[],st:{cover:number;cloudLit:number;darken:number;aurora:number;rain:number},t:number){
  shell.visible=on;rain.visible=on&&st.rain>.02;if(!on)return;shell.position.copy(eye);U.uUp.value.copy(up);U.uSun.value.copy(sun);U.uT.value=t;U.uCover.value=st.cover;U.uLit.value=st.cloudLit;U.uDark.value=st.darken;U.uAur.value=st.aurora;U.uHor.value.setRGB(hor[0],hor[1],hor[2]);
  if(!rain.visible)return;rm.opacity=.55*st.rain;rain.position.copy(eye);rain.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),up);
  const fall=t*14,L=.6;for(let i=0;i<N;i++){const x=base[i*3],z=base[i*3+2];const y=((base[i*3+1]-fall)%20+20)%20-6;const o=i*6;pos[o]=x;pos[o+1]=y;pos[o+2]=z;pos[o+3]=x+.05;pos[o+4]=y+L;pos[o+5]=z;}
  geo.attributes.position.needsUpdate=true;}};
}
