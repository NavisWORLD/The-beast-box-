/**
 * Spark Beast GLB runtime (Zeref pipeline): one sculpted, rigged body-plan GLB per plan
 * (public/creatures3d/beasts/<plan>.glb, built by scripts/creatures3d/beast_build.py, meshopt-packed),
 * painted per Beast at runtime from its genome: palette (paletteOf), seeded pattern, belly/accent masks,
 * part variants (ear, tail and wing variants), 12-layer shell fur (length noise, tapered strands, root AO, combed + CST wind),
 * glossy nebula eyes, real shape keys (blink/happy/sleepy/curious/scared/angry/mouth_*) and CST spring bones.
 * The code-built plush (creature-plush-3d.ts) stays as the low tier / fallback.
 */
import {springStep,clamp,seededRng} from '../lib/physics/cst-integrator.mjs';
import {paletteOf} from '../public/spark/draw.mjs';
import type {PlushGenome} from './creature-plush-3d';
type Three=typeof import('three');
export const GLB_PLANS=Object.freeze(['pup','fox','dragonling','axolotl','biped','bird','golem','sprout','moth','serpent','fish','res_frostmitt','res_nyxbean','res_shardhowl','res_velvetcoil','res_kairo']);
export type Tier='high'|'med'|'low';
const SHELLS:Record<Tier,number>={high:12,med:7,low:0};
const EAR_V:Record<string,string[]>={pointy:['ear_pointy'],round:['ear_round'],crown:['ear_pointy','ear_crown'],horns:['ear_horns'],crystal:['ear_horns'],flame:['ear_horns'],
 leaf:['ear_leaf'],antlers:['ear_leaf'],feelers:['ear_feelers'],antenna:['ear_feelers'],gills:['ear_gills'],bolts:['ear_round']};
const TAIL_V:Record<string,string>={fluffy:'tail_fluffy',plume:'tail_fluffy',leaf:'tail_fluffy',flame:'tail_flame',crystal:'tail_flame',fin:'tail_fin',fishtail:'tail_fin'};
const WING_V:Record<string,string>={feather:'wing_feather',leaf:'wing_feather',bat:'wing_bat',flame:'wing_bat',vanes:'wing_bat',moth:'wing_moth',crystal:'wing_moth'};
const GLOWING=new Set(['crystal','flame']);
/** species identity parts always shown (the genome still paints them); fur = coat length multiplier, scales = belly scale plates */
const SPECIES:Record<string,{ears?:string[];tail?:string;wings?:string;fur?:number;scales?:boolean;stone?:boolean;prop?:number;propGlow?:number;crystal?:boolean;crystalBody?:boolean;baked?:string;faceY?:number;cstFur?:string}>={
 res_frostmitt:{baked:'res_frostmitt',ears:['ear_pointy'],tail:'tail_fluffy',fur:1.5,prop:0x5b2fa8},res_nyxbean:{cstFur:'nyx',baked:'res_nyxbean',ears:[],tail:'tail_thin',fur:1.25,prop:0x3a1f6e},
 res_shardhowl:{ears:['ear_fox'],tail:'tail_brush',fur:0,prop:0x9a6cff,crystal:true,crystalBody:true},res_velvetcoil:{ears:['ear_horns'],tail:'tail_thin',fur:.1,scales:true,prop:0x2a1240},
 res_kairo:{baked:'res_kairo',ears:[],fur:0,prop:0x16121f,faceY:.7},
 fox:{ears:['ear_fox'],tail:'tail_brush',fur:1.25},dragonling:{ears:['ear_dhorn'],wings:'wing_dragon',fur:.55,scales:true},axolotl:{ears:['ear_frill'],tail:'tail_axfin',fur:.22},
 bird:{wings:'wing_feather',fur:.8},moth:{ears:['ear_feelers'],wings:'wing_moth',fur:1.35},golem:{ears:['ear_horns'],fur:0,stone:true},sprout:{ears:['ear_leaf'],fur:.3},
 serpent:{tail:'tail_thin',fur:.12,scales:true},fish:{tail:'tail_fin',fur:.1,scales:true},biped:{fur:1}};
let strandsTex:any=null;
function strands(THREE:Three){if(strandsTex)return strandsTex;const n=256,d=new Uint8Array(n*n*4),r=seededRng('strands');
 for(let i=0;i<n*n;i++){d[i*4+3]=255;}for(let k=0;k<5200;k++){const x=(r()*n)|0,y=(r()*n)|0,v=150+r()*105,rad=r()<.2?2:1;for(let a=-rad;a<=rad;a++)for(let b=-rad;b<=rad;b++){const xx=(x+a+n)%n,yy=(y+b+n)%n,f=1-Math.hypot(a,b)/(rad+1);const j=(yy*n+xx)*4;d[j]=Math.max(d[j],v*f);}}
 strandsTex=new THREE.DataTexture(d,n,n,THREE.RGBAFormat);strandsTex.wrapS=strandsTex.wrapT=THREE.RepeatWrapping;strandsTex.magFilter=THREE.LinearFilter;strandsTex.minFilter=THREE.LinearMipmapLinearFilter;strandsTex.generateMipmaps=true;strandsTex.needsUpdate=true;return strandsTex;}

export type Paint={base:number;alt:number;belly:number;accent:number;glow:number;dark?:number;light?:number};
export async function loadBeastGlb(THREE:Three,gen:PlushGenome,{tier='high' as Tier,base='/creatures3d/beasts/',paint=null as Paint|null}={}){
 const plan=gen.body;if(!GLB_PLANS.includes(plan))return null;
 const {GLTFLoader}=await import('three/examples/jsm/loaders/GLTFLoader.js');const {MeshoptDecoder}=await import('three/examples/jsm/libs/meshopt_decoder.module.js');
 const loader=new GLTFLoader();loader.setMeshoptDecoder(MeshoptDecoder);
 const gltf=await loader.loadAsync(base+plan+'.glb');const root=gltf.scene;root.name='beast-glb-'+plan;
 const SP=SPECIES[plan]||{};const G=gen.genes||{},g=(k:string,d=.5)=>Number.isFinite(G[k])?G[k]:d;const pal=paint?null:paletteOf(gen as any) as any;
 const col=(r:number[])=>new THREE.Color().setRGB(r[0]/255,r[1]/255,r[2]/255,THREE.SRGBColorSpace); // sprite palette is sRGB: convert, don't fake it with pow()
 const C=paint?{base:new THREE.Color(paint.base),dark:new THREE.Color(paint.dark??paint.base).multiplyScalar(paint.dark?1:.45),light:new THREE.Color(paint.light??0xffffff),alt:new THREE.Color(paint.alt),belly:new THREE.Color(paint.belly),accent:new THREE.Color(paint.accent),glow:new THREE.Color(paint.glow)}
  :{base:col(pal.base.mid),dark:col(pal.base.sh),light:col(pal.base.li),alt:col(pal.alt.mid),belly:col(pal.belly.mid),accent:col(pal.accent.mid),glow:col(pal.glow.mid)};
 const R=seededRng('beast-paint:'+gen.seed);const pat=['spots','stripes','belly','stars','facets','moss','plates','cracks','circuits'].indexOf(gen.pattern);
 const cstTex=(n:string)=>{const t=new THREE.TextureLoader().load(`/creatures3d/cst/${SP.cstFur}_fur_${n}.png`);t.wrapS=t.wrapT=THREE.RepeatWrapping;return t;};
 const U={uCst:{value:SP.cstFur?1:0},uFlow:{value:SP.cstFur?cstTex('flow'):null},uFly:{value:SP.cstFur?cstTex('flyaway'):null},uT:{value:0},uWind:{value:new THREE.Vector3()},uChaos:{value:.2},uBeat:{value:0},uSeed:{value:new THREE.Vector3(R()*50,R()*50,R()*50)},
  uBase:{value:C.base},uAlt:{value:C.alt},uBelly:{value:C.belly},uAccent:{value:C.accent},uGlow:{value:C.glow},uDark:{value:C.dark},uLight:{value:C.light},
  uPat:{value:pat<0?0:pat},uPd:{value:g('pattern_density')},uPs:{value:6+g('pattern_scale')*9},uStrands:{value:strands(THREE)},uScales:{value:SPECIES[plan]?.scales?1:0},uStone:{value:SPECIES[plan]?.stone?1:0},uVivid:{value:paint?0:1},uFaceY:{value:SPECIES[plan]?.faceY??-9}};
 const NOISE='float h31(vec3 p){p=fract(p*.3183099+.1);p*=17.0;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}'+
  'float n3(vec3 x){vec3 i=floor(x),f=fract(x);f=f*f*(3.0-2.0*f);return mix(mix(mix(h31(i),h31(i+vec3(1,0,0)),f.x),mix(h31(i+vec3(0,1,0)),h31(i+vec3(1,1,0)),f.x),f.y),mix(mix(h31(i+vec3(0,0,1)),h31(i+vec3(1,0,1)),f.x),mix(h31(i+vec3(0,1,1)),h31(i+vec3(1,1,1)),f.x),f.y),f.z);}'+
  'float fbm3(vec3 p){return n3(p)*.55+n3(p*2.1)*.3+n3(p*4.3)*.15;}\n';
 // coat painter: palette + seeded pattern + masks (R belly, G accent, B glow) + fur shading
 const furPatch=(mat:any,shell:{t:number,len:number}|null)=>{mat.onBeforeCompile=(sh:any)=>{Object.assign(sh.uniforms,U,{uS:{value:shell?shell.t:0},uLen:{value:shell?shell.len:0}});
  sh.vertexShader='uniform float uS,uLen,uT,uCst;uniform sampler2D uFlow,uFly;uniform vec3 uWind;uniform float uChaos;varying vec3 vObjP;varying vec2 vFurUv;varying float vLenN;varying vec3 vMask;varying float vFurL;\n'+NOISE+sh.vertexShader.replace('#include <begin_vertex>',`#include <begin_vertex>
   vObjP=position;vFurUv=uv;vMask=vec3(1.0);vFurL=1.0;
   #ifdef USE_COLOR
   vMask=color.rgb;vFurL=color.a*1.6;
   #endif
   vLenN=.5+.7*n3(position*38.0)*(.7+.3*n3(position*110.0));
   ${shell?`float L=uLen*vLenN*(1.0-vMask.b)*vFurL;vec3 comb=normalize(vec3(0.0,-.5,-1.0));if(uCst>.5){vec2 fl=texture2D(uFlow,uv*2.0).rg*2.0-1.0;comb=normalize(comb+vec3(fl.x,0.0,fl.y)*.8);L*=1.0+texture2D(uFly,uv*2.0).r*.9;}transformed+=objectNormal*L*uS+(comb*.7+uWind+vec3(sin(uT*7.0+position.x*20.0),0.0,cos(uT*6.0+position.z*20.0))*uChaos*.15)*L*uS*uS;`:''}`)
   .replace('#include <color_vertex>','');
  sh.fragmentShader='uniform float uS,uT,uBeat,uPat,uPd,uPs;uniform vec3 uSeed,uBase,uAlt,uBelly,uAccent,uGlow,uDark,uLight;uniform sampler2D uStrands;uniform float uScales,uStone,uVivid,uFaceY;varying vec3 vObjP;varying vec2 vFurUv;varying float vLenN;varying vec3 vMask;varying float vFurL;\n'+NOISE+
   sh.fragmentShader.replace('#include <color_fragment>',`
   ${shell?`if(uS>vLenN||vMask.b>.5||vFurL<.05)discard;vec3 sc=vObjP*230.0;float cell=h31(floor(sc));float cd=length(fract(sc)-.5);float strand=cell*smoothstep(.5,.15,cd);float sd=max(strand,texture2D(uStrands,vFurUv*14.0).r*.55+texture2D(uStrands,vFurUv*37.0).r*.25);float th=mix(.08,.85,clamp(uS/vLenN,0.0,1.0));float cov=smoothstep(th-.07,th+.07,sd);if(cov<.02)discard;`:''}
   vec3 p=vObjP*uPs+uSeed;float v=fbm3(p);float m=0.0;
   if(uPat<.5)m=smoothstep(.62-uPd*.12,.66-uPd*.12,v);                       // spots
   else if(uPat<1.5)m=smoothstep(.55,.6,abs(sin(vObjP.z*uPs*1.4+vObjP.y*3.0+v*4.0)));   // stripes
   else if(uPat<2.5)m=smoothstep(.7,1.15,vObjP.y)*.55+smoothstep(.55,.9,fbm3(p*.35))*.25;        // belly: soft points on crown/back
   else if(uPat<3.5)m=step(.93,h31(floor(p*2.0)))*smoothstep(.3,.0,length(fract(p*2.0)-.5));                             // stars (round)
   else if(uPat<4.5)m=step(.5,fract(v*6.0))*.5;                                // facets
   else if(uPat<5.5)m=smoothstep(.5,.75,fbm3(p*.6))*.8;                        // moss
   else if(uPat<6.5)m=step(.9,max(fract(p.x*.5),fract(p.y*.5)))*.6;            // plates
   else if(uPat<7.5)m=smoothstep(.02,.0,abs(v-.5))*.9;                         // cracks (glow)
   else m=step(.94,max(fract(p.x),fract(p.z)))*.7;                             // circuits
   vec3 c=mix(uBase,uAlt,m*(uPat>6.5&&uPat<7.5?0.0:1.0));
   c=mix(c,uLight,smoothstep(.1,.9,vObjP.y)*.12);c=mix(c,uBelly,vMask.r*.9*(uFaceY>-5.0?step(uFaceY,vObjP.y):1.0));c=mix(c,uAccent,vMask.g*.85);
   if(uScales>.5&&vMask.r>.35&&vFurL<.05){vec2 q=vec2(vObjP.x*26.0,vObjP.y*22.0+vObjP.z*8.0);q.x+=floor(q.y)*.5;vec2 f=fract(q)-vec2(.5,.2);float e=length(f*vec2(1.0,1.3));
     c=mix(uBelly*1.15,uAccent*.55,smoothstep(.38,.55,e))*(.85+.25*(1.0-f.y));}
   { // Sprite-faithful coat (Oct 16): palette colours stay the sprite's; the cosmos lives in a faint sheen + rim + stars, not in blotches.
     vec3 np=vObjP*3.2+uSeed*.1+vec3(0.0,uT*.03,0.0);float nb2=fbm3(np*1.9+4.0);
     vec3 neb=mix(uGlow,mix(vec3(.45,.2,1.0),vec3(.1,.85,1.0),nb2),.5);
     c=mix(c,c*(.9+.2*fbm3(vObjP*9.0+uSeed)),.6);                              // soft value variation, no hue blotches
     c=mix(c,c*.6+neb*.4,.1*(1.0-vMask.r)*uVivid);                             // faint cosmic undertone
     c=max(vec3(0.0),mix(vec3(dot(c,vec3(.299,.587,.114))),c,1.12)); }
   float hgt=${shell?'clamp(uS/vLenN,0.0,1.0)':'0.0'};
   diffuseColor.rgb=mix(c*mix(.5,1.0,hgt),uLight,hgt*hgt*.12);               // root AO -> clean bright tips
   ${shell?'diffuseColor.a=cov;':''}
   vec3 sp3=vObjP*58.0+vec3(0.0,0.0,uT*.25);float star=step(.985,h31(floor(sp3)))*smoothstep(.35,.0,length(fract(sp3)-.5))*(.6+.4*sin(uT*3.0+h31(floor(sp3))*40.0));
   vec3 rp=vObjP*7.0+uSeed*.3;vec3 rc=floor(rp);float rh=h31(rc);float rune=rh>.82?smoothstep(.06,.0,abs(length(fract(rp)-.5)-.28))+smoothstep(.04,.0,abs(fract(rp).x-.5))*step(.92,rh):0.0;
   float stoneCr=0.0;if(uStone>.5){float sv=fbm3(vObjP*7.0+uSeed);stoneCr=smoothstep(.035,.0,abs(sv-.5));c=mix(uDark*.7,uBase*1.05,fbm3(vObjP*22.0+uSeed))*(1.0-stoneCr*.6);}
   float glowM=stoneCr*1.4+vMask.b+star*2.0+smoothstep(.6,.8,fbm3(vObjP*3.2+uSeed*.1))*.06+rune*.3*(1.0-vMask.r)+(uPat>6.5&&uPat<7.5?m*.35:0.0)+(uPat>2.5&&uPat<3.5?m*.6:0.0);`)
   .replace('#include <emissivemap_fragment>',`#include <emissivemap_fragment>
   vec3 vd=normalize(vViewPosition),nn=normalize(vNormal);float fres=pow(1.0-abs(dot(nn,vd)),3.0);
   totalEmissiveRadiance+=uGlow*glowM*(1.2+uBeat*1.5)+c*vec3(1.0,.6,.8)*vMask.g*.25+mix(vec3(.55,.3,1.0),vec3(.2,.95,1.0),.5+.5*sin(dot(nn,vd)*9.0+uT))*fres*.35;`);};
  mat.customProgramCacheKey=()=>'beast-fur-'+(shell?shell.t.toFixed(3):'base');mat.needsUpdate=true;};
 // nebula eyes: glossy dark ball with a swirling seeded galaxy iris
 const eyeC={value:new THREE.Vector3()};
 const eyeMat=new THREE.MeshPhysicalMaterial({color:0x07060f,roughness:.06,clearcoat:1,clearcoatRoughness:.02,emissive:0xffffff,emissiveIntensity:1});
 eyeMat.onBeforeCompile=(sh:any)=>{Object.assign(sh.uniforms,U,{uEyeC:eyeC});sh.vertexShader='varying vec3 vEP;\n'+sh.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nvEP=position;');
  sh.fragmentShader='uniform float uT;uniform vec3 uGlow,uSeed,uEyeC;varying vec3 vEP;\n'+NOISE+sh.fragmentShader.replace('#include <emissivemap_fragment>',`#include <emissivemap_fragment>
   vec3 nv=normalize(vEP-vec3(sign(vEP.x)*uEyeC.x,uEyeC.y,uEyeC.z));vec2 q=nv.xy*3.2;float r=length(q);float a=atan(q.y,q.x)+uT*.2+r*1.6;
   vec2 sp=vec2(cos(a),sin(a))*r;float neb=fbm3(vec3(sp*1.6,uSeed.x+uT*.04));float arm=.5+.5*sin(a*2.0-r*5.0);
   vec3 deep=vec3(.05,.02,.14),vio=vec3(.48,.24,1.0);vec3 nc=mix(deep,mix(vio,uGlow,arm),smoothstep(.35,.85,neb*.7+arm*.4))*smoothstep(1.25,.2,r);
   nc+=uGlow*smoothstep(.35,.0,abs(r-.9))*.25;nc*=smoothstep(.18,.32,r)*.85+.15;
   float stars=step(.992,h31(floor(nv*180.0)))*smoothstep(1.1,.3,r);nc+=mix(vec3(.4,.2,1.0),vec3(.2,.9,1.0),.5+.5*sin(a*3.0))*smoothstep(.12,.0,abs(r-.62))*.6;totalEmissiveRadiance=nc*3.4+vec3(1.0)*stars*1.6;`);};
 eyeMat.customProgramCacheKey=()=>'beast-eye-v2';
 let face:any=null,body:any=null;const shells:any[]=[];const shown=new Set<string>(['body','face','detail',...(SP.ears||EAR_V[gen.ears]||['ear_pointy'])]);
 if(gen.ears==='crown')shown.add('ear_crown');
 if(SP.tail)shown.add(SP.tail);else if(gen.tail!=='none')shown.add(TAIL_V[gen.tail]||'tail_thin');
 if(SP.wings)shown.add(SP.wings);else if(gen.wings&&gen.wings!=='none')shown.add(WING_V[gen.wings]||'wing_feather');
 const glowMat=new THREE.MeshStandardMaterial({color:C.glow,emissive:C.glow,emissiveIntensity:2.2,roughness:.3});
 const pblink:any[]=[],floaters:any[]=[],eyeMats:any[]=[];
 root.traverse((o:any)=>{if(!o.isMesh)return;const n=(o.name||'').replace(/_\d+$/,'');const key=['body','face','detail'].find(k=>n.startsWith(k))||n;
  o.castShadow=true;o.frustumCulled=false;
  if(n.startsWith('ear_')||n.startsWith('tail_')||n.startsWith('wing_')){o.visible=shown.has(n.replace(/\.\d+$/,''));}
  const mn=o.material?.name||'';
  if(mn==='fur'){const m=new THREE.MeshPhysicalMaterial({vertexColors:true,roughness:.8,sheen:.6,sheenRoughness:.4,sheenColor:new THREE.Color(.55,.3,1),iridescence:.35,iridescenceIOR:1.4});furPatch(m,null);
   if(n.startsWith('ear_dhorn'))o.material=new THREE.MeshPhysicalMaterial({color:C.accent.clone().lerp(new THREE.Color(.95,.9,.8),.55),roughness:.3,clearcoat:.8,sheen:.3});
   else if(n.startsWith('wing_dragon')){const wm=new THREE.MeshPhysicalMaterial({vertexColors:true,roughness:.5,transmission:.0,side:THREE.DoubleSide,sheen:.5,sheenColor:C.glow,emissive:C.glow,emissiveIntensity:.08});furPatch(wm,null);o.material=wm;}
   else if(n.startsWith('ear_crown'))o.material=new THREE.MeshPhysicalMaterial({color:C.accent.clone().lerp(new THREE.Color(1,.82,.4),.6),metalness:1,roughness:.22,clearcoat:.6,emissive:C.glow,emissiveIntensity:.15});
   else if(n.startsWith('ear_')&&!SP.ears&&GLOWING.has(gen.ears)||n==='tail_flame'&&GLOWING.has(gen.tail))o.material=glowMat;else if(SP.crystalBody&&(n.startsWith('body')||n.startsWith('ear_')||n.startsWith('tail_')))o.material=new THREE.MeshPhysicalMaterial({color:C.base.clone().lerp(C.alt,.35),flatShading:true,roughness:.12,metalness:.15,clearcoat:1,clearcoatRoughness:.05,iridescence:1,iridescenceIOR:1.6,emissive:C.glow,emissiveIntensity:.12,sheen:.6,sheenColor:C.accent});
   else o.material=m;if(n.startsWith('wing_'))o.material.side=THREE.DoubleSide;if(n.startsWith('body')){body=o;if(SP.baked&&o.geometry.attributes.uv){/* playbook #1: sculpt->bake normal + AO from the high-res sculpt */
    const bm:any=o.material.clone();bm.onBeforeCompile=o.material.onBeforeCompile;bm.customProgramCacheKey=()=>'beast-fur-baked';const TL=new THREE.TextureLoader(),bt=(k:string)=>{const t=TL.load(`/creatures3d/bake/${SP.baked}_body_${k}.png`);t.flipY=false;return t;};
    bm.normalMap=bt('normal');bm.normalScale=new THREE.Vector2(.7,.7);bm.aoMap=bt('ao');bm.aoMapIntensity=.8;bm.needsUpdate=true;o.material=bm;}}}
  else if(mn.startsWith('pm_')){/* turnaround outfits: keep authored PBR (+maps) and add fabric sheen / glossy cornea / soft mist */const am:any=o.material;if(am&&am.isMeshStandardMaterial){const pm=new THREE.MeshPhysicalMaterial({color:am.color,map:am.map,normalMap:am.normalMap,normalScale:am.normalScale,roughness:am.roughness,metalness:am.metalness,emissive:am.emissive,emissiveMap:am.emissiveMap,emissiveIntensity:am.emissiveIntensity,transparent:am.transparent,opacity:am.opacity,depthWrite:!am.transparent,side:am.side,
   sheen:am.roughness>.5?.8:0,sheenColor:new THREE.Color(0xb48cff),sheenRoughness:.5,clearcoat:am.roughness<.3?.8:0,transmission:(am as any).transmission||0,ior:(am as any).ior||1.5,thickness:.02});
   if(mn==='pm_hair'){pm.sheen=.15;pm.sheenColor=new THREE.Color(0x3a2a55);pm.specularIntensity=.25;}/* black hair: no lilac grazing flecks */
   if(mn==='pm_eyeball'){pm.emissiveIntensity=1.15;pm.emissive=new THREE.Color(1,1,1);}/* playbook: iris glow <=1.2x its colour */
   if(SP.baked&&n.startsWith('prop_crown')&&o.geometry.attributes.uv){const t=new THREE.TextureLoader().load(`/creatures3d/bake/${SP.baked}_hat_ao.png`);t.flipY=false;pm.aoMap=t;pm.aoMapIntensity=1;}
   if(mn==='pm_cornea'){pm.transparent=true;pm.opacity=.05;pm.transmission=0;pm.roughness=.02;pm.clearcoat=1;pm.depthWrite=false;}
   if(mn==='pm_mist'){pm.transparent=true;pm.opacity=.3;pm.depthWrite=false;pm.side=THREE.DoubleSide;}
   if(mn==='pm_puffy'){/* 4D surface: CST turbulence over (xyz, t) gently breathes the quilt normal */pm.onBeforeCompile=(sh:any)=>{sh.uniforms.uT=U.uT;sh.uniforms.uChaos=U.uChaos;
    sh.vertexShader='varying vec3 vP4;\n'+sh.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nvP4=position;');
    sh.fragmentShader='uniform float uT,uChaos;varying vec3 vP4;\n'+sh.fragmentShader.replace('#include <normal_fragment_maps>','#include <normal_fragment_maps>\nvec3 q=vP4*40.0;normal=normalize(normal+.06*(.5+uChaos)*vec3(sin(q.y*1.7+uT*1.3)+.5*sin(q.z*2.3-uT*.7),sin(q.z*1.9+uT*1.1)+.5*sin(q.x*2.1+uT*.5),0.0));');};}
   if(mn==='pm_eyeball'&&pm.map){pm.map=pm.map.clone();pm.map.needsUpdate=true;pm.emissiveMap=pm.map;eyeMats.push(pm);}
   pm.name=mn;o.material=pm;}
   if(o.morphTargetDictionary&&'pblink' in o.morphTargetDictionary)pblink.push(o);if(/^prop_(pixels|mist)/.test(n))floaters.push(o);}
  else if(mn==='prop'){const pc=new THREE.Color(SP.prop??0x5b2fa8);o.material=SP.crystal?new THREE.MeshPhysicalMaterial({color:pc,roughness:.08,metalness:.1,transmission:.35,thickness:.2,iridescence:1,emissive:C.glow,emissiveIntensity:.5,clearcoat:1})
   :new THREE.MeshPhysicalMaterial({color:pc,roughness:.85,sheen:1,sheenColor:new THREE.Color(0xb48cff),sheenRoughness:.5,emissive:C.glow,emissiveIntensity:.06});}
  else if(mn==='eye'){o.material=eyeMat;o.geometry.computeBoundingBox();const bb=o.geometry.boundingBox;const w=(bb.max.x-bb.min.x)/2;eyeC.value.set(bb.max.x-w/2,(bb.max.y+bb.min.y)/2,(bb.max.z+bb.min.z)/2-(bb.max.z-bb.min.z)*.3);}else if(mn==='iris'){o.material=new THREE.MeshBasicMaterial({color:C.glow,transparent:true,opacity:.0});}
  else if(mn==='shine')o.material=new THREE.MeshBasicMaterial({color:0xffffff,toneMapped:false});else if(mn==='glow')o.material=glowMat;
  else if(mn==='mouth')o.material=new THREE.MeshStandardMaterial({color:0x1c0812,roughness:.55});else if(mn==='mouthin')o.material=new THREE.MeshStandardMaterial({color:0x2a0614,roughness:.7});else if(mn==='tongue')o.material=new THREE.MeshPhysicalMaterial({color:0xe0687e,roughness:.35,clearcoat:.5});else if(mn==='nose')o.material=new THREE.MeshPhysicalMaterial({color:0x1a1222,roughness:.25,clearcoat:.8});
  if(o.morphTargetDictionary&&'blink' in o.morphTargetDictionary)face=o;});
 // 12-layer shell fur on the visible coat meshes (body + active fur variants)
 const N=(SP.fur===0?0:SHELLS[tier]),len=.036*(.8+g('chub')*.4)*(SP.fur??1);
 if(N>0)root.traverse((o:any)=>{if(!o.isSkinnedMesh||o.userData.shell)return;const mn=(o.material as any);if(!(mn&&mn.isMeshPhysicalMaterial&&mn.vertexColors))return;if(!o.visible)return;
  for(let k=1;k<=N;k++){const t=k/N;const m=new THREE.MeshPhysicalMaterial({vertexColors:true,roughness:.85,sheen:.6,sheenRoughness:.35,sheenColor:new THREE.Color(.45,.35,1),transparent:false,alphaToCoverage:true});furPatch(m,{t,len});
   const s=new THREE.SkinnedMesh(o.geometry,m);s.bind(o.skeleton,o.bindMatrix);s.userData.shell=true;s.position.copy(o.position);s.quaternion.copy(o.quaternion);s.scale.copy(o.scale);s.frustumCulled=false;s.renderOrder=k;o.parent.add(s);shells.push(s);}});
 // bones (GLTFLoader strips dots: ear.0.L -> ear0L)
 const bones:Record<string,any>={};root.traverse((o:any)=>{if(o.isBone)bones[o.name]=o;});const bn=(n:string)=>bones[n.replace(/\./g,'')]||null;
 root.updateMatrixWorld(true);const rootInv=new THREE.Matrix4().copy(root.matrixWorld).invert();
 const rest=new Map<any,{q:any,mq:any}>();for(const b of Object.values(bones)){const mw=new THREE.Matrix4().multiplyMatrices(rootInv,b.matrixWorld);const mq=new THREE.Quaternion();mw.decompose(new THREE.Vector3(),mq,new THREE.Vector3());rest.set(b,{q:b.quaternion.clone(),mq});}
 const tq=new THREE.Quaternion(),ax=new THREE.Vector3(),acc=new THREE.Quaternion();
 /** rotate a bone about MODEL-space axes (x pitch, y yaw, z roll), relative to its rest pose */
 const pose=(b:any,x=0,y=0,z=0)=>{if(!b)return;const r=rest.get(b);if(!r)return;acc.identity();const inv=r.mq.clone().invert();
  for(const [a,v] of [[0,x],[1,y],[2,z]] as [number,number][]){if(!v)continue;ax.set(a===0?1:0,a===1?1:0,a===2?1:0).applyQuaternion(inv);tq.setFromAxisAngle(ax,v);acc.multiply(tq);}b.quaternion.copy(r.q).multiply(acc);};
 const legs=['legF0L','legF0R','legB0L','legB0R'].map(n=>bones[n]),knees=['legF1L','legF1R','legB1L','legB1R'].map(n=>bones[n]);
 const tail=[0,1,2,3,4].map(i=>bn('tail.'+i)).filter(Boolean),ears=['ear0L','ear0R'].map(n=>bones[n]),ears1=['ear1L','ear1R'].map(n=>bones[n]),wings=['wing0L','wing0R'].map(n=>bones[n]);
 const S=(n:number)=>Array.from({length:n},()=>({x:0,v:0}));const sp={ear:S(2),ear2:S(2),tail:S(tail.length),tail2:S(tail.length),wing:S(2)};
 const MK=face?.morphTargetDictionary||{};const W=face?.morphTargetInfluences||[];const setM=(k:string,v:number)=>{const i=MK[k];if(i!=null)W[i]=clamp(v);};
 const ex={blink:0,happy:0,sleepy:0,curious:0,scared:0,angry:0,grin:0,o:0,w:0};let blinkT=1+R()*3,t=0,prevH=0;
 let tris=0;root.traverse((o:any)=>{if(o.isMesh&&o.visible&&!o.userData.shell){const gg=o.geometry;tris+=(gg.index?gg.index.count:gg.attributes.position.count)/3;}});
 const anim={eT:0,eX:0,eY:0,ex:{x:0,v:0},ey:{x:0,v:0},mvJ:3,lookT:0,lookY:0,lookP:0,sy:{x:0,v:0},sp:{x:0,v:0},jp:-1,jt:2.5,sq:{x:0,v:0},st:3+R()*3,sp2:-1,hat:{x:0,v:0},hy:{x:0,v:0},pl:0,py:0};
 const rootRest=bones.root?bones.root.position.clone():null;
 function drive(dt:number,life:{speed:number;mode:string;sleep:number;lookCam:number;bob:number;heading:number;startle?:number},mp:any,lookLocal:{yaw:number;pitch:number}|null){
  t+=dt;U.uT.value=t;const mood=mp?.mood||{joy:.5,fear:.1,curiosity:.5,calm:.6,mischief:.3};const k=60*(mp?.stiffness||1),d=8*(mp?.damping||1),turb=mp?.turbulence||0,wind=mp?.wind||{x:0,y:0,z:0};
  U.uWind.value.set(wind.x*.4,wind.y*.2,wind.z*.4);U.uChaos.value=turb;
  let dh=life.heading-prevH;dh=((dh+Math.PI*3)%(Math.PI*2))-Math.PI;prevH=life.heading;const yr=clamp(dh/Math.max(dt,1e-3),-4,4);
  const st=clamp(life.speed*1.6),ph=life.bob,nap=life.sleep;
  legs.forEach((b,i)=>{const s_=Math.sin(ph+(i===0||i===3?0:Math.PI));const stance=s_>0?1:0;pose(b,(stance?s_*.45:s_*.62)*st-nap*1.2*(i<2?1:-.6));});knees.forEach((b,i)=>pose(b,Math.max(0,-Math.sin(ph+(i===0||i===3?0:Math.PI)))*.6*st+nap*(i<2?1.6:-1.4)));
  const breathe=Math.sin(t*(1.6-mood.calm*.5))*.025;
  pose(bones.hips,0,Math.sin(t*.55)*.05*(1-st)*(1-nap),Math.sin(ph)*.05*st+Math.sin(t*.55+1)*.03*(1-st));pose(bones.spine,-nap*.15+nap*.3+breathe,yr*.04+nap*.35,0);
  // ---- animation pass (CST + springs): look-around saccades, jump anticipation/squash/landing, happy bounce, stretch+yawn, hat follow-through
  anim.lookT-=dt;if(anim.lookT<=0){anim.lookT=1.1+R()*2.6*(.6+mood.calm*.8);anim.lookY=(R()-.5)*1.2*(1-nap)*(.5+mood.curiosity);anim.lookP=(R()-.5)*.35-nap*.1;}
  springStep(anim.sy,anim.lookY,55*(mp?.stiffness||1),11,dt);springStep(anim.sp,anim.lookP,55,11,dt);
  // eye saccades: fast spring-snapped iris shifts (UV offset on the galaxy eye), independent of the slower head look
  anim.eT-=dt;if(anim.eT<=0){anim.eT=.25+R()*1.1;anim.eX=(R()-.5)*.12+anim.lookY*.05;anim.eY=(R()-.5)*.07;}
  springStep(anim.ex,anim.eX,900,60,dt);springStep(anim.ey,anim.eY,900,60,dt);eyeMats.forEach(m=>m.map.offset.set(-anim.ex.x,anim.ey.x));
  const playing=life.mode==='play';
  if(life.speed>.3){anim.mvJ-=dt;if(anim.mvJ<=0&&anim.jp<0){anim.jp=0;anim.mvJ=3+R()*3;}}  // jumps while moving
  if(anim.jp<0){anim.jt-=dt;if((life as any).jump||(playing&&anim.jt<=0)||(life.startle||0)>.6){anim.jp=0;anim.jt=1.8+R()*3;}}
  let lift=0,sqT=0;if(anim.jp>=0){anim.jp+=dt/.95;const p=anim.jp;
   if(p<.24)sqT=-.2*Math.sin(p/.24*Math.PI/2);else if(p<.78){const q=(p-.24)/.54;lift=Math.sin(q*Math.PI)*(.18+.1*mood.joy);sqT=.12*(1-q*2);}else if(p<1)sqT=-.17*Math.sin((p-.78)/.22*Math.PI);else anim.jp=-1;}
  springStep(anim.sq,sqT,140,13,dt);
  const hop=lift+Math.abs(Math.sin(ph))*.014*st*(1-nap)+(playing?Math.abs(Math.sin(t*5.5))*.035*(.4+mood.joy):0)+(life.startle||0)*.04;
  if(bones.root&&rootRest){bones.root.position.copy(rootRest);bones.root.position.y+=hop;const q_=anim.sq.x;bones.root.scale.set(1-q_*.45,1+q_,1-q_*.45);}
  // stretch + yawn when idle and calm
  let stretch=0;if(life.speed<.05&&nap<.2){anim.st-=dt;if(anim.st<=0&&anim.sp2<0){anim.sp2=0;anim.st=9+R()*10;}}
  if(anim.sp2>=0){anim.sp2+=dt/2.6;stretch=Math.sin(Math.min(1,anim.sp2)*Math.PI);if(anim.sp2>=1)anim.sp2=-1;}
  // hat sack: spring driven by vertical velocity (hop) and head yaw velocity -> jiggle + band follow-through
  const vl=(hop-anim.pl)/Math.max(dt,1e-3),vy=(anim.sy.x-anim.py)/Math.max(dt,1e-3);anim.pl=hop;anim.py=anim.sy.x;
  springStep(anim.hat,clamp(-vl*.12,-.5,.5),70,5,dt);springStep(anim.hy,clamp(-vy*.06,-.4,.4)+wind.x*.1,60,5,dt);pose(bones.hat,anim.hat.x,anim.hy.x,Math.sin(t*1.3)*.02*turb);
  if(stretch>0){pose(bones.spine,-stretch*.28,0,0);ex.o=Math.max(ex.o,stretch>.6?(stretch-.6)*2.4:0);}
  const yaw=lookLocal?clamp(lookLocal.yaw,-1,1):anim.sy.x,pit=lookLocal?clamp(lookLocal.pitch,-.5,.5):nap*.5+anim.sp.x-stretch*.35;
  pose(bones.neck,pit*.4,yaw*.4,0);pose(bones.head,pit*.6+(life.startle||0)*-.2,yaw*.6,Math.sin(t*.7)*.06*mood.curiosity+ex.curious*.2);
  ears.forEach((b,i)=>{const s=i?1:-1;springStep(sp.ear[i],-yr*.08+wind.x*s*.3+Math.sin(t*9+i)*turb*.15-ex.scared*.7+ex.happy*.15,k,d,dt);springStep(sp.ear2[i],Math.abs(Math.sin(ph))*st*.3+ex.curious*.3-nap*.5,k,d,dt);
   pose(b,sp.ear2[i].x,0,sp.ear[i].x*s);pose(ears1[i],sp.ear2[i].x*.6,0,sp.ear[i].x*s*.6);});
  tail.forEach((b,i)=>{const wag=Math.sin(t*(4+mood.joy*6)-i*.7)*(.12+mood.joy*.4)*(1-nap*.8);springStep(sp.tail[i],wag-yr*.12*(i+1)/tail.length+wind.x*.2+Math.sin(t*7+i)*turb*.12,k*.8,d*.8,dt);
   springStep(sp.tail2[i],(i===0?.25-nap*.5:-.04)+st*.08,k*.8,d,dt);pose(b,-sp.tail2[i].x+nap*.25,sp.tail[i].x+nap*.55,0);});
  wings.forEach((b,i)=>{const s=i?1:-1;springStep(sp.wing[i],Math.sin(t*1.5)*.08+(life.speed>.9?Math.sin(t*12)*.5:0)+wind.z*.1,k*1.5,d,dt);pose(b,0,0,s*sp.wing[i].x);});
  blinkT-=dt;if(blinkT<=0){blinkT=2+((t*7919)%1)*4;ex.blink=1;}ex.blink=Math.max(0,ex.blink-dt*7);
  const tw=(key:keyof typeof ex,v:number,r=4)=>{ex[key]+=(v-ex[key])*Math.min(1,dt*r);};
  tw('sleepy',nap);tw('happy',life.mode==='play'||life.mode==='approach'?mood.joy:mood.joy*.25);tw('curious',life.mode==='glance'||life.mode==='sniff'?.8:mood.curiosity*.15);
  tw('scared',(life.startle||0)+mood.fear*.25);tw('angry',mood.mischief>.8?.4:0);tw('grin',life.mode==='play'?.8:mood.joy*.3);tw('o',life.mode==='sniff'&&life.speed<.05?.5+.4*Math.abs(Math.sin(t*6)):0,8);tw('w',life.mode==='approach'?.7:0);
  setM('blink',Math.max(ex.blink,ex.sleepy*.2));setM('happy',ex.happy*(1-ex.blink));setM('sleepy',ex.sleepy);setM('curious',ex.curious);setM('scared',ex.scared);setM('angry',ex.angry);
  pblink.forEach(m=>{const D_=m.morphTargetDictionary,I_=m.morphTargetInfluences,S_=(k:string,v:number)=>{const i=D_[k];if(i!=null)I_[i]=clamp(v);};
   S_('pblink',Math.max(ex.blink,ex.sleepy*.2));S_('phappy',ex.happy*(1-ex.blink));S_('psleepy',ex.sleepy*(1-ex.blink));S_('pcurious',ex.curious);S_('pscared',ex.scared);S_('pangry',ex.angry);});
  floaters.forEach((m,i)=>{m.position.y=Math.sin(t*1.3+i)*.012;m.rotation.y=Math.sin(t*.35+i)*.25;});
  setM('mouth_grin',ex.grin*(1-ex.o));setM('mouth_o',ex.o);setM('mouth_w',ex.w*(1-ex.o));
  U.uBeat.value=Math.pow(Math.max(0,Math.sin(t*(1+(mp?mp.stiffness:1)*.9)*Math.PI*2)),12);glowMat.emissiveIntensity=1.6+U.uBeat.value*1.4+mood.joy*.4;
 }
 return {root,drive,tris:Math.round(tris),shells:shells.length,plan,expr:ex,colors:C,setTier(tr:Tier){const n=SHELLS[tr];shells.forEach((s,i)=>{s.visible=n>=12||(i%12)%Math.ceil(12/Math.max(1,n))===0&&n>0;});},
  dispose(){root.traverse((o:any)=>{if(o.isMesh){o.geometry?.dispose();(Array.isArray(o.material)?o.material:[o.material]).forEach((m:any)=>m?.dispose());}});}};
}

/** Zeref-style studio for Beast renders: violet/cosmic-blue PMREM environment + key, cyan/violet rims, blue fill, AgX. */
export function beastStudio(THREE:Three,renderer:any,scene:any){
 const env=new THREE.Scene();
 env.add(new THREE.Mesh(new THREE.SphereGeometry(10,32,16),new THREE.ShaderMaterial({side:THREE.BackSide,depthWrite:false,
  vertexShader:'varying vec3 vP;void main(){vP=normalize(position);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
  fragmentShader:'varying vec3 vP;void main(){float y=vP.y;vec3 top=vec3(.32,.18,.72),hor=vec3(.10,.22,.55),bot=vec3(.02,.01,.05);vec3 c=y>0.?mix(hor,top,pow(y,.7)):mix(hor,bot,pow(-y,.5));gl_FragColor=vec4(c,1.);}'})));
 const panel=(col:number,s:number,w:number,h:number,p:[number,number,number])=>{const m=new THREE.Mesh(new THREE.PlaneGeometry(w,h),new THREE.MeshBasicMaterial({color:new THREE.Color(col).multiplyScalar(s),side:THREE.DoubleSide}));m.position.set(...p);m.lookAt(0,0,0);env.add(m);};
 panel(0xf1e6ff,6,5,4,[-5,6,6]);panel(0x7fe6ff,9,1.2,7,[4,3,-6]);panel(0xb88cff,7,1.2,7,[-5,3,-5]);panel(0x5a7bff,1.6,6,3,[6,1,4]);
 const pm=new THREE.PMREMGenerator(renderer);scene.environment=pm.fromScene(env,.03).texture;pm.dispose();scene.environmentIntensity=.3;
 // ACES keeps saturation (AgX greyed the coats out)
 renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=.9;
 const L:any[]=[new THREE.HemisphereLight(0xa996ff,0x0a0618,.15)];
 const key=new THREE.DirectionalLight(0xfff1ff,2.8);key.position.set(-2.2,3.2,3);key.castShadow=true;key.shadow.mapSize.set(1024,1024);key.shadow.bias=-.0005;L.push(key);
 const fill=new THREE.DirectionalLight(0x6f8cff,.7);fill.position.set(2.6,1,2.4);L.push(fill);
 const rim=new THREE.DirectionalLight(0x8fe8ff,4.2);rim.position.set(1.8,2.3,-3);L.push(rim);const rim2=new THREE.DirectionalLight(0xc08cff,3.2);rim2.position.set(-2.2,2.6,-2.4);L.push(rim2);
 L.forEach(l=>scene.add(l));return {key,lights:L};
}
