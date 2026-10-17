'use client';
/**
 * Living-core roamer (Oct 16): the home / Cage creature as its true-3D living-core model,
 * roaming a bigger, fuller pocket universe: ambient wisps + fireflies, favorite spots,
 * three mini libraries it visits and learns from, and CST particle constructs it makes
 * that persist in its world. Driven only by existing signals (session chat, beast-chat /
 * gba-input events, deriveEmotions, CHSH game, pocket journal); no new backend.
 */
import {useEffect,useRef,useState} from 'react';
import {CREATURES} from '../lib/living-core/creatures.js';
import {SPOTS,nextGoal,reactToWords,baseMood,rng,constructPoints,addCreation,loadCreations,saveCreations,hopPose,flap,SHAPES} from '../lib/living-core/roam-brain.mjs';
import {recordArrival,recordCombo} from '../lib/zeref/pocket-journal';
type Props={creature?:string;beastId:string;mood?:string;chatText?:string|null;chatCount?:number;game?:any;reduced?:boolean;caption?:boolean};
// Mesh cache: building the marching-cubes body is the expensive part, so one build per creature per page life.
const CACHE=new Map<string,Promise<any>>();
const isLow=()=>typeof navigator!=='undefined'&&(/iPhone|iPad|Android/i.test(navigator.userAgent)||(navigator as any).hardwareConcurrency<=4);
async function getCore(THREE:any,name:string,low:boolean){
 const key=name+(low?':low':'');let p=CACHE.get(key);
 if(!p){p=(async()=>{const {MarchingCubes}=await import('three/examples/jsm/objects/MarchingCubes.js');const {buildLivingCore}=await import('../lib/living-core/living-core.js');
  const C=(CREATURES as any)[name];// RES stays at the calibrated 110 (other layers assume it); LOD = fewer fur shells + lower pixel ratio, mesh built once and cached.
  const opts={...C.opts};if(low&&opts.furShells)opts.furShells={...opts.furShells,layers:Math.min(6,opts.furShells.layers||6)};
  return {LC:await buildLivingCore({THREE,MarchingCubes,src:'/living-core/'+C.src,opts}),light:C.light||{}};})();CACHE.set(key,p);p.catch(()=>CACHE.delete(key));}
 return p;
}
export default function LivingCoreRoamer({creature='zeref',beastId,mood='calm',chatText=null,chatCount=0,game=null,reduced=false,caption=true}:Props){
 const host=useRef<HTMLDivElement>(null);const api=useRef<any>(null);const [doing,setDoing]=useState('waking up');const [ready,setReady]=useState(false);
 useEffect(()=>{api.current?.mood(mood);},[mood,ready]);
 useEffect(()=>{if(chatCount&&chatText)api.current?.words(chatText,'chat');},[chatCount,chatText,ready]);
 useEffect(()=>{if(game)api.current?.words('look explore','game');},[game,ready]);
 useEffect(()=>{
  const el=host.current;if(!el)return;let dead=false,raf=0;let cleanup=()=>{};
  (async()=>{
   const THREE=await import('three');const low=isLow();
   const R=new THREE.WebGLRenderer({antialias:!low,alpha:true,powerPreference:'high-performance'});R.setPixelRatio(Math.min(low?1.5:2,devicePixelRatio));R.localClippingEnabled=true;R.toneMapping=THREE.ACESFilmicToneMapping;R.outputColorSpace=THREE.SRGBColorSpace;
   R.domElement.style.cssText='width:100%;height:100%;display:block;touch-action:pan-y';el.appendChild(R.domElement);
   const scene=new THREE.Scene();scene.fog=new THREE.FogExp2(0x070418,.05);
   const cam=new THREE.PerspectiveCamera(38,1,.1,80);
   const size=()=>{const w=el.clientWidth||300,h=el.clientHeight||300;R.setSize(w,h,false);cam.aspect=w/h;cam.updateProjectionMatrix();};size();const ro=new ResizeObserver(size);ro.observe(el);
   let core:any;try{core=await getCore(THREE,creature,low);}catch{core=null;}
   if(dead||!core){R.dispose();R.domElement.remove();return;}
   const {LC,light:LG}=core;
   scene.add(new THREE.HemisphereLight(LG.hemiS??0x6a5cff,LG.hemiG??0x3a1f7a,.7));const key=new THREE.DirectionalLight(LG.key??0xffffff,LG.keyI??2.4);key.position.set(3,5,5);scene.add(key);
   const rimL=new THREE.DirectionalLight(LG.rim??0x7a52ff,(LG.rimI??1.4)*1.3);rimL.position.set(-4,2,-4);scene.add(rimL);const fillL=new THREE.DirectionalLight(LG.fill??0xd8d8e0,LG.fillI??.9);fillL.position.set(-4,0,5);scene.add(fillL);scene.add(new THREE.AmbientLight(LG.amb??0x201a30,.6));
   // World: bigger floor with soft grid glow, starfield, fireflies, wisps.
   const floorY=0;const floor=new THREE.Mesh(new THREE.CircleGeometry(6,72),new THREE.MeshBasicMaterial({color:0x22164e,transparent:true,opacity:.55}));floor.rotation.x=-Math.PI/2;scene.add(floor);
   const ringG=new THREE.RingGeometry(5.8,6,96);const edge=new THREE.Mesh(ringG,new THREE.MeshBasicMaterial({color:0x8f6bff,transparent:true,opacity:.35,side:THREE.DoubleSide}));edge.rotation.x=-Math.PI/2;edge.position.y=.01;scene.add(edge);
   const pts=(n:number,f:(i:number,a:Float32Array)=>void,mat:any)=>{const g=new THREE.BufferGeometry(),a=new Float32Array(n*3);for(let i=0;i<n;i++)f(i,a);g.setAttribute('position',new THREE.BufferAttribute(a,3));const p=new THREE.Points(g,mat);scene.add(p);return p;};
   const R0=rng(beastId||'zeref');
   const stars=pts(low?900:2400,(i,a)=>{const u=R0()*Math.PI*2,v=Math.acos(2*R0()-1),r=24+R0()*10;a[i*3]=r*Math.sin(v)*Math.cos(u);a[i*3+1]=Math.abs(r*Math.cos(v))*.8+1;a[i*3+2]=r*Math.sin(v)*Math.sin(u);},new THREE.PointsMaterial({size:.08,color:0xb8a8ff,transparent:true,opacity:.8,depthWrite:false}));
   const NF=low?60:140;const ff=pts(NF,(i,a)=>{a[i*3]=(R0()-.5)*10;a[i*3+1]=.2+R0()*2.2;a[i*3+2]=(R0()-.5)*10;},new THREE.PointsMaterial({size:.07,color:0xffe6a0,transparent:true,opacity:.9,blending:THREE.AdditiveBlending,depthWrite:false}));
   const ffBase=(ff.geometry.attributes.position.array as Float32Array).slice();
   // Ambient creatures: little wisps that drift in loops and scatter from the roamer.
   const wisps=Array.from({length:low?5:9},(_,i)=>{const m=new THREE.Mesh(new THREE.SphereGeometry(.07,10,8),new THREE.MeshBasicMaterial({color:new THREE.Color().setHSL(.68+R0()*.2,.8,.72),transparent:true,opacity:.85,blending:THREE.AdditiveBlending}));scene.add(m);return {m,a:R0()*6.28,r:1.5+R0()*3.6,h:.5+R0()*1.6,s:(.15+R0()*.25)*(i%2?1:-1)};});
   // Spots: favorite rings + mini libraries (pedestal + floating tome + orbiting glyph motes).
   const spotObjs=SPOTS.map(s=>{const g=new THREE.Group();g.position.set(s.x,floorY,s.z);scene.add(g);const col=new THREE.Color(s.color);
    const ring=new THREE.Mesh(new THREE.RingGeometry(.35,.42,40),new THREE.MeshBasicMaterial({color:col,transparent:true,opacity:.6,side:THREE.DoubleSide,blending:THREE.AdditiveBlending}));ring.rotation.x=-Math.PI/2;ring.position.y=.02;g.add(ring);
    let tome:any=null;if(s.kind==='library'){const ped=new THREE.Mesh(new THREE.CylinderGeometry(.16,.22,.42,10),new THREE.MeshStandardMaterial({color:0x2a1d55,roughness:.6,emissive:col,emissiveIntensity:.15}));ped.position.y=.21;g.add(ped);
     tome=new THREE.Mesh(new THREE.BoxGeometry(.26,.06,.2),new THREE.MeshStandardMaterial({color:col,emissive:col,emissiveIntensity:.6}));tome.position.y=.62;g.add(tome);
     const motes=new THREE.Points(new THREE.BufferGeometry().setAttribute('position',new THREE.BufferAttribute(constructPoints('ring',s.id.length,24).map((v,k)=>k%3===1?v*.5+.4:v*.7),3)),new THREE.PointsMaterial({size:.05,color:col,transparent:true,opacity:.9,blending:THREE.AdditiveBlending,depthWrite:false}));g.add(motes);(g as any).motes=motes;}
    else if(s.id==='moon-pool'){const pool=new THREE.Mesh(new THREE.CircleGeometry(.34,32),new THREE.MeshBasicMaterial({color:0x3a6aff,transparent:true,opacity:.45}));pool.rotation.x=-Math.PI/2;pool.position.y=.015;g.add(pool);}
    return {s,g,ring,tome};});
   // Creations: persisted CST particle constructs.
   const store=window.localStorage;let creations=loadCreations(store,beastId);const cGroup=new THREE.Group();scene.add(cGroup);
   const drawCreation=(c:any,born=false)=>{const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(constructPoints(c.shape,c.seed,low?90:160),3));const p=new THREE.Points(g,new THREE.PointsMaterial({size:.06,color:new THREE.Color().setHSL(c.hue,.8,.7),transparent:true,opacity:born?0:.9,blending:THREE.AdditiveBlending,depthWrite:false}));p.position.set(c.x,0,c.z);p.userData={born:born?0:1,spin:.2+(c.seed%7)/20};cGroup.add(p);while(cGroup.children.length>12){const o=cGroup.children[0] as any;o.geometry.dispose();cGroup.remove(o);}};
   creations.forEach(c=>drawCreation(c));
   // Particle bursts (chat words, gameplay, learning).
   const NB=low?80:160;const burst=pts(NB,(i,a)=>{a[i*3+1]=-50;},new THREE.PointsMaterial({size:.06,color:0xffffff,transparent:true,opacity:.95,blending:THREE.AdditiveBlending,depthWrite:false}));const bv=new Float32Array(NB*3);let bLife=0;
   const doBurst=(x:number,y:number,z:number,hue:number)=>{const a=burst.geometry.attributes.position.array as Float32Array;for(let i=0;i<NB;i++){a[i*3]=x;a[i*3+1]=y;a[i*3+2]=z;const u=Math.random()*6.28,v=Math.random()*2-1;bv[i*3]=Math.cos(u)*Math.sqrt(1-v*v)*1.4;bv[i*3+1]=Math.abs(v)*1.8+.4;bv[i*3+2]=Math.sin(u)*Math.sqrt(1-v*v)*1.4;}(burst.material as any).color.setHSL(hue,.8,.75);bLife=1.4;};
   // Creature
   const root=new THREE.Group();const body=new THREE.Group();root.add(body);body.add(LC.group);scene.add(root);if(LC.dust)scene.add(LC.dust);if(LC.shadow)root.add(LC.shadow);
   // Living-core bodies stand ~2|footY| tall (particle pools park at -999, so no Box3 here); target ~1.7 world units.
   const k=.85/Math.max(.5,Math.abs(LC.footY||2.5));body.scale.setScalar(k);body.position.y=-LC.footY*k;
   if(LC.pmat?.uniforms?.uSize){const fit=()=>{LC.pmat.uniforms.uSize.value=0.045*1.55*(el.clientHeight||400)*.85*k*1.4;};fit();}
   const canFly=!!(CREATURES as any)[creature]?.opts?.wings;
   LC.birth?.();LC.setEmotion?.('calm');LC.transform?.(1);
   const st={x:0,z:0,h:0,goal:null as any,mood:'calm',override:null as string|null,ovT:0,pause:1.5,hopP:-1,fly:0,lookCam:0,visits:{} as Record<string,number>,t:0,flyH:0};
   const setMood=(m:string)=>{if(st.mood!==m){st.mood=m;LC.setEmotion?.(m);}};
   const sayDoing=(s:string)=>setDoing(s);
   const create=(shape:string,from:string)=>{const c={shape,x:st.x+Math.sin(st.h)*.9,z:st.z+Math.cos(st.h)*.9,seed:(Math.random()*2**31)>>>0,from,hue:.6+Math.random()*.35};creations=addCreation(creations,c);saveCreations(store,beastId,creations);drawCreation(creations.at(-1),true);doBurst(c.x,.6,c.z,c.hue);
    try{recordCombo(beastId,{key:'lc-create:'+shape+':'+c.seed,name:'Made a '+shape+' construct'});}catch{}sayDoing('made a '+shape+' ✦');};
   let baseM='calm';
   api.current={mood:(m:string)=>{baseM=m||'calm';},words:(text:string,from:string)=>{const r=reactToWords(text) as {emotion:string|null;shape:string|null;burst:number};if(r.emotion){st.override=r.emotion;st.ovT=5;setMood(r.emotion);}st.lookCam=2.5;doBurst(st.x,1.4,st.z,r.emotion==='angry'?0:r.emotion==='scared'?.55:.78);if(r.emotion==='happy')st.hopP=0;if(r.shape)create(r.shape,from);}};
   const onChat=(e:any)=>api.current.words(e?.detail?.text||'hi','chat');const onPad=(e:any)=>{if(e?.detail?.down){st.hopP=0;st.override='happy';st.ovT=2;setMood('happy');}};
   window.addEventListener('beastbox:beast-chat',onChat);window.addEventListener('beastbox:gba-input',onPad);
   setReady(true);
   const r=rng((beastId||'z')+':roam');let last=performance.now(),vis=true;
   const io=new IntersectionObserver(es=>{vis=es[0]?.isIntersecting??true;});io.observe(el);
   const loop=()=>{raf=requestAnimationFrame(loop);const now=performance.now();const dt=Math.min(.05,(now-last)/1000);last=now;if(!vis||document.hidden||dt<1e-4)return;const d=reduced?dt*.4:dt;st.t+=d;
    // mood: transient override (words / play) else the Beast's own mood.
    if(st.ovT>0){st.ovT-=d;if(st.ovT<=0)st.override=null;}setMood(st.override||baseM);
    // brain: pause -> pick goal -> travel -> arrive (learn / rest / create)
    if(!st.goal){st.pause-=d;if(st.pause<=0){st.goal=nextGoal(r,st.mood,st.visits);sayDoing(st.goal.kind==='library'?'heading to the '+st.goal.label:st.goal.kind==='favorite'?'off to '+st.goal.label:'exploring');st.fly=canFly&&Math.hypot(st.goal.x-st.x,st.goal.z-st.z)>3.5?1:0;}}
    else{const dx=st.goal.x-st.x,dz=st.goal.z-st.z,dist=Math.hypot(dx,dz);const want=Math.atan2(dx,dz);let dh=want-st.h;dh=Math.atan2(Math.sin(dh),Math.cos(dh));st.h+=dh*Math.min(1,d*3);
     const spd=(st.mood==='sleepy'?.45:st.mood==='scared'?1.3:st.mood==='happy'?1.05:.8)*(st.fly?1.5:1);
     if(dist>.55){st.x+=Math.sin(st.h)*spd*d*Math.max(.2,Math.cos(dh));st.z+=Math.cos(st.h)*spd*d*Math.max(.2,Math.cos(dh));if(!st.fly&&st.hopP<0&&(st.mood==='happy'||r()<d*.6))st.hopP=0;}
     else{const g=st.goal;st.goal=null;st.fly=0;st.pause=g.kind==='library'?4:g.id==='nap-moss'&&st.mood==='sleepy'?8:2+r()*2;st.visits[g.id]=(st.visits[g.id]||0)+1;
      if(g.kind==='library'){st.override='curious';st.ovT=4;setMood('curious');sayDoing('reading at the '+g.label);try{recordArrival(beastId,'library:'+g.topic);}catch{}
       const so=spotObjs.find(o=>o.s.id===g.id);if(so)doBurst(g.x,.7,g.z,new THREE.Color(g.color).getHSL({h:0,s:0,l:0}).h);
       setTimeout(()=>{if(!dead)create(SHAPES[(st.visits[g.id]+g.topic.length)%SHAPES.length],'library:'+g.topic);},2600);}
      else{if(g.id!=='wander')try{recordArrival(beastId,g.id);}catch{}sayDoing(g.kind==='favorite'?'resting at '+g.label:'looking around');if(r()<.5)st.lookCam=2;}}}
    // pose
    let lift=0,sy=1,sx=1;if(st.hopP>=0){st.hopP+=d*2.2;if(st.hopP>=1)st.hopP=-1;else{const hp=hopPose(st.hopP);lift=hp.lift;sy=hp.sy;sx=hp.sx;}}
    st.flyH+=((st.fly?1.1:0)-st.flyH)*Math.min(1,d*2);const fy=st.flyH;lift+=fy+(fy>.05?flap(st.t)*.05:0);
    if(st.lookCam>0)st.lookCam-=d;const camA=Math.atan2(cam.position.x-st.x,cam.position.z-st.z);let face=st.h;if(st.lookCam>0&&!st.goal){let dd=camA-st.h;dd=Math.atan2(Math.sin(dd),Math.cos(dd));face=st.h+dd*.85;}
    root.position.set(st.x,floorY+lift,st.z);root.rotation.y=face;body.scale.set(k*sx,k*sy,k*sx);
    // CST field integrates explicitly: substep at 1/120 s like the prototype or it diverges (NaN).
    {const n=Math.max(1,Math.ceil(d*120));for(let i=0;i<n;i++)LC.step(d/n);}
    // world life
    stars.rotation.y=st.t*.003;const fa=ff.geometry.attributes.position.array as Float32Array;for(let i=0;i<NF;i++){fa[i*3]=ffBase[i*3]+Math.sin(st.t*.5+i)*.3;fa[i*3+1]=ffBase[i*3+1]+Math.sin(st.t*.8+i*1.7)*.2;fa[i*3+2]=ffBase[i*3+2]+Math.cos(st.t*.4+i)*.3;}ff.geometry.attributes.position.needsUpdate=true;(ff.material as any).opacity=.55+.35*Math.sin(st.t*2);
    wisps.forEach(w=>{w.a+=w.s*d;let x=Math.cos(w.a)*w.r,z=Math.sin(w.a)*w.r;const dd=Math.hypot(x-st.x,z-st.z);if(dd<1){x+=(x-st.x)/dd*(1-dd);z+=(z-st.z)/dd*(1-dd);}w.m.position.set(x,w.h+Math.sin(st.t*1.3+w.a)*.15,z);});
    spotObjs.forEach((o,i)=>{(o.ring.material as any).opacity=.35+.25*Math.sin(st.t*1.5+i);if(o.tome){o.tome.position.y=.62+Math.sin(st.t*1.2+i)*.04;o.tome.rotation.y=st.t*.4;}const m=(o.g as any).motes;if(m)m.rotation.y=st.t*.6;});
    cGroup.children.forEach((p:any)=>{p.rotation.y+=d*p.userData.spin;if(p.userData.born<1){p.userData.born=Math.min(1,p.userData.born+d*.6);p.material.opacity=.9*p.userData.born;p.scale.setScalar(.2+.8*p.userData.born);}});
    if(bLife>0){bLife-=d;const a=burst.geometry.attributes.position.array as Float32Array;for(let i=0;i<NB;i++){a[i*3]+=bv[i*3]*d;a[i*3+1]+=bv[i*3+1]*d;a[i*3+2]+=bv[i*3+2]*d;bv[i*3+1]-=1.6*d;}burst.geometry.attributes.position.needsUpdate=true;(burst.material as any).opacity=Math.max(0,bLife/1.4);}
    // camera: slow orbit that keeps the creature in frame
    const ca=st.t*.05;const tx=st.x*.6,tz=st.z*.6;cam.position.set(tx+Math.sin(ca)*8.6,3.6,tz+Math.cos(ca)*8.6);cam.lookAt(tx,.8,tz);
    R.render(scene,cam);};
   loop();
   (window as any).__roamer={st,LC,advance:(s:number)=>{const n=Math.round(s*30);for(let i=0;i<n;i++){last=performance.now()-33;}},creations:()=>creations};
   cleanup=()=>{cancelAnimationFrame(raf);ro.disconnect();io.disconnect();window.removeEventListener('beastbox:beast-chat',onChat);window.removeEventListener('beastbox:gba-input',onPad);root.remove(LC.shadow);body.remove(LC.group);if(LC.dust)scene.remove(LC.dust);R.dispose();R.domElement.remove();};
  })();
  return()=>{dead=true;cleanup();api.current=null;};
 },[creature,beastId,reduced]);
 return <div ref={host} className="lc-roamer" data-living-core={creature} data-lc-ready={ready?'1':'0'} style={{position:'absolute',inset:0}}>
  {caption?<span className="lc-roamer-doing" aria-live="polite">{doing}</span>:null}
 </div>;
}
