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
export const GLB_PLANS=Object.freeze(['pup','fox','dragonling','axolotl']);
export type Tier='high'|'med'|'low';
const SHELLS:Record<Tier,number>={high:12,med:7,low:0};
const EAR_V:Record<string,string[]>={pointy:['ear_pointy'],round:['ear_round'],crown:['ear_pointy','ear_crown'],horns:['ear_horns'],crystal:['ear_horns'],flame:['ear_horns'],
 leaf:['ear_leaf'],antlers:['ear_leaf'],feelers:['ear_feelers'],antenna:['ear_feelers'],gills:['ear_gills'],bolts:['ear_round']};
const TAIL_V:Record<string,string>={fluffy:'tail_fluffy',plume:'tail_fluffy',leaf:'tail_fluffy',flame:'tail_flame',crystal:'tail_flame',fin:'tail_fin',fishtail:'tail_fin'};
const WING_V:Record<string,string>={feather:'wing_feather',leaf:'wing_feather',bat:'wing_bat',flame:'wing_bat',vanes:'wing_bat',moth:'wing_moth',crystal:'wing_moth'};
const GLOWING=new Set(['crystal','flame']);
let strandsTex:any=null;
function strands(THREE:Three){if(strandsTex)return strandsTex;const n=256,d=new Uint8Array(n*n*4),r=seededRng('strands');
 for(let i=0;i<n*n;i++){d[i*4+3]=255;}for(let k=0;k<5200;k++){const x=(r()*n)|0,y=(r()*n)|0,v=150+r()*105,rad=r()<.2?2:1;for(let a=-rad;a<=rad;a++)for(let b=-rad;b<=rad;b++){const xx=(x+a+n)%n,yy=(y+b+n)%n,f=1-Math.hypot(a,b)/(rad+1);const j=(yy*n+xx)*4;d[j]=Math.max(d[j],v*f);}}
 strandsTex=new THREE.DataTexture(d,n,n,THREE.RGBAFormat);strandsTex.wrapS=strandsTex.wrapT=THREE.RepeatWrapping;strandsTex.magFilter=THREE.LinearFilter;strandsTex.minFilter=THREE.LinearMipmapLinearFilter;strandsTex.generateMipmaps=true;strandsTex.needsUpdate=true;return strandsTex;}

export async function loadBeastGlb(THREE:Three,gen:PlushGenome,{tier='high' as Tier,base='/creatures3d/beasts/'}={}){
 const plan=gen.body;if(!GLB_PLANS.includes(plan))return null;
 const {GLTFLoader}=await import('three/examples/jsm/loaders/GLTFLoader.js');const {MeshoptDecoder}=await import('three/examples/jsm/libs/meshopt_decoder.module.js');
 const loader=new GLTFLoader();loader.setMeshoptDecoder(MeshoptDecoder);
 const gltf=await loader.loadAsync(base+plan+'.glb');const root=gltf.scene;root.name='beast-glb-'+plan;
 const G=gen.genes||{},g=(k:string,d=.5)=>Number.isFinite(G[k])?G[k]:d;const pal=paletteOf(gen as any) as any;
 const col=(r:number[])=>new THREE.Color(r[0]/255,r[1]/255,r[2]/255);
 const C={base:col(pal.base.mid),dark:col(pal.base.sh),light:col(pal.base.li),alt:col(pal.alt.mid),belly:col(pal.belly.mid),accent:col(pal.accent.mid),glow:col(pal.glow.mid)};
 const R=seededRng('beast-paint:'+gen.seed);const pat=['spots','stripes','belly','stars','facets','moss','plates','cracks','circuits'].indexOf(gen.pattern);
 const U={uT:{value:0},uWind:{value:new THREE.Vector3()},uChaos:{value:.2},uBeat:{value:0},uSeed:{value:new THREE.Vector3(R()*50,R()*50,R()*50)},
  uBase:{value:C.base},uAlt:{value:C.alt},uBelly:{value:C.belly},uAccent:{value:C.accent},uGlow:{value:C.glow},uDark:{value:C.dark},uLight:{value:C.light},
  uPat:{value:pat<0?0:pat},uPd:{value:g('pattern_density')},uPs:{value:6+g('pattern_scale')*9},uStrands:{value:strands(THREE)}};
 const NOISE='float h31(vec3 p){p=fract(p*.3183099+.1);p*=17.0;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}'+
  'float n3(vec3 x){vec3 i=floor(x),f=fract(x);f=f*f*(3.0-2.0*f);return mix(mix(mix(h31(i),h31(i+vec3(1,0,0)),f.x),mix(h31(i+vec3(0,1,0)),h31(i+vec3(1,1,0)),f.x),f.y),mix(mix(h31(i+vec3(0,0,1)),h31(i+vec3(1,0,1)),f.x),mix(h31(i+vec3(0,1,1)),h31(i+vec3(1,1,1)),f.x),f.y),f.z);}'+
  'float fbm3(vec3 p){return n3(p)*.55+n3(p*2.1)*.3+n3(p*4.3)*.15;}\n';
 // coat painter: palette + seeded pattern + masks (R belly, G accent, B glow) + fur shading
 const furPatch=(mat:any,shell:{t:number,len:number}|null)=>{mat.onBeforeCompile=(sh:any)=>{Object.assign(sh.uniforms,U,{uS:{value:shell?shell.t:0},uLen:{value:shell?shell.len:0}});
  sh.vertexShader='uniform float uS,uLen,uT;uniform vec3 uWind;uniform float uChaos;varying vec3 vObjP;varying vec2 vFurUv;varying float vLenN;varying vec3 vMask;\n'+NOISE+sh.vertexShader.replace('#include <begin_vertex>',`#include <begin_vertex>
   vObjP=position;vFurUv=uv;vMask=vec3(1.0);
   #ifdef USE_COLOR
   vMask=color.rgb;
   #endif
   vLenN=.5+.7*n3(position*38.0)*(.7+.3*n3(position*110.0));
   ${shell?`float L=uLen*vLenN*(1.0-vMask.b);vec3 comb=normalize(vec3(0.0,-1.0,-.35));transformed+=objectNormal*L*uS+(comb*.7+uWind+vec3(sin(uT*7.0+position.x*20.0),0.0,cos(uT*6.0+position.z*20.0))*uChaos*.15)*L*uS*uS;`:''}`)
   .replace('#include <color_vertex>','');
  sh.fragmentShader='uniform float uS,uT,uBeat,uPat,uPd,uPs;uniform vec3 uSeed,uBase,uAlt,uBelly,uAccent,uGlow,uDark,uLight;uniform sampler2D uStrands;varying vec3 vObjP;varying vec2 vFurUv;varying float vLenN;varying vec3 vMask;\n'+NOISE+
   sh.fragmentShader.replace('#include <color_fragment>',`
   ${shell?`if(uS>vLenN||vMask.b>.5)discard;float sd=texture2D(uStrands,vFurUv*14.0).r*.7+texture2D(uStrands,vFurUv*37.0).r*.3;if(sd<mix(.08,.85,clamp(uS/vLenN,0.0,1.0)))discard;`:''}
   vec3 p=vObjP*uPs+uSeed;float v=fbm3(p);float m=0.0;
   if(uPat<.5)m=smoothstep(.62-uPd*.12,.66-uPd*.12,v);                       // spots
   else if(uPat<1.5)m=smoothstep(.55,.6,abs(sin(vObjP.z*uPs*1.4+vObjP.y*3.0+v*4.0)));   // stripes
   else if(uPat<2.5)m=smoothstep(.7,1.15,vObjP.y)*.55+smoothstep(.55,.9,fbm3(p*.35))*.25;        // belly: soft points on crown/back
   else if(uPat<3.5)m=step(.86,h31(floor(p*2.0)));                             // stars
   else if(uPat<4.5)m=step(.5,fract(v*6.0))*.5;                                // facets
   else if(uPat<5.5)m=smoothstep(.5,.75,fbm3(p*.6))*.8;                        // moss
   else if(uPat<6.5)m=step(.9,max(fract(p.x*.5),fract(p.y*.5)))*.6;            // plates
   else if(uPat<7.5)m=smoothstep(.02,.0,abs(v-.5))*.9;                         // cracks (glow)
   else m=step(.94,max(fract(p.x),fract(p.z)))*.7;                             // circuits
   vec3 c=mix(uBase,uAlt,m*(uPat>6.5&&uPat<7.5?0.0:1.0));
   c=mix(c,uLight,smoothstep(.1,.9,vObjP.y)*.12);c=mix(c,uBelly,vMask.r*.9);c=mix(c,uAccent,vMask.g*.85);
   float hgt=${shell?'clamp(uS/vLenN,0.0,1.0)':'0.0'};
   diffuseColor.rgb=c*mix(.42,1.18,hgt);                                       // root AO -> bright tips
   float glowM=vMask.b+(uPat>6.5&&uPat<7.5?m:0.0)+(uPat>2.5&&uPat<3.5?m*.6:0.0);`)
   .replace('#include <emissivemap_fragment>',`#include <emissivemap_fragment>
   vec3 vd=normalize(vViewPosition),nn=normalize(vNormal);float fres=pow(1.0-abs(dot(nn,vd)),3.0);
   totalEmissiveRadiance+=uGlow*glowM*(1.2+uBeat*1.5)+vec3(.5,.6,1.0)*fres*fres*(.06+.3*hgt)+c*vec3(1.0,.6,.8)*vMask.g*.25;`);};
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
   float stars=step(.992,h31(floor(nv*180.0)))*smoothstep(1.1,.3,r);totalEmissiveRadiance=nc*2.2+vec3(1.0)*stars*1.4;`);};
 eyeMat.customProgramCacheKey=()=>'beast-eye-v2';
 let face:any=null,body:any=null;const shells:any[]=[];const shown=new Set<string>(['body','face','detail',...(EAR_V[gen.ears]||['ear_pointy'])]);
 if(gen.tail!=='none')shown.add(TAIL_V[gen.tail]||'tail_thin');if(gen.wings&&gen.wings!=='none')shown.add(WING_V[gen.wings]||'wing_feather');
 const glowMat=new THREE.MeshStandardMaterial({color:C.glow,emissive:C.glow,emissiveIntensity:2.2,roughness:.3});
 root.traverse((o:any)=>{if(!o.isMesh)return;const n=(o.name||'').replace(/_\d+$/,'');const key=['body','face','detail'].find(k=>n.startsWith(k))||n;
  o.castShadow=true;o.frustumCulled=false;
  if(n.startsWith('ear_')||n.startsWith('tail_')||n.startsWith('wing_')){o.visible=shown.has(n.replace(/\.\d+$/,''));}
  const mn=o.material?.name||'';
  if(mn==='fur'){const m=new THREE.MeshPhysicalMaterial({vertexColors:true,roughness:.85,sheen:.8,sheenRoughness:.5,sheenColor:C.light});furPatch(m,null);
   if(n.startsWith('ear_crown'))o.material=new THREE.MeshPhysicalMaterial({color:C.accent.clone().lerp(new THREE.Color(1,.82,.4),.6),metalness:1,roughness:.22,clearcoat:.6,emissive:C.glow,emissiveIntensity:.15});
   else if(n.startsWith('ear_')&&GLOWING.has(gen.ears)||n==='tail_flame'&&GLOWING.has(gen.tail))o.material=glowMat;else o.material=m;if(n.startsWith('body'))body=o;}
  else if(mn==='eye'){o.material=eyeMat;o.geometry.computeBoundingBox();const bb=o.geometry.boundingBox;const w=(bb.max.x-bb.min.x)/2;eyeC.value.set(bb.max.x-w/2,(bb.max.y+bb.min.y)/2,(bb.max.z+bb.min.z)/2-(bb.max.z-bb.min.z)*.3);}else if(mn==='iris'){o.material=new THREE.MeshBasicMaterial({color:C.glow,transparent:true,opacity:.0});}
  else if(mn==='shine')o.material=new THREE.MeshBasicMaterial({color:0xffffff,toneMapped:false});else if(mn==='glow')o.material=glowMat;
  else if(mn==='mouth')o.material=new THREE.MeshStandardMaterial({color:0x2a0f1c,roughness:.6});else if(mn==='nose')o.material=new THREE.MeshPhysicalMaterial({color:0x1a1222,roughness:.25,clearcoat:.8});
  if(o.morphTargetDictionary&&'blink' in o.morphTargetDictionary)face=o;});
 // 12-layer shell fur on the visible coat meshes (body + active fur variants)
 const N=SHELLS[tier],len=.034*(.8+g('chub')*.4);
 if(N>0)root.traverse((o:any)=>{if(!o.isSkinnedMesh||o.userData.shell)return;const mn=(o.material as any);if(!(mn&&mn.isMeshPhysicalMaterial&&mn.vertexColors))return;if(!o.visible)return;
  for(let k=1;k<=N;k++){const t=k/N;const m=new THREE.MeshPhysicalMaterial({vertexColors:true,roughness:.9,sheen:.6,sheenColor:C.light,transparent:false});furPatch(m,{t,len});
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
 function drive(dt:number,life:{speed:number;mode:string;sleep:number;lookCam:number;bob:number;heading:number;startle?:number},mp:any,lookLocal:{yaw:number;pitch:number}|null){
  t+=dt;U.uT.value=t;const mood=mp?.mood||{joy:.5,fear:.1,curiosity:.5,calm:.6,mischief:.3};const k=60*(mp?.stiffness||1),d=8*(mp?.damping||1),turb=mp?.turbulence||0,wind=mp?.wind||{x:0,y:0,z:0};
  U.uWind.value.set(wind.x*.4,wind.y*.2,wind.z*.4);U.uChaos.value=turb;
  let dh=life.heading-prevH;dh=((dh+Math.PI*3)%(Math.PI*2))-Math.PI;prevH=life.heading;const yr=clamp(dh/Math.max(dt,1e-3),-4,4);
  const st=clamp(life.speed*1.6),ph=life.bob,nap=life.sleep;
  legs.forEach((b,i)=>pose(b,Math.sin(ph+(i===0||i===3?0:Math.PI))*.55*st-nap*1.2*(i<2?1:-.6)));knees.forEach((b,i)=>pose(b,Math.max(0,-Math.sin(ph+(i===0||i===3?0:Math.PI)))*.6*st+nap*(i<2?1.6:-1.4)));
  const breathe=Math.sin(t*(1.6-mood.calm*.5))*.025;
  pose(bones.hips,0,0,Math.sin(ph)*.05*st);pose(bones.spine,-nap*.15+breathe,yr*.04,0);
  const yaw=lookLocal?clamp(lookLocal.yaw,-1,1):Math.sin(t*.4)*.3,pit=lookLocal?clamp(lookLocal.pitch,-.5,.5):nap*.5;
  pose(bones.neck,pit*.4,yaw*.4,0);pose(bones.head,pit*.6+(life.startle||0)*-.2,yaw*.6,Math.sin(t*.7)*.06*mood.curiosity+ex.curious*.2);
  ears.forEach((b,i)=>{const s=i?1:-1;springStep(sp.ear[i],-yr*.08+wind.x*s*.3+Math.sin(t*9+i)*turb*.15-ex.scared*.7+ex.happy*.15,k,d,dt);springStep(sp.ear2[i],Math.abs(Math.sin(ph))*st*.3+ex.curious*.3-nap*.5,k,d,dt);
   pose(b,sp.ear2[i].x,0,sp.ear[i].x*s);pose(ears1[i],sp.ear2[i].x*.6,0,sp.ear[i].x*s*.6);});
  tail.forEach((b,i)=>{const wag=Math.sin(t*(4+mood.joy*6)-i*.7)*(.12+mood.joy*.4)*(1-nap*.8);springStep(sp.tail[i],wag-yr*.12*(i+1)/tail.length+wind.x*.2+Math.sin(t*7+i)*turb*.12,k*.8,d*.8,dt);
   springStep(sp.tail2[i],(i===0?.25-nap*.5:-.04)+st*.08,k*.8,d,dt);pose(b,-sp.tail2[i].x,sp.tail[i].x,0);});
  wings.forEach((b,i)=>{const s=i?1:-1;springStep(sp.wing[i],Math.sin(t*1.5)*.08+(life.speed>.9?Math.sin(t*12)*.5:0)+wind.z*.1,k*1.5,d,dt);pose(b,0,0,s*sp.wing[i].x);});
  blinkT-=dt;if(blinkT<=0){blinkT=2+((t*7919)%1)*4;ex.blink=1;}ex.blink=Math.max(0,ex.blink-dt*7);
  const tw=(key:keyof typeof ex,v:number,r=4)=>{ex[key]+=(v-ex[key])*Math.min(1,dt*r);};
  tw('sleepy',nap);tw('happy',life.mode==='play'||life.mode==='approach'?mood.joy:mood.joy*.25);tw('curious',life.mode==='glance'||life.mode==='sniff'?.8:mood.curiosity*.15);
  tw('scared',(life.startle||0)+mood.fear*.25);tw('angry',mood.mischief>.8?.4:0);tw('grin',life.mode==='play'?.8:mood.joy*.3);tw('o',life.mode==='sniff'&&life.speed<.05?.5+.4*Math.abs(Math.sin(t*6)):0,8);tw('w',life.mode==='approach'?.7:0);
  setM('blink',Math.max(ex.blink,ex.sleepy*.2));setM('happy',ex.happy*(1-ex.blink));setM('sleepy',ex.sleepy);setM('curious',ex.curious);setM('scared',ex.scared);setM('angry',ex.angry);
  setM('mouth_grin',ex.grin*(1-ex.o));setM('mouth_o',ex.o);setM('mouth_w',ex.w*(1-ex.o));
  U.uBeat.value=Math.pow(Math.max(0,Math.sin(t*(1+(mp?mp.stiffness:1)*.9)*Math.PI*2)),12);glowMat.emissiveIntensity=1.6+U.uBeat.value*1.4+mood.joy*.4;
 }
 return {root,drive,tris:Math.round(tris),shells:shells.length,plan,expr:ex,setTier(tr:Tier){const n=SHELLS[tr];shells.forEach((s,i)=>{s.visible=n>=12||(i%12)%Math.ceil(12/Math.max(1,n))===0&&n>0;});},
  dispose(){root.traverse((o:any)=>{if(o.isMesh){o.geometry?.dispose();(Array.isArray(o.material)?o.material:[o.material]).forEach((m:any)=>m?.dispose());}});}};
}
