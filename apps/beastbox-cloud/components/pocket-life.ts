/**
 * LIVING POCKET: the cage world runs visibly on the one shared CST integrator.
 *  - CST state (Lorenz + coherence + chaos + Hebbian) from lib/physics/cst-integrator.mjs, fixed-step, seeded.
 *  - Flow-field "ink currents" on the ground + sky: the Lorenz state advects the field; the same field
 *    drives grass/flower sway, rain slant, fireflies and dust (one wind for everything).
 *  - Coherence → flowers bloom/spread + constellations settle. Chaos → rain, storm, lightning, turbulence.
 *  - Day/night sky, rain streaks with ground splash rings + puddle ripples, fireflies at night.
 *  - Hebbian thread: a glowing line from the creature to whatever it attends to (strength = hebb).
 *  - Ripples: poke/talk/treat send a visible ring through the field and nudge the CST emotion.
 * Deterministic from the seed (weather/time can be overridden by the play-god toolbar). Mobile tiers via `low`.
 */
import {oneSunAt,ONE_SUN} from '@/lib/universe/one-sun.mjs';
import {createCSTState,stepCSTState,createCSTClock,motionParams,seededRng,clamp} from '../lib/physics/cst-integrator.mjs';
type Three=typeof import('three');
export type Weather='auto'|'sun'|'rain'|'storm';
export type LifeEnv={night:number;rain:number;storm:number;flowers:{x:number;z:number;id?:string}[];treats:{x:number;z:number;id:string}[];fireflies:{x:number;y:number;z:number}[]};

const NOISE='float h21(vec2 p){p=fract(p*vec2(123.34,456.21));p+=dot(p,p+45.32);return fract(p.x*p.y);}'+
 'float vn(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(h21(i),h21(i+vec2(1,0)),f.x),mix(h21(i+vec2(0,1)),h21(i+vec2(1,1)),f.x),f.y);}'+
 'float fbm(vec2 p){float v=0.0,a=.5;for(int i=0;i<4;i++){v+=a*vn(p);p=p*2.03+vec2(1.7,9.2);a*=.5;}return v;}'+
 // flow field: curl of fbm, phase-advected by the Lorenz state (uFlow.xy) and time
 'vec2 flow(vec2 p,float t,vec3 F){vec2 q=p*.45+F.xy*.6+vec2(t*.05,-t*.035);float e=.08;float n1=fbm(q+vec2(0,e)),n2=fbm(q-vec2(0,e)),n3=fbm(q+vec2(e,0)),n4=fbm(q-vec2(e,0));return vec2(n1-n2,-(n3-n4))/(2.0*e);}';
const UNI='uniform float uTime;uniform vec2 uWind;uniform float uChaos;uniform float uCoh;uniform float uRain;uniform float uNight;uniform vec3 uFlow;uniform vec4 uRip[4];uniform vec4 uHush;';
// shared sway: wind (Lorenz) + flow field + turbulence (chaos) + ripple push. h = height factor 0..1
const SWAY='vec2 sway(vec2 wp,float h){vec2 f=flow(wp,uTime,uFlow);float gust=.6+.4*sin(uTime*1.3+wp.x*.7+wp.y*.4);vec2 d=(uWind*gust*.9+f*(.18+uChaos*.5))*h*h;'+
 'd+=vec2(sin(uTime*7.0+wp.x*9.0),cos(uTime*6.3+wp.y*8.0))*uChaos*.05*h;'+
 'for(int i=0;i<4;i++){vec2 o=wp-uRip[i].xy;float r=length(o);float age=uTime-uRip[i].z;float ring=exp(-pow((r-age*2.2)*2.5,2.0))*exp(-age*1.2)*uRip[i].w;d+=normalize(o+1e-4)*ring*.35*h;}return d;}';

export function addPocketLife(THREE:Three,scene:import('three').Scene,opts:{seed:string;low:boolean;reduced:boolean;counts?:Record<string,number>|null;hemi?:import('three').HemisphereLight;lights?:import('three').Light[];soft?:boolean}){
 // soft = software GL (SwiftShader/llvmpipe): every pixel is CPU-shaded, so the full-screen fbm layers (sky dome, ink
 // currents) are skipped and the meadow thinned; weather, flowers, rain, fireflies and the life brain all still run.
 const soft=!!opts.soft;
 const {seed,low,reduced}=opts;const rnd=seededRng('pocket-life:'+seed);
 const cst=createCSTState(seed,{counts:(opts.counts??null) as any});const clock=createCSTClock({seed,hz:60});
 const emo={valence:cst.ch.valence,arousal:cst.ch.arousal,curiosity:cst.ch.curiosity,fear:cst.ch.avoid};
 const baseEmo={...emo};
 const R=4.3;// planting radius (pocket floor is 9×9)
 const rips=[0,1,2,3].map(()=>new THREE.Vector4(0,0,-99,0));let ripI=0;
 const U={uTime:{value:0},uWind:{value:new THREE.Vector2()},uChaos:{value:.2},uCoh:{value:.6},uRain:{value:0},uNight:{value:.6},uFlow:{value:new THREE.Vector3()},uRip:{value:rips},uHush:{value:new THREE.Vector4(0,0,0,0)}};
 const group=new THREE.Group();group.name='pocket-life';scene.add(group);
 const disposables:{dispose():void}[]=[];const keep=<T extends {dispose():void}>(x:T)=>{disposables.push(x);return x;};

 // ---- ground ink currents + splash rings + ripples (the math, visible)
 const inkMat=keep(new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,uniforms:U,
  vertexShader:'varying vec2 vW;void main(){vec4 w=modelMatrix*vec4(position,1.0);vW=w.xz;gl_Position=projectionMatrix*viewMatrix*w;}',
  fragmentShader:UNI+NOISE+'varying vec2 vW;void main(){float r=length(vW);if(r>4.5)discard;'+
   // advect: trace back along the flow twice, then draw thin iso-lines of the advected scalar = ink streamlines
   'vec2 p=vW;for(int i=0;i<2;i++)p-=flow(p,uTime,uFlow)*.25;float s=fbm(p*.9+uFlow.z*.3);float line=1.0-smoothstep(0.0,.06,abs(fract(s*7.0)-.5));'+
   'vec3 ink=mix(vec3(.35,.25,.9),vec3(.2,.85,1.0),s)*line*(.07+.08*uCoh+.12*uChaos);'+
   // rain splash rings: per-cell hashed impacts
   'vec2 c=floor(vW*2.2);vec2 fc=fract(vW*2.2)-.5;float ph=fract(uTime*.9+h21(c));float rr=length(fc-(vec2(h21(c+3.1),h21(c+7.7))-.5)*.5);'+
   'float splash=uRain*(1.0-smoothstep(.0,.04,abs(rr-ph*.45)))*(1.0-ph)*step(.35,h21(c+floor(uTime*.9+h21(c))));'+
   'vec3 col=ink+vec3(.55,.75,1.0)*splash*.55;'+
   // poke/talk ripples
   'for(int i=0;i<4;i++){float age=uTime-uRip[i].z;float d=length(vW-uRip[i].xy);col+=vec3(.75,.55,1.0)*exp(-pow((d-age*2.2)*3.0,2.0))*exp(-age*1.1)*uRip[i].w*.6;}'+
   'gl_FragColor=vec4(col*(1.0-smoothstep(3.8,4.5,r)),1.0);}'}));
 const ink=new THREE.Mesh(keep(new THREE.CircleGeometry(4.5,low?48:96)),inkMat);ink.rotation.x=-Math.PI/2;ink.position.y=-.035;ink.renderOrder=1;ink.visible=!soft;group.add(ink);

 // ---- sky ink + day/night dome
 const skyMat=keep(new THREE.ShaderMaterial({transparent:true,side:THREE.BackSide,depthWrite:false,fog:false,uniforms:U,
  vertexShader:'varying vec3 vD;void main(){vD=normalize(position);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
  fragmentShader:UNI+NOISE+'varying vec3 vD;void main(){float up=clamp(vD.y,0.0,1.0);vec2 p=vD.xz/(vD.y+1.2)*3.0;for(int i=0;i<2;i++)p-=flow(p,uTime*.6,uFlow)*.3;float s=fbm(p*.7);'+
   'float line=1.0-smoothstep(0.0,.05,abs(fract(s*5.0)-.5));'+
   'vec3 day=mix(vec3(.30,.36,.78),vec3(.55,.42,.92),up);vec3 night=mix(vec3(.03,.02,.10),vec3(.06,.03,.16),up);vec3 storm=vec3(.08,.07,.16);'+
   'vec3 base=mix(day,night,uNight);base=mix(base,storm,clamp(uRain*1.2,0.0,.85));'+
   'vec3 c=base+mix(vec3(.35,.25,.9),vec3(.2,.8,1.0),s)*line*(.05+.1*uChaos)*(.4+uNight*.6);'+
   'gl_FragColor=vec4(c,.6*smoothstep(.12,.55,vD.y));}'}));   // fades out toward the horizon so the pocket world (shore, ocean, far sky) shows through
 const dome=new THREE.Mesh(keep(new THREE.SphereGeometry(14,low?24:40,low?12:20)),skyMat);dome.renderOrder=-2;dome.visible=!soft;group.add(dome);

 // ---- grass (GPU instanced, wind-swayed by the shared field)
 const blade=keep(new THREE.BufferGeometry());
 {const seg=low?2:3,pos:number[]=[],idx:number[]=[],hh:number[]=[];for(let i=0;i<=seg;i++){const t=i/seg,w=.035*(1-t*.85);pos.push(-w,t,0,w,t,0);hh.push(t,t);if(i<seg){const a=i*2;idx.push(a,a+1,a+2,a+1,a+3,a+2);}}
  blade.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));blade.setAttribute('aH',new THREE.Float32BufferAttribute(hh,1));blade.setIndex(idx);}
 const grassN=reduced||soft?400:low?1300:3600;
 const grassMat=keep(new THREE.ShaderMaterial({side:THREE.DoubleSide,uniforms:U,
  vertexShader:UNI+NOISE+SWAY+'attribute float aH;attribute vec3 aTint;varying float vH;varying vec3 vT;void main(){vec4 w=modelMatrix*instanceMatrix*vec4(position,1.0);vec2 root=(modelMatrix*instanceMatrix*vec4(0,0,0,1)).xz;vec2 d=sway(root,aH);w.xz+=d;w.y-=dot(d,d)*.5;float hu=uHush.w*(1.-smoothstep(.55,1.05,distance(root,uHush.xz)));w.y=mix(w.y,-.06,hu);vH=aH;vT=aTint;gl_Position=projectionMatrix*viewMatrix*w;}',
  fragmentShader:UNI+'varying float vH;varying vec3 vT;void main(){vec3 c=mix(vT*.35,vT,vH);c=mix(c,c*vec3(.45,.5,.9),uNight*.6);c+=vec3(.2,.5,.6)*pow(vH,4.0)*.25*(1.0-uNight*.5);gl_FragColor=vec4(c,1.0);\n#include <colorspace_fragment>\n}'}));
 const grass=new THREE.InstancedMesh(blade,grassMat,grassN);const tint=new Float32Array(grassN*3);
 const m4=new THREE.Matrix4(),q=new THREE.Quaternion(),e=new THREE.Euler(),v=new THREE.Vector3(),sc=new THREE.Vector3();
 for(let i=0;i<grassN;i++){const a=rnd()*Math.PI*2,d=Math.sqrt(rnd())*R;const x=Math.cos(a)*d,z=Math.sin(a)*d;const hgt=.12+rnd()*.26*(1-d/R*.5);
  e.set(0,rnd()*Math.PI,(rnd()-.5)*.25);q.setFromEuler(e);m4.compose(v.set(x,-.05,z),q,sc.set(1,hgt,1));grass.setMatrixAt(i,m4);
  const k=rnd();tint[i*3]=.18+k*.25;tint[i*3+1]=.55+k*.3;tint[i*3+2]=.55+(1-k)*.35;}// cosmic teal-violet grass
 blade.setAttribute('aTint',new THREE.InstancedBufferAttribute(tint,3));grass.frustumCulled=false;group.add(grass);

 // ---- flowers: bloom where seeded coherence field is high, threshold vs live coherence
 const flowerN=low?60:150;const headGeo=keep(new THREE.IcosahedronGeometry(.055,0));
 const flowerMat=keep(new THREE.ShaderMaterial({uniforms:U,
  vertexShader:UNI+NOISE+SWAY+'attribute vec4 aF;varying vec3 vC;varying float vB;void main(){vec2 root=(instanceMatrix*vec4(0,0,0,1)).xz;float b=smoothstep(aF.w-.06,aF.w+.06,uCoh);vB=b;'+
   'vec3 p=position*(.25+b*.95)*vec3(1.0,.55,1.0);vec4 w=modelMatrix*instanceMatrix*vec4(p,1.0);vec2 d=sway(root,1.0);w.xz+=d;w.y-=dot(d,d)*.5;vC=aF.rgb;gl_Position=projectionMatrix*viewMatrix*w;}',
  fragmentShader:UNI+'varying vec3 vC;varying float vB;void main(){vec3 c=mix(vC*.25,vC*1.15,vB)+vC*uNight*vB*.35;gl_FragColor=vec4(c,1.0);\n#include <colorspace_fragment>\n}'}));
 const flowers=new THREE.InstancedMesh(headGeo,flowerMat,flowerN+24);const fAttr=new Float32Array((flowerN+24)*4);
 const stems=new THREE.InstancedMesh(blade,grassMat,flowerN+24);const stemTint=new Float32Array((flowerN+24)*3);
 const flowerList:{x:number;z:number;id:string;thr:number}[]=[];
 const palette=[[.85,.55,1],[.55,.75,1],[1,.75,.95],[.6,1,.95],[1,.95,.6]];
 const centers=[0,1,2].map(()=>({x:(rnd()-.5)*5.5,z:(rnd()-.5)*5.5,r:1+rnd()*1.2}));
 const addFlower=(x:number,z:number,thr:number,i:number)=>{const h=.22+rnd()*.18;m4.compose(v.set(x,h-.05,z),q.identity(),sc.set(1,1,1));flowers.setMatrixAt(i,m4);
  m4.compose(v.set(x,-.05,z),q.identity(),sc.set(.8,h,.8));stems.setMatrixAt(i,m4);const c=palette[(rnd()*palette.length)|0];fAttr.set([c[0],c[1],c[2],thr],i*4);stemTint.set([.2,.6,.45],i*3);
  flowerList.push({x,z,id:'f'+i,thr});};
 let fi=0;for(let i=0;i<flowerN*4&&fi<flowerN;i++){const a=rnd()*Math.PI*2,d=Math.sqrt(rnd())*R*.95,x=Math.cos(a)*d,z=Math.sin(a)*d;
  let near=0;for(const c of centers)near=Math.max(near,1-Math.hypot(x-c.x,z-c.z)/c.r);if(near<=0&&rnd()>.15)continue;
  // nearer a bloom centre → lower threshold → blooms first; spreading outward as coherence rises
  addFlower(x,z,clamp(.78-near*.35+rnd()*.06,.35,.95),fi++);}
 const flowerBase=fi;flowers.count=fi;stems.count=fi;
 headGeo.setAttribute('aF',new THREE.InstancedBufferAttribute(fAttr,4));
 const stemGeo=keep(blade.clone());stemGeo.setAttribute('aTint',new THREE.InstancedBufferAttribute(stemTint,3));stems.geometry=stemGeo;
 flowers.frustumCulled=stems.frustumCulled=false;group.add(flowers,stems);
 const plantFlower=(x:number,z:number)=>{if(fi>=flowerBase+24)fi=flowerBase;addFlower(x,z,0,fi);fi++;flowers.count=Math.max(flowers.count,fi);stems.count=flowers.count;
  flowers.instanceMatrix.needsUpdate=stems.instanceMatrix.needsUpdate=true;(headGeo.getAttribute('aF') as import('three').InstancedBufferAttribute).needsUpdate=true;(stemGeo.getAttribute('aTint') as import('three').InstancedBufferAttribute).needsUpdate=true;};

 // ---- rain streaks
 const rainN=low?260:700;const rainPos=new Float32Array(rainN*6);const rainGeo=keep(new THREE.BufferGeometry());
 const drops=Array.from({length:rainN},()=>({x:(rnd()-.5)*9,y:rnd()*6,z:(rnd()-.5)*9,s:5+rnd()*3}));
 rainGeo.setAttribute('position',new THREE.BufferAttribute(rainPos,3));
 const rainMat=keep(new THREE.LineBasicMaterial({color:0xaecbff,transparent:true,opacity:0,depthWrite:false}));
 const rain=new THREE.LineSegments(rainGeo,rainMat);rain.frustumCulled=false;group.add(rain);

 // ---- fireflies (night + coherence)
 const ffN=low?18:42;const ffPos=new Float32Array(ffN*3);const ffGeo=keep(new THREE.BufferGeometry());ffGeo.setAttribute('position',new THREE.BufferAttribute(ffPos,3));
 const ff=Array.from({length:ffN},(_,i)=>({x:(rnd()-.5)*7,y:.3+rnd()*1.3,z:(rnd()-.5)*7,p:rnd()*9,i}));
 const ffMat=keep(new THREE.PointsMaterial({color:0xfff2a0,size:low?.09:.075,transparent:true,opacity:0,blending:THREE.AdditiveBlending,depthWrite:false}));
 const fireflies=new THREE.Points(ffGeo,ffMat);fireflies.frustumCulled=false;group.add(fireflies);

 // ---- lived-in pocket (Oct 16): a sunny favourite rock, rain puddles that linger and dry, splash particles
 const srand=seededRng('pocket-spots:'+seed);const ra=srand()*Math.PI*2,rr=1.9+srand()*.8;
 const rock=new THREE.Mesh(keep(new THREE.DodecahedronGeometry(.32,low?0:1)),keep(new THREE.MeshStandardMaterial({color:0x8a7f9a,roughness:.85,flatShading:true})));
 rock.scale.set(1.25,.42,1);rock.position.set(Math.cos(ra)*rr,.06,Math.sin(ra)*rr);rock.rotation.y=srand()*3;rock.name='sunny-rock';group.add(rock);
 const spots=[{x:rock.position.x,z:rock.position.z,kind:'sunrock'}];
 const pudGeo=keep(new THREE.CircleGeometry(1,low?20:40));
 const puddles=Array.from({length:3},(_,i)=>{const a=srand()*Math.PI*2,d=.8+srand()*2;const m=keep(new THREE.MeshStandardMaterial({color:0x1a2a55,roughness:.05,metalness:.6,transparent:true,opacity:0,depthWrite:false}));
  const mesh=new THREE.Mesh(pudGeo,m);mesh.rotation.x=-Math.PI/2;const r=.32+srand()*.25;mesh.position.set(Math.cos(a)*d,-.028,Math.sin(a)*d);mesh.scale.set(r*1.3,r,1);mesh.renderOrder=2;group.add(mesh);
  return {x:mesh.position.x,z:mesh.position.z,r,wet:0,mesh,m,i};});
 const spN=low?40:90;const spPos=new Float32Array(spN*3).fill(-9);const spVel=new Float32Array(spN*3);const spLife=new Float32Array(spN);let spI=0;
 const spGeo=keep(new THREE.BufferGeometry());spGeo.setAttribute('position',new THREE.BufferAttribute(spPos,3));
 const spMat=keep(new THREE.PointsMaterial({color:0xbfe8ff,size:low?.07:.05,transparent:true,opacity:.85,depthWrite:false}));const splashPts=new THREE.Points(spGeo,spMat);splashPts.frustumCulled=false;group.add(splashPts);
 let splashAcc=0,spDirty=false;
 function splash(x:number,z:number,k=1){for(let n=0;n<Math.ceil(6*k);n++){const i=spI++%spN;const a=rnd()*Math.PI*2,v=.6+rnd()*.9;spPos[i*3]=x;spPos[i*3+1]=0;spPos[i*3+2]=z;spVel[i*3]=Math.cos(a)*v*.6;spVel[i*3+1]=1.4+rnd()*1.2;spVel[i*3+2]=Math.sin(a)*v*.6;spLife[i]=.8;}spDirty=true;ripple(x,z,.35*k);}

 // ---- constellations: seeded stars that settle into linked figures as coherence rises
 const starN=low?28:48;const stars=Array.from({length:starN},()=>{const a=rnd()*Math.PI*2,u=.25+rnd()*.6;return new THREE.Vector3(Math.cos(a)*Math.cos(u)*11,Math.sin(u)*11,Math.sin(a)*Math.cos(u)*11);});
 const starHome=stars.map(s=>s.clone()),starJit=stars.map(()=>new THREE.Vector3((rnd()-.5)*2.4,(rnd()-.5)*2.4,(rnd()-.5)*2.4));
 const starPts=new Float32Array(starN*3);const starGeo=keep(new THREE.BufferGeometry());starGeo.setAttribute('position',new THREE.BufferAttribute(starPts,3));
 const starMat=keep(new THREE.PointsMaterial({color:0xe9e2ff,size:.22,transparent:true,opacity:.9,fog:false,depthWrite:false,blending:THREE.AdditiveBlending}));group.add(new THREE.Points(starGeo,starMat));
 const links:number[]=[];for(let i=0;i<starN;i++){let b=-1,bd=1e9;for(let j=0;j<starN;j++){if(j===i)continue;const d=starHome[i].distanceTo(starHome[j]);if(d<bd&&!links.some((_,k)=>k%2===0&&links[k]===j&&links[k+1]===i)){bd=d;b=j;}}if(bd<4.2)links.push(i,b);}
 const linkPos=new Float32Array(links.length*3);const linkGeo=keep(new THREE.BufferGeometry());linkGeo.setAttribute('position',new THREE.BufferAttribute(linkPos,3));
 const linkMat=keep(new THREE.LineBasicMaterial({color:0xbfa8ff,transparent:true,opacity:0,fog:false,depthWrite:false,blending:THREE.AdditiveBlending}));group.add(new THREE.LineSegments(linkGeo,linkMat));

 // ---- Hebbian thread: creature → attention
 const thrN=24;const thrPos=new Float32Array(thrN*3);const thrGeo=keep(new THREE.BufferGeometry());thrGeo.setAttribute('position',new THREE.BufferAttribute(thrPos,3));
 const thrMat=keep(new THREE.LineBasicMaterial({color:0x9ff3ff,transparent:true,opacity:0,depthWrite:false,blending:THREE.AdditiveBlending}));
 const thread=new THREE.Line(thrGeo,thrMat);thread.frustumCulled=false;group.add(thread);

 // ---- treats
 const treatGeo=keep(new THREE.IcosahedronGeometry(.07,1));const treatMat=keep(new THREE.MeshBasicMaterial({color:0xffd27a}));
 const treats:{x:number;z:number;id:string;mesh:import('three').Mesh;t:number}[]=[];let treatSeq=0;

 // ---- sun / lightning
 const sun=new THREE.DirectionalLight(0xfff0d8,0);sun.position.set(3,6,2);group.add(sun);
 const flash=new THREE.AmbientLight(0xcfd8ff,0);group.add(flash);

 // ---- controls state
 let weather:Weather='auto',tod:number|null=null;const phase0=rnd();
 let rainAmt=0,stormAmt=0,night=.6,lightningT=0;const lrnd=seededRng('lightning:'+seed);
 const ripple=(x:number,z:number,amp=1)=>{const r=rips[ripI++%4];r.set(x,z,U.uTime.value,amp);};
 const nudge=(d:Partial<typeof emo>)=>{for(const k in d)(emo as any)[k]=clamp((emo as any)[k]+(d as any)[k]);};
 const env:LifeEnv={night,rain:0,storm:0,flowers:[],treats:[],fireflies:[]};
 let t=0;
 function update(dt:number,creature:{x:number;y:number;z:number}|null,attn:{x:number;y:number;z:number}|null){
  if(reduced)dt=Math.min(dt,.016)*.25;t+=dt;U.uTime.value=t;
  // emotions relax back toward the seed baseline; CST integrates them (fixed step)
  for(const k in emo)(emo as any)[k]+=((baseEmo as any)[k]-(emo as any)[k])*Math.min(1,dt*.08);
  clock.tick(dt,(h:number)=>stepCSTState(cst,h,emo as any));
  const mp=motionParams(cst),c=cst.ch;
  U.uChaos.value+=(c.chaos-U.uChaos.value)*Math.min(1,dt*2);U.uCoh.value+=(c.coherence-U.uCoh.value)*Math.min(1,dt*.5);
  U.uWind.value.set(mp.wind.x*.5,mp.wind.z*.5);U.uFlow.value.set(cst.L.x/20,cst.L.y/25,cst.L.z/40);
  // weather: CST chaos decides unless the god toolbar overrides
  const wantRain=weather==='sun'?0:weather==='rain'?.75:weather==='storm'?1:clamp((c.chaos-.42)*2.6);
  const wantStorm=weather==='storm'?1:weather==='auto'?clamp((c.chaos-.62)*3):0;
  rainAmt+=(wantRain-rainAmt)*Math.min(1,dt*.6);stormAmt+=(wantStorm-stormAmt)*Math.min(1,dt*.6);U.uRain.value=rainAmt;
  // time of day: seeded slow cycle (12 min) unless pinned
  const cyc=tod??((phase0+t/720)%1);const want=.5-.5*Math.cos((cyc-.0)*Math.PI*2);// 0 = noon-ish, 1 = midnight
  night+=(want-night)*Math.min(1,dt*(tod===null?1:1.5));U.uNight.value=night;
  {const os=oneSunAt(Date.now()/1000);sun.position.set(os.dir[0]*7,os.dir[1]*7,os.dir[2]*7);sun.color.set(ONE_SUN.hex);}sun.intensity=(1-night)*(1-rainAmt*.7)*1.6;if(opts.hemi)opts.hemi.intensity=1.1+(1-night)*1.4-rainAmt*.4;
  const bg=scene.background as import('three').Color|null;if(bg&&(bg as any).isColor)bg.setRGB(.02+(1-night)*.16,.016+(1-night)*.16,.06+(1-night)*.34);
  const fog=scene.fog as import('three').FogExp2|null;if(fog)fog.color.setRGB(.05+(1-night)*.2,.04+(1-night)*.2,.15+(1-night)*.35);
  // lightning (deterministic stream)
  lightningT-=dt;if(stormAmt>.4&&lightningT<=0){lightningT=1.5+lrnd()*5;flash.intensity=3.5;ripple((lrnd()-.5)*6,(lrnd()-.5)*6,.6);}flash.intensity*=Math.exp(-dt*9);
  // rain (slanted by the same wind)
  rainMat.opacity=rainAmt*.55;if(rainAmt>.02){const wx=mp.wind.x*.9,wz=mp.wind.z*.9;for(let i=0;i<rainN;i++){const d=drops[i];d.y-=d.s*dt;d.x+=wx*dt;d.z+=wz*dt;
   if(d.y<0||(i/rainN)>rainAmt+.05){d.y=5.5+rnd()*1.5;d.x=(rnd()-.5)*9;d.z=(rnd()-.5)*9;}const o=i*6;rainPos[o]=d.x;rainPos[o+1]=d.y;rainPos[o+2]=d.z;rainPos[o+3]=d.x-wx*.05;rainPos[o+4]=d.y+.22;rainPos[o+5]=d.z-wz*.05;}
   rainGeo.attributes.position.needsUpdate=true;}
  // fireflies follow the flow + a Lorenz-perturbed wander
  ffMat.opacity=clamp(night*1.4-.3)*(1-rainAmt)*(.5+c.coherence*.5);
  env.fireflies.length=0;for(const f of ff){const k=f.p+t*.6;f.x+=(Math.sin(k*1.3+f.i)*.25+mp.wind.x*.3)*dt;f.z+=(Math.cos(k*1.1+f.i*2)*.25+mp.wind.z*.3)*dt;f.y=.35+.6*(.5+.5*Math.sin(k*.9))+.15*Math.sin(t*3+f.i);
   const r=Math.hypot(f.x,f.z);if(r>3.9){f.x*=3.9/r;f.z*=3.9/r;}ffPos[f.i*3]=f.x;ffPos[f.i*3+1]=f.y;ffPos[f.i*3+2]=f.z;if(ffMat.opacity>.2)env.fireflies.push(f);}
  ffGeo.attributes.position.needsUpdate=true;ffMat.size=(low?.09:.075)*(.8+.4*Math.sin(t*4));
  // constellations: stars drift (chaos) and settle into figures (coherence)
  const settle=clamp((c.coherence-.45)*2.2);for(let i=0;i<starN;i++){const s=stars[i];s.copy(starHome[i]).addScaledVector(starJit[i],(1-settle)*(.5+.5*Math.sin(t*.3+i)));starPts.set([s.x,s.y,s.z],i*3);}
  for(let k=0;k<links.length;k++){const s=stars[links[k]];linkPos.set([s.x,s.y,s.z],k*3);}starGeo.attributes.position.needsUpdate=linkGeo.attributes.position.needsUpdate=true;
  linkMat.opacity=settle*.45*(.4+night*.6)*(1-rainAmt*.7);starMat.opacity=(.35+night*.6)*(1-rainAmt*.6);
  // Hebbian thread
  if(creature&&attn){const a=new THREE.Vector3(creature.x,creature.y,creature.z),b=new THREE.Vector3(attn.x,attn.y,attn.z);const mid=a.clone().lerp(b,.5);mid.y+=.4+a.distanceTo(b)*.15;
   for(let i=0;i<thrN;i++){const u=i/(thrN-1),p=a.clone().multiplyScalar((1-u)*(1-u)).addScaledVector(mid,2*u*(1-u)).addScaledVector(b,u*u);p.y+=Math.sin(u*9-t*4)*.02;thrPos.set([p.x,p.y,p.z],i*3);}
   thrGeo.attributes.position.needsUpdate=true;thrMat.opacity+=((.15+cst.hebb*.6)-thrMat.opacity)*Math.min(1,dt*3);}else thrMat.opacity*=Math.exp(-dt*3);
  // treats bob + expire
  for(const tr of treats){tr.t+=dt;tr.mesh.position.y=.06+.04*Math.abs(Math.sin(tr.t*3));}
  // puddles fill while it rains and dry slowly afterwards; splash droplets are ballistic
  for(const p of puddles){p.wet=clamp(p.wet+rainAmt*dt*.12-(1-rainAmt)*dt*.008);p.m.opacity=p.wet*.75;p.mesh.visible=p.wet>.02;}
  let live=false;for(let i=0;i<spN;i++){if(spLife[i]<=0)continue;live=true;spLife[i]-=dt;spVel[i*3+1]-=9.8*dt;spPos[i*3]+=spVel[i*3]*dt;spPos[i*3+1]+=spVel[i*3+1]*dt;spPos[i*3+2]+=spVel[i*3+2]*dt;if(spPos[i*3+1]<0||spLife[i]<=0){spLife[i]=0;spPos[i*3+1]=-9;}}
  if(live||spDirty)spGeo.attributes.position.needsUpdate=true;spDirty=live;
  (env as any).spots=spots;(env as any).puddles=puddles;
  env.night=night;env.rain=rainAmt;env.storm=stormAmt;env.treats=treats;env.flowers=flowerList.filter(f=>f.thr<U.uCoh.value);
  return {cst,mp,mood:mp.mood,env};
 }
 return {update,env,cst,splash,
  /** flatten grass within ~1 unit of a flaring creature (a=0..1) so its nervous system reads */
  hush(x:number,z:number,a:number){U.uHush.value.set(x,0,z,a);},
  /** called while a creature runs through a puddle */
  splashStep(x:number,z:number,speed:number,dt:number){splashAcc+=dt*speed*14;while(splashAcc>1){splashAcc-=1;splash(x+(rnd()-.5)*.2,z+(rnd()-.5)*.2,.6);}},
  setWeather:(w:Weather)=>{weather=w;},getWeather:()=>weather,
  setTime:(x:number|null)=>{tod=x;},getTime:()=>tod,
  ripple,
  poke(x:number,z:number){ripple(x,z,1);nudge({arousal:.25,curiosity:.2,valence:.05});},
  talk(intensity=.4){ripple(0,0,.8);nudge({valence:.15*intensity+.05,arousal:.12*intensity,curiosity:.1});},
  dropTreat(x:number,z:number){const mesh=new THREE.Mesh(treatGeo,treatMat);mesh.position.set(x,.08,z);group.add(mesh);treats.push({x,z,id:'t'+(treatSeq++),mesh,t:0});ripple(x,z,.7);nudge({valence:.1,curiosity:.15});},
  eat(id:string){const i=treats.findIndex(t=>t.id===id);if(i>=0){group.remove(treats[i].mesh);ripple(treats[i].x,treats[i].z,.5);treats.splice(i,1);nudge({valence:.2});}},
  plantFlower(x:number,z:number){plantFlower(x,z);ripple(x,z,.6);nudge({valence:.08});},
  dispose(){scene.remove(group);disposables.forEach(d=>d.dispose());}};
}
