'use client';
/**
 * Sculpted, rigged Zeref (public/creatures3d/zeref.glb) on a three.js stage. Spring bones,
 * breathing and expressions all run on the CST integrator via lib/creatures3d/zeref-glb-driver.mjs.
 * Shown on /beast-cage/turntable only behind ?glb=1 while Cory reviews it.
 */
import {useEffect,useRef} from 'react';
import * as THREE from 'three';
import {createZerefDriver,ZEREF_GLB_URL} from '@/lib/creatures3d/zeref-glb-driver.mjs';

export type ZerefMood='calm'|'happy'|'curious'|'scared'|'sleepy'|'angry'|'walk';
export default function ZerefGlb3D({spin=true,angle=0,mood='calm',seed='zeref'}:{spin?:boolean;angle?:number;mood?:ZerefMood;seed?:string}){
 const host=useRef<HTMLDivElement>(null);
 const live=useRef({spin,angle,mood});
 useEffect(()=>{live.current={spin,angle,mood};},[spin,angle,mood]);
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
  const starT={value:0};
  // review hooks (?glb=1&yaw=45&mood=happy) so renders and screenshots are reproducible
  const qp=new URLSearchParams(window.location.search);const qYaw=qp.get('yaw');const qMood=qp.get('mood');const qNoBlink=qp.get('blink')==='0';let gltf0:any=null;
  if(qYaw)live.current={...live.current,spin:false,angle:Number(qYaw)};
  let driver:ReturnType<typeof createZerefDriver>|null=null;
  (async()=>{
   const [{GLTFLoader},{MeshoptDecoder}]=await Promise.all([import('three/examples/jsm/loaders/GLTFLoader.js'),import('three/examples/jsm/libs/meshopt_decoder.module.js')]);
   const loader=new GLTFLoader();loader.setMeshoptDecoder(MeshoptDecoder);
   const gltf=await loader.loadAsync(ZEREF_GLB_URL);if(disposed)return;
   gltf.scene.traverse((o:any)=>{if(o.isMesh){o.frustumCulled=false;}});
   // ONE impossible detail: starlight lives inside him. The fur and eye emissive starfields drift and twinkle.
   const twinkle=(mat:any,drift:number)=>{mat.onBeforeCompile=(sh:any)=>{sh.uniforms.uStarT=starT;
    sh.fragmentShader='uniform float uStarT;\n'+sh.fragmentShader.replace('#include <emissivemap_fragment>',
    `#ifdef USE_EMISSIVEMAP
     vec2 suv=vEmissiveMapUv+vec2(uStarT*${drift.toFixed(4)},uStarT*${(drift*.6).toFixed(4)});
     vec4 se=texture2D(emissiveMap,suv);
     float cell=fract(sin(dot(floor(suv*48.),vec2(12.9898,78.233)))*43758.5453);
     totalEmissiveRadiance*=se.rgb*(.55+.45*sin(uStarT*(1.5+cell*3.)+cell*6.2831));
    #endif`);};mat.customProgramCacheKey=()=>'zeref-star-'+drift;mat.needsUpdate=true;};
   const furMeshes:any[]=[];
   gltf.scene.traverse((o:any)=>{if(o.isMesh&&o.material){const n=o.material.name;if(n==='zeref_fur'){twinkle(o.material,.004);furMeshes.push(o);}if(n==='zeref_eye')twinkle(o.material,0);}});
   // Directional shell fur combed down/back, skipping eyelids (uv.x<0). Drawn at runtime, outside the 25k-tri asset budget.
   const SH=qp.get('fur')==='0'?0:reduced||window.innerWidth<480?4:7;
   const strands=await new THREE.TextureLoader().loadAsync('/creatures3d/zeref-fur-strands.png');strands.wrapS=strands.wrapT=THREE.RepeatWrapping;strands.repeat.set(14,14);
   for(const fm of furMeshes)for(let k=1;k<=SH;k++){const t=k/SH;
    const m=new THREE.MeshStandardMaterial({vertexColors:true,roughness:.6,alphaMap:strands,alphaTest:.22+.72*t,color:new THREE.Color(1+.7*t,1+.7*t,1.15+.8*t),
     emissive:0xffffff,emissiveMap:fm.material.emissiveMap,emissiveIntensity:1.1});
    m.onBeforeCompile=(sh:any)=>{sh.vertexShader=sh.vertexShader.replace('#include <begin_vertex>',
     `#include <begin_vertex>
      float fmask=uv.x<0.?0.:1.;
      transformed+=(objectNormal*${(0.016*t).toFixed(5)}+vec3(0.,-1.,-.4)*${(0.013*t*t).toFixed(5)})*fmask;`);};
    m.customProgramCacheKey=()=>'zeref-shell-'+k+'-'+SH;
    const shell=new THREE.SkinnedMesh(fm.geometry,m);shell.bind(fm.skeleton,fm.bindMatrix);
    shell.morphTargetInfluences=fm.morphTargetInfluences;shell.morphTargetDictionary=fm.morphTargetDictionary;
    shell.position.copy(fm.position);shell.quaternion.copy(fm.quaternion);shell.scale.copy(fm.scale);shell.frustumCulled=false;fm.parent.add(shell);}
   gltf0=gltf;pivot.add(gltf.scene);driver=createZerefDriver(THREE,gltf.scene,{seed,mood:live.current.mood});
   el.dataset.zerefGlb='ready';
  })().catch(err=>{el.dataset.zerefGlb='error';console.warn('zeref glb',err);});
  const resize=()=>{const r=el.getBoundingClientRect();if(r.width<2)return;renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();};
  const ro=new ResizeObserver(resize);ro.observe(el);resize();
  let last=performance.now(),yaw=qYaw?THREE.MathUtils.degToRad(Number(qYaw)):0;
  (window as any).__zerefReview={setYaw:(d:number)=>{live.current={...live.current,spin:false,angle:d};yaw=THREE.MathUtils.degToRad(d);},
   morphs:()=>{const o:any={};gltf0?.scene.traverse((m:any)=>{if(m.morphTargetDictionary&&!o[m.name]){o[m.name]=Object.fromEntries(Object.entries(m.morphTargetDictionary).map(([k,i]:any)=>[k,+m.morphTargetInfluences[i].toFixed(2)]).filter(([,v])=>v));}});return o;}};
  const qManual=qp.get('manual')==='1';let manualDt=0,manualMood:any=null;
  (window as any).__zerefReview.step=(dt:number,mood?:string,yawDeg?:number)=>{manualDt=dt;if(mood)manualMood=mood;if(yawDeg!==undefined){live.current={...live.current,spin:false,angle:yawDeg};yaw=THREE.MathUtils.degToRad(yawDeg);}tick(0);return !!driver;};
  const tick=(now:number)=>{
   if(qManual&&now!==0){raf=requestAnimationFrame(tick);return;}
   const dt=qManual?manualDt:Math.min(.1,(now-last)/1000);last=now;const L=live.current;
   starT.value+=reduced?0:dt;
   if(L.spin&&!reduced)yaw+=dt*.5;else yaw+=(THREE.MathUtils.degToRad(L.angle)-yaw)*Math.min(1,dt*6);
   pivot.rotation.y=-yaw;
   camera.position.set(0,.85,3.9);camera.lookAt(0,.68,0);
   if(driver){driver.setMood((manualMood as ZerefMood)||(qMood as ZerefMood)||L.mood);driver.update(reduced?0:dt);if(qNoBlink)gltf0?.scene.traverse((m:any)=>{const i=m.morphTargetDictionary?.blink;if(i!==undefined)m.morphTargetInfluences[i]=0;});}
   renderer.render(scene,camera);if(!(qManual&&now===0))raf=requestAnimationFrame(tick);
  };
  raf=requestAnimationFrame(tick);
  return ()=>{disposed=true;cancelAnimationFrame(raf);ro.disconnect();renderer.dispose();renderer.domElement.remove();};
 },[seed]);
 return <div ref={host} data-testid="zeref-glb-3d" style={{width:'100%',height:'100%',minHeight:360}} aria-label="Sculpted 3D Zeref, rotating"/>;
}
