// One World look pass 2 (additive). Three.js layers for the first-person ground view, all from Cosmo's One Universe pack:
// a gradient sky dome (pack stops, teal top, warm only near the sun), two far hill rings with blue aerial haze, and the
// volcano world in the sky (no ring, no light of its own, lava glow on its night side only). Placement is SEEDED; colour blends DERIVED.
// No random calls: hill shapes come from a seeded stream passed in by the caller.
type T=typeof import('three');
export const LOOK2=Object.freeze({label:'SEEDED',teal:'#437E9E',skyMid:'#88C9BB',horizonHaze:'#E4E4BD',hillsFar:'#8CA192',aerialTint:'#8CB3D6',warm:'#F2B27A',
 volcano:{azimuthDeg:191.785,elevationDeg:30.4477,angularDeg:9.292,body:'#B5532E',lava:'#FF7A2E',lavaIntensity:.35}});
const TO_SRGB='vec3 toS(vec3 c){c=max(c,0.0);return mix(c*12.92,1.055*pow(c,vec3(1.0/2.4))-.055,step(.0031308,c));}';
/** Scene units per metre: TRAV_H .5 = 1.7 m. */
export const M=.5/1.7;
/** Far ridges from Cosmo's FIX_NOTES_43c74d3 (aerial perspective k .000267/m, tint #8CB3D6). SEEDED shapes. */
export const RIDGES=Object.freeze([{d:300,crestDeg:1.99,fade:.077,hex:'#6A7864'},{d:1200,crestDeg:2.07,fade:.274,hex:'#819393'},{d:2000,crestDeg:2.24,fade:.414,hex:'#8FA1A7'},{d:4500,crestDeg:2.27,fade:.7,hex:'#A7B6C1'}]);
/** Sky dome: c = mix(horizon, zenith, pow(up,.45)); zenith = mix(pack zenith, teal mood target, .5) by day; warm only near the sun. Colours in linear, converted once. */
export function addSkyDome(THREE:T,scene:import('three').Object3D){
 const U={uUp:{value:new THREE.Vector3(0,1,0)},uSun:{value:new THREE.Vector3(0,1,0)},uZen:{value:new THREE.Color()},uHor:{value:new THREE.Color()},uDay:{value:0},
  uTeal:{value:new THREE.Color(LOOK2.teal)},uWarm:{value:new THREE.Color().setRGB(1,.875,.7055)}};
 const m=new THREE.ShaderMaterial({uniforms:U,side:THREE.BackSide,depthWrite:false,depthTest:false,fog:false,toneMapped:false,
  vertexShader:'varying vec3 vD;void main(){vD=normalize(position);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
  fragmentShader:`uniform vec3 uUp,uSun,uZen,uHor,uTeal,uWarm;uniform float uDay;varying vec3 vD;${TO_SRGB}
  void main(){vec3 d=normalize(vD);float e=dot(d,normalize(uUp));float s=max(0.0,dot(d,normalize(uSun)));
   vec3 zen=mix(uZen,mix(uZen,uTeal,.5),uDay);
   vec3 c=mix(uHor,zen,pow(clamp(e,0.0,1.0),.45));
   c=mix(c,uWarm*.9,.35*pow(s,24.0)*uDay);
   if(e<0.0)c=mix(uHor,vec3(.115,.147,.051)*mix(.15,1.0,uDay),smoothstep(0.0,-.04,e)); /* below the horizon: ground, not sky */
   gl_FragColor=vec4(toS(c),1.0);}`});
 const dome=new THREE.Mesh(new THREE.SphereGeometry(300,48,24),m);dome.renderOrder=-20;dome.frustumCulled=false;dome.visible=false;scene.add(dome);
 return {dome,update(on:boolean,cam:import('three').Vector3,up:import('three').Vector3,sun:import('three').Vector3,zen:number[],hor:number[],day:number){
  dome.visible=on;if(!on)return;dome.position.copy(cam);U.uUp.value.copy(up);U.uSun.value.copy(sun);U.uZen.value.setRGB(zen[0],zen[1],zen[2]);U.uHor.value.setRGB(hor[0],hor[1],hor[2]);U.uDay.value=day;}};
}
/** First person: a flat local ground patch (2.5 km radius) with aerial haze, plus four full 360 deg ridge rings. The 27 m sphere stays for orbit. */
export function addFlatGround(THREE:T,scene:import('three').Object3D,rand:()=>number){
 const g=new THREE.Group();g.visible=false;scene.add(g);const R=2500*M;const mats:any[]=[];
 const GU={uSunL:{value:1},uDay:{value:1},uHaze:{value:new THREE.Color(LOOK2.horizonHaze)},uTint:{value:new THREE.Color(LOOK2.aerialTint)},uBase:{value:new THREE.Color('#5F6B40')},uK:{value:.000267/M}};
 const gm=new THREE.ShaderMaterial({uniforms:GU,fog:false,toneMapped:false,
  vertexShader:'varying float vD;void main(){vD=length(position.xz);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
  fragmentShader:`uniform float uSunL,uDay,uK;uniform vec3 uHaze,uTint,uBase;varying float vD;${TO_SRGB}
  void main(){vec3 c=uBase*(.12+.88*uSunL)*mix(.15,1.0,uDay);float f=1.0-exp(-uK*vD);c=mix(c,mix(uHaze,uTint,.5)*mix(.08,1.0,uDay),f);gl_FragColor=vec4(toS(c),1.0);}`});
 const ground=new THREE.Mesh(new THREE.RingGeometry(14,R,96,4).rotateX(-Math.PI/2),gm);ground.renderOrder=-12;ground.frustumCulled=false;g.add(ground);mats.push(gm);
 for(const r of RIDGES){const rad=r.d*M,top=Math.tan(r.crestDeg*Math.PI/180)*rad;const ph=[rand()*6.28,rand()*6.28,rand()*6.28];const lobes=Math.max(6,Math.round(2*Math.PI*r.d/(3*r.d/40)/6));
  const U={uC:{value:new THREE.Color(r.hex)},uDay:{value:1},uP:{value:new THREE.Vector3(...ph)},uL:{value:lobes}};
  const m=new THREE.ShaderMaterial({uniforms:U,side:THREE.DoubleSide,fog:false,toneMapped:false,
   vertexShader:'varying vec2 vUv;varying vec3 vP;void main(){vUv=uv;vP=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
   fragmentShader:`uniform vec3 uC,uP;uniform float uDay,uL;varying vec2 vUv;varying vec3 vP;${TO_SRGB}
   void main(){float a=atan(vP.z,vP.x);float h=.55+.25*sin(uL*a+uP.x)+.12*sin(uL*2.3*a+uP.y)+.08*sin(uL*.37*a+uP.z);
    if(vUv.y>h)discard;gl_FragColor=vec4(toS(uC*mix(.1,1.0,uDay)),1.0);}`});
  const geo=new THREE.CylinderGeometry(rad,rad,top,192,1,true);geo.translate(0,top*.5,0);const mesh=new THREE.Mesh(geo,m);mesh.renderOrder=-11;mesh.frustumCulled=false;g.add(mesh);mats.push(m);}
 const life:{sp:any;r:number;a:number;w:number}[]=[];
 /** far creatures: resident sprites walking slow seeded circles on the patch at 15-120 m (mid) and 200-600 m (far); motion follows the clock t. */
 const addLife=(maps:any[])=>{maps.forEach((map,i)=>{for(const band of [0,1]){const sp=new THREE.Sprite(new THREE.SpriteMaterial({map,transparent:true,depthWrite:false,fog:false}));sp.center.set(.5,.02);
   const r=(band?200+rand()*400:15+rand()*105)*M;sp.scale.setScalar(.75);g.add(sp);life.push({sp,r,a:rand()*6.283,w:(rand()<.5?-1:1)*(.02+rand()*.04)/Math.max(1,r*.05)});}});};
 const step=(t:number)=>{for(const L of life){const a=L.a+L.w*t;L.sp.position.set(Math.cos(a)*L.r,0,Math.sin(a)*L.r);}};
 return {group:g,addLife,step,count:()=>life.length,farUnits:4600*M,update(on:boolean,groundPt:import('three').Vector3,up:import('three').Vector3,day:number,sunL:number){g.visible=on;if(!on)return;
  g.position.copy(groundPt);g.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),up);for(const m of mats)m.uniforms.uDay.value=day;GU.uSunL.value=sunL;}};
}
/** World-volcano in the sky: lit by the one sun, lava glow only on its night side, no ring, no light; blended .35*(1-fade) toward the sky by day. */
export function addSkyWorld(THREE:T,scene:import('three').Object3D){
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
  mesh.position.set(eye.x+dir[0]*D,eye.y+dir[1]*D,eye.z+dir[2]*D);mesh.scale.setScalar(D*Math.tan(V.angularDeg*Math.PI/360));U.uSun.value.copy(sun);U.uSky.value.setRGB(sky[0],sky[1],sky[2]);U.uSkyK.value=.35*day;}};
}
