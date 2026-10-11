'use client';
import {useEffect,useRef,useState} from 'react';
import {createPocketSky,orbitPosition} from '../lib/pocket-sky.mjs';
import styles from './cage-pocket-dimension.module.css';

type View={theta:number;phi:number;zoom:number};
type Pointer={x:number;y:number};
type Props={
 seed:string|null; qbeastId:string|null; stage:number; reduced:boolean;
 behaviorPosition:{x:number;y:number}|null; state:string;
 onActiveChange:(active:boolean)=>void;
};
const clamp=(x:number,low:number,high:number)=>Math.min(high,Math.max(low,x));
const visualSeed=(s:string)=>{let h=2166136261;for(let i=0;i<s.length;i++)h=Math.imul(h^s.charCodeAt(i),16777619);return h>>>0;};
const randomFor=(s:string)=>{let v=visualSeed(s)||1;return()=>{v^=v<<13;v^=v>>>17;v^=v<<5;return(v>>>0)/4294967296;};};

/**
 * A REAL 3D ENVIRONMENT, NOT A REPLACEMENT CREATURE.
 * Adapted in scope from the owner's two original CodePen archives:
 * GENESIS X Night Ops (terrain/atmosphere) and Genesis Engine Definitive
 * Core (reproducible celestial orbits). Both historical applications remain
 * separate. No microphone permissions, new model, quantum run, or game state.
 *
 * The existing SparkBeastArena remains visible and interactive IN FRONT of
 * this canvas, with exactly the original canonical QBEAST sprite/voice/saves.
 */
export default function CagePocketDimension({seed,qbeastId,stage,reduced,behaviorPosition,state,onActiveChange}:Props){
 const canvasRef=useRef<HTMLCanvasElement>(null);
 const motion=useRef({position:behaviorPosition,state,stage,impulse:0});
 const cameraView=useRef<View>({theta:.7,phi:1.05,zoom:10.6});
 const [ready,setReady]=useState(false),[failed,setFailed]=useState(false);
 const id=qbeastId||'visual-preview';
 const key=seed||'beastbox-visual-preview';
 useEffect(()=>{motion.current.position=behaviorPosition;motion.current.state=state;motion.current.stage=stage;},[behaviorPosition?.x,behaviorPosition?.y,state,stage]);
 useEffect(()=>{onActiveChange(ready&&!failed);return()=>onActiveChange(false);},[ready,failed,onActiveChange]);
 useEffect(()=>{
  const canvas=canvasRef.current;
  if(!canvas||failed)return;
  let disposed=false,frame=0,cleanup=()=>{};
  const parent=canvas.closest('.cage-habitat-visual') as HTMLElement|null;
  const activePointers=new Map<number,Pointer>();
  let moved=false,suppressClick=false;
  const isControl=(target:EventTarget|null)=>target instanceof Element&&Boolean(
   target.closest('input,select,textarea,a,summary,[contenteditable="true"]')||
   target.closest('button:not([aria-label^="Tap "])')
  );
  const pointerDown=(event:PointerEvent)=>{
   if(isControl(event.target)||event.button!==0&&event.pointerType==='mouse')return;
   activePointers.set(event.pointerId,{x:event.clientX,y:event.clientY});moved=false;
  };
  const pointerMove=(event:PointerEvent)=>{
   const prev=activePointers.get(event.pointerId);if(!prev)return;
   const dx=event.clientX-prev.x,dy=event.clientY-prev.y;
   if(Math.abs(dx)+Math.abs(dy)>3)moved=true;
   if(activePointers.size===1){
    cameraView.current.theta-=dx*.009;
    cameraView.current.phi=clamp(cameraView.current.phi+dy*.008,.35,1.47);
   }else if(activePointers.size===2){
    const other=[...activePointers.entries()].find(([id])=>id!==event.pointerId)?.[1];
    if(other){
     const before=Math.hypot(prev.x-other.x,prev.y-other.y);
     const after=Math.hypot(event.clientX-other.x,event.clientY-other.y);
     if(before>18&&after>18)cameraView.current.zoom=clamp(cameraView.current.zoom*before/after,5.9,14.2);
    }
   }
   activePointers.set(event.pointerId,{x:event.clientX,y:event.clientY});
  };
  const pointerEnd=(event:PointerEvent)=>{
   if(activePointers.has(event.pointerId)&&moved)suppressClick=true;
   activePointers.delete(event.pointerId);
  };
  const clickCapture=(event:MouseEvent)=>{
   // A camera drag on the companion must not turn into an accidental attack.
   if(suppressClick&&!isControl(event.target)){
    event.preventDefault();event.stopImmediatePropagation();
   }
   suppressClick=false;
  };
  const wheel=(event:WheelEvent)=>{
   if(isControl(event.target))return;
   event.preventDefault();
   cameraView.current.zoom=clamp(cameraView.current.zoom+event.deltaY*.013,5.9,14.2);
  };
  const keyboard=(event:KeyboardEvent)=>{
   if(event.target!==parent||isControl(event.target))return;
   if(event.key==='ArrowLeft'||event.key==='ArrowRight'){
    event.preventDefault();cameraView.current.theta+=(event.key==='ArrowLeft'?.17:-.17);
   }else if(event.key==='ArrowUp'||event.key==='ArrowDown'){
    event.preventDefault();cameraView.current.phi=clamp(cameraView.current.phi+(event.key==='ArrowUp'?-.14:.14),.35,1.47);
   }else if(event.key==='+'||event.key==='='){
    event.preventDefault();cameraView.current.zoom=clamp(cameraView.current.zoom-.7,5.9,14.2);
   }else if(event.key==='-'){
    event.preventDefault();cameraView.current.zoom=clamp(cameraView.current.zoom+.7,5.9,14.2);
   }else if(event.key==='Home'){
    event.preventDefault();cameraView.current={theta:.7,phi:1.05,zoom:10.6};
   }
  };
  // Existing sound-generator events: sound is a *visual stimulus*, not proof
  // of external microphone hearing or physical quantum/natural growth.
  const chirp=(e:Event)=>{const raw=Number((e as CustomEvent)?.detail?.intensity);motion.current.impulse=clamp(motion.current.impulse+(Number.isFinite(raw)?raw:.35)*.32,0,1.25);};
  const mute=()=>{motion.current.impulse=0;};
  const option={passive:true} as AddEventListenerOptions;
  if(parent){
   parent.addEventListener('pointerdown',pointerDown,option);
   parent.addEventListener('pointermove',pointerMove,option);
   parent.addEventListener('pointerup',pointerEnd,option);
   parent.addEventListener('pointercancel',pointerEnd,option);
   parent.addEventListener('wheel',wheel,{passive:false});
   parent.addEventListener('keydown',keyboard);
   parent.addEventListener('click',clickCapture,true);
  }
  window.addEventListener('beastbox:spark-chirp',chirp);
  window.addEventListener('beastbox:spark-mute',mute);
  const releaseListeners=()=>{
   if(parent){
    parent.removeEventListener('pointerdown',pointerDown);
    parent.removeEventListener('pointermove',pointerMove);
    parent.removeEventListener('pointerup',pointerEnd);
    parent.removeEventListener('pointercancel',pointerEnd);
    parent.removeEventListener('wheel',wheel);
    parent.removeEventListener('keydown',keyboard);
    parent.removeEventListener('click',clickCapture,true);
   }
   window.removeEventListener('beastbox:spark-chirp',chirp);
   window.removeEventListener('beastbox:spark-mute',mute);
  };
  void(async()=>{
   try{
    if(!window.WebGLRenderingContext)throw Error('WebGL unavailable');
    const THREE=await import('three');
    if(disposed)return;
    const low=window.innerWidth<600||window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const renderer=new THREE.WebGLRenderer({canvas,alpha:false,antialias:!low,powerPreference:'low-power'});
    renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,low?1:1.4));
    renderer.outputColorSpace=THREE.SRGBColorSpace;
    const scene=new THREE.Scene();
    scene.background=new THREE.Color(0x070e22);
    scene.fog=new THREE.FogExp2(0x0c1730,.035);
    const camera=new THREE.PerspectiveCamera(46,1,.1,70);
    scene.add(new THREE.HemisphereLight(0x94d9ff,0x20113b,1.8));
    const moonlight=new THREE.PointLight(0xa8eaff,24,12);
    moonlight.position.set(0,4,1);scene.add(moonlight);
    const glow=new THREE.PointLight(0xba82f4,13,11);glow.position.set(-2,2,-3);scene.add(glow);
    const stone=new THREE.MeshStandardMaterial({color:0x19304d,roughness:.9,metalness:.06});
    const floraMat=new THREE.MeshStandardMaterial({color:0x3fa8a0,emissive:0x0c5b6a,emissiveIntensity:.24,roughness:.52});
    const crystalMat=new THREE.MeshStandardMaterial({color:0x9b9cf6,emissive:0x554b9e,emissiveIntensity:.3,metalness:.2,roughness:.32});
    const ground=new THREE.Mesh(new THREE.BoxGeometry(9.1,.22,9.1),stone);
    ground.position.y=-.17;scene.add(ground);
    const grid=new THREE.GridHelper(9,12,0x4983a4,0x284c74);
    grid.position.y=-.05;scene.add(grid);
    // Dimensional pocket: finite cubic world occupying only the circle.
    const bounds=new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.BoxGeometry(9.2,5.2,9.2)),
      new THREE.LineBasicMaterial({color:0x718dcc,transparent:true,opacity:.27}));
    bounds.position.y=2.45;scene.add(bounds);
    const seedRandom=randomFor(key),flora:import('three').Object3D[]=[];
    for(let i=0;i<(low?17:34);i++){
     const x=(seedRandom()-.5)*7.8,z=(seedRandom()-.5)*7.8;
     if(Math.hypot(x,z)<1.4)continue;
     const height=.24+seedRandom()*.76;
     if(i%4===0){
      const crystal=new THREE.Mesh(new THREE.OctahedronGeometry(.14+seedRandom()*.22,0),crystalMat);
      crystal.position.set(x,.3,z);scene.add(crystal);flora.push(crystal);
     }else{
      const trunk=new THREE.Mesh(new THREE.ConeGeometry(.14+seedRandom()*.15,height,5),floraMat);
      trunk.position.set(x,height*.5,z);scene.add(trunk);flora.push(trunk);
     }
    }
    // The second CodePen's cyrb128/sfc32-based small celestial generator;
    // unlike its huge planetary scene, we cap this to 2–4 tiny bodies.
    const sky=createPocketSky(key,{quality:low?'low':'auto'});
    const skyGeometry=new THREE.SphereGeometry(1,low?8:12,low?6:10);
    const orbiters=sky.bodies.map(body=>{
     const color=new THREE.Color().setHSL(body.hue/360,.65,.6);
     const object=new THREE.Mesh(skyGeometry,new THREE.MeshBasicMaterial({color}));
     object.scale.setScalar(body.size);scene.add(object);
     return{body,object};
    });
    const starsGeom=new THREE.BufferGeometry(),points:number[]=[];
    for(let i=0;i<(low?55:120);i++)points.push((seedRandom()-.5)*8.8,.5+seedRandom()*4.5,(seedRandom()-.5)*8.8);
    starsGeom.setAttribute('position',new THREE.Float32BufferAttribute(points,3));
    scene.add(new THREE.Points(starsGeom,new THREE.PointsMaterial({color:0xb2dfff,size:.042,transparent:true,opacity:.75})));
    const resize=()=>{
     if(disposed)return;
     const rect=canvas.getBoundingClientRect();
     if(rect.width<2||rect.height<2)return;
     renderer.setSize(Math.floor(rect.width),Math.floor(rect.height),false);
     camera.aspect=rect.width/rect.height;camera.updateProjectionMatrix();
    };
    const ro=typeof ResizeObserver!=='undefined'?new ResizeObserver(resize):null;
    ro?.observe(canvas);resize();
    let visible=true,last=performance.now(),elapsed=0,lastPaint=0,rendered=false;
    const io=typeof IntersectionObserver!=='undefined'?new IntersectionObserver(entries=>visible=entries.some(e=>e.isIntersecting),{threshold:.01}):null;
    io?.observe(canvas);
    const onContextLost=(e:Event)=>{e.preventDefault();setReady(false);setFailed(true);};
    canvas.addEventListener('webglcontextlost',onContextLost);
    const focus=new THREE.Vector3(0,.85,0);
    const animate=(now:number)=>{
     if(disposed)return;
     frame=requestAnimationFrame(animate);
     const dt=clamp((now-last)/1000,0,.06);last=now;
     if(document.hidden||!visible||now-lastPaint<(low?55:33))return;
     lastPaint=now;
     if(!reduced)elapsed+=dt;
     motion.current.impulse=Math.max(0,motion.current.impulse-dt*.35);
     const pulse=motion.current.impulse;
     // World vegetation responds to the recorded/native stage and actual
     // local creature audio events. This is cosmetic, not learned growth.
     const growth=1+(clamp(motion.current.stage,1,3)-1)*.1+pulse*.19;
     flora.forEach((o,i)=>{o.scale.y=1+(growth-1)*(.6+(i%3)*.2);});
     moonlight.intensity=(motion.current.state==='sleeping'?16:24)+pulse*12;
     // Follow the existing saved creature's bounded environmental position:
     // moving light is presentation only; it does not create a new position.
     const p=motion.current.position;
     if(p&&Number.isFinite(p.x)&&Number.isFinite(p.y)){
      glow.position.lerp(new THREE.Vector3(
       (clamp(p.x,0,1)-.5)*5,1.9,(clamp(p.y,0,1)-.5)*5
      ),Math.min(1,dt*2.2));
     }
     for(const {body,object} of orbiters){
      const xyz=orbitPosition(body,elapsed,!reduced);
      object.position.set(xyz.x,xyz.y,xyz.z);
     }
     const v=cameraView.current;
     camera.position.set(v.zoom*Math.sin(v.phi)*Math.sin(v.theta),v.zoom*Math.cos(v.phi),v.zoom*Math.sin(v.phi)*Math.cos(v.theta));
     camera.lookAt(focus);
     try{renderer.render(scene,camera);}catch{setReady(false);setFailed(true);return;}
     if(!rendered){rendered=true;setReady(true);}
    };
    frame=requestAnimationFrame(animate);
    cleanup=()=>{
     cancelAnimationFrame(frame);ro?.disconnect();io?.disconnect();
     canvas.removeEventListener('webglcontextlost',onContextLost);
     const geometries=new Set<import('three').BufferGeometry>(),materials=new Set<import('three').Material>();
     scene.traverse(o=>{
      if(o instanceof THREE.Mesh||o instanceof THREE.LineSegments||o instanceof THREE.Points){
       geometries.add(o.geometry);
       const m=o.material;(Array.isArray(m)?m:[m]).forEach(k=>materials.add(k));
      }
     });
     geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());renderer.dispose();
    };
   }catch{
    if(!disposed){setFailed(true);setReady(false);}
   }
  })();
  return()=>{disposed=true;cancelAnimationFrame(frame);cleanup();releaseListeners();};
 },[key,failed,reduced]);
 return <div className={styles.root} data-pocket-dimension="true"
  data-world-source="genesis-nightops-core-visual-v1"
  data-pocket-state={failed?'fallback':ready?'ready':'loading'} data-creature-id={id}>
  {!failed?<canvas data-pocket-webgl="true" className={styles.canvas} ref={canvasRef}
   aria-hidden="true"/>:null}
  {!failed&&!ready?<span className={styles.sr} role="status">Opening the dimensional world behind your Beast…</span>:null}
 </div>;
}
