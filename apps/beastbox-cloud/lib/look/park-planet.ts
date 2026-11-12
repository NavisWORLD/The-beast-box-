// Park look PKU1: the orbit planet shell. Presentation only, orbit only, Park only.
// - A Park twin of the page's planet material: same uniforms (read only), a saturated toy-world grade on its final colour
//   (bright shallows toward #4DD9FC, land toward #79D389). The page's material is never edited.
// - A painterly cloud shell (seeded value noise in latitude bands) and a candy-blue atmosphere limb, lit by the one sun.
//   The night side faces away from that sun. No new light, no second sun, no unseeded draws.
// Clouds drift on the one world tick; reduced motion holds them still. Nothing here writes world, beast or traveler state.
import {stream01} from './seed.ts';
import {PARK_DAY,PARK_NIGHT,PK_OUT,hexRgb} from './park-palette.ts';

export const PARK_PLANET_LABEL='Park planet shell · SIMULATED clouds';
/** Shell detail per tier (spec K11): LOW rim only, MED 32 segments, HIGH 48, GOD 64. */
export const PARK_PLANET_BUDGET=Object.freeze({
 LOW:{segments:0,limb:true,costMs:.2},
 MED:{segments:32,limb:true,costMs:.3},
 HIGH:{segments:48,limb:true,costMs:.5},
 GOD:{segments:64,limb:true,costMs:.7},
} as Record<string,{segments:number;limb:boolean;costMs:number}>);
export function planetBudget(tier:string){return PARK_PLANET_BUDGET[tier]||PARK_PLANET_BUDGET.MED;}

const GRADE=`uniform vec3 uPkShallow,uPkDeep,uPkMeadow;
float pkLum(vec3 c){return dot(c,vec3(.2126,.7152,.0722));}
/* Park re-colour that keeps the light: each surface keeps its own brightness (sun, night side, texture detail) and takes a Park hue.
   Seas go pool-cyan, every land biome (icy, violet or grey included) goes meadow green, warm soil stays biscuit sand or terracotta. */
vec3 pkPlanet(vec3 c){
 float l=pkLum(c);
 float mx=max(c.r,max(c.g,c.b)),mn=min(c.r,min(c.g,c.b));float sat=(mx-mn)/max(mx,1e-3);
 float water=step(c.r,c.b)*smoothstep(.02,.07,c.b-c.g*.92)*smoothstep(.2,.36,sat);
 float warm=smoothstep(.05,.15,c.r-c.g)*smoothstep(.08,.2,c.r-c.b)*(1.0-water);
 float ice=smoothstep(.5,.75,l)*(1.0-smoothstep(.1,.28,sat))*(1.0-water);
 vec3 sand=vec3(.96,.84,.63),cliff=vec3(.88,.54,.38);
 vec3 meadow=mix(uPkMeadow*.72,uPkMeadow*1.08,smoothstep(.2,.65,l));
 vec3 landT=mix(meadow,mix(cliff,sand,smoothstep(.45,.7,l)),warm);
 float lL=l*mix(1.0,.7,ice);
 vec3 land=landT*(lL/max(pkLum(landT),.05));
 vec3 seaT=mix(uPkDeep,uPkShallow,smoothstep(.12,.45,l));
 vec3 sea=seaT*(l*1.2/max(pkLum(seaT),.05));
 vec3 o=mix(land,sea,water);
 float lo=pkLum(o);o=max(vec3(0.0),mix(vec3(lo),o,1.15));
 return mix(c,o,.88);
}
`;

/** Insert the Park grade into a planet fragment shader: helpers before main, grade on the final colour. Null if it does not fit. */
export function gradePlanetShader(src:string){
 const i=src.indexOf('void main(');
 const j=src.lastIndexOf('}');
 if(i<0||j<i)return null;
 return src.slice(0,i)+GRADE+src.slice(i,j)+'gl_FragColor.rgb=pkPlanet(gl_FragColor.rgb);\n'+src.slice(j);
}

const SHELL_VERT=`varying vec3 vN;varying vec3 vW;
void main(){vN=normalize(position);vec4 w=modelMatrix*vec4(position,1.0);vW=w.xyz;gl_Position=projectionMatrix*viewMatrix*w;}`;
const CLOUD_FRAG=`uniform vec3 uSun,uLit,uShade;uniform float uDrift,uSeed,uOpacity;
varying vec3 vN;varying vec3 vW;
float h31(vec3 p){p=fract(p*.1031+uSeed);p+=dot(p,p.yzx+33.33);return fract((p.x+p.y)*p.z);}
float vn3(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);
 return mix(mix(mix(h31(i),h31(i+vec3(1,0,0)),f.x),mix(h31(i+vec3(0,1,0)),h31(i+vec3(1,1,0)),f.x),f.y),
  mix(mix(h31(i+vec3(0,0,1)),h31(i+vec3(1,0,1)),f.x),mix(h31(i+vec3(0,1,1)),h31(i+vec3(1,1,1)),f.x),f.y),f.z);}
void main(){
 vec3 n=normalize(vN);
 float a=uDrift;vec3 q=vec3(n.x*cos(a)-n.z*sin(a),n.y,n.x*sin(a)+n.z*cos(a));
 float f=vn3(q*3.2)*.55+vn3(q*7.1)*.3+vn3(q*15.0)*.15;
 float band=.5+.5*sin(n.y*7.5+f*3.0);
 float k=smoothstep(.64,.8,f*.75+band*.35);
 float sunK=dot(n,normalize(uSun));
 float lit=smoothstep(-.25,.45,sunK);
 vec3 col=mix(uShade,uLit,lit);
 vec3 V=normalize(cameraPosition-vW);
 float edge=smoothstep(.0,.25,dot(n,V));
 float alpha=k*uOpacity*edge*mix(.35,1.0,lit);
 gl_FragColor=vec4(col,alpha);
${PK_OUT}}`;
const LIMB_FRAG=`uniform vec3 uSun,uDayC,uNightC;
varying vec3 vN;varying vec3 vW;
void main(){
 vec3 n=normalize(vN);vec3 V=normalize(cameraPosition-vW);
 float rim=pow(1.0-abs(dot(n,V)),2.6);
 float day=smoothstep(-.3,.35,dot(n,normalize(uSun)));
 vec3 col=mix(uNightC,uDayC,day);
 gl_FragColor=vec4(col*rim*mix(.35,1.25,day),rim*mix(.3,.95,day));
${PK_OUT}}`;

/** sRGB hex to linear: the planet and shells go through the page's linear output path. */
const lin=(h:string)=>hexRgb(h).map(v=>Math.pow(v,2.2)) as [number,number,number];

type Opts={
 planet:()=>any;radius:number;seed?:string;
 getLook?:()=>string;
 /** True while the camera is out in orbit (the Genesis ground is hidden then). */
 inOrbit:()=>boolean;
 sunDir:()=>{x:number;y:number;z:number};
 tier?:()=>string;
 tick?:()=>number;
 reduced?:()=>boolean;
 parent?:{add:(o:any)=>void;remove?:(o:any)=>void};
};

export function attachParkPlanet(THREE:typeof import('three'),opts:Opts){
 let twin:{base:any;mat:any}|null=null;
 let clouds:any=null,limb:any=null,builtTier='';
 let on=false;
 const seed=opts.seed||'park';
 const seedF=stream01(seed+':park-planet:clouds');
 const drift0=stream01(seed+':park-planet:drift')*Math.PI*2;
 function restoreMaterial(){
  const p=opts.planet();
  if(p&&twin&&p.material===twin.mat)p.material=twin.base;
 }
 function hideShells(){if(clouds)clouds.visible=false;if(limb)limb.visible=false;}
 function build(tier:string){
  const B=planetBudget(tier);
  for(const m of [clouds,limb]){if(m){opts.parent?.remove?.(m);m.geometry.dispose();m.material.dispose();}}
  clouds=null;limb=null;
  if(B.segments>0){
   const cm=new THREE.ShaderMaterial({
    uniforms:{uSun:{value:new THREE.Vector3(0,1,0)},uLit:{value:new THREE.Color().setRGB(...lin(PARK_DAY.cloudLit))},uShade:{value:new THREE.Color().setRGB(...lin(PARK_NIGHT.skyFill)).multiplyScalar(.35)},uDrift:{value:0},uSeed:{value:seedF},uOpacity:{value:.72}},
    vertexShader:SHELL_VERT,fragmentShader:CLOUD_FRAG,transparent:true,depthWrite:false,fog:false,
   });
   cm.name='park:planet-clouds';
   clouds=new THREE.Mesh(new THREE.SphereGeometry(opts.radius*1.03,B.segments,Math.round(B.segments*.6)),cm);
   clouds.name='park-planet-clouds';clouds.renderOrder=3;
   opts.parent?.add(clouds);
  }
  const lm=new THREE.ShaderMaterial({
   uniforms:{uSun:{value:new THREE.Vector3(0,1,0)},uDayC:{value:new THREE.Color().setRGB(...lin(PARK_DAY.skyHorizon))},uNightC:{value:new THREE.Color().setRGB(...lin('#1A2F8A'))}},
   vertexShader:SHELL_VERT,fragmentShader:LIMB_FRAG,transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,side:THREE.FrontSide,fog:false,
  });
  lm.name='park:planet-limb';
  limb=new THREE.Mesh(new THREE.SphereGeometry(opts.radius*1.06,Math.max(32,B.segments),Math.max(20,Math.round(B.segments*.6))),lm);
  limb.name='park-planet-limb';limb.renderOrder=4;
  opts.parent?.add(limb);
  builtTier=tier;
 }
 function apply(){
  const look=(opts.getLook?opts.getLook():'park')==='park';
  on=look&&opts.inOrbit();
  const p=opts.planet();
  if(!look){restoreMaterial();hideShells();return null;}
  /* Nov 12: the Park colour twin now stays on from orbit down to the ground (one world, one palette); only the cloud shell and limb are orbit-only */
  if(p&&p.material&&p.material.fragmentShader){
   if(!twin||(twin.base!==p.material&&twin.mat!==p.material)){
    const frag=gradePlanetShader(p.material.fragmentShader);
    if(frag){
     const base=p.material;
     const mat=new THREE.ShaderMaterial({
      uniforms:{...base.uniforms,uPkShallow:{value:new THREE.Color().setRGB(...lin(PARK_DAY.oceanShallow))},uPkDeep:{value:new THREE.Color().setRGB(...lin(PARK_DAY.oceanDeep))},uPkMeadow:{value:new THREE.Color().setRGB(...lin(PARK_DAY.meadowSun))}},
      vertexShader:base.vertexShader,fragmentShader:frag,side:base.side,transparent:base.transparent,depthWrite:base.depthWrite,depthTest:base.depthTest,
      extensions:base.extensions,defines:base.defines,fog:false,
     });
     mat.name='park:planet';
     twin={base,mat};
    }
   }
   if(twin&&p.material===twin.base)p.material=twin.mat;
  }
  const tier=String(opts.tier?.()||'MED');
  if(tier!==builtTier)build(tier);
  const s=opts.sunDir();
  const reduced=!!opts.reduced?.();
  const drift=reduced?0:drift0+Number(opts.tick?.()||0)*.0025;
  if(!on){hideShells();return {drift};}
  if(clouds){clouds.visible=true;clouds.material.uniforms.uSun.value.set(s.x,s.y,s.z);clouds.material.uniforms.uDrift.value=drift;}
  if(limb){limb.visible=true;limb.material.uniforms.uSun.value.set(s.x,s.y,s.z);}
  return {drift};
 }
 return {
  apply,
  get on(){return on;},
  state(){return {on,tier:builtTier||null,clouds:!!clouds&&clouds.visible,limb:!!limb&&limb.visible,graded:!!twin&&opts.planet()?.material===twin.mat,label:PARK_PLANET_LABEL};},
  dispose(){restoreMaterial();for(const m of [clouds,limb]){if(m){opts.parent?.remove?.(m);m.geometry.dispose();m.material.dispose();}}twin?.mat.dispose();},
 };
}
