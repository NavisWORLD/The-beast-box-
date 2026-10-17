/**
 * Life on top of the existing pocket (Oct 16): Cory's cage look (grid, deep purples, starfield) is untouched;
 * this only adds favorite spots, three mini libraries, ambient wisps + fireflies, persistent CST particle
 * creations, and the living-core synapse layer (12-channel sensor/wire net + soft-body ripples + quiet clicks).
 */
import {addRiverFlow} from './river-flow';
import {SPOTS,constructPoints,addCreation,loadCreations,saveCreations,reactToWords} from './roam-brain.mjs';
import {buildSynapseNet,channelValues,fireStep,EMO_VIBE} from './synapse-net.mjs';
import {createCSTState,stepCSTState} from '../physics/cst-integrator.mjs';
import {getBeastAudio} from '../companion/beast-audio-engine.mjs';
type T=typeof import('three');
// Cage palette only (crystal violet, flora cyan, bounds lavender).
const PAL=[0xc6a2ff,0x6fe7ff,0x8f7ad8,0xba82f4,0xa8eaff];

// ---------------------------------------------------------------- quiet mechanical clicks
let lastClick=0;
/** Soft 'click / clack' tick through the site SFX bus: only when sound is unlocked and not muted; very low gain, rate-limited. */
export function synapseClick(ch:number,strength=.5){
 try{const a:any=getBeastAudio();const s=a.getSnapshot?.();if(!s||s.sparkMuted||!s.unlocked||s.hidden)return false;
  const now=performance.now();if(now-lastClick<110)return false;lastClick=now;
  const o=a.output?.();if(!o)return false;const {ctx,dest}=o;const t=ctx.currentTime+.005;
  const len=Math.floor(ctx.sampleRate*.018),buf=ctx.createBuffer(1,len,ctx.sampleRate),d=buf.getChannelData(0);for(let i=0;i<len;i++)d[i]=(Math.random()*2-1)*Math.pow(1-i/len,6);
  const src=ctx.createBufferSource();src.buffer=buf;const bp=ctx.createBiquadFilter();bp.type='bandpass';bp.frequency.value=1800+ch*260+(ch%3===2?-900:0);bp.Q.value=ch%3===2?3:9;
  const g=ctx.createGain();g.gain.setValueAtTime(.012+.02*Math.min(1,strength),t);g.gain.exponentialRampToValueAtTime(.0001,t+.05);
  src.connect(bp);bp.connect(g);g.connect(dest);src.start(t);src.stop(t+.06);return true;}catch{return false;}
}

// ---------------------------------------------------------------- synapse + vibration layer
export function attachSynapse(THREE:T,LC:any,seed:string,low:boolean){
 // LC.body is a Group holding the marching-cubes mesh(es); take the biggest mesh and its real vertex count.
 let src:any=null;(LC.body?.isMesh?[LC.body]:LC.body?.children||[]).forEach((o:any)=>{if(o.isMesh&&o.geometry?.attributes?.position&&(!src||o.geometry.attributes.position.count>src.geometry.attributes.position.count))src=o;});
 const body=src?src.parent:LC.body;const geo=src?.geometry;const P=geo?.attributes?.position?.array as Float32Array|undefined;
 const Nn=geo?.attributes?.normal?.array as Float32Array|undefined;
 let count=0;if(P){const dr=geo.drawRange?.count;if(Number.isFinite(dr)&&dr>0)count=Math.min(dr,P.length/3);else if(geo.index)count=P.length/3;else{let n=P.length/3;while(n>0&&P[n*3-1]===0&&P[n*3-2]===0&&P[n*3-3]===0)n--;count=n;}}
 const fire=new Float32Array(12);const U={uTime:{value:0},uFire:{value:fire},uRipA:{value:0},uRipHz:{value:1.2},uTap:{value:new THREE.Vector3(0,0,0)},uTapT:{value:-10}};
 const group=new THREE.Group();group.name='lc-synapse';
 if(P&&count>50){
  const net=buildSynapseNet(P,Nn||null,count,{perChannel:low?5:9,inset:-.004});
  const chF=new Float32Array(net.count);net.ch.forEach((c,i)=>chF[i]=c);
  const vs='attribute float aCh;uniform float uTime;uniform float uFire[12];uniform float uRipA;uniform float uRipHz;varying float vB;varying float vC;'+
   'void main(){int c=int(aCh+.5);float f=0.;for(int i=0;i<12;i++){if(i==c)f=uFire[i];}vec3 p=position;float w=sin(dot(p,vec3(5.1,7.3,4.2))-uTime*uRipHz*6.2832);p+=normalize(p+1e-4)*w*uRipA*.6;'+
   'vB=.34+f*.9+max(0.,w)*min(1.,uRipA*30.)*.5;vC=aCh/11.;vec4 mv=modelViewMatrix*vec4(p,1.);gl_PointSize=(3.+f*5.)*clamp(7./-mv.z,.7,2.2)*smoothstep(.35,1.1,-mv.z);gl_Position=projectionMatrix*mv;}';
  const fsP='varying float vB;varying float vC;void main(){vec2 q=gl_PointCoord-.5;float a=smoothstep(.5,0.,length(q));vec3 col=mix(vec3(.78,.64,1.),vec3(.44,.9,1.),vC);gl_FragColor=vec4(col*vB,a*min(1.,vB)*.8);}';
  const fsL='varying float vB;varying float vC;void main(){vec3 col=mix(vec3(.7,.55,1.),vec3(.44,.9,1.),vC);gl_FragColor=vec4(col*vB,min(1.,vB)*.42);}';
  const mk=(fs:string)=>new THREE.ShaderMaterial({uniforms:U as any,vertexShader:vs,fragmentShader:fs,transparent:true,depthWrite:false,depthTest:false,blending:THREE.AdditiveBlending});
  const pg=new THREE.BufferGeometry();pg.setAttribute('position',new THREE.BufferAttribute(net.nodes,3));pg.setAttribute('aCh',new THREE.BufferAttribute(chF,1));
  group.add(new THREE.Points(pg,mk(fsP)));
  const lg=new THREE.BufferGeometry();lg.setAttribute('position',new THREE.BufferAttribute(net.nodes,3));lg.setAttribute('aCh',new THREE.BufferAttribute(chF,1));lg.setIndex(new THREE.BufferAttribute(net.edges,1));
  group.add(new THREE.LineSegments(lg,mk(fsL)));group.renderOrder=5;group.children.forEach(c=>c.renderOrder=5);group.position.copy(src.position);group.quaternion.copy(src.quaternion);group.scale.copy(src.scale);body.add(group);
 }
 // Soft-body ripple through the body and fur: chain onto each lit material's shader (keeps the living-core patches).
 const patched:any[]=[];LC.group.traverse((o:any)=>{const m=o.material;if(!o.isMesh||!m||m.isShaderMaterial||patched.includes(m))return;if(!(m.isMeshStandardMaterial||m.isMeshPhysicalMaterial||m.isMeshLambertMaterial))return;
  const prev=m.onBeforeCompile;m.onBeforeCompile=(sh:any,r:any)=>{prev?.call(m,sh,r);Object.assign(sh.uniforms,{uTime:U.uTime,uRipA:U.uRipA,uRipHz:U.uRipHz});
   if(sh.vertexShader.includes('#include <begin_vertex>'))sh.vertexShader='uniform float uTime;uniform float uRipA;uniform float uRipHz;\n'+sh.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\n transformed+=normal*sin(dot(position,vec3(5.1,7.3,4.2))-uTime*uRipHz*6.2832)*uRipA*.35;');};
  m.customProgramCacheKey=()=>(m.uuid+':lcrip');m.needsUpdate=true;patched.push(m);});
 const S:any=createCSTState(seed);const acc=new Float32Array(12);for(let i=0;i<12;i++)acc[i]=(i*.618)%1;
 let excite=0,emo='calm',rip=0;const listeners:((c:number)=>void)[]=[];
 return {
  group,
  onFire(fn:(c:number)=>void){listeners.push(fn);},
  kick(amount=.6){excite=Math.min(1.5,excite+amount);rip=Math.min(1,rip+amount*.8);},
  setEmotion(e:string){emo=EMO_VIBE[e as keyof typeof EMO_VIBE]?e:'calm';},
  step(dt:number){if(!(dt>0))return;U.uTime.value+=dt;const ev=(EMO_VIBE as any)[emo];(stepCSTState as any)(S,dt,{arousal:.3+ev.ex*.6});
   const fired=fireStep(acc,channelValues(S),dt,excite+ev.ex);for(let i=0;i<12;i++)fire[i]*=Math.exp(-dt*5);
   for(const c of fired){fire[c]=1;listeners.forEach(f=>f(c));}
   excite*=Math.exp(-dt*.7);rip*=Math.exp(-dt*1.1);U.uRipHz.value+=(ev.hz-U.uRipHz.value)*Math.min(1,dt*2);U.uRipA.value=.008+.03*Math.min(1,rip+ev.ex*.35);},
  dispose(){group.parent?.remove(group);group.traverse((o:any)=>{o.geometry?.dispose?.();o.material?.dispose?.();});},
 };
}

// ---------------------------------------------------------------- spots, libraries, wisps, creations
export function addRoamExtras(THREE:T,scene:import('three').Scene,{beastId,low,scale=.55,floorY=-.05,onDoing=(_s:string)=>{}}:{beastId:string;low:boolean;scale?:number;floorY?:number;onDoing?:(s:string)=>void}){
 const root=new THREE.Group();root.name='lc-roam-extras';scene.add(root);
 const spots=SPOTS.map((s:any,i:number)=>{const g=new THREE.Group();g.position.set(s.x*scale,floorY,s.z*scale);root.add(g);const col=PAL[i%PAL.length];
  const ring=new THREE.Mesh(new THREE.RingGeometry(.16,.2,36),new THREE.MeshBasicMaterial({color:col,transparent:true,opacity:.45,side:THREE.DoubleSide,blending:THREE.AdditiveBlending,depthWrite:false}));ring.rotation.x=-Math.PI/2;ring.position.y=.01;g.add(ring);
  if(s.kind==='far'){const beam=new THREE.Mesh(new THREE.CylinderGeometry(.04,.12,6,8,1,true),new THREE.MeshBasicMaterial({color:col,transparent:true,opacity:.22,blending:THREE.AdditiveBlending,depthWrite:false,side:THREE.DoubleSide}));beam.position.y=3;g.add(beam);ring.scale.setScalar(3);}// distant beacon
  let tome:any=null;if(s.kind==='library'){const ped=new THREE.Mesh(new THREE.CylinderGeometry(.06,.085,.2,8),new THREE.MeshStandardMaterial({color:0x1c1530,emissive:col,emissiveIntensity:.35,roughness:.6}));ped.position.y=.1;g.add(ped);
   tome=new THREE.Mesh(new THREE.BoxGeometry(.12,.025,.09),new THREE.MeshStandardMaterial({color:col,emissive:col,emissiveIntensity:.9}));tome.position.y=.3;g.add(tome);}
  return {s:{...s,x:s.x*scale,z:s.z*scale},g,ring,tome};});
 const NF=low?40:90,ffG=new THREE.BufferGeometry(),ffA=new Float32Array(NF*3);for(let i=0;i<NF;i++){const a=Math.random()*6.28,r=.5+Math.random()*3.6;ffA[i*3]=Math.cos(a)*r;ffA[i*3+1]=.15+Math.random()*1.6;ffA[i*3+2]=Math.sin(a)*r;}
 ffG.setAttribute('position',new THREE.BufferAttribute(ffA,3));const ffBase=ffA.slice();const ff=new THREE.Points(ffG,new THREE.PointsMaterial({size:.035,color:0xa8eaff,transparent:true,opacity:.7,blending:THREE.AdditiveBlending,depthWrite:false}));root.add(ff);
 const wisps=Array.from({length:low?4:7},(_,i)=>{const m=new THREE.Mesh(new THREE.SphereGeometry(.035,8,6),new THREE.MeshBasicMaterial({color:PAL[i%PAL.length],transparent:true,opacity:.8,blending:THREE.AdditiveBlending}));root.add(m);return {m,a:i*1.3,r:1+(i%4)*.6,h:.35+(i%3)*.35,s:(.12+(i%5)*.04)*(i%2?1:-1)};});
 const store=typeof window!=='undefined'?window.localStorage:null as any;let creations=store?loadCreations(store,beastId):[];const cg=new THREE.Group();root.add(cg);
 const draw=(c:any,born=false)=>{const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(constructPoints(c.shape,c.seed,low?80:140),3));const p=new THREE.Points(g,new THREE.PointsMaterial({size:.03,color:PAL[c.seed%PAL.length],transparent:true,opacity:born?0:.85,blending:THREE.AdditiveBlending,depthWrite:false}));p.position.set(c.x,floorY,c.z);p.scale.setScalar(.45);p.userData={born:born?0:1,tgt:born?(g.attributes.position.array as Float32Array).slice():null};cg.add(p);while(cg.children.length>12){const o:any=cg.children[0];o.geometry.dispose();cg.remove(o);}};
 creations.forEach((c:any)=>draw(c));
 const NB=low?60:120,bG=new THREE.BufferGeometry(),bA=new Float32Array(NB*3).fill(-50),bv=new Float32Array(NB*3);bG.setAttribute('position',new THREE.BufferAttribute(bA,3));const burst=new THREE.Points(bG,new THREE.PointsMaterial({size:.03,color:0xc6a2ff,transparent:true,opacity:0,blending:THREE.AdditiveBlending,depthWrite:false}));root.add(burst);let bLife=0;
 const doBurst=(x:number,y:number,z:number)=>{for(let i=0;i<NB;i++){bA[i*3]=x;bA[i*3+1]=y;bA[i*3+2]=z;const u=Math.random()*6.28,v=Math.random()*2-1,s=Math.sqrt(1-v*v);bv[i*3]=Math.cos(u)*s*.7;bv[i*3+1]=Math.abs(v)*.9+.2;bv[i*3+2]=Math.sin(u)*s*.7;}bLife=1.2;};
 const create=(shape:string,x:number,z:number,from:string)=>{const c={shape,x,z,seed:(Math.random()*2**31)>>>0,from};creations=addCreation(creations,c);if(store)saveCreations(store,beastId,creations);draw(creations[creations.length-1],true);doBurst(x,.3,z);onDoing('made a '+shape+' ✦');};
 const river=addRiverFlow(THREE,root,{low,seed:beastId,floorY});
 let t=0;
 return {river,spots:spots.map(s=>s.s),create,burst:doBurst,count:()=>creations.length,
  step(dt:number,who:{x:number;z:number}|null){t+=dt;river.step(dt);
   for(let i=0;i<NF;i++){{const th=Math.atan2(ffBase[i*3+2],ffBase[i*3])+t*.06*(i%2?1:-1),rr=Math.hypot(ffBase[i*3],ffBase[i*3+2])*(1+.12*Math.sin(th*3+t*.3));ffA[i*3]=Math.cos(th)*rr;ffA[i*3+2]=Math.sin(th)*rr;}ffA[i*3+1]=ffBase[i*3+1]+Math.sin(t*.8+i*1.7)*.12;}ffG.attributes.position.needsUpdate=true;
   wisps.forEach(w=>{w.a+=w.s*dt;const wr=w.r*(1+.18*Math.sin(w.a*3+t*.4));let x=Math.cos(w.a)*wr,z=Math.sin(w.a)*wr;if(who){const d=Math.hypot(x-who.x,z-who.z);if(d<.6&&d>1e-3){x+=(x-who.x)/d*(.6-d);z+=(z-who.z)/d*(.6-d);}}w.m.position.set(x,w.h+Math.sin(t*1.3+w.a)*.08,z);});
   spots.forEach((o,i)=>{(o.ring.material as any).opacity=.25+.2*Math.sin(t*1.5+i);if(o.tome){o.tome.position.y=.3+Math.sin(t*1.2+i)*.02;o.tome.rotation.y=t*.4;}});
   cg.children.forEach((p:any)=>{p.rotation.y+=dt*.25;if(p.userData.born<1){p.userData.born=Math.min(1,p.userData.born+dt*.6);p.material.opacity=.85*p.userData.born;const b=p.userData.born,e=1-(1-b)*(1-b)*(1-b);const A=p.geometry.attributes.position.array,T0=p.userData.tgt;if(T0){for(let j=0;j<A.length;j+=3){const k=Math.floor(j/24);const sx=Math.sin(k*7.1)*.9,sy=Math.sin(k*3.3)*.6+.4,sz=Math.cos(k*5.7)*.9;A[j]=T0[j]+(sx-T0[j])*(1-e);A[j+1]=T0[j+1]+(sy-T0[j+1])*(1-e);A[j+2]=T0[j+2]+(sz-T0[j+2])*(1-e);}p.geometry.attributes.position.needsUpdate=true;}}});
   if(bLife>0){bLife-=dt;for(let i=0;i<NB;i++){bA[i*3]+=bv[i*3]*dt;bA[i*3+1]+=bv[i*3+1]*dt;bA[i*3+2]+=bv[i*3+2]*dt;bv[i*3+1]-=.9*dt;}bG.attributes.position.needsUpdate=true;(burst.material as any).opacity=Math.max(0,bLife/1.2);}},
  words:(text:string)=>reactToWords(text),
  dispose(){scene.remove(root);root.traverse((o:any)=>{o.geometry?.dispose?.();o.material?.dispose?.();});}};
}
