// One World look pass 2 (additive). Three.js layers for the first-person ground view, all from Cosmo's One Universe pack:
// a gradient sky dome (pack stops, teal top, warm only near the sun), two far hill rings with blue aerial haze, and the
// volcano world in the sky (no ring, no light of its own, lava glow on its night side only). Placement is SEEDED; colour blends DERIVED.
// No random calls: hill shapes come from a seeded stream passed in by the caller.
type T=typeof import('three');
export const LOOK2=Object.freeze({label:'SEEDED',teal:'#437E9E',skyMid:'#88C9BB',horizonHaze:'#E4E4BD',hillsFar:'#8CA192',aerialTint:'#8CB3D6',warm:'#F2B27A',
 volcano:{azimuthDeg:191.785,elevationDeg:30.4477,angularDeg:9.292,body:'#B5532E',lava:'#FF7A2E',lavaIntensity:.35}});
const TO_SRGB='vec3 toS(vec3 c){c=max(c,0.0);return mix(c*12.92,1.055*pow(c,vec3(1.0/2.4))-.055,step(.0031308,c));}';
/** GENESIS X step 1: triangular screen-space dither (+-1 LSB of 8-bit) applied after the sRGB encode, so smooth sky and haze gradients show no bands. A fixed hash of the pixel position, no random calls, no clock. */
export const DITHER_GLSL='float dz1(vec2 p){return fract(sin(dot(p,vec2(12.9898,78.233)))*43758.5453);}vec3 dith(vec3 c){vec2 p=gl_FragCoord.xy;float n=dz1(p)+dz1(p+vec2(.5193,.3711))-1.0;return c+vec3(n,dz1(p+vec2(7.1,3.3))+dz1(p+vec2(1.7,9.2))-1.0,n)/255.0;}';
/** P2 ground fix (art target 36, Oct 30): a lush green meadow to the horizon instead of the pale olive plain. sRGB hexes (three converts to linear). SEEDED palette, DERIVED blends. */
export const MEADOW36=Object.freeze({label:'SEEDED',dark:'#2C5A1C',base:'#4C8C2A',tip:'#8CC04A',soil:'#6E5A36',blade:'#B8E070',haze:'#A9C9DE',belowHorizon:'#3E6E2A'});
/** Target 36 sun bloom (SEEDED look numbers). core is linear and above the P1 bloom threshold (~1.6 before exposure); halo/wide are the soft warm glow. */
export const SUNBLOOM36=Object.freeze({label:'SEEDED',core:2.4,coreExp:900,halo:.55,haloExp:64,wide:.16,wideExp:6});
/** Scene units per metre: TRAV_H .5 = 1.7 m. */
export const M=.5/1.7;
/** P1 fix-up (art target 36): in first person the neighbour world sits smaller and higher so it reads as a far planet, not a wall. SEEDED placement. */
export const NEIGHBOUR_FP=Object.freeze({label:'SEEDED',elevationDeg:44,angularDeg:5.4});
const NOISE='float h21(vec2 p){p=fract(p*vec2(123.34,456.21));p+=dot(p,p+45.32);return fract(p.x*p.y);}float vn(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(h21(i),h21(i+vec2(1,0)),f.x),mix(h21(i+vec2(0,1)),h21(i+vec2(1,1)),f.x),f.y);}float fbm(vec2 p){return .5*vn(p)+.25*vn(p*2.03+7.1)+.125*vn(p*4.01+3.7)+.0625*vn(p*8.07+1.3);}';
/** Far ridges from Cosmo's FIX_NOTES_43c74d3 (aerial perspective k .000267/m, tint #8CB3D6). SEEDED shapes. */
export const RIDGES=Object.freeze([{d:300,crestDeg:1.99,fade:.077,hex:'#4F7A45'},{d:1200,crestDeg:2.07,fade:.274,hex:'#6E9283'},{d:2000,crestDeg:2.24,fade:.414,hex:'#8FA1A7'},{d:4500,crestDeg:2.27,fade:.7,hex:'#A7B6C1'}]);
/** Sky dome: c = mix(horizon, zenith, pow(up,.45)); zenith = mix(pack zenith, teal mood target, .5) by day; warm only near the sun. Colours in linear, converted once. */
export function addSkyDome(THREE:T,scene:import('three').Object3D){
 const U={uUp:{value:new THREE.Vector3(0,1,0)},uSun:{value:new THREE.Vector3(0,1,0)},uZen:{value:new THREE.Color()},uHor:{value:new THREE.Color()},uDay:{value:0},
  uTeal:{value:new THREE.Color(LOOK2.teal)},uWarm:{value:new THREE.Color().setRGB(1,.875,.7055)},uBelow:{value:new THREE.Color(MEADOW36.belowHorizon)}};
 const m=new THREE.ShaderMaterial({uniforms:U,side:THREE.BackSide,depthWrite:false,depthTest:false,fog:false,toneMapped:false,
  vertexShader:'varying vec3 vD;void main(){vD=normalize(position);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
  fragmentShader:`uniform vec3 uUp,uSun,uZen,uHor,uTeal,uWarm,uBelow;uniform float uDay;varying vec3 vD;${TO_SRGB}${DITHER_GLSL}
  void main(){vec3 d=normalize(vD);float e=dot(d,normalize(uUp));float s=max(0.0,dot(d,normalize(uSun)));
   vec3 zen=mix(uZen,mix(uZen,uTeal,.5),uDay);
   vec3 c=mix(uHor,zen,pow(clamp(e,0.0,1.0),.45));
   c=mix(c,uWarm*.9,.35*pow(s,24.0)*uDay);
   c+=uWarm*(${SUNBLOOM36.core.toFixed(2)}*pow(s,${SUNBLOOM36.coreExp.toFixed(2)})+${SUNBLOOM36.halo.toFixed(2)}*pow(s,${SUNBLOOM36.haloExp.toFixed(2)})+${SUNBLOOM36.wide.toFixed(2)}*pow(s,${SUNBLOOM36.wideExp.toFixed(2)}))*uDay*step(0.0,e); /* target 36 warm sun bloom by day: a hot core over the P1 bloom threshold (so the existing P1 bloom pass blooms it on MED/HIGH/GOD) plus a soft warm halo that also shows on LOW; only above the horizon, fades with the one sun's day factor */
   if(e<0.0)c=mix(uHor,uBelow*mix(.15,1.0,uDay),smoothstep(0.0,-.04,e)); /* below the horizon: ground, not sky */
   gl_FragColor=vec4(dith(toS(c)),1.0);}`});
 const dome=new THREE.Mesh(new THREE.SphereGeometry(300,48,24),m);dome.renderOrder=-20;dome.frustumCulled=false;dome.visible=false;scene.add(dome);
 return {dome,update(on:boolean,cam:import('three').Vector3,up:import('three').Vector3,sun:import('three').Vector3,zen:number[],hor:number[],day:number){
  dome.visible=on;if(!on)return;dome.position.copy(cam);U.uUp.value.copy(up);U.uSun.value.copy(sun);U.uZen.value.setRGB(zen[0],zen[1],zen[2]);U.uHor.value.setRGB(hor[0],hor[1],hor[2]);U.uDay.value=day;}};
}
/** First person (target 36): the flat patch starts ~4 m out, just inside where the curved 8-unit planet drops below the 1.6 m eye's horizon (was 14 units, which left a flat below-horizon band and a teal planet rim between near grass and meadow). SEEDED look value. */
export const FLAT_INNER=1.2;
/** First person: a flat local ground patch (2.5 km radius) with aerial haze, plus four full 360 deg ridge rings. The 27 m sphere stays for orbit. */
export function addFlatGround(THREE:T,scene:import('three').Object3D,rand:()=>number){
 const g=new THREE.Group();g.visible=false;scene.add(g);const R=2500*M;const mats:any[]=[];
 const GU={uSunL:{value:1},uDay:{value:1},uHaze:{value:new THREE.Color(LOOK2.horizonHaze)},uTint:{value:new THREE.Color(LOOK2.aerialTint)},uBase:{value:new THREE.Color(MEADOW36.base)},uDark:{value:new THREE.Color(MEADOW36.dark)},uTip:{value:new THREE.Color(MEADOW36.tip)},uSoil:{value:new THREE.Color(MEADOW36.soil)},uBlade:{value:new THREE.Color(MEADOW36.blade)},uAir:{value:new THREE.Color(MEADOW36.haze)},uK:{value:.000267/M}};
 const gm=new THREE.ShaderMaterial({uniforms:GU,fog:false,toneMapped:false,
  vertexShader:'varying float vD;varying vec2 vXZ;void main(){vD=length(position.xz);vXZ=position.xz;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
  fragmentShader:`uniform float uSunL,uDay,uK;uniform vec3 uHaze,uTint,uBase,uDark,uTip,uSoil,uBlade,uAir;varying float vD;varying vec2 vXZ;${TO_SRGB}${NOISE}${DITHER_GLSL}
  void main(){vec2 q=vXZ*.012;float m=fbm(q),d=fbm(q*3.1+11.0),r=fbm(q*.23+5.0);
   vec3 tip=uTip,dark=uDark,soil=uSoil;
   vec3 land=mix(dark,uBase,smoothstep(.25,.6,m));land=mix(land,tip,smoothstep(.55,.85,d)*.55);land=mix(land,soil,smoothstep(.62,.8,r)*.5);
   land*=mix(.7,1.2,fbm(q*.4+2.0))*mix(.85,1.1,vn(q*9.0)); /* meadow patches, darker hollows, bare soil: seeded noise, no tiling */
   float nb=1.0-smoothstep(4.0,90.0,vD);float bl=vn(vec2(vXZ.x*7.0,vXZ.y*1.3))*vn(vec2(vXZ.x*1.1,vXZ.y*6.5));land=mix(land,uBlade*.55,smoothstep(.35,.8,bl)*.35*nb);land*=mix(1.0,.78+.44*vn(vXZ*3.0),nb); /* target 36: near grass streaks and light/dark tufts, fading out with distance */
   vec3 c=land*(.12+.88*uSunL)*mix(.15,1.0,uDay);float f=1.0-exp(-uK*vD);c=mix(c,mix(mix(uHaze,uTint,.5),uAir,.6)*mix(.08,1.0,uDay),min(f,.85)); /* cooler blue-green air (target 36), and the far meadow never fully washes out */gl_FragColor=vec4(dith(toS(c)),1.0);}`});
 const ground=new THREE.Mesh(new THREE.RingGeometry(FLAT_INNER,R,96,8).rotateX(-Math.PI/2).translate(0,-.02,0),gm); /* inner edge meets the 8-unit planet's horizon seen from the 1.6 m eye, so no below-horizon band, hard seam or bright rim (the planet's far edge) shows between the near grass and the far meadow */ground.renderOrder=-12;ground.frustumCulled=false;g.add(ground);mats.push(gm);
 for(const r of RIDGES){const rad=r.d*M,top=Math.tan(r.crestDeg*Math.PI/180)*rad;const ph=[rand()*6.28,rand()*6.28,rand()*6.28];const lobes=Math.max(6,Math.round(2*Math.PI*r.d/(3*r.d/40)/6));
  const U={uC:{value:new THREE.Color(r.hex)},uHz:{value:new THREE.Color(LOOK2.horizonHaze).lerp(new THREE.Color(LOOK2.aerialTint),.5)},uF:{value:r.fade},uDay:{value:1},uP:{value:new THREE.Vector3(...ph)},uL:{value:lobes}};
  const m=new THREE.ShaderMaterial({uniforms:U,side:THREE.DoubleSide,fog:false,toneMapped:false,
   vertexShader:'varying vec2 vUv;varying vec3 vP;void main(){vUv=uv;vP=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
   fragmentShader:`uniform vec3 uC,uP,uHz;uniform float uDay,uL,uF;varying vec2 vUv;varying vec3 vP;${TO_SRGB}${DITHER_GLSL}
   void main(){float a=atan(vP.z,vP.x);float h=.55+.25*sin(uL*a+uP.x)+.12*sin(uL*2.3*a+uP.y)+.08*sin(uL*.37*a+uP.z);
    if(vUv.y>h)discard;float k=clamp(.25+uF*.7+.35*(1.0-vUv.y/h),0.0,.92);vec3 c=mix(uC,uHz,k); /* hazy far ridges: aerial haze rises toward the base (valley mist) and with distance */
    gl_FragColor=vec4(dith(toS(c*mix(.1,1.0,uDay))),1.0);}`});
  const geo=new THREE.CylinderGeometry(rad,rad,top,192,1,true);geo.translate(0,top*.5,0);const mesh=new THREE.Mesh(geo,m);mesh.renderOrder=-11;mesh.frustumCulled=false;g.add(mesh);mats.push(m);}
 const life:{sp:any;r:number;a:number;w:number}[]=[];
 /** far creatures: resident sprites walking slow seeded circles on the patch at 25-120 m (mid; target 36: nothing crowds the near frame) and 200-600 m (far); motion follows the clock t. */
 const addLife=(maps:any[])=>{maps.forEach((map,i)=>{for(const band of [0,1]){const sp=new THREE.Sprite(new THREE.SpriteMaterial({map,transparent:true,depthWrite:false,fog:false}));sp.center.set(.5,.02);
   const r=(band?200+rand()*400:25+rand()*95)*M;sp.scale.setScalar(.75);g.add(sp);life.push({sp,r,a:rand()*6.283,w:(rand()<.5?-1:1)*(.02+rand()*.04)/Math.max(1,r*.05)});}});};
 const step=(t:number)=>{for(const L of life){const a=L.a+L.w*t;L.sp.position.set(Math.cos(a)*L.r,0,Math.sin(a)*L.r);}};
 return {group:g,addLife,step,count:()=>life.length,farUnits:4600*M,update(on:boolean,groundPt:import('three').Vector3,up:import('three').Vector3,day:number,sunL:number,face?:{fwd:import('three').Vector3;bearing:number}|null){g.visible=on;if(!on)return;
  g.position.copy(groundPt);g.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),up);if(face)g.quaternion.premultiply(yawToward(THREE,g.quaternion,up,face.fwd,face.bearing)); /* GENESIS X step 0: optional yaw so a SEEDED local bearing (the P3 bay) lies along a given world heading */for(const m of mats)m.uniforms.uDay.value=day;GU.uSunL.value=sunL;}};
}
/** Yaw (about up) that turns the local bearing b (local dir (cos b,0,sin b) under q) onto fwd projected into the tangent plane. Pure maths, no random calls. */
export function yawToward(THREE:T,q:import('three').Quaternion,up:import('three').Vector3,fwd:import('three').Vector3,b:number){
 const u=up.clone().normalize();const d=new THREE.Vector3(Math.cos(b),0,Math.sin(b)).applyQuaternion(q);d.addScaledVector(u,-d.dot(u));const f=fwd.clone().addScaledVector(u,-fwd.dot(u));
 if(d.lengthSq()<1e-8||f.lengthSq()<1e-8)return new THREE.Quaternion();d.normalize();f.normalize();const th=Math.atan2(u.dot(new THREE.Vector3().crossVectors(d,f)),d.dot(f));return new THREE.Quaternion().setFromAxisAngle(u,th);}
/** World-volcano in the sky: lit by the one sun, lava glow only on its night side, no ring, no light; blended .35*(1-fade) toward the sky by day. */
export function addSkyWorld(THREE:T,scene:import('three').Object3D,angularDeg?:number){
 const V=LOOK2.volcano;const U={uSun:{value:new THREE.Vector3(0,1,0)},uBody:{value:new THREE.Color(V.body)},uLava:{value:new THREE.Color(V.lava)},uLavaK:{value:V.lavaIntensity},uSky:{value:new THREE.Color()},uSkyK:{value:0}};
 const m=new THREE.ShaderMaterial({uniforms:U,depthWrite:false,depthTest:false,fog:false,toneMapped:false,
  vertexShader:'varying vec3 vN;varying vec3 vO;void main(){vN=normalize(mat3(modelMatrix)*normal);vO=normalize(position);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
  fragmentShader:`uniform vec3 uSun,uBody,uLava,uSky;uniform float uLavaK,uSkyK;varying vec3 vN;varying vec3 vO;${TO_SRGB}
  float hs(vec3 p){return fract(sin(dot(floor(p*9.0),vec3(12.9898,78.233,37.719)))*43758.5453);}
  void main(){float l=dot(normalize(vN),normalize(uSun));float lit=smoothstep(-.06,.25,l);
   vec3 c=uBody*(.04+.96*lit);float crack=smoothstep(.82,.97,hs(vO))*(1.0-lit);c+=(uLava*crack*2.2+uLava*.15)*uLavaK*(1.0-lit);
   c=mix(c,uSky,uSkyK);gl_FragColor=vec4(toS(c),1.0);}`});
 const mesh=new THREE.Mesh(new THREE.SphereGeometry(1,40,24),m);mesh.renderOrder=-19;mesh.visible=false;mesh.frustumCulled=false;scene.add(mesh);
 return {mesh,update(on:boolean,eye:import('three').Vector3,dir:number[],sun:import('three').Vector3,sky:number[],day:number){mesh.visible=on;if(!on)return;const D=250;
  mesh.position.set(eye.x+dir[0]*D,eye.y+dir[1]*D,eye.z+dir[2]*D);mesh.scale.setScalar(D*Math.tan((angularDeg||V.angularDeg)*Math.PI/360));U.uSun.value.copy(sun);U.uSky.value.setRGB(sky[0],sky[1],sky[2]);U.uSkyK.value=.35*day;}};
}
