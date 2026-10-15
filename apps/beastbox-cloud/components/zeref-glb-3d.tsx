'use client';
/**
 * Sculpted, rigged Zeref (public/creatures3d/zeref.glb) on a three.js stage. Spring bones,
 * breathing and expressions all run on the CST integrator via lib/creatures3d/zeref-glb-driver.mjs.
 * Shown on /beast-cage/turntable only behind ?glb=1 while Cory reviews it.
 */
import {useEffect,useRef} from 'react';
import * as THREE from 'three';
import {createZerefDriver,ZEREF_GLB_URL} from '@/lib/creatures3d/zeref-glb-driver.mjs';

export type ZerefMood='calm'|'happy'|'curious'|'scared'|'sleepy'|'angry';
export default function ZerefGlb3D({spin=true,angle=0,mood='calm',seed='zeref'}:{spin?:boolean;angle?:number;mood?:ZerefMood;seed?:string}){
 const host=useRef<HTMLDivElement>(null);
 const live=useRef({spin,angle,mood});live.current={spin,angle,mood};
 useEffect(()=>{
  const el=host.current;if(!el)return;let disposed=false,raf=0;
  const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});
  renderer.setPixelRatio(Math.min(2,window.devicePixelRatio||1));renderer.outputColorSpace=THREE.SRGBColorSpace;
  renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.1;
  el.appendChild(renderer.domElement);renderer.domElement.style.width='100%';renderer.domElement.style.height='100%';
  const scene=new THREE.Scene();const camera=new THREE.PerspectiveCamera(32,1,.05,50);
  scene.add(new THREE.HemisphereLight(0xb9a2ff,0x090414,.7));
  const key=new THREE.DirectionalLight(0xffffff,2.2);key.position.set(-2,3,3);scene.add(key);
  const rim=new THREE.DirectionalLight(0x8fe8ff,2.4);rim.position.set(1.5,2.5,-3);scene.add(rim);
  const rim2=new THREE.DirectionalLight(0xc59bff,1.6);rim2.position.set(-2,2,-2.5);scene.add(rim2);
  const floor=new THREE.Mesh(new THREE.CircleGeometry(1.6,64),new THREE.MeshBasicMaterial({color:0x05020c,transparent:true,opacity:.6}));
  floor.rotation.x=-Math.PI/2;scene.add(floor);
  const pivot=new THREE.Group();scene.add(pivot);
  let driver:ReturnType<typeof createZerefDriver>|null=null;
  (async()=>{
   const [{GLTFLoader},{MeshoptDecoder}]=await Promise.all([import('three/examples/jsm/loaders/GLTFLoader.js'),import('three/examples/jsm/libs/meshopt_decoder.module.js')]);
   const loader=new GLTFLoader();loader.setMeshoptDecoder(MeshoptDecoder);
   const gltf=await loader.loadAsync(ZEREF_GLB_URL);if(disposed)return;
   gltf.scene.traverse((o:any)=>{if(o.isMesh){o.frustumCulled=false;}});
   pivot.add(gltf.scene);driver=createZerefDriver(THREE,gltf.scene,{seed,mood:live.current.mood});
   el.dataset.zerefGlb='ready';
  })().catch(err=>{el.dataset.zerefGlb='error';console.warn('zeref glb',err);});
  const resize=()=>{const r=el.getBoundingClientRect();if(r.width<2)return;renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();};
  const ro=new ResizeObserver(resize);ro.observe(el);resize();
  let last=performance.now(),yaw=0;
  const tick=(now:number)=>{
   const dt=Math.min(.1,(now-last)/1000);last=now;const L=live.current;
   if(L.spin&&!reduced)yaw+=dt*.5;else yaw+=(THREE.MathUtils.degToRad(L.angle)-yaw)*Math.min(1,dt*6);
   pivot.rotation.y=-yaw;
   camera.position.set(0,.85,3.9);camera.lookAt(0,.68,0);
   if(driver){driver.setMood(L.mood);driver.update(reduced?0:dt);}
   renderer.render(scene,camera);raf=requestAnimationFrame(tick);
  };
  raf=requestAnimationFrame(tick);
  return ()=>{disposed=true;cancelAnimationFrame(raf);ro.disconnect();renderer.dispose();renderer.domElement.remove();};
 },[seed]);
 return <div ref={host} data-testid="zeref-glb-3d" style={{width:'100%',height:'100%',minHeight:360}} aria-label="Sculpted 3D Zeref, rotating"/>;
}
