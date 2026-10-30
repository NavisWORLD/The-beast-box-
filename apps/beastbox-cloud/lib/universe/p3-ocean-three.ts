// GENESIS X P3: a first-person ocean bay on the flat local ground patch (child of the one-world-look ground group, so it shows and hides with first person).
// Waves: the 4 SEA layers (same direction, amplitude, chop and whitecaps as the planet sea) as crest-sharpened sines in metres, SIMULATED on engine time.
// Light: the one engine sun only (sky reflection by Schlick fresnel, sun glitter, dark at night). Coast shape and bay bearing are SEEDED. No random calls.
import {OCEAN3,waveLayers} from './p3-ocean.mjs';
type T=typeof import('three');
const TO_SRGB='vec3 toS(vec3 c){c=max(c,0.0);return mix(c*12.92,1.055*pow(c,vec3(1.0/2.4))-.055,step(.0031308,c));}';
const NOISE='float h21(vec2 p){p=fract(p*vec2(123.34,456.21));p+=dot(p,p+45.32);return fract(p.x*p.y);}float vn(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(h21(i),h21(i+vec2(1,0)),f.x),mix(h21(i+vec2(0,1)),h21(i+vec2(1,1)),f.x),f.y);}float fbm(vec2 p){return .5*vn(p)+.25*vn(p*2.03+7.1)+.125*vn(p*4.01+3.7)+.0625*vn(p*8.07+1.3);}';
export type OceanState={dir:number;chop:number;whitecap:number;ampM:number;rough:number;glint:number;glintWidth:number;glintColor:number[];darken:number;day:number};
export function addP3Ocean(THREE:T,parent:import('three').Object3D,bay:{bearing:number;halfWidth:number;innerM:number;outerM:number},mpu:number,octaves=4){
 const Ls=waveLayers();
 const U:any={uT:{value:0},uDir:{value:0},uAmp:{value:.2},uChop:{value:.25},uRough:{value:.1},uGlint:{value:0},uGW:{value:.1},uGC:{value:new THREE.Color(1,1,1)},uDay:{value:1},uDark:{value:0},uWhite:{value:0},
  uSun:{value:new THREE.Vector3(0,1,0)},uZen:{value:new THREE.Color(.3,.5,.8)},uHor:{value:new THREE.Color(.7,.8,.9)},uHaze:{value:new THREE.Color('#A9C9DE')},
  uDeep:{value:new THREE.Color(OCEAN3.deep)},uMid:{value:new THREE.Color(OCEAN3.mid)},uShal:{value:new THREE.Color(OCEAN3.shallow)},uFoam:{value:new THREE.Color(OCEAN3.foam)},uSand:{value:new THREE.Color(OCEAN3.sand)},
  uBear:{value:bay.bearing},uHW:{value:bay.halfWidth},uIn:{value:bay.innerM},uShore:{value:OCEAN3.shoreM},uMPU:{value:mpu},uOct:{value:octaves},uK:{value:.000267},
  uNS:{value:0},uMoonOn:{value:0},uMoonD:{value:new THREE.Vector3(0,1,0)},uL:{value:Ls.map(l=>new THREE.Vector4(l[0],l[1],l[2],l[3]))},uPh:{value:new THREE.Vector4(...Ls.map(l=>l[4]))}};
 const m=new THREE.ShaderMaterial({uniforms:U,transparent:true,depthWrite:false,fog:false,toneMapped:false,polygonOffset:true,polygonOffsetFactor:-2,polygonOffsetUnits:-2,
  vertexShader:'varying vec2 vXZ;varying vec3 vW,vUp,vTx,vTz;void main(){vXZ=position.xz;vec4 w=modelMatrix*vec4(position,1.0);vW=w.xyz;mat3 R=mat3(modelMatrix);vUp=normalize(R*vec3(0,1,0));vTx=normalize(R*vec3(1,0,0));vTz=normalize(R*vec3(0,0,1));gl_Position=projectionMatrix*viewMatrix*w;}',
  fragmentShader:`uniform float uOct,uT,uDir,uAmp,uChop,uRough,uGlint,uGW,uDay,uDark,uWhite,uBear,uHW,uIn,uShore,uMPU,uK;uniform vec3 uGC,uSun,uZen,uHor,uHaze,uDeep,uMid,uShal,uFoam,uSand;uniform vec4 uL[4];uniform vec4 uPh;uniform float uNS,uMoonOn;uniform vec3 uMoonD;
  varying vec2 vXZ;varying vec3 vW,vUp,vTx,vTz;${NOISE}${TO_SRGB}
  void main(){vec2 p=vXZ/uMPU;float r=length(p);
   float a=atan(p.y,p.x)-uBear;a=mod(a+3.14159265,6.2831853)-3.14159265;
   float rin=uIn*(1.0+.45*(fbm(vec2(a*2.6+4.0,1.7))-.5));float hw=uHW*(1.0+.25*(fbm(vec2(r*.004,3.3))-.5));
   float sd=min((hw-abs(a))*r,r-rin)+(fbm(p*.02)-.5)*26.0; /* SEEDED coastline: metres inside the water (+) or up the beach (-) */
   if(sd<-uShore)discard;
   vec3 up=normalize(vUp);vec3 V=normalize(cameraPosition-vW);vec3 S=normalize(uSun);
   float sunUp=max(dot(up,S),0.0);float lit=(.12+.88*smoothstep(-.05,.25,dot(up,S)))*mix(.12,1.0,uDay)*(1.0-.5*uDark);
   float fd=1.0/(1.0+r/350.0); /* far waves flatten so the horizon does not shimmer */
   float h=0.0;vec2 g=vec2(0.0);
   for(int k=0;k<4;k++){vec4 L=uL[k];float ph0=k==0?uPh.x:k==1?uPh.y:k==2?uPh.z:uPh.w;float ang=uDir+L.w;vec2 d=vec2(cos(ang),sin(ang));float w=6.2831853/L.x;
    float ph=w*dot(d,p)-w*L.z*uT+ph0;float q=.5+.5*sin(ph);float am=uAmp*L.y*(k<2?1.0:uChop);h+=am*(2.0*q*q-1.0);g+=am*2.0*q*cos(ph)*w*d;}
   g*=fd;vec2 wq=p*.11+vec2(fbm(p*.013+uT*.01),fbm(p*.013+5.2-uT*.008))*6.0; /* domain warp: no repeating tile */vec2 mic=vec2(0.0);float oa=1.0,of=1.0;for(int o=0;o<4;o++){if(float(o)>=uOct)break;vec2 qq=wq*of*3.1+vec2(uT*.35*of,-uT*.27*of);float e=.15;mic+=oa*vec2(fbm(qq+vec2(e,0.0))-fbm(qq-vec2(e,0.0)),fbm(qq+vec2(0.0,e))-fbm(qq-vec2(0.0,e)))/(2.0*e);oa*=.5;of*=2.07;}mic*=(.12+uRough*1.6)*fd*.35; /* multi-octave warped ripples; storm roughness scales them (SIMULATED) */
   vec3 nL=normalize(vec3(-g.x-mic.x,1.0,-g.y-mic.y));vec3 N=normalize(nL.x*vTx+nL.y*up+nL.z*vTz);
   vec3 R=reflect(-V,N);float re=clamp(dot(R,up),0.0,1.0);vec3 sky=mix(uHor,uZen,pow(re,.45));
   float fres=.02+.98*pow(1.0-max(dot(N,V),0.0),5.0);
   float depth=smoothstep(0.0,30.0,sd);vec3 body=mix(uShal,mix(uMid,uDeep,smoothstep(30.0,260.0,sd)),depth)*lit*(.45+.55*sunUp);
   vec3 c=mix(body,sky,clamp(fres,0.0,1.0));
   float s=max(dot(R,S),0.0);float ex=mix(1800.0,60.0,clamp(uRough+uGW,0.0,1.0));c+=uGC*uGlint*(pow(s,ex)*mix(9.0,2.5,uRough)+.18*pow(s,ex*.04)); /* one-sun glitter: tight at a high calm sun, wide and gold low or rough */
   float crest=smoothstep(.5,.95,h/max(.001,uAmp*1.5))*uWhite*smoothstep(.35,.75,vn(p*.15+uT*.05));c=mix(c,uFoam*lit,crest*.8*fd); /* whitecaps from storm and wind */
   float sh=1.0-smoothstep(0.0,9.0,sd);float lap=.5+.5*sin(sd*.7-uT*1.3+fbm(p*.05)*6.0);c=mix(c,uFoam*lit,sh*smoothstep(.6,.95,lap)*step(0.0,sd)*.7); /* shore foam lines lapping in on the clock */
   if(sd<0.0){float wet=smoothstep(-uShore*.5,0.0,sd);c=uSand*lit*mix(1.0,.62,wet);} /* beach: dry sand fading into the meadow, darker wet sand at the waterline */
   if(uNS>0.0){float tw=pow(vn(R.xz*260.0+R.y*40.0),16.0);c+=uNS*(vec3(.05,.07,.13)*fres*(.5+.5*re)+vec3(.85,.9,1.0)*tw*.5*fres*fd);if(uMoonOn>.5){float ms=max(dot(R,normalize(uMoonD)),0.0);c+=uNS*vec3(.62,.68,.8)*(pow(ms,mix(900.0,80.0,clamp(uRough,0.0,1.0)))*3.0+.12*pow(ms,24.0));}c+=uNS*vec3(.051,.06,.072)*(1.0-fd)*(.55+.45*re); /* far night sheen ~0.06 linear (DERIVED, below bloom): the night sky reflected on the far sea (DERIVED, reflection only), well below the bloom threshold */} /* night sheen DERIVED from the night sky: star glints and the moon's path on the water (reflection only, no new light) */
   float f=1.0-exp(-uK*r);c=mix(c,uHaze*mix(.08,1.0,uDay),min(f,.85));
   float al=sd<0.0?smoothstep(-uShore,-uShore*.35,sd):1.0;
   gl_FragColor=vec4(toS(c),al);}`});
 const geo=new THREE.RingGeometry(bay.innerM*.4*mpu,bay.outerM*mpu,180,24).rotateX(-Math.PI/2).translate(0,.04,0);
 const mesh=new THREE.Mesh(geo,m);mesh.renderOrder=-11;mesh.frustumCulled=false;mesh.name='p3-ocean';parent.add(mesh);
 return {mesh,bay,update(t:number,st:OceanState,sun:import('three').Vector3,zen:number[],hor:number[],night?:{k:number;moon?:import('three').Vector3|null}|null){U.uNS.value=night?Math.max(0,Math.min(1,night.k)):0;U.uMoonOn.value=night&&night.moon?1:0;if(night&&night.moon)U.uMoonD.value.copy(night.moon);
  U.uT.value=t;U.uDir.value=st.dir;U.uAmp.value=st.ampM;U.uChop.value=st.chop;U.uRough.value=st.rough;U.uGlint.value=st.glint;U.uGW.value=st.glintWidth;U.uGC.value.setRGB(st.glintColor[0],st.glintColor[1],st.glintColor[2]);
  U.uDay.value=st.day;U.uDark.value=st.darken;U.uWhite.value=st.whitecap;U.uSun.value.copy(sun);U.uZen.value.setRGB(zen[0],zen[1],zen[2]);U.uHor.value.setRGB(hor[0],hor[1],hor[2]);},
  dispose(){geo.dispose();m.dispose();parent.remove(mesh);}};
}
