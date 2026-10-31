// One World look pass 2 (additive). Three.js layers for the first-person ground view, all from Cosmo's One Universe pack:
// a gradient sky dome (pack stops, teal top, warm only near the sun), two far hill rings with blue aerial haze, and the
// volcano world in the sky (no ring, no light of its own, lava glow on its night side only). Placement is SEEDED; colour blends DERIVED.
// No random calls: hill shapes come from a seeded stream passed in by the caller.
import {landArcAngle} from './p3-ocean.mjs';
import {farLayersFor,recentreAnchor,layerPhase,HORIZON_LABEL} from './horizon-terrain.mjs';
import {activeTier} from './post-tiers.mjs';
import {VOLCANO_DAY_LOOK,crackSeed,daySkyK,crackK,skyAtUp,VOLCANO_LIT_LOOK,termEdges,setOccluder} from './fp-volcano-sky.mjs';
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
/** GENESIS X step 3: night starfield with depth (three star layers: many faint far, fewer mid, a few bright near with a soft halo; warm/cool colour by a fixed hash)
 and a nebula band (two-tone glow with dark dust lanes) around a SEEDED axis. Fixed in world directions; twinkle on the caller's world clock. No random calls. A designed look (SEEDED), not a sky survey. */
export const STARS3=Object.freeze({label:'SEEDED',nebulaAxis:[.35,.82,-.45],layers:[[300,.55,.32,.55],[120,.72,.16,1.0],[42,.93,.05,1.9]],nebulaA:'#7A2E8E',nebulaB:'#1E6E86',nebulaGain:.6});
const STAR_GLSL=`float h31(vec3 p){p=fract(p*.1031);p+=dot(p,p.yzx+33.33);return fract((p.x+p.y)*p.z);}
float n3(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(mix(h31(i),h31(i+vec3(1,0,0)),f.x),mix(h31(i+vec3(0,1,0)),h31(i+vec3(1,1,0)),f.x),f.y),mix(mix(h31(i+vec3(0,0,1)),h31(i+vec3(1,0,1)),f.x),mix(h31(i+vec3(0,1,1)),h31(i+vec3(1,1,1)),f.x),f.y),f.z);}
float f3(vec3 p){return .5*n3(p)+.25*n3(p*2.03+7.1)+.125*n3(p*4.01+3.7)+.0625*n3(p*8.05+1.3);}
vec3 starLayer(vec3 d,float sc,float th,float sz,float gain,float t,float boost){vec3 g=d*sc;vec3 c=floor(g);float h=h31(c);if(h<th-boost*.18)return vec3(0.0);
 vec3 sp=c+.25+.5*vec3(h31(c+11.3),h31(c+27.1),h31(c+53.9));float dd=length(g-sp);float m=h31(c+91.7);
 float tw=.75+.25*sin(t*(1.3+2.0*m)+m*40.0);float core=smoothstep(sz,0.0,dd);float halo=gain>1.5?.22*smoothstep(sz*2.2,0.0,dd):0.0;
 vec3 tint=mix(vec3(.70,.80,1.0),vec3(1.0,.86,.68),h31(c+5.5));return tint*(core+halo)*gain*tw*(.5+.8*m);}
vec3 nightSky(vec3 d,float e,vec3 ax,float t){vec3 b1=normalize(abs(ax.y)<.9?cross(ax,vec3(0,1,0)):cross(ax,vec3(1,0,0)));vec3 b2=cross(ax,b1);
 float lat=dot(d,ax);float band=exp(-pow(lat/.36,2.0));vec3 q=d*3.2;float n=f3(q);float n2=f3(q*2.2+4.0);float dust=smoothstep(.48,.7,f3(q*4.1+9.0));
 vec3 neb=mix(vec3(0.1946,0.0273,0.2705),vec3(0.0130,0.1559,0.2384),smoothstep(.35,.65,n2))*band*smoothstep(.25,.7,n)*(1.0-.75*dust)*${STARS3.nebulaGain.toFixed(2)};
 neb+=vec3(.55,.5,.7)*.10*exp(-pow(lat/.09,2.0))*(1.0-.8*dust); /* the bright core of the band */
 vec3 st=vec3(0.0);float bo=band*(1.0-dust);
 st+=starLayer(d,300.0,.55,.32,.55,t,bo);st+=starLayer(d,120.0,.72,.16,1.0,t,bo);st+=starLayer(d,42.0,.93,.05,1.9,t,bo*.5);
 return (neb+st)*smoothstep(-.02,.14,e);}`;
/** GENESIS X terrain: two nearer hill layers so the land steps back in more bands to the horizon (SEEDED shapes and colours). cutBay: they stop at the bay. */
export const RIDGES_NEAR=Object.freeze([{d:130,crestDeg:2.9,fade:.02,hex:'#3B6A31',lobes:9,cutBay:true},{d:650,crestDeg:2.35,fade:.16,hex:'#5A8355',lobes:14}]);
const NOISE3='float h31(vec3 p){p=fract(p*.3183099+.1);p*=17.0;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}float vn3(vec3 x){vec3 i=floor(x),f=fract(x);f=f*f*(3.0-2.0*f);return mix(mix(mix(h31(i),h31(i+vec3(1,0,0)),f.x),mix(h31(i+vec3(0,1,0)),h31(i+vec3(1,1,0)),f.x),f.y),mix(mix(h31(i+vec3(0,0,1)),h31(i+vec3(1,0,1)),f.x),mix(h31(i+vec3(0,1,1)),h31(i+vec3(1,1,1)),f.x),f.y),f.z);}';
/** Sky dome: c = mix(horizon, zenith, pow(up,.45)); zenith = mix(pack zenith, teal mood target, .5) by day; warm only near the sun. Colours in linear, converted once. */
export function addSkyDome(THREE:T,scene:import('three').Object3D){
 const U={uUp:{value:new THREE.Vector3(0,1,0)},uSun:{value:new THREE.Vector3(0,1,0)},uZen:{value:new THREE.Color()},uHor:{value:new THREE.Color()},uDay:{value:0},
  uTeal:{value:new THREE.Color(LOOK2.teal)},uWarm:{value:new THREE.Color().setRGB(1,.875,.7055)},uBelow:{value:new THREE.Color(MEADOW36.belowHorizon)},uNight:{value:0},uT:{value:0},uNebAx:{value:new THREE.Vector3(...STARS3.nebulaAxis).normalize()}};
 const m=new THREE.ShaderMaterial({uniforms:U,side:THREE.BackSide,depthWrite:false,depthTest:false,fog:false,toneMapped:false,
  vertexShader:'varying vec3 vD;void main(){vD=normalize(position);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
  fragmentShader:`uniform vec3 uUp,uSun,uZen,uHor,uTeal,uWarm,uBelow;uniform float uDay,uNight,uT;uniform vec3 uNebAx;varying vec3 vD;${TO_SRGB}${DITHER_GLSL}${STAR_GLSL}
  void main(){vec3 d=normalize(vD);float e=dot(d,normalize(uUp));float s=max(0.0,dot(d,normalize(uSun)));
   vec3 zen=mix(uZen,mix(uZen,uTeal,.5),uDay);
   vec3 c=mix(uHor,zen,pow(clamp(e,0.0,1.0),.45));
   c=mix(c,uWarm*.9,.35*pow(s,24.0)*uDay);
   c+=uWarm*(${SUNBLOOM36.core.toFixed(2)}*pow(s,${SUNBLOOM36.coreExp.toFixed(2)})+${SUNBLOOM36.halo.toFixed(2)}*pow(s,${SUNBLOOM36.haloExp.toFixed(2)})+${SUNBLOOM36.wide.toFixed(2)}*pow(s,${SUNBLOOM36.wideExp.toFixed(2)}))*uDay*step(0.0,e); /* target 36 warm sun bloom by day: a hot core over the P1 bloom threshold (so the existing P1 bloom pass blooms it on MED/HIGH/GOD) plus a soft warm halo that also shows on LOW; only above the horizon, fades with the one sun's day factor */
   if(uNight>.002&&e>-.02)c+=nightSky(d,e,normalize(uNebAx),uT)*uNight; /* GENESIS X step 3: the night starfield + nebula, faded in by the one sun's night factor and thinned by cloud cover */
   if(e<0.0)c=mix(uHor,uBelow*mix(.15,1.0,uDay),smoothstep(0.0,-.04,e)); /* below the horizon: ground, not sky */
   gl_FragColor=vec4(dith(toS(c)),1.0);}`});
 const dome=new THREE.Mesh(new THREE.SphereGeometry(300,48,24),m);dome.renderOrder=-20;dome.frustumCulled=false;dome.visible=false;scene.add(dome);
 return {dome,update(on:boolean,cam:import('three').Vector3,up:import('three').Vector3,sun:import('three').Vector3,zen:number[],hor:number[],day:number,night?:{amount:number;t:number;axis?:number[]}){
  dome.visible=on;if(!on)return;U.uNight.value=night?Math.max(0,Math.min(1,night.amount)):0;if(night){U.uT.value=night.t;if(night.axis)U.uNebAx.value.set(night.axis[0],night.axis[1],night.axis[2]).normalize();}dome.position.copy(cam);U.uUp.value.copy(up);U.uSun.value.copy(sun);U.uZen.value.setRGB(zen[0],zen[1],zen[2]);U.uHor.value.setRGB(hor[0],hor[1],hor[2]);U.uDay.value=day;}};
}
/** First person (target 36): the flat patch starts ~4 m out, just inside where the curved 8-unit planet drops below the 1.6 m eye's horizon (was 14 units, which left a flat below-horizon band and a teal planet rim between near grass and meadow). SEEDED look value. */
export const FLAT_INNER=1.2;
/** First person: a flat local ground patch (2.5 km radius) with aerial haze, plus four full 360 deg ridge rings. The 27 m sphere stays for orbit. */
export function addFlatGround(THREE:T,scene:import('three').Object3D,rand:()=>number,tierIn?:string){
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
 const RU:any[]=[];const ridgeMeshes:{mesh:any;dM:number;anchor:number[]|null}[]=[];const FAR_DRAW_U=1400;const mkRidge=(r:{d:number;crestDeg:number;fade:number;hex:string;cutBay?:boolean},ph:number[],lobes:number)=>{const rad=r.d*M,top=Math.tan(r.crestDeg*Math.PI/180)*rad;
  const U={uC:{value:new THREE.Color(r.hex)},uHz:{value:new THREE.Color(LOOK2.horizonHaze).lerp(new THREE.Color(LOOK2.aerialTint),.5)},uHz0:{value:new THREE.Color(LOOK2.horizonHaze).lerp(new THREE.Color(LOOK2.aerialTint),.5)},uF:{value:r.fade},uDay:{value:1},uP:{value:new THREE.Vector3(...ph)},uL:{value:lobes},uBay:{value:new THREE.Vector3(0,0,0)},uCut:{value:r.cutBay?1:0}};RU.push(U);
  const m=new THREE.ShaderMaterial({uniforms:U,side:THREE.DoubleSide,fog:false,toneMapped:false,
   vertexShader:'varying vec2 vUv;varying vec3 vP;varying vec3 vW;void main(){vUv=uv;vP=position;vW=(modelMatrix*vec4(position,1.0)).xyz;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
   fragmentShader:`uniform vec3 uC,uP,uHz,uBay;uniform float uDay,uL,uF,uCut;varying vec2 vUv;varying vec3 vP;varying vec3 vW;${TO_SRGB}${DITHER_GLSL}${NOISE3}
   void main(){vec3 dw=normalize(vW);float F=uL*.55; /* GENESIS X terrain: the skyline is a function of WORLD direction, so as you walk near ridges slide past far ones (parallax ~ 1/distance) and coming back shows the same hills */
    float n1=vn3(dw*F+uP),n2=vn3(dw*F*2.7+uP.yzx*1.3),n3=vn3(dw*F*7.1+uP.zxy);float rg=1.0-abs(2.0*n2-1.0);
    float h=clamp(.14+.6*n1+.26*rg*rg+.04*n3,0.0,1.0);
    if(uCut>.5){float a=atan(vP.z,vP.x)-uBay.x;a=mod(a+3.14159265,6.2831853)-3.14159265;h*=smoothstep(uBay.y*1.05,uBay.y*1.35,abs(a));} /* near hills stop at the bay, they do not stand in the sea */
    if(vUv.y>h)discard;float k=clamp(.12+uF*.8+.3*(1.0-vUv.y/max(h,.001)),0.0,.9);vec3 c=mix(uC*(.85+.3*vUv.y/max(h,.001)),uHz,k)*(.92+.16*n3); /* hazy layers: aerial haze grows with distance and toward the base (valley mist); haze colour follows the live sky horizon */
    gl_FragColor=vec4(dith(toS(c*mix(.1,1.0,uDay))),1.0);}`});
  const drawR=Math.min(rad,FAR_DRAW_U),topD=Math.tan(r.crestDeg*Math.PI/180)*drawR; /* horizonterrain F5/F6: drawn at the camera far limit at their true crest angle (same size on screen) */
  const geo=new THREE.CylinderGeometry(drawR,drawR,topD,192,1,true);geo.translate(0,topD*.5,0);const mesh=new THREE.Mesh(geo,m);mesh.renderOrder=-11;mesh.frustumCulled=false;g.add(mesh);mats.push(m);ridgeMeshes.push({mesh,dM:r.d,anchor:null as number[]|null});};
 for(const r of RIDGES){const ph=[rand()*6.28,rand()*6.28,rand()*6.28];const lobes=Math.max(6,Math.round(2*Math.PI*r.d/(3*r.d/40)/6));mkRidge(r,ph,lobes);}
 for(const r of RIDGES_NEAR){const ph=[rand()*6.28,rand()*6.28,rand()*6.28];mkRidge(r,ph,r.lobes);}
 /* GENESIS X horizonterrain (SEEDED, Cosmo's pack): far layers F5 9 km and F6 18 km by quality tier (HIGH adds F5, GOD adds F6). Phases come from each layer's
    seed tag (no stream draws, so every older layer keeps its seeded shape); colour and fade are the pack's DERIVED aerial values; lit by the one sun only via uDay. */
 const tier=tierIn||(()=>{try{const w:any=globalThis as any;return activeTier(w.localStorage,{phone:(w.innerWidth||1280)<820,cores:w.navigator?.hardwareConcurrency,memoryGB:w.navigator?.deviceMemory,reducedMotion:!!w.matchMedia?.('(prefers-reduced-motion: reduce)').matches});}catch{return 'MED';}})();
 const farIds:string[]=[];for(const l of farLayersFor(tier)){mkRidge({d:l.distance_m,crestDeg:l.crest_elev_deg,fade:l.fade,hex:l.colour.hex},layerPhase(l.noise.seed_tag),Math.max(6,Math.round(2*Math.PI*l.distance_m/l.noise.wavelength_m/6)));farIds.push(l.id);}
 (globalThis as any).__lwHorizon={label:HORIZON_LABEL,tier,far:farIds,rings:ridgeMeshes.length,recentres:0}; /* after the old layers, so their seeded shapes keep their stream draws */
 const life:{sp:any;r:number;a:number;w:number}[]=[];
 /** far creatures: resident sprites walking slow seeded circles on the patch at 25-120 m (mid; target 36: nothing crowds the near frame) and 200-600 m (far); motion follows the clock t. */
 const addLife=(maps:any[])=>{maps.forEach((map,i)=>{for(const band of [0,1]){const sp=new THREE.Sprite(new THREE.SpriteMaterial({map,transparent:true,depthWrite:false,fog:false}));sp.center.set(.5,.02);
   const r=(band?200+rand()*400:25+rand()*95)*M;sp.scale.setScalar(.75);g.add(sp);life.push({sp,r,a:rand()*6.283,w:(rand()<.5?-1:1)*(.02+rand()*.04)/Math.max(1,r*.05)});}});};
 const step=(t:number,bay?:{bearing:number;halfWidth:number;innerM:number}|null)=>{for(const L of life){const a0=L.a+L.w*t;const a=bay?landArcAngle(bay,L.r/M,a0):a0; /* GENESIS X: walkers turn back at the P3 bay shore, so none walks on the drawn sea */L.sp.position.set(Math.cos(a)*L.r,0,Math.sin(a)*L.r);}};
 return {group:g,addLife,step,count:()=>life.length,farUnits:4600*M,update(on:boolean,groundPt:import('three').Vector3,up:import('three').Vector3,day:number,sunL:number,face?:{fwd:import('three').Vector3;bearing:number}|null,look?:{hor?:number[];bay?:{bearing:number;halfWidth:number}}|null){g.visible=on;if(!on)return;for(const U of RU){if(look?.hor)U.uHz.value.setRGB(look.hor[0],look.hor[1],look.hor[2]).lerp(U.uHz0.value,.5);if(look?.bay)U.uBay.value.set(look.bay.bearing,look.bay.halfWidth,1);} /* GENESIS X terrain: haze takes the live sky horizon colour (dusk, night, storm) */
  g.position.copy(groundPt);g.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),up);if(face)g.quaternion.premultiply(yawToward(THREE,g.quaternion,up,face.fwd,face.bearing)); /* GENESIS X step 0: optional yaw so a SEEDED local bearing (the P3 bay) lies along a given world heading */
  /* GENESIS X horizonterrain parallax: each ridge ring is world-fixed at an anchor and only recentres once the ground point has moved 5% of its distance; it then eases back over
     ~0.5 s (instead of a pop), so near rings slide past far ones while you walk. Pure maths on positions, no random calls, no clock. */
  g.updateMatrixWorld(true);const gp=[groundPt.x,groundPt.y,groundPt.z];for(const rm of ridgeMeshes){const prev=rm.anchor;const nx=prev?recentreAnchor(prev,gp,rm.dM,M):gp.slice();
   if(prev&&nx!==prev){(globalThis as any).__lwHorizon&&((globalThis as any).__lwHorizon.recentres++);}rm.anchor=prev&&nx!==prev?[prev[0]+(nx[0]-prev[0])*.12,prev[1]+(nx[1]-prev[1])*.12,prev[2]+(nx[2]-prev[2])*.12]:nx;
   const lp=g.worldToLocal(new THREE.Vector3(rm.anchor[0],rm.anchor[1],rm.anchor[2]));rm.mesh.position.set(lp.x,0,lp.z);}for(const m of mats)m.uniforms.uDay.value=day;GU.uSunL.value=sunL;}};
}
/** Yaw (about up) that turns the local bearing b (local dir (cos b,0,sin b) under q) onto fwd projected into the tangent plane. Pure maths, no random calls. */
export function yawToward(THREE:T,q:import('three').Quaternion,up:import('three').Vector3,fwd:import('three').Vector3,b:number){
 const u=up.clone().normalize();const d=new THREE.Vector3(Math.cos(b),0,Math.sin(b)).applyQuaternion(q);d.addScaledVector(u,-d.dot(u));const f=fwd.clone().addScaledVector(u,-fwd.dot(u));
 if(d.lengthSq()<1e-8||f.lengthSq()<1e-8)return new THREE.Quaternion();d.normalize();f.normalize();const th=Math.atan2(u.dot(new THREE.Vector3().crossVectors(d,f)),d.dot(f));return new THREE.Quaternion().setFromAxisAngle(u,th);}
/** World-volcano in the sky: lit by the one sun, lava glow only on its night side, no ring, no light; blended .35*(1-fade) toward the sky by day. */
export function addSkyWorld(THREE:T,scene:import('three').Object3D,angularDeg?:number){
 /* GENESIS X: Cosmo's spec. Cracks are drawn in the shader (seeded Voronoi edges, ~0.02 wide on the sphere, fwidth antialiased; no texture). By day the sky lies
    over the disc at no more than 0.2 (VOLCANO_DAY_LOOK.daySkyMax), cracks at 0.3 of night strength, plus a thin sunlit crescent rim from the one sun. Night (day=0) is as before. */
 const V=LOOK2.volcano,L=VOLCANO_DAY_LOOK,sd=crackSeed();const U={uSun:{value:new THREE.Vector3(0,1,0)},uBody:{value:new THREE.Color(V.body)},uLava:{value:new THREE.Color(V.lava)},uLavaK:{value:V.lavaIntensity},uSky:{value:new THREE.Color()},uSkyK:{value:0},
  uCrack:{value:new THREE.Color(L.crackHex)},uCrackFall:{value:new THREE.Color(L.crackFallHex)},uDayBody:{value:new THREE.Color(L.dayBodyHex)},uNightBody:{value:new THREE.Color(L.nightBodyHex)},uDay:{value:0},uCrackK:{value:1},uSeed:{value:new THREE.Vector3(sd[0],sd[1],sd[2])},uCell:{value:L.cellScale},uLine:{value:L.lineWidth},uDayBodyK:{value:L.dayBodyK},uLitBody:{value:new THREE.Color(VOLCANO_LIT_LOOK.litHex)},uLitCrackDark:{value:VOLCANO_LIT_LOOK.litCrackDark},uTerm:{value:new THREE.Vector2(...termEdges())}};
 const m=new THREE.ShaderMaterial({uniforms:U,depthWrite:false,depthTest:false,fog:false,toneMapped:false,
  vertexShader:'varying vec3 vN;varying vec3 vO;varying vec3 vW;void main(){vN=normalize(mat3(modelMatrix)*normal);vO=normalize(position);vW=(modelMatrix*vec4(position,1.0)).xyz;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
  fragmentShader:`uniform vec3 uSun,uBody,uLava,uSky,uCrack,uCrackFall,uDayBody,uNightBody,uSeed;uniform vec3 uLitBody;uniform float uLitCrackDark;uniform vec2 uTerm;uniform float uLavaK,uSkyK,uDay,uCrackK,uCell,uLine,uDayBodyK;varying vec3 vN;varying vec3 vO;varying vec3 vW;${TO_SRGB}
  vec3 h3(vec3 p){p=vec3(dot(p,vec3(127.1,311.7,74.7)),dot(p,vec3(269.5,183.3,246.1)),dot(p,vec3(113.5,271.9,124.6)));return fract(sin(p)*43758.5453);}
  float vEdge(vec3 x){vec3 n=floor(x),f=fract(x);vec3 mr=vec3(0.0);float md=8.0;vec3 mg=vec3(0.0);
   for(int k=-1;k<=1;k++)for(int j=-1;j<=1;j++)for(int i=-1;i<=1;i++){vec3 g=vec3(float(i),float(j),float(k));vec3 r=g+h3(n+g+uSeed)-f;float d=dot(r,r);if(d<md){md=d;mr=r;mg=g;}}
   md=8.0;for(int k=-2;k<=2;k++)for(int j=-2;j<=2;j++)for(int i=-2;i<=2;i++){vec3 g=mg+vec3(float(i),float(j),float(k));vec3 r=g+h3(n+g+uSeed)-f;if(dot(mr-r,mr-r)>1e-5)md=min(md,dot(.5*(mr+r),normalize(r-mr)));}
   return md;}
  void main(){float l=dot(normalize(vN),normalize(uSun));float lit=smoothstep(uTerm.x,uTerm.y,l); /* #741: crisp terminator, softness 0.05, same centre as before */
   float e=vEdge(vO*uCell)/uCell;float fw=max(fwidth(e),1e-5);float hw=uLine*.5;float crack=1.0-smoothstep(hw-fw,hw+fw,e);
   vec3 cc=mix(uCrack,uCrackFall,smoothstep(0.0,hw,e));
   vec3 side=mix(uNightBody,uDayBody,uDay);vec3 litSurf=uLitBody*(1.0-uLitCrackDark*crack); /* #741: the lit crescent is the #B5532E surface with the cracks as darker lines, not a flat wash */vec3 c=mix(side,litSurf,lit); /* #739: the face away from the sun is a dark rust body (night (28,16,14), day #B5532E×0.4); sky bodies take no scene light, only this shader */
   c+=cc*crack*2.2*uLavaK*uCrackK*(1.0-lit);
   vec3 vv=normalize(cameraPosition-vW);float limb=1.0-max(dot(normalize(vN),vv),0.0);float rim=smoothstep(-.02,.12,l)*smoothstep(.72,.97,limb)*uDay;c+=vec3(1.0,.93,.82)*rim*.6;
   gl_FragColor=vec4(mix(toS(c),toS(uSky),uSkyK),1.0);}`}); /* #739: the air over the disc is laid on in display (sRGB) space at 0.15, so blue sky over dark rust stays warm instead of going mauve */
 const mesh=new THREE.Mesh(new THREE.SphereGeometry(1,64,40),m);mesh.renderOrder=-19;mesh.visible=false;mesh.frustumCulled=false;scene.add(mesh);
 return {mesh,update(on:boolean,eye:import('three').Vector3,dir:number[],sun:import('three').Vector3,sky:number[],day:number,zen?:number[]|null,up?:import('three').Vector3|null){mesh.visible=on;setOccluder(on,dir,angularDeg||V.angularDeg);if(!on)return;const D=250;
  if(zen&&up){const u=up.clone().normalize();const tl=new THREE.Color(LOOK2.teal);sky=skyAtUp(sky,zen,[tl.r,tl.g,tl.b],day,dir[0]*u.x+dir[1]*u.y+dir[2]*u.z);} /* #738: the dome's colour at the disc's elevation, not the pale horizon */
  mesh.position.set(eye.x+dir[0]*D,eye.y+dir[1]*D,eye.z+dir[2]*D);mesh.scale.setScalar(D*Math.tan((angularDeg||V.angularDeg)*Math.PI/360));U.uSun.value.copy(sun);U.uSky.value.setRGB(sky[0],sky[1],sky[2]);
  U.uSkyK.value=daySkyK(day);U.uCrackK.value=crackK(day);U.uDay.value=Math.max(0,Math.min(1,day||0));(globalThis as any).__lwVolcanoLook={skyK:U.uSkyK.value,crackK:U.uCrackK.value,day:U.uDay.value,bodyK:L.dayBodyK,sky:sky.map(v=>+v.toFixed(4))};}};
}
