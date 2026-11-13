// Park look PKU1: the orbit planet shell. Presentation only, orbit only, Park only.
// - A Park twin of the page's planet material: same uniforms (read only), a saturated toy-world grade on its final colour
//   (bright shallows toward #4DD9FC, land toward #79D389). The page's material is never edited.
// - A painterly cloud shell (seeded value noise in latitude bands) and a candy-blue atmosphere limb, lit by the one sun.
//   The night side faces away from that sun. No new light, no second sun, no unseeded draws.
// Clouds drift on the one world tick; reduced motion holds them still. Nothing here writes world, beast or traveler state.
import {stream01} from './seed.ts';
import {bakeGroundDetail,groundDetailSize} from './third-party/texture-lab.ts';
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

/* Realistic-cosmic surface light, inside the planet's own shader so displaced mountains never poke through a shell:
   soft terminator with a twilight band, cloud shadows (the cloud field sampled toward the sun), sea-only sun glint + fresnel.
   Needs the page's world-position varying (vWp), height map and eqUV; skipped when the shader does not have them. */
const COSMIC=`uniform vec3 uPkSun;uniform float uPkDrift,uPkSeed,uPkFx,uPkCloud,uPkDet;uniform sampler2D uPkDetail;
float pkH3(vec3 p){p=fract(p*.1031+uPkSeed);p+=dot(p,p.yzx+33.33);return fract((p.x+p.y)*p.z);}
float pkV3(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);
 return mix(mix(mix(pkH3(i),pkH3(i+vec3(1,0,0)),f.x),mix(pkH3(i+vec3(0,1,0)),pkH3(i+vec3(1,1,0)),f.x),f.y),
  mix(mix(pkH3(i+vec3(0,0,1)),pkH3(i+vec3(1,0,1)),f.x),mix(pkH3(i+vec3(0,1,1)),pkH3(i+vec3(1,1,1)),f.x),f.y),f.z);}
vec3 pkCosmic(vec3 c){
 vec3 n=normalize(vWp);vec3 L=normalize(uPkSun);vec3 V=normalize(cameraPosition-vWp);float sd=dot(n,L);
 /* relief: the height map's slope lights the hills (east/north tangent frame); close up, the third-party torus-tiled Sobel detail (TextureLab port) adds fine relief, triplanar so no tile grid */
 if(uPkFx>0.0&&uUseMap>.5){float h0=texture2D(uHeight,eqUV(n)).r;vec3 E=normalize(cross(vec3(0.0,1.0,0.0),n)+vec3(1e-4,0.0,0.0));vec3 N=cross(n,E);
  float hx=texture2D(uHeight,eqUV(normalize(n+E*.012))).r-h0,hy=texture2D(uHeight,eqUV(normalize(n+N*.012))).r-h0;float land=smoothstep(.42,.45,h0);
  vec3 nr=normalize(n-(E*hx+N*hy)*16.0);c*=1.0+clamp(dot(nr,L)-sd,-.45,.45)*1.5*land*smoothstep(-.1,.2,sd);
  if(uPkDet>0.0){float near=smoothstep(7.0,1.2,distance(cameraPosition,vWp));if(near>0.0){vec3 w=abs(n);w/=w.x+w.y+w.z;
   vec2 t1=(texture2D(uPkDetail,vWp.zy*.55).xy*w.x+texture2D(uPkDetail,vWp.xz*.55).xy*w.y+texture2D(uPkDetail,vWp.xy*.55).xy*w.z)*2.0-1.0;
   vec2 t2=(texture2D(uPkDetail,vWp.yz*2.3+.37).xy*w.x+texture2D(uPkDetail,vWp.zx*2.3+.37).xy*w.y+texture2D(uPkDetail,vWp.yx*2.3+.37).xy*w.z)*2.0-1.0;
   vec2 tn=t1*.65+t2*.35;vec3 nd=normalize(n+(E*tn.x+N*tn.y)*.7);c*=1.0+clamp(dot(nd,L)-sd,-.4,.4)*.9*near*uPkDet*land;}}}
 if(uPkCloud>0.0){vec3 m=normalize(n+L*.035);float a=uPkDrift;vec3 q=vec3(m.x*cos(a)-m.z*sin(a),m.y,m.x*sin(a)+m.z*cos(a));
  float f=pkV3(q*3.2)*.55+pkV3(q*7.1)*.3+pkV3(q*15.0)*.15;float band=.5+.5*sin(m.y*7.5+f*3.0);
  c*=1.0-smoothstep(.62,.82,f*.75+band*.35)*.3*uPkCloud*smoothstep(-.05,.3,sd);}
 float night=1.0-smoothstep(-.22,.1,sd);float twi=exp(-pow((sd+.02)/.1,2.0));
 c=mix(c,c*vec3(.2,.26,.52),night*.5*uPkFx);c+=vec3(.9,.42,.2)*twi*.07*uPkFx;
 float sea=(1.0-smoothstep(.40,.43,texture2D(uHeight,eqUV(n)).r))*step(.5,uUseMap);
 vec3 H=normalize(L+V);float nh=max(dot(n,H),0.0);float lit=smoothstep(-.05,.2,sd);
 c+=(vec3(1.0,.95,.82)*(pow(nh,220.0)*2.4+pow(nh,28.0)*.12)+vec3(.45,.72,1.0)*pow(1.0-max(dot(n,V),0.0),5.0)*.3)*sea*lit*uPkFx;
 return c;}
/* seeded biomes after the Park grade (so the grade cannot repaint them): snow caps by latitude and peak height, dry sand belts, darker forest;
   each keeps the pixel's own light so the day stays Park-bright. Designed, not a climate model. */
vec3 pkBiome(vec3 c){
 if(uPkFx<=0.0||uUseMap<.5)return c;
 vec3 n=normalize(vWp);float h=texture2D(uHeight,eqUV(n)).r;float land=smoothstep(.43,.47,h);if(land<=0.0)return c;
 float lat=abs(n.y);float nz=pkV3(n*3.1+11.0),nz2=pkV3(n*9.0+3.0);float lum=dot(c,vec3(.2126,.7152,.0722));
 float snow=clamp(smoothstep(.8,.9,lat+(h-.5)*.45+(nz2-.5)*.12)+smoothstep(.8,.9,h),0.0,1.0);
 float desert=smoothstep(.6,.7,nz)*(1.0-smoothstep(.16,.4,lat))*(1.0-snow);
 float forest=smoothstep(.48,.62,nz2)*(1.0-smoothstep(.52,.6,nz))*(1.0-desert)*(1.0-snow)*smoothstep(.12,.28,lat);
 vec3 o=mix(c,vec3(.93,.78,.5)*clamp(lum*2.1,.12,1.0),desert*.7);
 o=mix(o,o*vec3(.6,.78,.58),forest*.65);
 o=mix(o,vec3(.94,.97,1.0)*clamp(lum*2.4+.1,.2,1.1),snow*.85);
 return mix(c,o,land);}
`;
/** Insert the Park grade into a planet fragment shader: helpers before main, grade on the final colour. Null if it does not fit. */
export function gradePlanetShader(src:string){
 const i=src.indexOf('void main(');
 const j=src.lastIndexOf('}');
 if(i<0||j<i)return null;
 const cosmic=/varying vec3 vWp/.test(src)&&/uHeight/.test(src)&&/vec2 eqUV\(/.test(src)&&/uUseMap/.test(src);
 return src.slice(0,i)+GRADE+(cosmic?COSMIC:'')+src.slice(i,j)+(cosmic?'gl_FragColor.rgb=pkCosmic(gl_FragColor.rgb);\n':'')+'gl_FragColor.rgb=pkPlanet(gl_FragColor.rgb);\n'+(cosmic?'gl_FragColor.rgb=pkBiome(gl_FragColor.rgb);\n':'')+src.slice(j);
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
/* Realistic-cosmic pass (Cory, Nov 12: "Realistic cosmic"). A designed look, not a physical simulation:
   - limb: Rayleigh-blue in-scatter along the rim of the disc, brighter toward the sun (forward-scatter phase), warm twilight band at the terminator;
   - halo: an outer back-face shell glowing by how closely each view ray grazes the planet (blue by day, orange at twilight, dark on the night side);
   - terminator: a soft night side with a twilight band; cloud shadow: the cloud field sampled toward the sun, darkening the ground below;
   - glint: sun specular + fresnel on the sea only (sea mask from the page's height map), the one sun's direction. */
const LIMB_FRAG=`uniform vec3 uSun,uDayC,uNightC;
varying vec3 vN;varying vec3 vW;
void main(){
 vec3 n=normalize(vN);vec3 V=normalize(cameraPosition-vW);vec3 L=normalize(uSun);
 float rim=pow(1.0-abs(dot(n,V)),2.8);
 float sd=dot(n,L);float day=smoothstep(-.28,.32,sd);float twi=exp(-pow(sd/.16,2.0));
 float ph=.75*(1.0+pow(max(0.0,dot(-V,L))*.5+.5,2.0));
 vec3 col=mix(uNightC*.35,uDayC*ph,day)+vec3(1.0,.46,.2)*twi*.8;
 gl_FragColor=vec4(col*rim*1.35,rim*clamp(.25+.85*day+.5*twi,0.0,1.0));
${PK_OUT}}`;
const HALO_FRAG=`uniform vec3 uSun,uDayC;uniform float uR,uRa;
varying vec3 vN;varying vec3 vW;
void main(){
 vec3 D=normalize(vW-cameraPosition);float t=-dot(cameraPosition,D);vec3 c=cameraPosition+D*t;float d=length(c);
 float h=clamp((d-uR)/(uRa-uR),0.0,1.0);float g=exp(-h*4.2)*(1.0-h);
 vec3 n0=normalize(c);vec3 L=normalize(uSun);float sd=dot(n0,L);float day=smoothstep(-.3,.3,sd);float twi=exp(-pow(sd/.18,2.0));
 vec3 col=uDayC*(.3+day*1.2)+vec3(1.0,.5,.22)*twi*.9;
 gl_FragColor=vec4(col*g*1.3,g*clamp(.35+.65*day+.5*twi,0.0,1.0));
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
 let detailTex:any=null,detailSize=0,flat:any=null;const seedStr=String(opts.seed||'tiny');
 const flatDetail=()=>{if(!flat){flat=new THREE.DataTexture(new Uint8Array([128,128,255,255]),1,1,THREE.RGBAFormat);flat.needsUpdate=true;}return flat;};
 let halo:any=null;
 const shells=()=>[clouds,limb,halo];
 let on=false;
 const seed=opts.seed||'park';
 const seedF=stream01(seed+':park-planet:clouds');
 const drift0=stream01(seed+':park-planet:drift')*Math.PI*2;
 function restoreMaterial(){
  const p=opts.planet();
  if(p&&twin&&p.material===twin.mat)p.material=twin.base;
 }
 function hideShells(){for(const m of shells())if(m)m.visible=false;}
 function build(tier:string){
  const B=planetBudget(tier);
  for(const m of shells()){if(m){opts.parent?.remove?.(m);m.geometry.dispose();m.material.dispose();}}
  clouds=null;limb=null;halo=null;
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
  const R=opts.radius,segs=Math.max(32,B.segments),rings=Math.max(20,Math.round(B.segments*.6));
  const shell=(name:string,frag:string,r:number,u:any,o:any,order:number)=>{const m=new THREE.ShaderMaterial({uniforms:{uSun:{value:new THREE.Vector3(0,1,0)},...u},vertexShader:SHELL_VERT,fragmentShader:frag,transparent:true,depthWrite:false,fog:false,...o});m.name='park:'+name;const me=new THREE.Mesh(new THREE.SphereGeometry(R*r,segs,rings),m);me.name=name;me.renderOrder=order;opts.parent?.add(me);return me;};
  /* outer halo on every tier (cheap, one draw): LOW keeps a real atmosphere edge */
  halo=shell('park-planet-halo',HALO_FRAG,1.16,{uDayC:{value:new THREE.Color().setRGB(...lin('#4FA8FF'))},uR:{value:R},uRa:{value:R*1.16}},{blending:THREE.AdditiveBlending,side:THREE.BackSide},5);
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
      uniforms:{...base.uniforms,uPkShallow:{value:new THREE.Color().setRGB(...lin(PARK_DAY.oceanShallow))},uPkDeep:{value:new THREE.Color().setRGB(...lin(PARK_DAY.oceanDeep))},uPkMeadow:{value:new THREE.Color().setRGB(...lin(PARK_DAY.meadowSun))},uPkSun:{value:new THREE.Vector3(0,1,0)},uPkDrift:{value:0},uPkSeed:{value:seedF},uPkFx:{value:0},uPkCloud:{value:0},uPkDet:{value:0},uPkDetail:{value:flatDetail()}},
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
  if(twin){const U=twin.mat.uniforms;U.uPkSun.value.set(s.x,s.y,s.z);U.uPkDrift.value=drift;U.uPkFx.value=tier==='LOW'?0:1;U.uPkCloud.value=on&&tier!=='LOW'?1:0;const want=groundDetailSize(tier);if(want&&want!==detailSize){detailSize=want;const bytes=bakeGroundDetail(seedStr,want);const t=new THREE.DataTexture(bytes,want,want,THREE.RGBAFormat);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.magFilter=THREE.LinearFilter;t.minFilter=THREE.LinearMipmapLinearFilter;t.generateMipmaps=true;t.needsUpdate=true;if(detailTex)detailTex.dispose();detailTex=t;}if(detailTex)U.uPkDetail.value=detailTex;U.uPkDet.value=want?1:0;}
  if(!on){hideShells();return {drift};}
  if(clouds){clouds.visible=true;clouds.material.uniforms.uSun.value.set(s.x,s.y,s.z);clouds.material.uniforms.uDrift.value=drift;}
  if(limb){limb.visible=true;limb.material.uniforms.uSun.value.set(s.x,s.y,s.z);}
  if(halo){halo.visible=true;halo.material.uniforms.uSun.value.set(s.x,s.y,s.z);}
  return {drift};
 }
 return {
  apply,
  get on(){return on;},
  state(){return {on,tier:builtTier||null,clouds:!!clouds&&clouds.visible,limb:!!limb&&limb.visible,graded:!!twin&&opts.planet()?.material===twin.mat,label:PARK_PLANET_LABEL};},
  dispose(){restoreMaterial();for(const m of shells()){if(m){opts.parent?.remove?.(m);m.geometry.dispose();m.material.dispose();}}twin?.mat.dispose();detailTex?.dispose();flat?.dispose();},
 };
}
