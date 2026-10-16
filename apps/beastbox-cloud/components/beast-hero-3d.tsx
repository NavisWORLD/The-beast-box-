'use client';
import {useEffect,useRef} from 'react';
import type {PlushGenome} from './creature-plush-3d';
/**
 * Home hero: the player's saved Beast as a live 3D creature. Sculpted Zeref-pipeline GLB (creature-glb-beast) when its
 * body plan has one, otherwise / on low tier the code-built plush. Zeref studio lighting, idle CST motion, slow turntable.
 */
export default function BeastHero3D({genome,label}:{genome:PlushGenome;label:string}){
 const host=useRef<HTMLDivElement>(null);
 useEffect(()=>{const el=host.current;if(!el)return;let disposed=false,raf=0;let cleanup=()=>{};
  (async()=>{
   const THREE=await import('three');const [{loadBeastGlb,beastStudio},{buildPlush},cst]=await Promise.all([import('./creature-glb-beast'),import('./creature-plush-3d'),import('../lib/physics/cst-integrator.mjs')]);
   if(disposed)return;
   const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;const {isSoftwareGL}=await import('../lib/three/soft-gl');const low=reduced||isSoftwareGL()||window.innerWidth<420&&(navigator.hardwareConcurrency||4)<4;
   const r=new THREE.WebGLRenderer({antialias:!low,alpha:true,powerPreference:'low-power'});r.setPixelRatio(Math.min(window.devicePixelRatio||1,low?1:1.5));r.outputColorSpace=THREE.SRGBColorSpace;
   el.appendChild(r.domElement);r.domElement.style.width='100%';r.domElement.style.height='100%';
   const scene=new THREE.Scene();beastStudio(THREE,r,scene);const cam=new THREE.PerspectiveCamera(30,1,.05,50);
   const pivot=new THREE.Group();scene.add(pivot);
   let drive:(dt:number,l:any,mp:any)=>void=()=>{};let dispose=()=>{};
   const plush=buildPlush(THREE,genome as any,{low:true});plush.root.scale.setScalar(1.3);pivot.add(plush.root);
   drive=(dt,l,mp)=>plush.drive(dt,l,mp,null);dispose=()=>plush.dispose();
   if(!low)loadBeastGlb(THREE,genome,{tier:'high'}).then(gb=>{if(!gb||disposed){gb?.dispose();return;}plush.root.visible=false;gb.root.scale.setScalar(1.15);pivot.add(gb.root);
    drive=(dt,l,mp)=>gb.drive(dt,l,mp,null);const pd=dispose;dispose=()=>{gb.dispose();pd();};}).catch(()=>{});
   const st=cst.createCSTState(genome.seed);const life={speed:0,mode:'glance',sleep:0,lookCam:1,bob:0,heading:0};
   const size=()=>{const w=el.clientWidth||300,h=el.clientHeight||300;r.setSize(w,h,false);cam.aspect=w/h;cam.updateProjectionMatrix();};size();
   const ro=new ResizeObserver(size);ro.observe(el);let last=performance.now(),t=0;
   const loop=(now:number)=>{raf=requestAnimationFrame(loop);const dt=Math.min(.05,(now-last)/1000);last=now;if(document.hidden)return;t+=dt;
    cst.stepCSTState(st,dt);drive(reduced?0:dt,life,cst.motionParams(st));pivot.rotation.y=reduced?.5:.5+Math.sin(t*.25)*.6;
    cam.position.set(0,1.0,3.1);cam.lookAt(0,.6,0);r.render(scene,cam);};raf=requestAnimationFrame(loop);
   cleanup=()=>{cancelAnimationFrame(raf);ro.disconnect();dispose();r.dispose();r.domElement.remove();};
  })();
  return()=>{disposed=true;cleanup();};},[genome]);
 return <div ref={host} className="cosmos-home-beast3d" role="img" aria-label={label} data-home-beast3d="" style={{position:'absolute',inset:0}}/>;
}
