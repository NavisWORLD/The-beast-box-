'use client';
/**
 * Sculpted, rigged Zeref (public/creatures3d/zeref.glb) on a cinematic three.js stage. Spring bones,
 * breathing, gait and expressions all run on the CST integrator via lib/creatures3d/zeref-glb-driver.mjs.
 * Shown on /beast-cage/turntable only behind ?glb=1 while Cory reviews it.
 *
 * v4 look: PMREM violet/cosmic-blue environment, key + strong rim + fill, AgX, bloom on emissives/starlight,
 * plush shell fur (length noise, tapered strands, root AO, rim sheen, combed + wind), ear/paw warmth,
 * wing backlight, glossy refracting cornea, shader-drawn ^^ happy eyes, contact shadows that follow the paws.
 * Adaptive quality tier: high / med / low (?tier= to force), downgraded live if frames are slow.
 */
import {createCSTTurntable} from '@/lib/physics/cst-turntable.mjs';
import {useEffect,useRef} from 'react';
import * as THREE from 'three';
import {createZerefDriver,ZEREF_GLB_URL} from '@/lib/creatures3d/zeref-glb-driver.mjs';
import {seededRng} from '@/lib/physics/cst-integrator.mjs';
import {guardCanvasTouch} from '@/lib/three/touch-guard';

export type ZerefMood='calm'|'happy'|'curious'|'scared'|'sleepy'|'angry'|'walk';
type Tier='high'|'med'|'low';
const TIERS:Record<Tier,{shells:number;bloom:boolean;dpr:number;motes:number}>={high:{shells:12,bloom:true,dpr:2,motes:260},med:{shells:7,bloom:true,dpr:1.5,motes:140},low:{shells:3,bloom:false,dpr:1,motes:60}};
function pickTier(q:string|null,reduced:boolean):Tier{
 if(q==='high'||q==='med'||q==='low')return q;
 const nav:any=navigator,mobile=matchMedia('(pointer: coarse)').matches||window.innerWidth<820;
 if(reduced||(mobile&&(nav.hardwareConcurrency||4)<=4)||nav.deviceMemory&&nav.deviceMemory<=3)return 'low';
 return mobile?'med':'high';
}
function gradientTex(stops:[number,string][],w=4,h=256,radial=false){
 const c=document.createElement('canvas');c.width=radial?256:w;c.height=h;const g=c.getContext('2d')!;
 const gr=radial?g.createRadialGradient(128,h*.42,4,128,h*.5,h*.75):g.createLinearGradient(0,0,0,h);for(const [o,col] of stops)gr.addColorStop(o,col);
 g.fillStyle=gr;g.fillRect(0,0,c.width,h);const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t;
}
function blobTex(){const c=document.createElement('canvas');c.width=c.height=128;const g=c.getContext('2d')!;
 const gr=g.createRadialGradient(64,64,0,64,64,64);gr.addColorStop(0,'rgba(0,0,0,1)');gr.addColorStop(.45,'rgba(0,0,0,.55)');gr.addColorStop(1,'rgba(0,0,0,0)');
 g.fillStyle=gr;g.fillRect(0,0,128,128);return new THREE.CanvasTexture(c);}
/** Violet / cosmic-blue studio environment, prefiltered with PMREM (image-based light + reflections). */
function cosmicEnvironment(renderer:THREE.WebGLRenderer){
 const env=new THREE.Scene();
 const sky=new THREE.Mesh(new THREE.SphereGeometry(10,32,16),new THREE.ShaderMaterial({side:THREE.BackSide,depthWrite:false,
  vertexShader:'varying vec3 vP;void main(){vP=normalize(position);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
  fragmentShader:`varying vec3 vP;void main(){float y=vP.y;vec3 top=vec3(.32,.18,.72),hor=vec3(.10,.22,.55),bot=vec3(.02,.01,.05);
   vec3 c=y>0.?mix(hor,top,pow(y,.7)):mix(hor,bot,pow(-y,.5));gl_FragColor=vec4(c,1.);}`}));
 env.add(sky);
 const panel=(col:number,s:number,w:number,h:number,p:[number,number,number])=>{const m=new THREE.Mesh(new THREE.PlaneGeometry(w,h),new THREE.MeshBasicMaterial({color:new THREE.Color(col).multiplyScalar(s),side:THREE.DoubleSide}));m.position.set(...p);m.lookAt(0,0,0);env.add(m);};
 panel(0xf1e6ff,6,5,4,[-5,6,6]);        // key softbox (warm lavender white)
 panel(0x7fe6ff,9,1.2,7,[4,3,-6]);       // cyan rim strip
 panel(0xb88cff,7,1.2,7,[-5,3,-5]);      // violet rim strip
 panel(0x5a7bff,1.6,6,3,[6,1,4]);        // blue fill
 const pm=new THREE.PMREMGenerator(renderer);const rt=pm.fromScene(env,.03);pm.dispose();return rt.texture;
}
export default function ZerefGlb3D({spin=true,angle=0,mood='calm',seed='zeref'}:{spin?:boolean;angle?:number;mood?:ZerefMood;seed?:string}){
 const host=useRef<HTMLDivElement>(null);
 const live=useRef({spin,angle,mood});
 useEffect(()=>{live.current={spin,angle,mood};},[spin,angle,mood]);
 useEffect(()=>{
  const el=host.current;if(!el)return;let disposed=false,raf=0;
  const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const qp=new URLSearchParams(window.location.search);const qYaw=qp.get('yaw');const qMood=qp.get('mood');const qNoBlink=qp.get('blink')==='0';
  let tier:Tier=pickTier(qp.get('tier'),reduced);const tierLocked=!!qp.get('tier');
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:'high-performance'});
  renderer.setPixelRatio(Math.min(TIERS[tier].dpr,window.devicePixelRatio||1));renderer.outputColorSpace=THREE.SRGBColorSpace;
  renderer.toneMapping=THREE.AgXToneMapping;renderer.toneMappingExposure=1.0;
  el.appendChild(renderer.domElement);renderer.domElement.style.width='100%';renderer.domElement.style.height='100%';
  const scene=new THREE.Scene();const camera=new THREE.PerspectiveCamera(32,1,.05,50);
  scene.background=gradientTex([[0,'#3a2370'],[.55,'#1a1546'],[1,'#07061a']],4,256,true);
  scene.environment=cosmicEnvironment(renderer);scene.environmentIntensity=.5;
  // cinematic light rig: key + strong cyan/violet rims + soft blue fill
  scene.add(new THREE.HemisphereLight(0xa996ff,0x0a0618,.2));
  const key=new THREE.DirectionalLight(0xfff1ff,2.6);key.position.set(-2.2,3.2,3);scene.add(key);
  const fill=new THREE.DirectionalLight(0x6f8cff,.7);fill.position.set(2.6,1,2.4);scene.add(fill);
  const rim=new THREE.DirectionalLight(0x8fe8ff,4.2);rim.position.set(1.8,2.3,-3);scene.add(rim);
  const rim2=new THREE.DirectionalLight(0xc08cff,3.2);rim2.position.set(-2.2,2.6,-2.4);scene.add(rim2);
  const pivot=new THREE.Group();scene.add(pivot);
  // floor: faint star-dust ground that scrolls with the gait (feet stay planted on it) + soft contact shadows
  const uSwirl={value:0},uBeat={value:0},uStir={value:0},uCoh={value:.6},uChaos={value:.2},uMoteScale={value:400};
  const uTravel={value:0},starT={value:0},uHappy={value:0},uRimView={value:new THREE.Vector3()},uWind={value:new THREE.Vector3()};
  const floor=new THREE.Mesh(new THREE.CircleGeometry(1.7,64),new THREE.ShaderMaterial({transparent:true,depthWrite:false,uniforms:{uTravel,uT:starT},
   vertexShader:'varying vec2 vP;void main(){vP=position.xy;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
   fragmentShader:`varying vec2 vP;uniform float uTravel,uT;
    float h(vec2 p){return fract(sin(dot(p,vec2(41.3,289.1)))*43758.5);}
    void main(){vec2 p=vec2(vP.x,-vP.y+uTravel);float r=length(vP)/1.7;
     vec2 g=p*9.;vec2 i=floor(g),f=fract(g);float s=h(i);float d=length(f-vec2(h(i+.3),h(i+.7)));
     float star=step(.93,s)*smoothstep(.08,.0,d)*(.6+.4*sin(uT*2.+s*40.));
     float grid=(smoothstep(.985,1.,abs(sin(p.x*6.2832*1.2)))+smoothstep(.985,1.,abs(sin(p.y*6.2832*1.2))))*.06;
     vec3 c=vec3(.05,.035,.12)+vec3(.55,.5,1.)*star+vec3(.3,.26,.7)*grid;
     gl_FragColor=vec4(c,(1.-smoothstep(.5,1.,r))*.8);}`}));
  floor.rotation.x=-Math.PI/2;pivot.add(floor);
  const blob=blobTex();
  const shadowMat=(o:number)=>new THREE.MeshBasicMaterial({map:blob,transparent:true,opacity:o,depthWrite:false,color:0x000000});
  const bodyShadow=new THREE.Mesh(new THREE.PlaneGeometry(1.15,.95),shadowMat(.55));bodyShadow.rotation.x=-Math.PI/2;bodyShadow.position.set(0,.002,-.02);pivot.add(bodyShadow);
  const footShadows:THREE.Mesh[]=[];for(let i=0;i<4;i++){const m=new THREE.Mesh(new THREE.PlaneGeometry(.22,.2),shadowMat(.7));m.rotation.x=-Math.PI/2;m.position.y=.003;pivot.add(m);footShadows.push(m);}
  if(qYaw)live.current={...live.current,spin:false,angle:Number(qYaw)};
  let driver:ReturnType<typeof createZerefDriver>|null=null,gltf0:any=null;
  let composer:any=null,bloomPass:any=null;const shells:THREE.Mesh[]=[];const pulseMats:{mat:any,base:number}[]=[];let motes:THREE.Points|null=null;let eyeMat:any=null,catchMat:any=null,happyMesh:any=null;
  const applyTier=()=>{const T=TIERS[tier];renderer.setPixelRatio(Math.min(T.dpr,window.devicePixelRatio||1));
   shells.forEach((s,i)=>{s.visible=(s.userData.k%Math.ceil(12/T.shells)===0)||T.shells>=12;});if(bloomPass)bloomPass.enabled=T.bloom;if(motes)motes.geometry.setDrawRange(0,T.motes);resize();};
  (async()=>{
   const [{GLTFLoader},{MeshoptDecoder},{EffectComposer},{RenderPass},{UnrealBloomPass},{OutputPass}]=await Promise.all([
    import('three/examples/jsm/loaders/GLTFLoader.js'),import('three/examples/jsm/libs/meshopt_decoder.module.js'),
    import('three/examples/jsm/postprocessing/EffectComposer.js'),import('three/examples/jsm/postprocessing/RenderPass.js'),
    import('three/examples/jsm/postprocessing/UnrealBloomPass.js'),import('three/examples/jsm/postprocessing/OutputPass.js')]);
   const loader=new GLTFLoader();loader.setMeshoptDecoder(MeshoptDecoder);
   const gltf=await loader.loadAsync(ZEREF_GLB_URL);if(disposed)return;
   composer=new EffectComposer(renderer);composer.addPass(new RenderPass(scene,camera));
   bloomPass=new UnrealBloomPass(new THREE.Vector2(256,256),.3,.35,1.0);composer.addPass(bloomPass);composer.addPass(new OutputPass());
   gltf.scene.traverse((o:any)=>{if(o.isMesh){o.frustumCulled=false;}});
   const strands=await new THREE.TextureLoader().loadAsync('/creatures3d/zeref-fur-strands.png');strands.wrapS=strands.wrapT=THREE.RepeatWrapping;
   // shared fur shading: starlight twinkle (the ONE impossible detail), root AO + tip sheen for shells, ear/paw warmth, rim sheen
   const furPatch=(mat:any,shell:{t:number,len:number}|null,drift:number)=>{
    mat.onBeforeCompile=(sh:any)=>{Object.assign(sh.uniforms,{uSwirl,uCoh,uChaos,uStarT:starT,uRimView,uWind,uStrands:{value:strands},uT:{value:shell?shell.t:0},uLen:{value:shell?shell.len:0}});
     sh.vertexShader=`uniform float uT,uLen;uniform vec3 uWind;varying vec3 vObjP;varying vec2 vFurUv;varying float vLenN;
      float vn(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);float a=fract(sin(dot(i,vec2(127.1,311.7)))*43758.5),b=fract(sin(dot(i+vec2(1,0),vec2(127.1,311.7)))*43758.5),
       c=fract(sin(dot(i+vec2(0,1),vec2(127.1,311.7)))*43758.5),d=fract(sin(dot(i+vec2(1,1),vec2(127.1,311.7)))*43758.5);return mix(mix(a,b,f.x),mix(c,d,f.x),f.y);}
      `+sh.vertexShader.replace('#include <begin_vertex>',`#include <begin_vertex>
      vObjP=position;vFurUv=uv;float fmask=uv.x<0.?0.:1.;
      vLenN=.55+.75*vn(uv*11.)*(.7+.3*vn(uv*37.));
      ${shell?`float L=uLen*vLenN*fmask;transformed+=objectNormal*L*uT+(normalize(vec3(0.,-1.,-.5))*.75+uWind)*L*uT*uT;`:''}`);
     sh.fragmentShader=`uniform float uStarT,uT,uSwirl,uCoh,uChaos;float h21(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}vec2 h22(vec2 p){return vec2(h21(p),h21(p+19.19));}
      float dSeg(vec2 p,vec2 a,vec2 b){vec2 pa=p-a,ba=b-a;return length(pa-ba*clamp(dot(pa,ba)/dot(ba,ba),0.,1.));}uniform vec3 uRimView;uniform sampler2D uStrands;varying vec3 vObjP;varying vec2 vFurUv;varying float vLenN;
      `+sh.fragmentShader.replace('#include <color_fragment>',`#include <color_fragment>
      ${shell?`if(vFurUv.x<0.||uT>vLenN)discard;float sd=texture2D(uStrands,vFurUv*15.).r*.75+texture2D(uStrands,vFurUv*41.).r*.25;
       float need=mix(.18,.96,clamp(uT/vLenN,0.,1.));if(sd<need)discard;`:''}
      float hgt=${shell?'clamp(uT/vLenN,0.,1.)':'0.'};
      diffuseColor.rgb*=mix(.4,1.05,hgt);   // self-shadowing toward the roots, lighter tips
      float earM=smoothstep(1.06,1.16,vObjP.y)*smoothstep(.15,.25,abs(vObjP.x)),pawM=1.-smoothstep(.04,.13,vObjP.y);float warmM=max(earM,pawM);`)
      .replace('#include <emissivemap_fragment>',`#ifdef USE_EMISSIVEMAP
       // live CST starlight: the field swirls with chaos + Lorenz energy, twinkles harder when chaotic, and settles into
       // steady constellations (linked star pairs) as coherence rises
       float sa=uSwirl*${(drift*30).toFixed(4)};vec2 cu=vEmissiveMapUv-.5;cu=mat2(cos(sa),-sin(sa),sin(sa),cos(sa))*cu;
       vec2 suv=cu+.5+vec2(uSwirl*${drift.toFixed(4)},uSwirl*${(drift*.6).toFixed(4)});vec4 se=texture2D(emissiveMap,suv);
       float cell=h21(floor(suv*48.));float coh=smoothstep(.5,.85,uCoh),tw=mix(.5,.1,coh)*(1.+uChaos);
       totalEmissiveRadiance*=se.rgb*((1.-tw)+tw*sin(uStarT*(1.5+cell*3.)*(1.+2.*uChaos)+cell*6.2831));
       vec2 cg=vEmissiveMapUv*7.,ci=floor(cg),cf=fract(cg);vec2 pa=.2+.6*h22(ci),pb=.2+.6*h22(ci+17.);
       float con=(smoothstep(.014,.0,dSeg(cf,pa,pb))*.4+smoothstep(.06,.0,min(length(cf-pa),length(cf-pb))))*step(.5,h21(ci+3.))*coh;
       totalEmissiveRadiance+=vec3(.72,.78,1.)*con*.85;
      #endif
      vec3 vd=normalize(vViewPosition),nn=normalize(vNormal);float fres=pow(1.-abs(dot(nn,vd)),3.);
      float back=pow(clamp(dot(-vd,normalize(uRimView))*.5+.5,0.,1.),2.);
      totalEmissiveRadiance+=mix(vec3(.55,.25,1.),vec3(.15,.9,1.),.5+.5*nn.y)*fres*fres*(.12+.35*hgt);                       // rim sheen on the coat
      totalEmissiveRadiance+=diffuseColor.rgb*vec3(1.,.55,.8)*warmM*(.25+.9*back*fres+.25*back);  // subsurface-like warmth (ears, paws)`);};
    mat.customProgramCacheKey=()=>'zeref-fur-'+(shell?shell.t.toFixed(3):'base');mat.needsUpdate=true;};
   const furMeshes:any[]=[];
   gltf.scene.traverse((o:any)=>{if(!(o.isMesh&&o.material))return;const mat=o.material,n=mat.name;
    if(n==='zeref_fur'){mat.color.setRGB(.85,.8,1.0);if('sheen' in mat){mat.sheen=.55;mat.sheenColor=new THREE.Color(0xc7a4ff);mat.sheenRoughness=.45;}mat.envMapIntensity=.6;
     if(o.geometry.attributes.uv1){/* realism v5: sculpt->bake normal + AO on the dedicated bake UV (TEXCOORD_1) */const TL=new THREE.TextureLoader(),bt=(k:string)=>{const t=TL.load(`/creatures3d/bake/zeref_body_${k}.png`);t.flipY=false;t.channel=1;return t;};
      mat.normalMap=bt('normal');mat.normalScale=new THREE.Vector2(.6,.6);mat.aoMap=bt('ao');mat.aoMapIntensity=.5;}
     furPatch(mat,null,.004);furMeshes.push(o);}
    else if(n==='zeref_eye'){eyeMat=new THREE.MeshPhysicalMaterial({map:mat.map,emissive:0xffffff,emissiveMap:mat.emissiveMap,emissiveIntensity:2.7,roughness:.25,clearcoat:1,clearcoatRoughness:.03,ior:1.4,envMapIntensity:.55});
     eyeMat.name='zeref_eye';o.material=eyeMat;happyMesh=o;
     eyeMat.onBeforeCompile=(sh:any)=>{Object.assign(sh.uniforms,{uHappy,uStarT:starT,uSwirl,uChaos});
      sh.fragmentShader='uniform float uHappy,uStarT,uSwirl,uChaos;\nfloat vn2(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);float a=fract(sin(dot(i,vec2(127.1,311.7)))*43758.5),b=fract(sin(dot(i+vec2(1,0),vec2(127.1,311.7)))*43758.5),c=fract(sin(dot(i+vec2(0,1),vec2(127.1,311.7)))*43758.5),d=fract(sin(dot(i+vec2(1,1),vec2(127.1,311.7)))*43758.5);return mix(mix(a,b,f.x),mix(c,d,f.x),f.y);}\n'+sh.fragmentShader
      .replace('#include <map_fragment>',`#ifdef USE_MAP
        // glossy cornea refraction: iris sampled with a view-dependent parallax that grows toward the pupil
        vec2 c0=vMapUv-.5;float rr=clamp(length(c0)*2.,0.,1.);vec3 vdir=normalize(vViewPosition);
        vec2 puv=vMapUv-vec2(-vdir.x,vdir.y)*.045*(1.-rr*rr);vec4 tc=texture2D(map,puv);diffuseColor*=tc;
       #endif
        // windows into a nebula: three parallax layers sunk behind the cornea, swirling on the CST clock
        vec3 neb=vec3(0.);{vec2 e0=(vMapUv-.5);vec3 vd2=normalize(vViewPosition);
         for(int L=1;L<=3;L++){float fl=float(L);vec2 q=e0-vec2(-vd2.x,vd2.y)*.07*fl;float a=uSwirl*.12*fl*(mod(fl,2.)*2.-1.);q=mat2(cos(a),-sin(a),sin(a),cos(a))*q;
          float n=vn2(q*5.+fl*7.3)*vn2(q*11.-fl*3.1);float st=step(.985,vn2(q*60.+fl*13.))*1.5;
          neb+=mix(vec3(.45,.16,.9),vec3(.15,.5,.9),fl/3.)*(n*n*1.1+st*3.)/fl;}}
        float pupM=1.-smoothstep(.16,.3,length(vMapUv-.5)),irisM=1.-smoothstep(.36,.48,length(vMapUv-.5));
        // ^^ happy: the eye closes into the rig's lavender arc (shader-drawn, crisp at any zoom)
        vec2 hx=(vMapUv-.5)*vec2(2.,-2.);float ya=-.22+.6*(1.-hx.x*hx.x);float dl=abs(hx.y-ya);
        float aa=fwidth(hx.y)*1.5;float arc=(1.-smoothstep(.075-aa,.075+aa,dl))*(1.-smoothstep(.78,.86,abs(hx.x)));
        diffuseColor.rgb=mix(diffuseColor.rgb,mix(vec3(.035,.022,.07),vec3(.86,.76,1.),arc),uHappy);`)
      .replace('#include <emissivemap_fragment>',`#include <emissivemap_fragment>
        totalEmissiveRadiance+=neb*(.12*irisM+.13*pupM)*(1.+.6*uChaos);totalEmissiveRadiance*=1.-uHappy*.92;totalEmissiveRadiance+=vec3(.75,.62,1.)*arc*uHappy*.9;`);};
     eyeMat.customProgramCacheKey=()=>'zeref-eye-v4';}
    else if(n==='zeref_catch'){catchMat=mat;mat.transparent=true;}
    else if(n==='zeref_wing'){mat.side=THREE.DoubleSide;mat.transparent=true;mat.opacity=.9;mat.depthWrite=false;
     mat.onBeforeCompile=(sh:any)=>{sh.uniforms.uRimView=uRimView;sh.uniforms.uBeat=uBeat;sh.uniforms.uStir=uStir;sh.fragmentShader='uniform vec3 uRimView;uniform float uBeat,uStir;\n'+sh.fragmentShader.replace('#include <emissivemap_fragment>',`#include <emissivemap_fragment>
      totalEmissiveRadiance*=1.+uBeat*(.55+.8*uStir);   // veins pulse with the heartbeat (rate = arousal)
      vec3 wv=normalize(vViewPosition);float bl=pow(clamp(dot(-wv,normalize(uRimView))*.5+.5,0.,1.),3.);
      totalEmissiveRadiance+=diffuseColor.rgb*vec3(.75,.85,1.2)*(.18+1.1*bl);   // membrane translucency, glows when backlit`);};
     mat.customProgramCacheKey=()=>'zeref-wing-v4';mat.needsUpdate=true;}
    else if(n==='zeref_glow'||n==='zeref_gem'||n==='zeref_moon'||n==='zeref_wisp'){mat.emissiveIntensity=(mat.emissiveIntensity||1)*1.25;if(n==='zeref_moon'||n==='zeref_gem')pulseMats.push({mat,base:mat.emissiveIntensity});}
   });
   // plush shell fur: up to 12 shells; tiers show every 2nd/4th shell. Runtime only (outside the 25k-tri asset budget).
   const SH=qp.get('fur')==='0'?0:12;
   for(const fm of furMeshes)for(let k=1;k<=SH;k++){const t=k/SH;
    const m=new THREE.MeshPhysicalMaterial({vertexColors:true,roughness:.7,color:new THREE.Color(.85,.8,1.0),sheen:.55,sheenColor:new THREE.Color(0xc7a4ff),sheenRoughness:.4,
     emissive:0xffffff,emissiveMap:fm.material.emissiveMap,emissiveIntensity:1.15,envMapIntensity:.9});
    furPatch(m,{t,len:.024},.004);
    const shell=new THREE.SkinnedMesh(fm.geometry,m);shell.bind(fm.skeleton,fm.bindMatrix);shell.userData.k=k;
    shell.morphTargetInfluences=fm.morphTargetInfluences;shell.morphTargetDictionary=fm.morphTargetDictionary;
    shell.position.copy(fm.position);shell.quaternion.copy(fm.quaternion);shell.scale.copy(fm.scale);shell.frustumCulled=false;shell.renderOrder=k;fm.parent.add(shell);shells.push(shell);}
   // aura: a soft halo behind him (no hull ghosting over the face), faint at rest, swelling when the beast stirs
   {const am=new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,uniforms:{uStir,uBeat,uSwirl},
     vertexShader:'varying vec2 vU;void main(){vU=uv-.5;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
     fragmentShader:`varying vec2 vU;uniform float uStir,uBeat,uSwirl;void main(){vec2 q=vU*vec2(1.,1.15);float r=length(q);float a=atan(q.y,q.x);
      float rays=.75+.25*sin(a*7.+uSwirl*.8)*sin(a*3.-uSwirl*.5);float g=exp(-r*r*14.)*rays;
      vec3 c=mix(vec3(.35,.85,1.),vec3(.55,.3,1.),smoothstep(.0,.35,r));gl_FragColor=vec4(c*g*(.10+.45*uStir)*(1.+.3*uBeat),1.);}`});
    const halo=new THREE.Mesh(new THREE.PlaneGeometry(2.6,2.6),am);halo.position.set(0,.68,-.55);halo.renderOrder=-1;scene.add(halo);}
   // starlight motes shed when stirred: GPU-animated points, layout deterministic from the seed
   {const N=TIERS.high.motes,rng=seededRng('motes:'+seed),pos=new Float32Array(N*3),sd=new Float32Array(N*4);
    for(let i=0;i<N;i++){const u=rng()*2-1,a=rng()*Math.PI*2,r=Math.sqrt(1-u*u);pos.set([r*Math.cos(a),u,r*Math.sin(a)],i*3);sd.set([rng(),rng(),rng(),rng()],i*4);}
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(pos,3));g.setAttribute('aSeed',new THREE.BufferAttribute(sd,4));
    const m=new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,uniforms:{uT:starT,uStir,uSwirl,uChaos,uScale:uMoteScale},
     vertexShader:`attribute vec4 aSeed;uniform float uT,uStir,uSwirl,uChaos,uScale;varying float vA;varying vec3 vC;
      void main(){float life=fract(uT*(.18+.3*aSeed.w)*(1.+uChaos)+aSeed.z);vec3 d=position;
       vec3 p=vec3(0.,.62,0.)+d*vec3(.40,.52,.34)+(d*.3+vec3(0.,.55,0.))*life*(.45+.6*uChaos);
       float a=uSwirl*.5*life+aSeed.x*6.2831*.05;p.xz=mat2(cos(a),-sin(a),sin(a),cos(a))*p.xz;
       vA=uStir*smoothstep(0.,.12,life)*(1.-life)*(.5+.5*aSeed.y);vC=mix(vec3(.65,.4,1.),vec3(.45,.9,1.),aSeed.x);
       vec4 mv=modelViewMatrix*vec4(p,1.);gl_PointSize=(.012+.02*aSeed.y)*uScale*(1.-.4*life)/-mv.z;gl_Position=projectionMatrix*mv;}`,
     fragmentShader:`varying float vA;varying vec3 vC;void main(){vec2 c=gl_PointCoord-.5;float d=length(c);if(d>.5)discard;float k=smoothstep(.5,0.,d);gl_FragColor=vec4(vC*k*k*vA*1.6,1.);}`});
    motes=new THREE.Points(g,m);motes.frustumCulled=false;motes.renderOrder=30;pivot.add(motes);}
   gltf0=gltf;pivot.add(gltf.scene);driver=createZerefDriver(THREE,gltf.scene,{seed,mood:live.current.mood});
   applyTier();el.dataset.zerefGlb='ready';el.dataset.zerefTier=tier;
  })().catch(err=>{el.dataset.zerefGlb='error';console.warn('zeref glb',err);});
  function resize(){const r=el!.getBoundingClientRect();if(r.width<2)return;renderer.setSize(r.width,r.height,false);composer?.setSize(r.width,r.height);
   bloomPass?.resolution.set(r.width/2,r.height/2);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();
   uMoteScale.value=r.height*renderer.getPixelRatio()/(2*Math.tan(THREE.MathUtils.degToRad(camera.fov/2)));}
  const ro=new ResizeObserver(resize);ro.observe(el);resize();
  // one-finger / mouse drag spins him (page scroll is untouched outside the stage)
  const unguard=guardCanvasTouch(el,{hint:'↔ Drag sideways to spin Zeref'});let drag:{x:number,yaw:number}|null=null;
  const pd=(e:PointerEvent)=>{drag={x:e.clientX,yaw};};const pm=(e:PointerEvent)=>{if(!drag)return;const w=el.getBoundingClientRect().width||1;yaw=drag.yaw-(e.clientX-drag.x)/w*Math.PI*2;live.current={...live.current,spin:false,angle:THREE.MathUtils.radToDeg(yaw)};};
  const pu=()=>{drag=null;};el.addEventListener('pointerdown',pd);el.addEventListener('pointermove',pm);el.addEventListener('pointerup',pu);el.addEventListener('pointercancel',pu);
  const cstTT=createCSTTurntable(seed,{speed:.5});// CST inertia + damping + Lorenz sway instead of a linear spin
  let last=performance.now(),yaw=qYaw?THREE.MathUtils.degToRad(Number(qYaw)):0,perfN=0,perfAcc=0;
  const qManual=qp.get('manual')==='1';let manualDt=0,manualMood:any=null;
  const review:any={setYaw:(d:number)=>{live.current={...live.current,spin:false,angle:d};yaw=THREE.MathUtils.degToRad(d);},
   morphs:()=>{const o:any={};gltf0?.scene.traverse((m:any)=>{if(m.morphTargetDictionary&&!o[m.name]){o[m.name]=Object.fromEntries(Object.entries(m.morphTargetDictionary).map(([k,i]:any)=>[k,+m.morphTargetInfluences[i].toFixed(2)]).filter(([,v])=>v));}});return o;},
   tier:()=>tier,feet:()=>driver?.feet(),cosmic:()=>driver?.cosmic(),
   step:(dt:number,mood?:string,yawDeg?:number)=>{manualDt=dt;if(mood)manualMood=mood;if(yawDeg!==undefined){live.current={...live.current,spin:false,angle:yawDeg};yaw=THREE.MathUtils.degToRad(yawDeg);}tick(0);return !!driver;}};
  (window as any).__zerefReview=review;
  const tv=new THREE.Vector3();
  function tick(now:number){
   if(qManual&&now!==0){raf=requestAnimationFrame(tick);return;}
   const dt=qManual?manualDt:Math.min(.1,(now-last)/1000);last=now;const L=live.current;
   // adaptive tier: if frames run slow for ~2 s, step down (never in manual/forced mode)
   if(!qManual&&!tierLocked&&driver&&tier!=='low'){perfAcc+=dt;perfN++;if(perfN>=120){if(perfAcc/perfN>1/38){tier=tier==='high'?'med':'low';applyTier();el!.dataset.zerefTier=tier;}perfN=0;perfAcc=0;}}
   starT.value+=reduced?0:dt;
   if(L.spin&&!reduced){const p0=cstTT.yaw;cstTT.step(dt);yaw+=cstTT.yaw-p0;}else yaw+=(THREE.MathUtils.degToRad(L.angle)-yaw)*Math.min(1,qManual?1:dt*6);
   pivot.rotation.y=-yaw;
   camera.position.set(0,.85,3.9);camera.lookAt(0,.66,0);
   if(driver){driver.setMood((manualMood as ZerefMood)||(qMood as ZerefMood)||L.mood);driver.update(reduced?0:dt);
    if(qNoBlink)gltf0?.scene.traverse((m:any)=>{const i=m.morphTargetDictionary?.blink;if(i!==undefined)m.morphTargetInfluences[i]=0;});
    uTravel.value=driver.travel;
    const hi=happyMesh?.morphTargetDictionary?.happy;const hv=hi!==undefined?happyMesh.morphTargetInfluences[hi]:0;uHappy.value=THREE.MathUtils.smoothstep(hv,.35,.8);
    if(eyeMat)eyeMat.clearcoat=1-.8*uHappy.value;if(catchMat)catchMat.opacity=1-uHappy.value;
    const ft=driver.feet();ft.forEach((f:any,i:number)=>{const s=footShadows[i];if(!s)return;s.position.x=f.x;s.position.z=f.z;const k=1-Math.min(1,f.lift/.05);
     (s.material as THREE.MeshBasicMaterial).opacity=.15+.55*k;s.scale.setScalar(1.25-.35*k);});
    const cz=driver.cosmic();uSwirl.value=cz.swirl;uBeat.value=reduced?0:cz.beat;uStir.value=cz.stir;uCoh.value=cz.coherence;uChaos.value=cz.chaos;
    for(const p of pulseMats)p.mat.emissiveIntensity=p.base*(1+.7*uBeat.value*(.5+.5*cz.stir));
    const mp:any=driver.params;uWind.value.set(mp.wind.x*.25,0,mp.wind.z*.25);}
   tv.copy(rim.position).normalize().transformDirection(camera.matrixWorldInverse);uRimView.value.copy(tv);
   if(composer&&TIERS[tier].bloom)composer.render(dt);else renderer.render(scene,camera);
   if(!(qManual&&now===0))raf=requestAnimationFrame(tick);
  }
  raf=requestAnimationFrame(tick);
  return ()=>{disposed=true;unguard();el.removeEventListener('pointerdown',pd);el.removeEventListener('pointermove',pm);el.removeEventListener('pointerup',pu);el.removeEventListener('pointercancel',pu);cancelAnimationFrame(raf);ro.disconnect();composer?.dispose?.();renderer.dispose();renderer.domElement.remove();};
 },[seed]);
 return <div ref={host} data-testid="zeref-glb-3d" style={{width:'100%',height:'100%',minHeight:360}} aria-label="Sculpted 3D Zeref, rotating"/>;
}
