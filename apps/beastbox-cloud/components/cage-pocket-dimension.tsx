'use client';
import {flowStars,flowGrid} from '../lib/living-core/river-flow';
import {capScenePoints,pushCameraOut} from '../lib/living-core/near-lens';
import {buildWorlds} from '../lib/worlds/worlds';
import {buildTerrain} from '../lib/worlds/terrain';
import {buildIsland} from '../lib/geyser/island';
import {addGeyserEvents} from '../lib/geyser/events';
import {addIslandLife} from '../lib/geyser/life';
import {createGeyserSound} from '../lib/geyser/sound';
import {inBlock as gjInBlock,islandGround,GJ as GJ_ALL} from '../lib/geyser/geyser-math.mjs';
const GJ_V=GJ_ALL.volcano,GJ_G=GJ_ALL.geyser;
import {addHeaven,HEAVEN} from '../lib/worlds/heaven';
import {terrainHeight} from '../lib/worlds/terrain-math.mjs';
import {createCompanions} from '../lib/companions/companions';
import {createSensors,bodyDims,nervePaletteChoice} from '../lib/sensors/sensors';
import {neonPatch,neonUniforms,neonDistGain,makeFilaments} from '../lib/worlds/neon-wire';
import {createGravityCam} from '../lib/living-core/gravity-camera';
import {getLivingCore,stepLivingCore,livingCoreScale,fitLivingCoreParticles,LC_WORLD_H} from '../lib/living-core/core-cache';
import {attachSynapse,addRoamExtras,synapseClick} from '../lib/living-core/roam-extras';
import {nextGoal,UNIVERSE_R,rng as lcRng,SHAPES} from '../lib/living-core/roam-brain.mjs';
import {recordArrival} from '../lib/zeref/pocket-journal';
import {motionPersona,createActor,stepActor} from '../lib/companion/film-motion.mjs';
import {addGodView,ZOOM_MIN,ZOOM_LIMIT} from './pocket-god-view';
import {isPanGesture,panStep,decayPan,centroid,keyPanPixels,worldPerPixel} from '@/lib/universe/view-gestures.mjs';
import {ARTIST_RESIDENTS} from '../lib/companion/artist-residents.mjs';
import {MAX_SAVED_ROAMERS,homeLabel} from '../lib/companion/creations.mjs';
import {addSavedBeastSprites} from './pocket-saved-beasts';
import {useCreations,readCreations} from './use-creations';
import {useActiveBeastName} from './use-active-beast-name';
import CreationThumb from './creation-thumb';
import {addPocketResidents} from './pocket-residents';
import {addPocketSand} from './pocket-sand-layer';
import {SAND_LABEL} from '../lib/pocket-sand.mjs';
import {environmentWeights,isFresh} from '../lib/environment/environment-link.mjs';
import {getEnvironment} from '../lib/environment/environment-store.mjs';
import {guardCanvasTouch} from '../lib/three/touch-guard';
import {isSoftwareGL} from '../lib/three/soft-gl';
import {createHop,stepHop} from '../lib/physics/ground-hop.mjs';
import {useEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {createPocketSky,orbitPosition} from '../lib/pocket-sky.mjs';
import {DEFAULT_POCKET_3D,POCKET_3D_KEY,POCKET_3D_EVENT,POCKET_3D_CAMERA_RESET,devicePocket3D,deviceClassicPixel,saveClassicPixel} from '../lib/companion/pocket-3d-settings.mjs';
import styles from './cage-pocket-dimension.module.css';
import {addPocketLife,type Weather} from './pocket-life';
import {buildPlush,type PlushGenome} from './creature-plush-3d';
import {loadBeastGlb,GLB_PLANS} from './creature-glb-beast';
import {addPocketWorld} from './pocket-world';
import {createLife,stepLife,pokeLife} from '../lib/creatures3d/life-brain.mjs';
import {useCageCreature} from './use-cage-creature';
import {insideCreatureVisible} from '../lib/world/cage-creature.mjs';
type God={weather:(w:Weather)=>void;time:(t:number|null)=>void;treat:()=>void;flower:()=>void;poke:()=>void};
const WEATHERS:Weather[]=['auto','sun','rain','storm'];const WEATHER_ICON:Record<Weather,string>={auto:'✦',sun:'☀',rain:'☂',storm:'⚡'};
const TIMES:(number|null)[]=[null,0,.3,.5];const TIME_ICON=['◐','☀','🌇','☾'];

type View={theta:number;phi:number;zoom:number};
type Pointer={x:number;y:number};
type Props={
 seed:string|null; qbeastId:string|null; stage:number; reduced:boolean;
 behaviorPosition:{x:number;y:number}|null; state:string;
 onActiveChange:(active:boolean)=>void;
 qvmCounts?:Record<string,number>|null;
 /** Slow camera auto-orbit (home pocket). Drag still takes over; paused in reduced motion. */
 autoOrbit?:boolean;
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
export default function CagePocketDimension({seed,qbeastId,stage,reduced,behaviorPosition,state,onActiveChange,qvmCounts=null,autoOrbit=false,chatLine=null,menuHost=null,ignorePixel=false}:Props&{chatLine?:string|null;menuHost?:HTMLElement|null;ignorePixel?:boolean}){
 const [creatureOn]=useCageCreature();const creatureRef=useRef(creatureOn);creatureRef.current=creatureOn;
 const lcBus=useRef<any>(null);useEffect(()=>{if(chatLine)lcBus.current?.words(chatLine);},[chatLine]);
 const autoOrbitRef=useRef(autoOrbit);autoOrbitRef.current=autoOrbit;const lastDragAt=useRef(0);
 useEffect(()=>{if(autoOrbit)cameraView.current={...cameraView.current,zoom:8.5,phi:1.18};},[autoOrbit]);
 const sandSource=qvmCounts?'receipt':'seed';
 const canvasRef=useRef<HTMLCanvasElement>(null);
 const motion=useRef({position:behaviorPosition,state,stage,impulse:0});
 const cameraView=useRef<View>({theta:.7,phi:1.22,zoom:13.5});
 // Tap-a-creature: set once the scene exists; a tap (no drag) raycasts and focuses the camera on what it hits.
 const pickRef=useRef<((x:number,y:number)=>void)|null>(null);
 const [visualSettings,setVisualSettings]=useState<{enabled:boolean;quality:'auto'|'low'|'high';neonWire?:boolean}>({...DEFAULT_POCKET_3D});
 const neonOn=useRef(true);neonOn.current=visualSettings.neonWire!==false;
 useEffect(()=>{
  const sync=()=>setVisualSettings(devicePocket3D());
  const onStorage=(event:StorageEvent)=>{if(event.key===POCKET_3D_KEY)sync();};
  sync();window.addEventListener(POCKET_3D_EVENT,sync);window.addEventListener('storage',onStorage);
  return()=>{window.removeEventListener(POCKET_3D_EVENT,sync);window.removeEventListener('storage',onStorage);};
 },[]);
 const [ready,setReady]=useState(false),[failed,setFailed]=useState(false);
 // Living pocket: play-god toolbar + classic pixel toggle + collapsible info (LIVE feed framing).
 const godRef=useRef<God|null>(null);const [weatherI,setWeatherI]=useState(0),[timeI,setTimeI]=useState(0),[infoOpen,setInfoOpen]=useState(false);
 const [pixel,setPixel]=useState(false);const pixelRef=useRef(false);pixelRef.current=pixel;
 useEffect(()=>{const rd=()=>ignorePixel?false:deviceClassicPixel();setPixel(rd());const on=()=>setPixel(rd());window.addEventListener('beastbox:pixel-mode',on);return()=>window.removeEventListener('beastbox:pixel-mode',on);},[]);
 const togglePixel=()=>{const v=!pixel;setPixel(v);saveClassicPixel(v);window.dispatchEvent(new Event('beastbox:pixel-mode'));};
 const [residentsOpen,setResidentsOpen]=useState(true);
 const creations=useCreations();const homeName=useActiveBeastName();
 useEffect(()=>{if(window.matchMedia('(max-width:560px)').matches)setResidentsOpen(false);},[]);
 const id=qbeastId||'visual-preview';
 const key=seed||'beastbox-visual-preview';
 useEffect(()=>{motion.current.position=behaviorPosition;motion.current.state=state;motion.current.stage=stage;},[behaviorPosition?.x,behaviorPosition?.y,state,stage]);
 useEffect(()=>{onActiveChange(visualSettings.enabled&&ready&&!failed);return()=>onActiveChange(false);},[ready,failed,visualSettings.enabled,onActiveChange]);
 useEffect(()=>{
  const canvas=canvasRef.current;
  if(!canvas||failed||!visualSettings.enabled)return;
  let disposed=false,frame=0,cleanup=()=>{};
  // Cage habitat, or the home pocket art (home: the god view is driven from the whole pocket).
  const parent=canvas.closest('.cage-habitat-visual,.beast-landing-art') as HTMLElement|null;
  const activePointers=new Map<number,Pointer>();
  // shared camera pan (two-finger drag, right drag, Shift+drag, Shift+arrows): an offset on the look-at point, eased back whenever the camera focuses something
  let pan={x:0,y:0,z:0};const panBasis={rx:1,ry:0,rz:0,ux:0,uy:1,uz:0,k:.01};const panPtr=new Set<number>();const panBy=(dx:number,dy:number)=>{pan=panStep(pan,panBasis,dx,dy,cameraView.current.zoom*2+6);};(window as any).__pocketPan=()=>({...pan});
  let moved=false,suppressClick=false,pinching=false; // pinching: once two fingers are down, the gesture only zooms until every finger lifts
  const isControl=(target:EventTarget|null)=>target instanceof Element&&Boolean(
   target.closest('input,select,textarea,a,summary,[contenteditable="true"]')||
   target.closest('button:not([aria-label^="Tap "])')
  );
  const pointerDown=(event:PointerEvent)=>{
   if(isControl(event.target)||event.button!==0&&event.button!==2&&event.pointerType==='mouse')return;
   if(isPanGesture({button:event.pointerType==='mouse'?event.button:0,shiftKey:event.pointerType==='mouse'&&event.shiftKey}))panPtr.add(event.pointerId);
   activePointers.set(event.pointerId,{x:event.clientX,y:event.clientY});moved=false;if(activePointers.size>=2)pinching=true;
  };
  const pointerMove=(event:PointerEvent)=>{
   const prev=activePointers.get(event.pointerId);if(!prev)return;
   const dx=event.clientX-prev.x,dy=event.clientY-prev.y;
   if(Math.abs(dx)+Math.abs(dy)>3)moved=true;
   if(activePointers.size===1&&!pinching&&panPtr.has(event.pointerId)){panBy(dx,dy);lastDragAt.current=performance.now();}
   else if(activePointers.size===1&&!pinching){
    cameraView.current.theta-=dx*.009;lastDragAt.current=performance.now();
    cameraView.current.phi=clamp(cameraView.current.phi+dy*.008,.06,3.08);
   }else if(activePointers.size===2){
    const other=[...activePointers.entries()].find(([id])=>id!==event.pointerId)?.[1];
    if(other){
     const before=Math.hypot(prev.x-other.x,prev.y-other.y);
     const after=Math.hypot(event.clientX-other.x,event.clientY-other.y);
     if(before>18&&after>18)cameraView.current.zoom=clamp(cameraView.current.zoom*before/after,ZOOM_MIN,ZOOM_LIMIT);
     {const c0=centroid(prev,other),c1=centroid({x:event.clientX,y:event.clientY},other);panBy(c1.x-c0.x,c1.y-c0.y);lastDragAt.current=performance.now();}
    }
   }
   activePointers.set(event.pointerId,{x:event.clientX,y:event.clientY});
  };
  const pointerEnd=(event:PointerEvent)=>{
   const tap=activePointers.has(event.pointerId)&&!moved&&activePointers.size===1;
   if(activePointers.has(event.pointerId)&&moved)suppressClick=true;
   activePointers.delete(event.pointerId);panPtr.delete(event.pointerId);if(activePointers.size===0)pinching=false;
   if(tap)pickRef.current?.(event.clientX,event.clientY);
  };
  const clickCapture=(event:MouseEvent)=>{
   // A camera drag on the companion must not turn into an accidental attack.
   if(suppressClick&&!isControl(event.target)){
    event.preventDefault();event.stopImmediatePropagation();
   }
   suppressClick=false;
  };
  const wheel=(event:WheelEvent)=>{
   // desktop wheel zoom works over the creature and its tap target too; only real form fields keep the wheel
   if(event.target instanceof Element&&event.target.closest('input,select,textarea,[contenteditable="true"]'))return;
   event.preventDefault();
   cameraView.current.zoom=clamp(cameraView.current.zoom*Math.exp(event.deltaY*.0016),ZOOM_MIN,ZOOM_LIMIT);
  };
  const keyboard=(event:KeyboardEvent)=>{
   if(event.target!==parent||isControl(event.target))return;
   const kp=event.shiftKey?keyPanPixels(event.key):null;
   if(kp){event.preventDefault();panBy(kp[0],kp[1]);}
   else if(event.key==='ArrowLeft'||event.key==='ArrowRight'){
    event.preventDefault();cameraView.current.theta+=(event.key==='ArrowLeft'?.17:-.17);
   }else if(event.key==='ArrowUp'||event.key==='ArrowDown'){
    event.preventDefault();cameraView.current.phi=clamp(cameraView.current.phi+(event.key==='ArrowUp'?-.14:.14),.06,3.08);
   }else if(event.key==='+'||event.key==='='){
    event.preventDefault();cameraView.current.zoom=clamp(cameraView.current.zoom/1.3,ZOOM_MIN,ZOOM_LIMIT);
   }else if(event.key==='-'){
    event.preventDefault();cameraView.current.zoom=clamp(cameraView.current.zoom*1.3,ZOOM_MIN,ZOOM_LIMIT);
   }else if(event.key==='Home'){
    event.preventDefault();cameraView.current={theta:.7,phi:1.22,zoom:13.5};pan={x:0,y:0,z:0};
   }
  };
  // Existing sound-generator events: sound is a *visual stimulus*, not proof
  // of external microphone hearing or physical quantum/natural growth.
  const chirp=(e:Event)=>{const raw=Number((e as CustomEvent)?.detail?.intensity);motion.current.impulse=clamp(motion.current.impulse+(Number.isFinite(raw)?raw:.35)*.32,0,1.25);};
  const mute=()=>{motion.current.impulse=0;};
  const resetCamera=()=>{pan={x:0,y:0,z:0};cameraView.current={theta:.7,phi:1.22,zoom:13.5};pickRef.current?.(-1e6,-1e6);};
  const noMenu=(e:Event)=>{e.preventDefault();}; // right drag pans
  const option={passive:true} as AddEventListenerOptions;
  const unguard=parent?guardCanvasTouch(parent,{hint:parent.classList.contains('beast-landing-art')?'↔ Drag sideways to spin · swipe to scroll':'↔ Drag sideways to explore · pinch to zoom'}):()=>{};
  if(parent){
   parent.addEventListener('pointerdown',pointerDown,option);
   parent.addEventListener('pointermove',pointerMove,option);
   parent.addEventListener('pointerup',pointerEnd,option);
   parent.addEventListener('pointercancel',pointerEnd,option);
   parent.addEventListener('wheel',wheel,{passive:false});parent.addEventListener('contextmenu',noMenu);
   parent.addEventListener('keydown',keyboard);
   parent.addEventListener('click',clickCapture,true);
  }
  window.addEventListener('beastbox:spark-chirp',chirp);
  window.addEventListener('beastbox:spark-mute',mute);
  window.addEventListener(POCKET_3D_CAMERA_RESET,resetCamera);
  const releaseListeners=()=>{
   unguard();
   if(parent){
    parent.removeEventListener('pointerdown',pointerDown);
    parent.removeEventListener('pointermove',pointerMove);
    parent.removeEventListener('pointerup',pointerEnd);
    parent.removeEventListener('pointercancel',pointerEnd);
    parent.removeEventListener('wheel',wheel);parent.removeEventListener('contextmenu',noMenu);
    parent.removeEventListener('keydown',keyboard);
    parent.removeEventListener('click',clickCapture,true);
   }
   window.removeEventListener('beastbox:spark-chirp',chirp);
   window.removeEventListener('beastbox:spark-mute',mute);
   window.removeEventListener(POCKET_3D_CAMERA_RESET,resetCamera);
  };
  void(async()=>{
   try{
    if(!window.WebGLRenderingContext)throw Error('WebGL unavailable');
    // Home: let the 3D Zeref finish cutting his layers first (both share one main thread on phones / software GL).
    // The pocket's first frame links its shader programs synchronously; starting it while Zeref is still loading
    // starves his 9s fallback guard too, so neither ever settles on slow machines. His guard (main thread free while
    // we wait) always ends 'loading', so wait for that; the 60s cap is only a safety net.
    if(autoOrbitRef.current){const t0=performance.now();while(!disposed&&performance.now()-t0<60000&&document.querySelector('[data-zeref-sprite3d="loading"]'))await new Promise(r=>setTimeout(r,250));if(disposed)return;}
    const THREE=await import('three');
    if(disposed)return;
    // User quality never overrides the OS reduced-motion safety boundary.
    let low=reduced||visualSettings.quality==='low'||(visualSettings.quality==='auto'&&window.innerWidth<600);
    // Phones with a real GPU (iPhone etc.) are 'low' only for world density; they still get AA, a crisper ratio and the sculpted GLBs.
    // Probe for software GL (CI SwiftShader, GPU-less VMs) BEFORE creating the renderer: MSAA + a high pixel ratio on a
    // CPU rasteriser starves the main thread (taps, sound dock, game shell all time out), and antialias can't be undone later.
    const softProbe=isSoftwareGL();
    const phoneGpu=low&&!reduced&&!softProbe&&visualSettings.quality!=='low';
    const renderer=new THREE.WebGLRenderer({canvas,alpha:false,antialias:(!low||phoneGpu)&&!softProbe,powerPreference:phoneGpu?'default':'low-power'});
    renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,low?(phoneGpu?1.25:1):1.5));
    // Software GL (CI SwiftShader, very old phones): force the low tier so the main thread never starves.
    let soft=false;try{const gl=renderer.getContext();const dbg=gl.getExtension('WEBGL_debug_renderer_info');soft=!!dbg&&/swiftshader|llvmpipe|software/i.test(String(gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL)));}catch{}
    if(soft){low=true;renderer.setPixelRatio(1);if(cameraView.current.zoom===13.5)cameraView.current={theta:.7,phi:1.28,zoom:10.6};}// software GL keeps the classic framing (wider view = more fill on CPU rasterisers)
    const glbTier:'med'|'low'|null=soft?null:!low?'med':phoneGpu?'med':null;(window as any).__pocketGlbTier=glbTier;
    // Living-core bodies: real GPUs (incl. phones). Software GL keeps the classic pocket like the GLBs; ?livingcore=1 forces it for review.
    const lcForced=new URLSearchParams(location.search).get('livingcore')==='1';const lcBody=new URLSearchParams(location.search).get('lcbody')==='1';// ?lcbody=1 shows the living-core particle body instead of the original sculpt
    const lcOk=!reduced&&(!soft||lcForced);
    renderer.outputColorSpace=THREE.SRGBColorSpace;
    // Living Cosmos polish: filmic tone mapping for deeper, less flat contrast.
    renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=HEAVEN.exposure;
    const scene=new THREE.Scene();
    scene.background=new THREE.Color(0x05040f);
    scene.fog=new THREE.FogExp2(0x0d0a26,.017);
    const camera=new THREE.PerspectiveCamera(46,1,.1,30000);
    const hemi=new THREE.HemisphereLight(0x94d9ff,0x20113b,1.8);scene.add(hemi);
    const moonlight=new THREE.PointLight(0xa8eaff,24,12);
    moonlight.position.set(0,4,1);scene.add(moonlight);
    const glow=new THREE.PointLight(0xba82f4,13,11);glow.position.set(-2,2,-3);scene.add(glow);
    const heaven=addHeaven(THREE,scene,{low,rand:randomFor(key+':heaven'),far:soft?undefined:(()=>{const r=randomFor(key+':sun');const a=r()*6.283,el=.42+r()*.35;return {dir:[Math.cos(a)*Math.cos(el),Math.sin(el),Math.sin(a)*Math.cos(el)] as [number,number,number],dist:70};})()});// the user's heaven: warm divine light, endless depth, serene flow
    // Lost COSMOS look: dark cosmic sand floor instead of blue stone.
    const stone=new THREE.MeshStandardMaterial({color:0x1c1530,emissive:0x0a0618,roughness:1,metalness:.02});
    const floraMat=new THREE.MeshStandardMaterial({color:0x6fe7ff,emissive:0x2aa6d6,emissiveIntensity:.9,metalness:.3,roughness:.18,transparent:true,opacity:.9});
    const crystalMat=new THREE.MeshStandardMaterial({color:0xc6a2ff,emissive:0x7a4fe0,emissiveIntensity:.95,metalness:.3,roughness:.18,transparent:true,opacity:.92});
    const ground=new THREE.Mesh(new THREE.BoxGeometry(9.1,.22,9.1),stone);
    ground.position.y=-.17;scene.add(ground);
    // Feet on the world: a real downward raycast against the habitat floor (cached on a coarse grid; the floor is static).
    const gRay=new THREE.Raycaster(),gO=new THREE.Vector3(),gD=new THREE.Vector3(0,-1,0),gCache=new Map<number,number>();
    const groundAt=(x:number,z:number)=>{const k=Math.round(x*20)*4096+Math.round(z*20);let y=gCache.get(k);if(y===undefined){ground.updateMatrixWorld();gO.set(x,5,z);gRay.set(gO,gD);const h=gRay.intersectObject(ground,false)[0];y=h?h.point.y+.02:(gjInBlock(x,z)?islandGround(x,z):terrainHeight(x,z))+.02;gCache.set(k,y);}return y;};
    const flowU={uTime:{value:0}};// gentle river drift for stars + grid glow (look unchanged)
    const grid=new THREE.GridHelper(9,12,0x4983a4,0x284c74);
    grid.position.y=-.05;scene.add(grid);
    // Bigger universe: the same grid continues far out (same colours, even fainter) on a wide dark floor.
    const farGrid=new THREE.GridHelper(UNIVERSE_R*2.2,low?40:72,0x4983a4,0x284c74);farGrid.position.y=-.06;
    (farGrid.material as import('three').Material).transparent=true;(farGrid.material as import('three').Material).opacity=.05;scene.add(farGrid);
    const farFloor=new THREE.Mesh(new THREE.CircleGeometry(UNIVERSE_R*1.1,low?48:96),new THREE.MeshBasicMaterial({color:0x0b0820,transparent:true,opacity:.92,depthWrite:false}));farFloor.rotation.x=-Math.PI/2;farFloor.position.y=-.075;farFloor.renderOrder=-1;scene.add(farFloor);
    // Faded, not deleted: the grid now only whispers under the sand.
    (grid.material as import('three').Material).transparent=true;(grid.material as import('three').Material).opacity=.07;
    // Dimensional pocket: finite cubic world occupying only the circle.
    const bounds=new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.BoxGeometry(9.2,5.2,9.2)),
      new THREE.LineBasicMaterial({color:0x8f7ad8,transparent:true,opacity:.06}));
    bounds.position.y=2.45;scene.add(bounds);
    const seedRandom=randomFor(key),flora:import('three').Object3D[]=[];
    for(let i=0;i<(low?17:34);i++){
     const x=(seedRandom()-.5)*7.8,z=(seedRandom()-.5)*7.8;
     if(Math.hypot(x,z)<2.1)continue;// keep Zeref's walking patch clear
     const height=.24+seedRandom()*.76;
     if(i%4===0){
      const crystal=new THREE.Mesh(new THREE.OctahedronGeometry(.14+seedRandom()*.22,0),crystalMat);
      crystal.position.set(x,.3,z);scene.add(crystal);flora.push(crystal);
     }else{
      // Glowing crystal spire cluster (was a cone tree): 2-3 stretched shards per site.
      const cluster=new THREE.Group();cluster.position.set(x,0,z);
      for(let k=0;k<2+(i%2);k++){const r=.07+seedRandom()*.08;const shard=new THREE.Mesh(new THREE.OctahedronGeometry(1,0),k%2?crystalMat:floraMat);shard.scale.set(r,height*(.45+k*.18),r);shard.position.set((seedRandom()-.5)*.22,height*(.42+k*.12),(seedRandom()-.5)*.22);shard.rotation.set((seedRandom()-.5)*.5,seedRandom()*3,(seedRandom()-.5)*.5);cluster.add(shard);}
      scene.add(cluster);flora.push(cluster);
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
    for(let i=0;i<(low?140:320);i++){const a=seedRandom()*Math.PI*2,rr=5+Math.sqrt(seedRandom())*UNIVERSE_R;points.push(Math.cos(a)*rr,.5+seedRandom()*9,Math.sin(a)*rr);}// far stars over the wide universe
    starsGeom.setAttribute('position',new THREE.Float32BufferAttribute(points,3));
    const starMat=new THREE.PointsMaterial({color:0xb2dfff,size:.042,transparent:true,opacity:.75});
    flowStars(starMat,flowU);flowGrid(grid.material as import('three').Material,flowU);flowGrid(farGrid.material as import('three').Material,flowU);
    scene.add(new THREE.Points(starsGeom,starMat));
    // Living Cosmos depth polish (visual only): far star shell for parallax,
    // a soft portal rim at the pocket floor, and a nebula backdrop.
    const farGeom=new THREE.BufferGeometry(),far:number[]=[];
    for(let i=0;i<(low?70:180);i++){const t=seedRandom()*Math.PI*2,u=seedRandom()*.9+.05,r=26;far.push(Math.cos(t)*Math.sin(u*Math.PI)*r,Math.cos(u*Math.PI)*r*.6+6,Math.sin(t)*Math.sin(u*Math.PI)*r);}
    farGeom.setAttribute('position',new THREE.Float32BufferAttribute(far,3));
    scene.add(new THREE.Points(farGeom,new THREE.PointsMaterial({color:0xe6d9ff,size:.16,transparent:true,opacity:.55,fog:false,depthWrite:false})));
    const rim=new THREE.Mesh(new THREE.RingGeometry(4.25,4.75,low?48:96),new THREE.MeshBasicMaterial({color:0x7fe6ff,transparent:true,opacity:.22,blending:THREE.AdditiveBlending,depthWrite:false,side:THREE.DoubleSide}));
    rim.rotation.x=-Math.PI/2;rim.position.y=-.04;scene.add(rim);
    // Nebula shader adapted from Cory's "Genesis Engine: The Definitive Core" (createNebula: fbm noise,
    // additive, BackSide sphere) and tinted to the Lost COSMOS violet/cyan palette.
    const nebulaMat=new THREE.ShaderMaterial({transparent:true,side:THREE.BackSide,depthWrite:false,fog:false,blending:THREE.AdditiveBlending,
     uniforms:{time:{value:0},baseColor:{value:new THREE.Color(0x5b2fb0)},altColor:{value:new THREE.Color(0x1f8fb8)},noiseScale:{value:.09},density:{value:.85}},
     vertexShader:'varying vec3 vP;void main(){vP=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
     fragmentShader:'uniform float time;uniform vec3 baseColor;uniform vec3 altColor;uniform float noiseScale;uniform float density;varying vec3 vP;'+
      'float h(vec3 p){p=fract(p*.3183099+.1);p*=17.0;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}'+
      'float n(vec3 x){vec3 i=floor(x),f=fract(x);f=f*f*(3.0-2.0*f);return mix(mix(mix(h(i),h(i+vec3(1,0,0)),f.x),mix(h(i+vec3(0,1,0)),h(i+vec3(1,1,0)),f.x),f.y),mix(mix(h(i+vec3(0,0,1)),h(i+vec3(1,0,1)),f.x),mix(h(i+vec3(0,1,1)),h(i+vec3(1,1,1)),f.x),f.y),f.z);}'+
      'float fbm(vec3 p){float v=0.0,a=.5;for(int i=0;i<5;i++){v+=a*n(p);p*=2.02;a*=.5;}return v;}'+
      'void main(){vec3 p=vP*noiseScale+vec3(time*.015,0.0,time*.01);float f=fbm(p);float g=fbm(p*2.3+f);float m=smoothstep(.38,.9,f*.7+g*.5)*density;'+
      'vec3 c=mix(baseColor,altColor,smoothstep(.3,.8,g));gl_FragColor=vec4(c*m,m*.8);}'});
    const nebula=new THREE.Mesh(new THREE.SphereGeometry(30,low?24:40,low?12:24),nebulaMat);
    scene.add(nebula);
    // Cosmic dust (Lost COSMOS particles): additive motes drifting up through the pocket.
    const dustN=low?60:220,dustGeom=new THREE.BufferGeometry(),dust=new Float32Array(dustN*3);
    for(let i=0;i<dustN;i++){dust[i*3]=(seedRandom()-.5)*8.6;dust[i*3+1]=seedRandom()*4.8;dust[i*3+2]=(seedRandom()-.5)*8.6;}
    dustGeom.setAttribute('position',new THREE.BufferAttribute(dust,3));
    const dustPts=new THREE.Points(dustGeom,new THREE.PointsMaterial({color:0xd7b8ff,size:.07,transparent:true,opacity:.7,blending:THREE.AdditiveBlending,depthWrite:false}));
    scene.add(dustPts);
    // Shimmering fluid pool: a small cosmic spring off to one side of the creature.
    const poolMat=new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,uniforms:{time:{value:0}},
     vertexShader:'varying vec2 vU;void main(){vU=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
     fragmentShader:'uniform float time;varying vec2 vU;void main(){vec2 q=vU-.5;float r=length(q)*2.0;if(r>1.0)discard;float w=.5+.5*sin(r*18.0-time*2.2)*sin(atan(q.y,q.x)*3.0+time*.7);'+
      'vec3 c=mix(vec3(.12,.55,.85),vec3(.65,.4,1.0),w);gl_FragColor=vec4(c*(1.0-r*.7),(1.0-r)*.55+.08);}'});
    const pool=new THREE.Mesh(new THREE.CircleGeometry(1,low?32:64),poolMat);pool.rotation.x=-Math.PI/2;pool.position.set(2.15,-.03,-1.7);pool.scale.setScalar(.95);scene.add(pool);
    // Artist-drawn residents (separate creatures, never the active Beast) roam the pocket.
    const resi=addPocketResidents(THREE,scene,seedRandom,reduced,low,glbTier,groundAt,lcOk&&lcBody);const texCache=resi.texCache;
    // Every beast saved on this device roams here too (same list as the legend): see lib/companion/creations.mjs.
    const saved=addSavedBeastSprites(THREE,scene,readCreations().filter(c=>c.kind==='saved'&&c.genome).slice(0,low?4:MAX_SAVED_ROAMERS),reduced,groundAt);
    const stepResidents=(t:number,theta:number,cam?:{x:number;z:number},beast?:{x:number;z:number;moment?:string|null}|null)=>{resi.stepResidents(t,theta,cam,beast);saved.step(t,cam);};
    const disturbers=()=>[...resi.disturbers(),...saved.disturbers()];const pickables=()=>[...resi.pickables(),...saved.pickables()];
    // God view: habitat on a small planet, orbiting its suns, inside a galaxy (Genesis Engine, recoloured).
    const god=addGodView(THREE,scene,{rand:randomFor(key+':system'),low,counts:qvmCounts,stage:motion.current.stage||stage||1});
    const godFocus=new THREE.Vector3();
    // Home: the sprite-built 3D Zeref lives here, standing on the habitat floor (one world, one camera).
    const zHolder=new THREE.Group();zHolder.scale.setScalar(.45);zHolder.position.set(0,-.07,0);zHolder.rotation.y=.7;scene.add(zHolder);
    // Universe of worlds: home trees/clouds/sky dome/parallax haze + distant worlds with gravity wells; Zeref travels between them.
    const neonU=neonUniforms();const uw=buildWorlds(THREE,scene,{low,universe:UNIVERSE_R,neon:neonU});const land=(!soft||lcForced)?buildTerrain(THREE,scene,{low}):null;if(lcForced)(window as any).__lcLand=land;const gj=(!soft||lcForced)?buildIsland(THREE,scene,{low,open:true}):null;const gjEv=gj?addGeyserEvents(THREE,gj,{low}):null;const gjLife=gj&&gjEv?addIslandLife(THREE,gj,gjEv.puff,{low}):null;const gjSnd=gj?createGeyserSound():null;gjEv?.on(e=>{gjSnd?.event(e==='geyser-tap'?'':e);if(e==='tremor'||e==='erupt')gjLife?.scare();});gjLife?.on(e=>gjSnd?.event(e));if(lcForced){(window as any).__geyser=gj;(window as any).__geyserEv=gjEv;(window as any).__geyserLife=gjLife;}
    const onGj=(e:any)=>{const a=String(e?.detail?.action||'');if(a==='erupt')gjEv?.erupt();else if(a==='tremor')gjEv?.tremor();else if(a==='geyser')gjEv?.geyser();else if(a==='breach')gjLife?.breach();else if(a==='castoff')gjLife?.castoff();};window.addEventListener('beastbox:geyser',onGj);if(gj){(window as any).__geyserReady=true;window.dispatchEvent(new Event('beastbox:geyser-ready'));}
    // tap the geyser, volcano, whale or boat to trigger it (taps only; drags keep orbiting the camera)
    const gjRay=new THREE.Raycaster(),gjNdc=new THREE.Vector2();let gjDown:{x:number;y:number;t:number}|null=null;
    const gjPD=(e:PointerEvent)=>{gjDown={x:e.clientX,y:e.clientY,t:performance.now()};};
    const gjPU=(e:PointerEvent)=>{const d0=gjDown;gjDown=null;if(!gj||!d0||Math.hypot(e.clientX-d0.x,e.clientY-d0.y)>8||performance.now()-d0.t>450)return;const rc=renderer.domElement.getBoundingClientRect();gjNdc.set((e.clientX-rc.left)/rc.width*2-1,-(e.clientY-rc.top)/rc.height*2+1);gjRay.setFromCamera(gjNdc,camera);
      const objs=[...(gjEv?.pickables()||[]),...(gjLife?.pickables()||[]),gj.land];const hit=gjRay.intersectObjects(objs,false)[0];if(!hit)return;let n=hit.object.name;
      if(n==='gj-land'){const lp=gj.root.worldToLocal(hit.point.clone());n=Math.hypot(lp.x-GJ_V.x,lp.z-GJ_V.z)<GJ_V.r*.8?'gj-volcano':Math.hypot(lp.x-GJ_G.x,lp.z-GJ_G.z)<.45?'gj-geyser':'';}
      const act={'gj-geyser':'geyser','gj-volcano':'erupt','gj-whale':'breach','gj-boat':'castoff'}[n];if(act)window.dispatchEvent(new CustomEvent('beastbox:geyser',{detail:{action:act}}));};
    renderer.domElement.addEventListener('pointerdown',gjPD);renderer.domElement.addEventListener('pointerup',gjPU);// Geyser Jelly island diorama behind the cage
// software GL (CI) skips the big land; debug handle only with ?livingcore=1

    // grounding + contact shadow + jellyfish tail filaments (neon wire language)
    const shadowTex=(()=>{const c=document.createElement('canvas');c.width=c.height=64;const x=c.getContext('2d')!;const g=x.createRadialGradient(32,32,2,32,32,32);g.addColorStop(0,'rgba(0,0,0,.75)');g.addColorStop(1,'rgba(0,0,0,0)');x.fillStyle=g;x.fillRect(0,0,64,64);return new THREE.CanvasTexture(c);})();
    const contact=new THREE.Mesh(new THREE.CircleGeometry(.55,24),new THREE.MeshBasicMaterial({map:shadowTex,transparent:true,depthWrite:false,opacity:.5}));contact.name='contact-shadow';contact.renderOrder=1;scene.add(contact);
    const fil=makeFilaments(THREE,scene,{count:low?2:3,len:low?10:14});const _Y=new THREE.Vector3(0,1,0),_Z=new THREE.Vector3(0,0,1),_n=new THREE.Vector3(),_q=new THREE.Quaternion(),_q2=new THREE.Quaternion(),_e=new THREE.Euler(),_tip=new THREE.Vector3();let filK=0;
    // wireframe companion critters: one per creature, feeding on universe motes
    const comps=createCompanions(THREE,scene,{low});const compOwners:any[]=[];comps.onFeed((id:string,e:number)=>{uw.pulseNear({x:zHolder.position.x,y:zHolder.position.y,z:zHolder.position.z},Math.min(1,e*6));if(id==='zeref')lcS.syn?.kick(Math.min(1,e*4));extras.river.kick(e*2);});const nervePal=nervePaletteChoice();
    const sensors=createSensors(THREE,scene,{low,points:uw.sensorPoints(low?60:140)});
    if(lcForced){(window as any).__lcComps=comps;(window as any).__lcPlasma=uw;(window as any).__lcSensors=sensors;(window as any).__lcCamera=camera;}let uwPose:any=null;if(lcForced){(window as any).__lcWorlds=uw;(window as any).__lcTravel=(i:number)=>uw.startTrip(i,{x:zHolder.position.x,y:zHolder.position.y,z:zHolder.position.z});}
    // Film motion for Zeref (bb-7f9c2a03 persona: no recorded seed of his own here → id-only persona).
    const zActorNode=new THREE.Group();zHolder.add(zActorNode);
    const zActor=createActor(motionPersona({id:'bb-7f9c2a03'}),{x:-1.15,z:.75,radius:1.1,seed:'bb-7f9c2a03',universe:UNIVERSE_R});// offset so Zeref never stands inside the active Beast
    // ---- Oct 16 living-core: Zeref as the true-3D living-core body (same actor, same pocket look) + life layer on top.
    const lcId=qbeastId||'bb-deada969';const lcS:any={LC:null,syn:null,goal:null,pause:2,mood:'calm',ov:null,ovT:0,visits:{},r:lcRng(lcId+':roam')};
    const gcam=createGravityCam(THREE,{camera,scene,renderer,low:low||soft,dof:(!low&&!soft&&!phoneGpu)||(lcForced&&new URLSearchParams(location.search).get('dof')==='1')});let zr=0;
    const extras=addRoamExtras(THREE,scene,{beastId:lcId,low:low||soft,onDoing:(d:string)=>{lcS.doing=d;}});
    const lcWords=(text:string)=>{const w:any=extras.words(text);if(w.emotion){lcS.ov=w.emotion;lcS.ovT=5;}lcS.syn?.kick(.4+w.burst*.6);extras.river.kick(.5+w.burst*.5);extras.burst(zHolder.position.x,.5,zHolder.position.z);if(w.shape){extras.create(w.shape,zHolder.position.x+.3,zHolder.position.z+.3,'chat');comps.remnant({x:zHolder.position.x+.3,y:0,z:zHolder.position.z+.3});}comps.glyph({x:zHolder.position.x,y:.4,z:zHolder.position.z});
      sensors.flare('zeref',.8);sensors.signal('zeref',{x:zHolder.position.x,y:zHolder.position.y+.35,z:zHolder.position.z},.5+w.burst*.5,()=>{lcS.syn?.kick(.6);synapseClick(2,.4);extras.river.kick(.6);});};// words → light pulses → vibration
    lcBus.current={words:lcWords};if(lcForced)(window as any).__lcWords=lcWords;
    const onLcChat=(e:any)=>lcWords(String(e?.detail?.text||'hi'));const onLcLevel=(e:any)=>{const l=Number(e?.detail?.level)||0;if(l>.05)lcS.syn?.kick(Math.min(.5,l*.6));};const onLcChirp=(e:any)=>lcS.syn?.kick(.25*(Number(e?.detail?.intensity)||.5));
    const onLcTap=()=>{lcS.syn?.kick(.9);extras.river.kick(.4);lcS.ov=lcS.ov||'happy';lcS.ovT=Math.max(lcS.ovT,2);};
    window.addEventListener('beastbox:beast-chat',onLcChat);window.addEventListener('beastbox:local-sensor-level',onLcLevel);window.addEventListener('beastbox:spark-chirp',onLcChirp);renderer.domElement.addEventListener('pointerdown',onLcTap);
    if(lcOk)void getLivingCore(THREE,'zeref',low).then(({LC})=>{if(disposed)return;const g=new THREE.Group();const k=livingCoreScale(LC,LC_WORLD_H*1.1/.45);g.scale.setScalar(k);fitLivingCoreParticles(LC,k*.45,renderer.domElement.height);g.position.y=-LC.footY*k;g.add(LC.group);zActorNode.add(g);lcS.LC=LC;lcS.g=g;if(lcForced)(window as any).__lcPocket={lcS,zHolder,zActorNode,camera};// capture hook only with ?livingcore=1
     lcS.syn=attachSynapse(THREE,LC,lcId,low);lcS.syn.onFire((c:number)=>{synapseClick(c,.35);});}).catch(()=>{});
    if(typeof window!=='undefined')(window as any).__pocketCamera=cameraView;
    const sand=addPocketSand(THREE,scene,{seed:key,low,reduced});
    sand.field.setCounts(qvmCounts);
    let envSig=-1;// consent-based environment numbers tilt the same wells (see lib/environment)
    // ---- LIVING POCKET (CST-driven world) + the Beast as a plush 3D creature living its own life
    const life=addPocketLife(THREE,scene,{seed:key,low,reduced,counts:qvmCounts,hemi,soft});
    // Software GL (CI SwiftShader, GPU-less VMs): the terrain/ocean/nebula-sky shaders take tens of seconds to link there and
    // starve the main thread, so the classic pocket stays and the world layer is skipped. Real GPUs (incl. phones) keep it.
    const world=soft?{update:(..._a:any[])=>{},dispose:()=>{}}:addPocketWorld(THREE,scene,{seed:key,low});
    const brain:any=createLife(key,{x:.8,z:.6} as any);const shelterAt=flora[0]?{x:flora[0].position.x*.8,z:flora[0].position.z*.8}:{x:2,z:-1.4};
    let plush:ReturnType<typeof buildPlush>|null=null;let beastFoot=0;const hop=createHop(key);const beastNode=new THREE.Group();beastNode.name='beast-3d';scene.add(beastNode);
    const syncPlush=()=>{const gen=(window as any).__beastGenome as PlushGenome|null;const want=!!gen&&!pixelRef.current;
     if(plush&&(!want||plush.root.userData.seed!==gen?.seed)){beastNode.remove(plush.root);plush.dispose();plush=null;}
     if(want&&!plush&&gen){plush=buildPlush(THREE,gen,{low});plush.root.userData.seed=gen.seed;plush.root.scale.setScalar(.5);beastNode.add(plush.root);
      // Zeref-pipeline sculpted GLB replaces the plush when available (plush stays as low tier / fallback while loading or on failure)
      if((glbTier||new URLSearchParams(location.search).get('beastglb')==='1')&&GLB_PLANS.includes(gen.body)){const mine=plush;loadBeastGlb(THREE,gen,{tier:glbTier||'med'}).then(gb=>{
        if(!gb||disposed||plush!==mine){gb?.dispose();return;}gb.root.scale.setScalar(.44);mine.root.visible=false;beastNode.add(gb.root);beastNode.updateMatrixWorld(true);{const bb=new THREE.Box3().setFromObject(gb.root);beastFoot=beastNode.position.y-bb.min.y;}
        const pd=mine.drive,pdis=mine.dispose;const lp=new THREE.Vector3();
        (mine as any).drive=(dt:number,b:any,mp:any,look:any)=>{let ll=null;if(look){lp.set(look.x,look.y,look.z);gb.root.worldToLocal(lp);ll={yaw:Math.atan2(lp.x,lp.z),pitch:Math.atan2(lp.y-.6,Math.hypot(lp.x,lp.z))};}gb.drive(dt,b,mp,ll);};
        (mine as any).dispose=()=>{beastNode.remove(gb.root);gb.dispose();pdis();};(mine as any).tris=gb.tris;void pd;}).catch(()=>{});}}
     if(plush)document.documentElement.setAttribute('data-beast-3d','');else document.documentElement.removeAttribute('data-beast-3d');};
    syncPlush();window.addEventListener('beastbox:genome',syncPlush);window.addEventListener('beastbox:pixel-mode',syncPlush);
    if(new URLSearchParams(location.search).get('qa')==='1')(window as any).__pocketQA={brain,life};// QA captures only: force a life mode
    const lifeRand=randomFor(key+':god');const camXZ=()=>({x:camera.position.x,z:camera.position.z});
    const near=(r:number)=>{const a=brain.heading+(lifeRand()-.5)*1.6,d=.9+lifeRand()*r;let x=brain.x+Math.cos(a)*d,z=brain.z+Math.sin(a)*d;const m=Math.hypot(x,z);if(m>4){x*=4/m;z*=4/m;}return {x,z};};
    const pokeBeast=()=>{const mood=life.update(0,null,null).mood;pokeLife(brain,mood as any,camXZ() as any);life.poke(brain.x,brain.z);};
    godRef.current={weather:w=>life.setWeather(w),time:t=>life.setTime(t),treat:()=>{const p=near(1.2);life.dropTreat(p.x,p.z);},flower:()=>{const p=near(1.5);life.plantFlower(p.x,p.z);},poke:pokeBeast};
    const onTalk=(e:Event)=>{const raw=Number((e as CustomEvent)?.detail?.intensity);life.talk(Number.isFinite(raw)?raw:.4);if(brain.mode!=='nap'&&brain.mode!=='shelter'){brain.mode='glance';brain.timer=1.6;}};
    window.addEventListener('beastbox:spark-chirp',onTalk);
    let attn:{x:number;y:number;z:number}|null=null;
    const resize=()=>{
     if(disposed)return;
     const rect=canvas.getBoundingClientRect();
     if(rect.width<2||rect.height<2)return;
     renderer.setSize(Math.floor(rect.width),Math.floor(rect.height),false);
     camera.aspect=rect.width/rect.height;camera.updateProjectionMatrix();gcam.resize(Math.floor(rect.width),Math.floor(rect.height));
    };
    const ro=typeof ResizeObserver!=='undefined'?new ResizeObserver(resize):null;
    ro?.observe(canvas);resize();
    let visible=true,last=performance.now(),elapsed=0,lastPaint=0,rendered=false;
    const io=typeof IntersectionObserver!=='undefined'?new IntersectionObserver(entries=>visible=entries.some(e=>e.isIntersecting),{threshold:.01}):null;
    io?.observe(canvas);
    const onContextLost=(e:Event)=>{e.preventDefault();setReady(false);setFailed(true);};
    canvas.addEventListener('webglcontextlost',onContextLost);
    const focus=new THREE.Vector3(0,.85,0),homeFocus=new THREE.Vector3(0,.85,0);
    // Tap-a-creature focus: the camera eases onto the tapped creature and follows it; tap empty space to let go.
    let focused:{id:string;obj:import('three').Object3D}|null=null;const ray=new THREE.Raycaster(),ndc=new THREE.Vector2(),tgt=new THREE.Vector3();
    pickRef.current=(cx,cy)=>{
     const rect=canvas.getBoundingClientRect();if(cx<rect.left||cx>rect.right||cy<rect.top||cy>rect.bottom){focused=null;(window as any).__pocketFocus={id:null};return;}
     ndc.set((cx-rect.left)/rect.width*2-1,-((cy-rect.top)/rect.height*2-1));ray.setFromCamera(ndc,camera);
     const list:{id:string;obj:import('three').Object3D}[]=[...pickables()];if(plush&&beastNode.visible)list.push({id:'beast',obj:plush.root});const ze=(window as any).__zerefEmbed;if(insideCreatureVisible(creatureRef.current)&&ze?.claimed&&ze.root)list.push({id:'zeref',obj:ze.root});
     let best:{id:string;obj:import('three').Object3D}|null=null,bestD=Infinity;
     for(const c of list){if(!c.obj.visible&&c.id!=='zeref')continue;const h=ray.intersectObject(c.obj,true)[0];if(h&&h.distance<bestD){bestD=h.distance;best=c;}}
     if(!best){
      // forgiving finger: nearest creature to the ray within ~0.6 world units
      for(const c of list){c.obj.getWorldPosition(tgt);const d=ray.ray.distanceToPoint(tgt);if(d<.6&&d<bestD){bestD=d;best=c;}}
     }
     window.dispatchEvent(new CustomEvent('beastbox:look-closer',{detail:{id:best?.id??null}}));
     if(best?.id==='beast'){pokeBeast();return;}
     focused=best;if(best)cameraView.current.zoom=Math.min(cameraView.current.zoom,4.6);
     (window as any).__pocketFocus={id:best?.id??null};
    };
    (window as any).__pocketFocus={id:null};
    // Test/QA hook: where each tappable creature currently is on screen (client px).
    (window as any).__pocketTargets=()=>{const rect=canvas.getBoundingClientRect();return pickables().map(c=>{c.obj.getWorldPosition(tgt);tgt.y+=.25;tgt.project(camera);return {id:c.id,x:rect.left+(tgt.x+1)/2*rect.width,y:rect.top+(1-tgt.y)/2*rect.height,on:tgt.z<1&&Math.abs(tgt.x)<.95&&Math.abs(tgt.y)<.95};});};
    const animate=(now:number)=>{
     if(disposed)return;
     frame=requestAnimationFrame(animate);
     const dt=clamp((now-last)/1000,0,.06);last=now;
     if(document.hidden||(!visible&&rendered)||now-lastPaint<(soft?120:low?66:33))return;
     lastPaint=now;beastNode.visible=insideCreatureVisible(creatureRef.current);
     if(!reduced)elapsed+=dt;
     nebulaMat.uniforms.time.value=elapsed;poolMat.uniforms.time.value=elapsed;
     if(!reduced){for(let i=0;i<dustN;i++){let y=dust[i*3+1]+dt*(.12+(i%5)*.03);if(y>4.8)y=0;dust[i*3+1]=y;dust[i*3]+=Math.sin(elapsed*.4+i)*dt*.05;}dustGeom.attributes.position.needsUpdate=true;}
     if(autoOrbitRef.current&&!reduced&&now-lastDragAt.current>2500)cameraView.current.theta+=dt*.09*HEAVEN.orbit;
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
     stepResidents(elapsed,v.theta,{x:camera.position.x,z:camera.position.z},plush?{x:brain.x,z:brain.z,moment:brain.moment}:null);
     {const E=getEnvironment(),live=E.consent&&isFresh(E.numbers,E.measuredAtMs,Date.now()),sig=live?E.version:-1;if(sig!==envSig){envSig=sig;sand.field.setEnvironment(live?environmentWeights(sand.field.counts,E.numbers):null);}}
     sand.update(dt,[{x:glow.position.x,z:glow.position.z,r:1.2,s:1.6+motion.current.impulse*3},{x:0,z:0,r:1.1,s:1.2},...disturbers()]);
     const ze=(window as any).__zerefEmbed;
     if(ze?.root&&ze.root.parent!==zActorNode){zActorNode.add(ze.root);ze.root.position.y=1.68;ze.claimed=true;}
     // cute & creepy again: Zeref's original sculpted body is the one you see; the living core keeps running underneath (brain, roam, hidden nerves) and only shows as a fallback or with ?livingcore=1
     if(lcS.LC&&lcS.g){const orig=!!ze?.root&&!lcBody;lcS.g.visible=!orig;if(ze?.root)ze.root.visible=orig;}
     if(lcS.LC){// roam brain: favorite spots / mini libraries / free wander; arrival = learn + make a CST construct
      const mood=lcS.ov||(state==='sleeping'?'sleepy':'calm');if(lcS.ovT>0){lcS.ovT-=dt;if(lcS.ovT<=0)lcS.ov=null;}
      if(lcS.mood!==mood){lcS.mood=mood;lcS.LC.setEmotion?.(mood);lcS.syn?.setEmotion(mood);}
      if(!lcS.goal){lcS.pause-=dt;if(lcS.pause<=0){let g:any=nextGoal(lcS.r,mood,lcS.visits);const others=(window as any).__lcResidents as any[]|undefined;if(others?.length&&lcS.r()<.25){const o=others[Math.floor(lcS.r()*others.length)];g={id:'visit-'+o.r.id,kind:'favorite',x:o.x+.6,z:o.z+.6};}lcS.goal=g.kind==='wander'?g:extras.spots.find((s:any)=>s.id===g.id)||g;(zActor as any).target={x:lcS.goal.x,z:lcS.goal.z};}}
      else if(Math.hypot(zHolder.position.x-lcS.goal.x,zHolder.position.z-lcS.goal.z)<.35){const g=lcS.goal;lcS.goal=null;lcS.visits[g.id]=(lcS.visits[g.id]||0)+1;lcS.pause=g.kind==='library'?4:2.5;
       if(g.kind==='library'){lcS.ov='curious';lcS.ovT=4;lcS.syn?.kick(.7);try{recordArrival(lcId,'library:'+g.topic);}catch{}const sh=SHAPES[(lcS.visits[g.id]+g.topic.length)%SHAPES.length];setTimeout(()=>{if(!disposed)extras.create(sh,g.x+.25,g.z+.25,'library:'+g.topic);},2200);}
       else if(g.id!=='wander'){try{recordArrival(lcId,g.id);}catch{}}}
      if(lcS.goal)(zActor as any).target={x:lcS.goal.x,z:lcS.goal.z};
      stepLivingCore(lcS.LC,reduced?0:dt);lcS.syn?.step(reduced?0:dt);}
     flowU.uTime.value+=reduced?0:dt*HEAVEN.flow;heaven.update(elapsed);
     land?.update(elapsed,camera);gj?.update(reduced?0:dt,elapsed);gjEv?.update(reduced?0:dt,elapsed);gjLife?.update(reduced?0:dt,elapsed);uwPose=uw.update(reduced?0:dt,elapsed,camera,{x:zHolder.position.x,y:zHolder.position.y,z:zHolder.position.z},!reduced&&!!(ze?.claimed||lcS.LC));
     extras.step(reduced?0:dt*HEAVEN.flow,{x:zHolder.position.x,z:zHolder.position.z});
     if(ze?.claimed||lcS.LC){
      const zp=stepActor(zActor,reduced?0:dt,{lookAt:{x:camera.position.x,z:camera.position.z},reduced});
      zHolder.position.set(zp.x,-.07+zp.lift,zp.z);zHolder.rotation.y=.7+zp.heading*.5+zp.head;
      if(uwPose)zHolder.position.set(uwPose.pos.x,uwPose.pos.y,uwPose.pos.z);
      {const yaw=zHolder.rotation.y;const airT=uwPose&&(uwPose.phase==='go'||uwPose.phase==='back')?1:0;lcS.air=(lcS.air??0)+(airT-(lcS.air??0))*Math.min(1,dt*2.5);const air=lcS.air;
       const g=uwPose&&uwPose.phase==='stay'?{y:0,n:uwPose.n,kind:'world'}:uw.ground({x:zHolder.position.x,y:zHolder.position.y+.25,z:zHolder.position.z});
       if(!uwPose&&g.kind!=='floor'&&air<.5)zHolder.position.y=g.y;// foot plant on island tops / tree limbs
       _n.set(g.n.x,g.n.y,g.n.z).normalize();_q.setFromUnitVectors(_Y,_n);// up vector = surface normal (walks on curved worlds)
       _e.set(Math.sin(elapsed*2.1)*.22*air,yaw,Math.sin(elapsed*1.6+1)*.18*air);_q2.setFromEuler(_e);zHolder.quaternion.copy(_q).multiply(_q2);// swim roll/pitch when airborne
       const gy=uwPose&&uwPose.phase==='stay'?null:(g.kind==='world'?null:g.y);const gap=gy===null?0:Math.max(0,zHolder.position.y-gy);
       if(gy===null)contact.position.copy(zHolder.position).addScaledVector(_n,.012);else contact.position.set(zHolder.position.x,gy+.012,zHolder.position.z);
       contact.quaternion.setFromUnitVectors(_Z,_n);(contact.material as any).opacity=.5*Math.max(0,1-gap/2.5);contact.scale.setScalar(1+gap*.25);
       const tp=(filK++%2===0)&&lcS.LC?.tailProbe?.();if(tp?.tip)_tip.fromArray(tp.tip);else if(filK<3)_tip.copy(zHolder.position);
       fil.step(_tip,elapsed,air,neonOn.current&&!!lcS.LC,reduced?0:dt);}
      zActorNode.scale.set(zp.sx,zp.sy,zp.sx);zActorNode.rotation.x=zp.lean;if(ze){ze.motion={tail:zp.tail,ear:zp.ear};
      let d=-(v.theta-zHolder.rotation.y)*180/Math.PI;d=((d%360)+540)%360-180;ze.viewYaw=d;}}
     // living pocket step: CST world → life brain → plush rig
     {const cp=plush?{x:brain.x,y:.45,z:brain.z}:null;const L=life.update(reduced?0:dt,cp,plush?attn:null);world.update(reduced?0:dt,L.env,L.cst.ch,camera.position);
      if(plush){stepLife(brain,reduced?0:dt,{...L.env,universe:UNIVERSE_R,mood:L.mood,cam:camXZ(),residents:disturbers(),shelter:shelterAt,onEat:(id:string)=>life.eat(id)});
       attn=brain.attn?{x:brain.attn.x,y:brain.attn.y,z:brain.attn.z}:null;
       {const hp=stepHop(hop,reduced?0:dt,{mode:brain.mode,speed:brain.speed,startle:brain.startle||0,mp:L.mp,scale:1.3,groundY:groundAt(brain.x,brain.z)});const sq=hp.squash;
        beastNode.position.set(brain.x,hp.y+beastFoot,brain.z);beastNode.scale.set(1-sq*.5,1+sq,1-sq*.5);(brain as any).air=hp.air;
        if(brain.moment==='splash')life.splashStep(brain.x,brain.z,brain.speed,reduced?0:dt);if(hp.air===false&&(brain as any).wasAir&&brain.inPuddle)life.splash(brain.x,brain.z,1.4);(brain as any).wasAir=hp.air;}beastNode.rotation.y=Math.PI/2-brain.heading;
       plush.drive(reduced?0:dt,brain,L.mp,brain.lookCam>.3?{x:camera.position.x,y:camera.position.y,z:camera.position.z}:attn);
       // observer camera: a gentle side/away drift that keeps the Beast framed, never forced into its face
       if(!autoOrbitRef.current&&!focused&&!reduced&&now-lastDragAt.current>1500){const want=-brain.heading+Math.PI/2+.5*Math.PI+(brain.lookCam>.5?Math.PI*.35:0);
        let dth=((want-v.theta)%(Math.PI*2)+Math.PI*3)%(Math.PI*2)-Math.PI;v.theta+=dth*Math.min(1,dt*.45);v.zoom+=(9.4-v.zoom)*Math.min(1,dt*.6);v.phi+=(1.36-v.phi)*Math.min(1,dt*.6);
        homeFocus.set(brain.x*.6,1.05,brain.z*.6);/* lower + pulled back so the pocket world shows behind the Beast */}else homeFocus.set(0,.85,0);
       (window as any).__beastLife={moment:brain.moment??null,y:+beastNode.position.y.toFixed(3),ground:+groundAt(brain.x,brain.z).toFixed(3),air:!!(brain as any).air,mode:brain.mode,x:brain.x,z:brain.z,attn:brain.attn?.kind??null,weather:life.getWeather(),coherence:L.cst.ch.coherence,chaos:L.cst.ch.chaos,hebb:L.cst.hebb,rain:L.env.rain,night:L.env.night,tris:plush.tris};}}
     {zr=Math.hypot(zHolder.position.x,zHolder.position.z);const capZ=lcForced&&(window as any).__lcFocusZeref;const pull=focused?0:capZ||(lcS.camEase??0)>.05?Math.max(capZ?1:0,lcS.camEase??0):(now-lastDragAt.current>2500?Math.min(1,Math.max(0,(zr-3)/4)):0);
      homeFocus.copy(gcam.focus(reduced?0:dt,homeFocus,{x:zHolder.position.x,z:zHolder.position.z},extras.spots,pull));}
     if(uwPose&&!focused)homeFocus.set(zHolder.position.x,zHolder.position.y+.6,zHolder.position.z);// camera rides the gravity tunnel with Zeref// gravity-well follow across the universe
     {const fp=lcForced&&(window as any).__lcFocusPoint;if(fp&&!focused)homeFocus.set(fp.x,fp.y,fp.z);}// capture hook only with ?livingcore=1
     if(focused){focused.obj.getWorldPosition(tgt);tgt.y+=.35;focus.lerp(tgt,Math.min(1,dt*4));}else focus.lerp(homeFocus,Math.min(1,dt*3));
     const f0=god.update(elapsed,v.zoom,focus,godFocus);const f=new THREE.Vector3(f0.x,f0.y,f0.z);if(focused||uwPose)pan=decayPan(pan,reduced?1:dt);f.x+=pan.x;f.y+=pan.y;f.z+=pan.z;
     (scene.fog as import('three').FogExp2).density=.012*Math.min(1.6,12/v.zoom)*(uwPose?.45:1);// cage-purple fog, tuned for the expanded universe
     const lens=gcam.lens(reduced?0:dt,v.zoom,zr,reduced?0:Math.min(1,(lcS.LC?.__surf?.U.uFlowA.value||0)*.5));let zd=lens.zoom;camera.fov=lens.fov;
     {// hidden nervous system: felt, not seen. Signal level drives core pulse, surface-life flow and mood/roam (no overlay, no dim, no camera move)
      const tf=sensors.topFlare();const fz=sensors.flareLevel('zeref');lcS.nerveF=(lcS.nerveF??0)+(fz-(lcS.nerveF??0))*Math.min(1,dt*2);
      if(!reduced&&lcS.nerveF>.08){lcS.syn?.kick(Math.min(.25,lcS.nerveF*dt*3));const U=lcS.LC?.__surf?.U;if(U?.uFlowA)U.uFlowA.value=Math.min(1.5,U.uFlowA.value+lcS.nerveF*dt*.6);}
      if(tf&&tf.id==='zeref'&&tf.f>.7&&!lcS.ov){lcS.ov='curious';lcS.ovT=1.5;if(lcS.goal==null)lcS.pause=Math.min(lcS.pause??2,.4);}
      sensors.hush(null,0);}
     camera.near=Math.max(.05,zd*.01);camera.far=Math.max(30000,zd*5);camera.updateProjectionMatrix();{const e=camera.matrixWorld.elements;panBasis.rx=e[0];panBasis.ry=e[1];panBasis.rz=e[2];panBasis.ux=e[4];panBasis.uy=e[5];panBasis.uz=e[6];panBasis.k=worldPerPixel(camera.fov,zd,Math.max(1,canvas.clientHeight||600));}
     camera.position.set(f.x+zd*Math.sin(v.phi)*Math.sin(v.theta),f.y+zd*Math.cos(v.phi),f.z+zd*Math.sin(v.phi)*Math.cos(v.theta));{const bods:any[]=[{x:zHolder.position.x,y:zHolder.position.y+.3,z:zHolder.position.z,r:.4},{x:beastNode.position.x,y:beastNode.position.y+.3,z:beastNode.position.z,r:.45}];for(const r of ((window as any).__lcResidents||[]))bods.push({x:r.x,y:.35,z:r.z,r:.4});for(const b of uw.bodies())bods.push(b);
      if(pushCameraOut(camera.position,bods)>0)camera.lookAt(f);}// creatures can never get inside the lens
     if(elapsed-((camera as any).__capT||-9)>1){(camera as any).__capT=elapsed;capScenePoints(scene);
      const lcs=[lcS.LC,...(((window as any).__lcResidents||[]).map((r:any)=>r.slot?.lc))];for(const L of lcs)L?.group?.traverse((o:any)=>{const m=o.material;if(o.isMesh&&m&&(m.isMeshStandardMaterial||m.isMeshPhysicalMaterial))neonPatch(m,neonU,{mode:'body',freq:11,amt:.35});});}
     {compOwners.length=0;if(lcS.LC||ze?.claimed)compOwners.push({id:'zeref',x:zHolder.position.x,y:zHolder.position.y,z:zHolder.position.z,air:lcS.air||0});
      if(plush)compOwners.push({id:key,x:brain.x,y:-.05,z:brain.z});if(lcForced&&Array.isArray((window as any).__lcCompShow))(window as any).__lcCompShow.forEach((id:string,i:number)=>compOwners.push({id,x:zHolder.position.x+(i-2.5)*.35,y:-.05,z:zHolder.position.z+.5}));
      for(const r of ((window as any).__lcResidents||[]))if(r?.r?.id)compOwners.push({id:r.r.id,x:r.x,y:-.05,z:r.z});
      if(elapsed-((comps as any).__syncT??-9)>1){(comps as any).__syncT=elapsed;comps.sync(compOwners);}comps.step(reduced?0:dt,elapsed,compOwners,(p:any)=>uw.ground(p));}
     {const fl=uw.flash();renderer.toneMappingExposure=HEAVEN.exposure+fl*2.2;const inv=fl>.55;if(inv!==(renderer.domElement as any).__inv){(renderer.domElement as any).__inv=inv;renderer.domElement.style.filter=inv?'invert(1) hue-rotate(180deg)':'';}
      nebula.rotation.y+=(reduced?0:dt)*(.01+fl*2.5+(uwPose?.06:0));}// tunneling flash + inversion, nebula swirl reacts
     if(elapsed-((sensors as any).__attT??-9)>1){(sensors as any).__attT=elapsed;const att=(id:string,L:any)=>{if(!L||sensors.nerves.has(id))return;const d=bodyDims(L);if(d){sensors.attach(id,d.host,d.dims,nervePal);}};const sz=renderer.getDrawingBufferSize(new THREE.Vector2());sensors.setResolution(sz.x,sz.y);att('zeref',lcS.LC);for(const r of ((window as any).__lcResidents||[]))if(r?.r?.id)att(r.r.id,r.slot?.lc);}
     {const emo:Record<string,number>={zeref:lcS.ovT>0?1:0};if(!reduced)sensors.update(dt,elapsed,emo);if(((sensors as any).__k=((sensors as any).__k||0)+1)%6===0)for(const c of comps.list.values())sensors.stimulate({x:c.x,y:c.y,z:c.z},.9,.5);}
     neonU.uNeon.value=neonOn.current?1:0;neonU.uNeonDist.value=neonDistGain(camera.position.distanceTo(zHolder.position));// farther = brighter wire network
     gcam.step(reduced?0:dt);
     camera.lookAt(f);
     try{gcam.render(camera.position.distanceTo(zHolder.position));}catch{setReady(false);setFailed(true);return;}
     if(!rendered){rendered=true;setReady(true);}
    };
    // Link every shader program off the main thread before the first frame where the browser can (KHR_parallel_shader_compile):
    // a synchronous first-frame link of the whole pocket takes many seconds on software GL / weak GPUs and freezes the page
    // (taps, Zeref, the rest of the UI). Bounded so a driver that never reports completion still starts.
    if(renderer.extensions.get('KHR_parallel_shader_compile')){try{await Promise.race([renderer.compileAsync(scene,camera),new Promise(r=>setTimeout(r,8000))]);}catch{}if(disposed)return;}
    else{
     // No parallel link (SwiftShader/llvmpipe, some mobile drivers): warm up progressively. Reveal the drawables a few at
     // a time and render, yielding between batches, so each frame only links a handful of programs and input, Zeref and
     // the rest of the page keep running. Visibility is restored exactly before the real loop starts.
     const drawn:any[]=[];scene.traverse((o:any)=>{if(o.visible&&o.material&&(o.isMesh||o.isPoints||o.isLine||o.isSprite))drawn.push(o);});
     drawn.forEach(o=>{o.visible=false;});
     try{for(let i=0;i<drawn.length&&!disposed;i+=4){for(let j=i;j<Math.min(drawn.length,i+4);j++)drawn[j].visible=true;renderer.render(scene,camera);await new Promise(r=>setTimeout(r,0));}}
     catch{}finally{drawn.forEach(o=>{o.visible=true;});}
     if(disposed)return;
    }
    frame=requestAnimationFrame(animate);
    cleanup=()=>{
     window.removeEventListener('beastbox:beast-chat',onLcChat);window.removeEventListener('beastbox:geyser',onGj);renderer.domElement.removeEventListener('pointerdown',gjPD);renderer.domElement.removeEventListener('pointerup',gjPU);(window as any).__geyserReady=false;gjSnd?.dispose();window.removeEventListener('beastbox:local-sensor-level',onLcLevel);window.removeEventListener('beastbox:spark-chirp',onLcChirp);renderer.domElement.removeEventListener('pointerdown',onLcTap);
     lcS.syn?.dispose();if(lcS.g){lcS.g.remove(lcS.LC.group);zActorNode.remove(lcS.g);}extras.dispose();gcam.dispose();lcBus.current=null;
     pickRef.current=null;godRef.current=null;world.dispose();window.removeEventListener('beastbox:genome',syncPlush);window.removeEventListener('beastbox:pixel-mode',syncPlush);window.removeEventListener('beastbox:spark-chirp',onTalk);document.documentElement.removeAttribute('data-beast-3d');life.dispose();plush?.dispose();
     {const ze=(window as any).__zerefEmbed;if(ze?.root?.parent===zActorNode){zActorNode.remove(ze.root);ze.root.position.y=0;ze.claimed=false;}}
     cancelAnimationFrame(frame);ro?.disconnect();io?.disconnect();
     canvas.removeEventListener('webglcontextlost',onContextLost);
     const geometries=new Set<import('three').BufferGeometry>(),materials=new Set<import('three').Material>();
     scene.traverse(o=>{
      if(o instanceof THREE.Sprite){materials.add(o.material);}
      if(o instanceof THREE.Mesh||o instanceof THREE.LineSegments||o instanceof THREE.Points){
       geometries.add(o.geometry);
       const m=o.material;(Array.isArray(m)?m:[m]).forEach(k=>materials.add(k));
      }
     });
     texCache.forEach(t=>t.dispose());saved.dispose();sand.dispose();geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());renderer.dispose();
    };
   }catch{
    if(!disposed){setFailed(true);setReady(false);}
   }
  })();
  return()=>{disposed=true;cancelAnimationFrame(frame);cleanup();releaseListeners();};
 },[key,failed,reduced,visualSettings.enabled,visualSettings.quality,qvmCounts]);
  return <div className={styles.root} data-pocket-dimension="true"
  data-world-source="genesis-nightops-core-visual-v1"
  data-pocket-state={!visualSettings.enabled?'disabled':failed?'fallback':ready?'ready':'loading'} data-creature-id={id}>
  {visualSettings.enabled&&!failed?<canvas data-pocket-webgl="true" className={styles.canvas} ref={canvasRef}
   aria-hidden="true"/>:null}
  {!visualSettings.enabled?<span className={styles.sr} role="status">3D scenery is off. Your Beast and game remain available.</span>:!failed&&!ready?<span className={styles.sr} role="status">Opening the dimensional world behind your Beast…</span>:null}
 {ready?<div className={styles.live} aria-hidden="true"><i/>LIVE · CST</div>:null}
 {ready?(()=>{
  // One menu: when the Cage/Home menu is present these tools live in it (labelled, 44px targets) and nothing sits on the scene.
  const wLab='Weather: '+WEATHERS[weatherI],tLab=['Time: live cycle','Time: day','Time: dusk','Time: night'][timeI];
  const cycleWeather=()=>{const i=(weatherI+1)%4;setWeatherI(i);godRef.current?.weather(WEATHERS[i]);};
  const cycleTime=()=>{const i=(timeI+1)%4;setTimeI(i);godRef.current?.time(TIMES[i]);};
  if(menuHost)return createPortal(<div role="toolbar" aria-label="Pocket controls" data-pocket-tools-menu>
   <button type="button" aria-label={wLab} onClick={cycleWeather}><span aria-hidden="true">{WEATHER_ICON[WEATHERS[weatherI]]}</span>{wLab}</button>
   <button type="button" aria-label="Time of day" onClick={cycleTime}><span aria-hidden="true">{TIME_ICON[timeI]}</span>{tLab}</button>
   <button type="button" aria-label="Drop a treat" onClick={()=>godRef.current?.treat()}><span aria-hidden="true">●</span>Drop a treat</button>
   <button type="button" aria-label="Plant a flower" onClick={()=>godRef.current?.flower()}><span aria-hidden="true">✿</span>Plant a flower</button>
   <button type="button" aria-label="Poke your Beast" onClick={()=>godRef.current?.poke()}><span aria-hidden="true">☝</span>Poke your Beast</button>
   <button type="button" aria-label="About this world" aria-expanded={infoOpen} onClick={()=>setInfoOpen(o=>!o)}><span aria-hidden="true">ⓘ</span>Who lives here</button>
  </div>,menuHost);
  return <div className={styles.godbar} role="toolbar" aria-label="Pocket controls">
  <button type="button" aria-label={'Weather: '+WEATHERS[weatherI]} title={'Weather: '+WEATHERS[weatherI]} onClick={cycleWeather}>{WEATHER_ICON[WEATHERS[weatherI]]}</button>
  <button type="button" aria-label="Time of day" title={tLab} onClick={cycleTime}>{TIME_ICON[timeI]}</button>
  <button type="button" aria-label="Drop a treat" title="Drop a treat" onClick={()=>godRef.current?.treat()}>●</button>
  <button type="button" aria-label="Plant a flower" title="Plant a flower" onClick={()=>godRef.current?.flower()}>✿</button>
  <button type="button" aria-label="Poke your Beast" title="Poke" onClick={()=>godRef.current?.poke()}>☝</button>
  <button type="button" aria-label={pixel?'Show 3D Beast':'Show classic pixel Beast'} title={pixel?'3D Beast':'Classic pixel'} aria-pressed={pixel} onClick={togglePixel}>{pixel?'3D':'▦'}</button>
  <button type="button" aria-label="About this world" aria-expanded={infoOpen} onClick={()=>setInfoOpen(o=>!o)}>ⓘ</button>
 </div>;})():null}
 <p className={styles.sandLabel} data-open={infoOpen||!ready} data-sand-source={sandSource}>{SAND_LABEL} · {sandSource==='receipt'?'IBM seed + this Beast\u2019s Rigetti simulator counts (SIMULATED)':'IBM seed only · no simulator receipt for this Beast'}</p>
 {infoOpen?<details className={styles.residentsBox} open={residentsOpen} onToggle={e=>setResidentsOpen((e.currentTarget as HTMLDetailsElement).open)}><summary aria-label={residentsOpen?"Minimize residents":"Show residents"}>{residentsOpen?"– Residents":"✦ Who lives here"}</summary>
 <ul className={styles.residents} aria-label="Everyone who lives in this pocket" data-artist-residents={ARTIST_RESIDENTS.length} data-creations={creations.length}>
  {creations.length?creations.map(r=><li key={r.id} data-resident-id={r.id} data-resident-kind={r.kind} data-creation-source={r.kind==='active'||r.kind==='saved'?'saved-beast':'artist'}>{r.art?<img src={r.art} alt={`${r.name}: ${r.look||''}`} width={44} height={44} loading="lazy"/>:r.genome?<CreationThumb genome={r.genome} label={`${r.name}, a saved beast`}/>:<span aria-hidden="true" style={{width:30,height:30}}/>}<span><b>{r.name}</b><small>{r.kind==='trainer'?'Trainer':r.kind==='active'?'Your beast':r.kind==='saved'?'Saved beast':'Beast'} · {r.origin}</small></span></li>):<li data-creations-empty><b>{homeLabel(homeName)}</b></li>}
 </ul></details>:null}
 </div>;
}
