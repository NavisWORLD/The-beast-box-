// three.js side of the living-world mechanics: seeded rain + drifting volumetric-ish clouds (stacked soft puffs),
// kelp + bubbles in the sea, a warm torch circle, distant mountain silhouettes. Seeds via lwStream; no unseeded RNG.
import {lwStream} from './living-world.mjs';
import {seededCloudPuffs,mountainProfile} from './world-mechanics.mjs';
import {sheet} from './landforms-three';
export const AM='/universe/livingworld/asciimode/';
export const UW_STOPS:[number,string][]=[[0,'#46c8d7'],[.25,'#1e8caa'],[.55,'#0e466e'],[.8,'#0a1e46'],[1,'#060a1e']];
export function underwaterColor(THREE:T,t:number){t=Math.max(0,Math.min(1,t));for(let i=1;i<UW_STOPS.length;i++){const [a,ca]=UW_STOPS[i-1],[b,cb]=UW_STOPS[i];if(t<=b)return new THREE.Color(ca).lerp(new THREE.Color(cb),(t-a)/(b-a));}return new THREE.Color(UW_STOPS[4][1]);}
type T=typeof import('three');type V3=import('three').Vector3;
const puffTex=(THREE:T)=>{const c=document.createElement('canvas');c.width=c.height=64;const g=c.getContext('2d')!;const gr=g.createRadialGradient(32,32,2,32,32,31);gr.addColorStop(0,'rgba(255,255,255,1)');gr.addColorStop(.5,'rgba(255,255,255,.55)');gr.addColorStop(1,'rgba(255,255,255,0)');g.fillStyle=gr;g.fillRect(0,0,64,64);const t=new THREE.CanvasTexture(c);return t;};
export function addMechanics(THREE:T,scene:import('three').Scene,o:{seed:string;R:number;mpu:number;phone:boolean;unitFrom:(r:()=>number)=>number[];isWater:(n:V3)=>boolean}){
 const root=new THREE.Group();root.name='lw-mechanics';scene.add(root);const R=o.R;const pt=puffTex(THREE);
 // clouds: each cloud = several overlapping soft sprites at slightly different heights (reads volumetric), drifting with the Lorenz wind
 const clouds=new THREE.Group();root.add(clouds);const cloudMat=new THREE.SpriteMaterial({map:pt,color:0xffffff,transparent:true,opacity:.7,depthWrite:false,fog:false});
 const cr=lwStream(o.seed+':cloudpuff');for(const c of seededCloudPuffs(o.seed,o.phone?14:26,o.unitFrom)){const g=new THREE.Group();const n=new THREE.Vector3(...c.d).normalize();
  for(let i=0;i<c.puffs;i++){const s=new THREE.Sprite(cloudMat);const sz=c.size*(1+cr()*.8);s.scale.set(sz*1.6,sz,1);s.position.set((cr()-.5)*c.size*1.6,(cr()-.3)*c.size*.5,(cr()-.5)*c.size*1.2);g.add(s);}
  g.position.copy(n).multiplyScalar(R+1.6+c.alt);g.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),n);clouds.add(g);}
 // rain (Cosmo): instanced streak quads (8 seeded variants via UV offset), Y-locked billboards tilted by atan(wind/fall); splash sheet 8f @24fps once
 const RN=o.phone?300:800;const rs=lwStream(o.seed+':rain');const seeds=Array.from({length:RN},()=>[rs()*2-1,rs()*2-1,rs(),Math.floor(rs()*8),.6+rs()*.6]);
 const stTex=new THREE.TextureLoader().load(AM+'rain_streaks_8x_32x128.png');stTex.colorSpace=THREE.SRGBColorSpace;
 const rgeo=new THREE.PlaneGeometry(1,1);const vAttr=new THREE.InstancedBufferAttribute(new Float32Array(RN),1);rgeo.setAttribute('aVar',vAttr);seeds.forEach((sd,i)=>vAttr.setX(i,sd[3]));
 const rmat=new THREE.MeshBasicMaterial({map:stTex,transparent:true,opacity:.5,depthWrite:false,blending:THREE.AdditiveBlending,color:0xbfd8ff,side:THREE.DoubleSide});
 rmat.onBeforeCompile=(sh:any)=>{sh.vertexShader=sh.vertexShader.replace('#include <common>','#include <common>\nattribute float aVar;varying float vVar;').replace('#include <uv_vertex>','#include <uv_vertex>\nvVar=aVar;');
  sh.fragmentShader=sh.fragmentShader.replace('#include <common>','#include <common>\nvarying float vVar;').replace('#include <map_fragment>','vec4 sampledDiffuseColor=texture2D(map,vec2((vVar+vMapUv.x)/8.0,vMapUv.y));diffuseColor*=sampledDiffuseColor;');};
 const rain=new THREE.InstancedMesh(rgeo,rmat,RN);rain.frustumCulled=false;rain.count=0;root.add(rain);
 const splashes=Array.from({length:o.phone?8:16},()=>{const sp=sheet(THREE,AM+'rain_splash_8f_64.png',{fps:24,loop:false,cols:8,rows:1});sp.sp.scale.setScalar(.4*o.mpu/ .294*.294);root.add(sp.sp);return sp;});let splashI=0,splashAcc=0;
 // sea life: kelp ribbons + bubbles placed on seeded ocean points
 const kr=lwStream(o.seed+':kelp');const kelpPts:V3[]=[];for(let i=0;i<4000&&kelpPts.length<(o.phone?60:140);i++){const v=new THREE.Vector3(...o.unitFrom(kr)).normalize();if(o.isWater(v))kelpPts.push(v);}
 const kelpGeo=new THREE.PlaneGeometry(.05,.5,1,6);kelpGeo.translate(0,.25,0);const kelpMat=new THREE.MeshStandardMaterial({color:0x2f8f5a,emissive:0x0b3a22,side:THREE.DoubleSide,roughness:.8});const KU={uT:{value:0}};
 // Cosmo's kelp sway: x += sin(t*1.3 + wx*.7 + seed)*.25*h*h, plus a slower .4 Hz secondary at .1
 kelpMat.onBeforeCompile=(sh:any)=>{sh.uniforms.uT=KU.uT;sh.vertexShader=sh.vertexShader.replace('#include <common>','#include <common>\nuniform float uT;').replace('#include <begin_vertex>','#include <begin_vertex>\nfloat kh=clamp(position.y/.5,0.,1.);vec4 kw=instanceMatrix*vec4(0.,0.,0.,1.);float ks=kw.x*13.1+kw.z*7.7;transformed.x+=(sin(uT*1.3+kw.x*.7+ks)*.25+sin(uT*2.513+ks)*.1)*kh*kh*.4;');};
 const kelp=new THREE.InstancedMesh(kelpGeo,kelpMat,Math.max(1,kelpPts.length));kelp.count=kelpPts.length;const m4=new THREE.Matrix4(),q=new THREE.Quaternion(),up=new THREE.Vector3(0,1,0),sc=new THREE.Vector3();
 kelpPts.forEach((n,i)=>{q.setFromUnitVectors(up,n);const h=.6+kr()*1.2;sc.set(1,h,1);m4.compose(n.clone().multiplyScalar(R-.35),q,sc);kelp.setMatrixAt(i,m4);});root.add(kelp);
 // bubbles (Cosmo): 8-frame sheet looping @12fps, rising .4-.8 m/s with a small sin wobble, above seeded kelp
 const bub=Array.from({length:o.phone?14:30},(_,i)=>{const b=sheet(THREE,AM+'bubbles_8f_64x128.png',{fps:12,loop:true,cols:8,rows:1});b.sp.scale.set(.12,.24,1);root.add(b.sp);return {b,k:Math.floor(kr()*Math.max(1,kelpPts.length)),ph:kr(),sp:.4+kr()*.4,w:kr()*6.283};});
 // torch (Cosmo): warm cookie decal on the ground + glow sprite + PointLight (~8 m, decay 2), flicker .92-1.0 at ~8 Hz from a seeded table;
 // Nyxlet-violet glow sprite on the beast, steady .5 Hz pulse
 const L=new THREE.TextureLoader();const ld=(f:string)=>{const t=L.load(AM+f);t.colorSpace=THREE.SRGBColorSpace;return t;};
 const torch=new THREE.PointLight(0xffd199,0,8*o.mpu,2);root.add(torch);
 const circ=new THREE.Mesh(new THREE.CircleGeometry(1,40),new THREE.MeshBasicMaterial({map:ld('torch_cookie_512.png'),transparent:true,opacity:0,depthWrite:false,blending:THREE.AdditiveBlending,toneMapped:false}));root.add(circ);
 const tGlow=new THREE.Sprite(new THREE.SpriteMaterial({map:ld('glow_sprite_torch_256.png'),transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,toneMapped:false}));tGlow.scale.setScalar(.6);root.add(tGlow);
 const nGlow=new THREE.Sprite(new THREE.SpriteMaterial({map:ld('glow_sprite_nyxlet_256.png'),transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,toneMapped:false}));nGlow.scale.setScalar(.9);root.add(nGlow);
 const nLight=new THREE.PointLight(0xb86bff,0,6*o.mpu,2);root.add(nLight);
 const fr=lwStream(o.seed+':torch-flicker');const flick=Array.from({length:64},()=>.92+fr()*.08);
 // distant mountain silhouettes: a seeded profile on a far ring band around the focus (long draw distance feel)
 const prof=mountainProfile(o.seed);const mc=document.createElement('canvas');mc.width=1024;mc.height=128;{const g=mc.getContext('2d')!;g.fillStyle='rgba(0,0,0,0)';g.clearRect(0,0,1024,128);
  for(const [layer,col,amp] of [[0,'rgba(40,30,80,.9)',1],[1,'rgba(20,16,44,.95)',.7]] as const){g.fillStyle=col;g.beginPath();g.moveTo(0,128);for(let i=0;i<=1024;i++){const h=prof[(Math.floor(i/4)+layer*37)%prof.length]*amp;g.lineTo(i,128-h*110);}g.lineTo(1024,128);g.fill();}}
 const mt=new THREE.CanvasTexture(mc);mt.wrapS=THREE.RepeatWrapping;mt.colorSpace=THREE.SRGBColorSpace;
 const mountains=new THREE.Mesh(new THREE.CylinderGeometry(60,60,14,64,1,true),new THREE.MeshBasicMaterial({map:mt,transparent:true,side:THREE.BackSide,depthWrite:false,fog:false,color:0xffffff}));mountains.renderOrder=-8;root.add(mountains);
 const tmp=new THREE.Vector3();let rainAmt=0;const kelpMatRef=kelpMat;void kelpMatRef;
 return {root,kelpCount:kelpPts.length,
  update(t:number,dt:number,s:{focus:V3;up:V3;camPos:V3;rain:number;cloud:number;wind:[number,number];torch:V3|null;beast?:V3|null;night:number;dusk:number;ground3:boolean}){
   clouds.rotateOnAxis(new THREE.Vector3(s.wind[1]*.3,1,s.wind[0]*.3).normalize(),dt*.01*(1+Math.abs(s.wind[0])));cloudMat.opacity=.25+.55*s.cloud;cloudMat.color.setRGB(1-.45*s.rain,1-.4*s.rain-.25*s.dusk,1-.35*s.rain-.45*s.dusk).multiplyScalar(1-.6*s.night);
   rainAmt+=(s.rain-rainAmt)*Math.min(1,dt);const vis=s.ground3?Math.floor(RN*rainAmt):0;rain.count=vis;
   if(vis){const f=s.focus,u2=s.up;const a=new THREE.Vector3(1,0,0).cross(u2);if(a.lengthSq()<1e-4)a.set(0,0,1).cross(u2);a.normalize();const b=new THREE.Vector3().crossVectors(u2,a);
    const fall=10*o.mpu,tilt=Math.atan2(s.wind[0]*4*o.mpu,fall);const toCam=new THREE.Vector3();const qq=new THREE.Quaternion(),qt=new THREE.Quaternion(),M=new THREE.Matrix4(),S=new THREE.Vector3();
    for(let i=0;i<vis;i++){const [x,z,ph,,len]=seeds[i];const k=((ph-t*fall/(4))%1+1)%1;tmp.copy(f).addScaledVector(a,x*3+(1-k)*Math.tan(tilt)*1.2).addScaledVector(b,z*3).addScaledVector(u2,k*4);
     toCam.copy(s.camPos).sub(tmp);toCam.addScaledVector(u2,-toCam.dot(u2)).normalize();const m=new THREE.Matrix4().makeBasis(new THREE.Vector3().crossVectors(u2,toCam),u2,toCam);qq.setFromRotationMatrix(m);qt.setFromAxisAngle(toCam,tilt);qq.premultiply(qt);
     S.set(.03,len*.33*o.mpu/.294*(1+Math.abs(s.wind[0])*.3),1);M.compose(tmp,qq,S);rain.setMatrixAt(i,M);}rain.instanceMatrix.needsUpdate=true;
    splashAcc+=dt*rainAmt*30;while(splashAcc>1){splashAcc-=1;const sp=splashes[splashI++%splashes.length];const [x,z]=seeds[(splashI*7)%RN];tmp.copy(f).addScaledVector(a,x*2.5).addScaledVector(b,z*2.5);sp.sp.position.copy(tmp);sp.play();}}
   for(const sp of splashes)sp.update(dt);KU.uT.value=t;kelpMat.emissiveIntensity=.6+.4*Math.sin(t*1.3);
   for(const q2 of bub){if(!kelpPts.length)break;const n=kelpPts[q2.k];const life=((q2.ph+t*q2.sp*.25)%1);tmp.copy(n).multiplyScalar(R-.3+life*.35);q2.b.sp.position.copy(tmp).add(new THREE.Vector3(Math.sin(q2.w+t*3)*.015,0,Math.cos(q2.w+t*3)*.015));q2.b.update(dt);}
   if(s.torch){const fl=flick[Math.floor(t*8)%64];torch.position.copy(s.torch);torch.intensity=(.8+3.4*s.night)*fl;tGlow.position.copy(s.torch);(tGlow.material as any).opacity=(.35+.65*s.night)*fl;tGlow.visible=true;
    const g=s.torch.clone().normalize();circ.position.copy(g).multiplyScalar(R+.03);circ.quaternion.setFromUnitVectors(new THREE.Vector3(0,0,1),g);(circ.material as any).opacity=(.2+.6*s.night)*fl;circ.scale.setScalar(1.4);}
   else{torch.intensity=0;(circ.material as any).opacity=0;tGlow.visible=false;}
   if(s.beast){const pu=.75+.25*Math.sin(t*Math.PI);nGlow.position.copy(s.beast);(nGlow.material as any).opacity=(.25+.5*s.night)*pu;nLight.position.copy(s.beast);nLight.intensity=(.4+2.2*s.night)*pu;}
   mountains.position.copy(s.camPos);mountains.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),s.up);mountains.visible=s.ground3;(mountains.material as any).color.setScalar(.5+.5*(1-s.night));}};
}

/** Cosmo's ASCII view mode: render the scene (pre-tonemap, linear HDR) to a target, then a glyph pass to screen.
 *  Toggle only: the neon world renders normally when off. */
export function createAsciiPass(THREE:T,renderer:import('three').WebGLRenderer,{phone}:{phone:boolean}){
 const hi=!phone&&renderer.getPixelRatio()>1.5;const atlas=new THREE.TextureLoader().load(AM+(hi?'glyph_atlas_16x24.png':'glyph_atlas_8x12.png'));atlas.magFilter=atlas.minFilter=THREE.NearestFilter;atlas.generateMipmaps=false;
 const rt=new THREE.WebGLRenderTarget(2,2,{type:THREE.HalfFloatType});
 const mat=new THREE.ShaderMaterial({uniforms:{tDiffuse:{value:rt.texture},tAtlas:{value:atlas},resolution:{value:new THREE.Vector2(2,2)},cell:{value:new THREE.Vector2(hi?16:8,hi?24:12)},glyphCount:{value:25},emissiveKeep:{value:.6}},depthTest:false,depthWrite:false,
  vertexShader:'varying vec2 vUv;void main(){vUv=uv;gl_Position=vec4(position.xy,0.,1.);}',
  fragmentShader:`uniform sampler2D tDiffuse,tAtlas;uniform vec2 resolution,cell;uniform float glyphCount,emissiveKeep;varying vec2 vUv;
  void main(){vec2 px=vUv*resolution;vec2 cellId=floor(px/cell);vec2 cs=cell/resolution;vec2 c0=(cellId+.5)*cs;
   vec3 col=(texture2D(tDiffuse,c0+cs*vec2(-.25,-.25)).rgb+texture2D(tDiffuse,c0+cs*vec2(.25,-.25)).rgb+texture2D(tDiffuse,c0+cs*vec2(-.25,.25)).rgb+texture2D(tDiffuse,c0+cs*vec2(.25,.25)).rgb)*.25;
   float lum=dot(col,vec3(.2126,.7152,.0722));lum=pow(clamp(lum,0.,1.),.8);float gi=floor(lum*(glyphCount-.001));vec2 ic=fract(px/cell);ic.y=1.-ic.y;
   float mask=texture2D(tAtlas,vec2((gi+ic.x)/glyphCount,ic.y)).a;vec3 tint=col/max(max(col.r,max(col.g,col.b)),1e-3);vec3 o=tint*mask*max(lum,.25)*1.6;
   float hot=smoothstep(.85,1.2,max(col.r,max(col.g,col.b)));o=mix(o,col,hot*emissiveKeep*mask)+col*hot*.15;gl_FragColor=vec4(o+col*.04,1.);
   #include <tonemapping_fragment>
   #include <colorspace_fragment>
  }`});mat.toneMapped=true;
 const quad=new THREE.Mesh(new THREE.PlaneGeometry(2,2),mat);quad.frustumCulled=false;const qs=new THREE.Scene();qs.add(quad);const qc=new THREE.OrthographicCamera(-1,1,1,-1,0,1);
 return {render(scene:any,camera:any){const s=renderer.getDrawingBufferSize(new THREE.Vector2());if(rt.width!==s.x||rt.height!==s.y){rt.setSize(s.x,s.y);mat.uniforms.resolution.value.copy(s);}
   renderer.setRenderTarget(rt);renderer.render(scene,camera);renderer.setRenderTarget(null);renderer.render(qs,qc);},dispose(){rt.dispose();mat.dispose();atlas.dispose();}};
}
