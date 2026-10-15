'use client';
import {useEffect,useRef,useState} from 'react';
import {useUniverseMotion} from './use-universe-motion';
import ZerefMoonwraith from './zeref-moonwraith';
import {createMind,stepMind,frameFor,forceBehavior,greetMind} from '../lib/zeref/zeref-mind.mjs';
import {buildZerefRig,poseZerefRig,disposeZerefRig} from '../lib/companion/zeref-rig.mjs';

export type ZerefStageState='idle'|'listening'|'speaking'|'sleeping'|'celebrating';
type Props={
 care?:{energy?:number;bond?:number};
 state?:ZerefStageState;
 turntable?:boolean;
 turntableAngle?:number|null;
 paused?:boolean;
 quality?:'auto'|'low';
 className?:string;
 label?:string;
 qbeastId?:string;
};

/**
 * Dimensional Zeref stage: the SAME deterministic zeref-mind that poses the
 * SVG rig now poses real Three.js geometry (body, head, ears, wings,
 * segmented tail, gem, halo). Artistic representation, not a new phenotype.
 *
 * - listening: the mesh looks at the viewer (centered gaze, no invented input)
 * - speaking/celebrating: one friendly reaction per transition
 * - sleeping: the mind rests until the state changes back
 * Reduced motion, WebGL loss, and low-power paths fall back to the existing
 * static SVG instead of a blank canvas.
 */
export default function ZerefTrue3D({care,state='idle',turntable=false,turntableAngle=null,paused=false,quality='auto',className='',label='Zeref in 3D',qbeastId='bb-7f9c2a03'}:Props){
 const canvas=useRef<HTMLCanvasElement>(null);
 const mindRef=useRef<ReturnType<typeof createMind>|null>(null);
 if(!mindRef.current)mindRef.current=createMind({care:care||{}});
 const stateRef=useRef(state),pausedRef=useRef(paused);
 const rotationRef=useRef({turntable,angle:turntableAngle});
 useEffect(()=>{rotationRef.current={turntable,angle:typeof turntableAngle==='number'&&Number.isFinite(turntableAngle)?turntableAngle:null};},[turntable,turntableAngle]);
 useEffect(()=>{stateRef.current=state;},[state]);
 useEffect(()=>{pausedRef.current=paused;},[paused]);
 const [ready,setReady]=useState(false),[fallback,setFallback]=useState(false);
 const {reduced}=useUniverseMotion();
 useEffect(()=>{
  const element=canvas.current,mind=mindRef.current;
  if(!element||!mind||reduced||fallback||typeof window.WebGLRenderingContext==='undefined')return;
  let disposed=false,animation=0,rendererCleanup=()=>{},lastState:ZerefStageState=stateRef.current;
  void (async()=>{
   try{
    const THREE=await import('three');
    if(disposed)return;
    const renderer=new THREE.WebGLRenderer({canvas:element,alpha:true,antialias:quality!=='low',powerPreference:'low-power'});
    renderer.setPixelRatio(Math.min(quality==='low'?1:1.5,window.devicePixelRatio||1));
    renderer.outputColorSpace=THREE.SRGBColorSpace;
    const scene=new THREE.Scene();
    const camera=new THREE.PerspectiveCamera(32,1,.1,50);
    camera.position.set(0,.5,5.4);camera.lookAt(0,.35,0);
    scene.add(new THREE.AmbientLight(0xbfc6ff,1.1));
    const key=new THREE.PointLight(0xcfd8ff,26,16);key.position.set(-2,2.4,3);scene.add(key);
    const rim=new THREE.PointLight(0x8b5cf6,40,16);rim.position.set(2.2,-.4,-2.4);scene.add(rim);
    const rig=buildZerefRig(THREE);
    scene.add(rig.group);
    const shadowTex=(()=>{const c=document.createElement('canvas');c.width=c.height=64;const g=c.getContext('2d');if(g){const r=g.createRadialGradient(32,32,2,32,32,32);r.addColorStop(0,'rgba(4,2,16,.6)');r.addColorStop(1,'rgba(4,2,16,0)');g.fillStyle=r;g.fillRect(0,0,64,64);}return new THREE.CanvasTexture(c);})();
    const shadow=new THREE.Mesh(new THREE.PlaneGeometry(1.9,.8),new THREE.MeshBasicMaterial({map:shadowTex,transparent:true,depthWrite:false}));
    shadow.rotation.x=-Math.PI/2;shadow.position.y=-.62;scene.add(shadow);
    const onLost=(event:Event)=>{event.preventDefault();cancelAnimationFrame(animation);setReady(false);setFallback(true);};
    element.addEventListener('webglcontextlost',onLost);
    const resize=()=>{
     if(disposed)return;
     const rect=element.getBoundingClientRect();
     if(rect.width<1||rect.height<1)return;
     const w=Math.max(1,Math.floor(rect.width)),h=Math.max(1,Math.floor(rect.height));
     renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();
    };
    const observer=new ResizeObserver(resize);observer.observe(element);resize();
    let prev=performance.now(),lastPaint=0,turntablePhase=0,rendered=false;
    const animate=(now:number)=>{
     if(disposed||document.hidden)return;
     const dt=Math.min((now-prev)/1000,.07);prev=now;
     animation=requestAnimationFrame(animate);
     if(pausedRef.current&&rendered)return;
     if(now-lastPaint<(quality==='low'?66:34))return;
     lastPaint=now;
     const mood=stateRef.current;
     if(mood!==lastState){
      if(mood==='sleeping'&&mind.behavior!=='sleep')forceBehavior(mind,'sleep');
      if((mood==='speaking'||mood==='celebrating')&&(lastState!=='speaking'&&lastState!=='celebrating'))greetMind(mind);
      lastState=mood;
     }
     const inputs=mood==='listening'?{pointer:{x:0,y:0,moved:true}}:{};
     if(!pausedRef.current)stepMind(mind,dt,inputs);
     poseZerefRig(rig,frameFor(mind));
     if(rotationRef.current.turntable)turntablePhase=(turntablePhase+dt*Math.PI/4)%(Math.PI*2);
     const faceYaw=rig.group.rotation.y;
     rig.group.rotation.y=rotationRef.current.turntable?turntablePhase+faceYaw
      :rotationRef.current.angle!==null?rotationRef.current.angle*Math.PI/180+faceYaw:faceYaw;
     shadow.scale.setScalar(1-Math.min(.25,Math.max(0,rig.group.position.y)*.9));
     try{renderer.render(scene,camera);}catch{
      cancelAnimationFrame(animation);
      if(!disposed){setReady(false);setFallback(true);}
      return;
     }
     if(!rendered){rendered=true;setReady(true);}
    };
    const visibility=()=>{if(!document.hidden&&!disposed){prev=performance.now();cancelAnimationFrame(animation);animation=requestAnimationFrame(animate);}else cancelAnimationFrame(animation);};
    document.addEventListener('visibilitychange',visibility);
    animation=requestAnimationFrame(animate);
    rendererCleanup=()=>{
     cancelAnimationFrame(animation);
     observer.disconnect();document.removeEventListener('visibilitychange',visibility);
     element.removeEventListener('webglcontextlost',onLost);
     disposeZerefRig(rig);
     shadow.geometry.dispose();(shadow.material as import('three').Material).dispose();shadowTex.dispose();
     renderer.dispose();
    };
   }catch{
    if(!disposed){setFallback(true);setReady(false);}
   }
  })();
  return()=>{disposed=true;rendererCleanup();};
 },[quality,reduced,fallback]);
 return <div className={'zeref-true3d '+className} aria-label={label} data-graphics={ready&&!reduced&&!fallback?'zeref-true3d':'zeref-illustration'} data-creature-id={qbeastId} data-motion={paused?'paused':reduced?'reduced':'active'} data-zeref-stage={state}>
  {(reduced||fallback||!ready)&&<div className="zeref-true3d-fallback"><ZerefMoonwraith greet={0} showCaption={false}/></div>}
  {!reduced&&!fallback?<canvas ref={canvas} className="zeref-true3d-canvas" aria-hidden="true"/>:null}
 </div>;
}
