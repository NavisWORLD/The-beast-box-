'use client';
import {addGodView,ZOOM_MIN,ZOOM_MAX} from './pocket-god-view';
import {ARTIST_RESIDENTS} from '../lib/companion/artist-residents.mjs';
import {addPocketResidents} from './pocket-residents';
import {addPocketSand} from './pocket-sand-layer';
import {SAND_LABEL} from '../lib/pocket-sand.mjs';
import {useEffect,useRef,useState} from 'react';
import {createPocketSky,orbitPosition} from '../lib/pocket-sky.mjs';
import {DEFAULT_POCKET_3D,POCKET_3D_KEY,POCKET_3D_EVENT,POCKET_3D_CAMERA_RESET,devicePocket3D} from '../lib/companion/pocket-3d-settings.mjs';
import styles from './cage-pocket-dimension.module.css';

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
export default function CagePocketDimension({seed,qbeastId,stage,reduced,behaviorPosition,state,onActiveChange,qvmCounts=null,autoOrbit=false}:Props){
 const autoOrbitRef=useRef(autoOrbit);autoOrbitRef.current=autoOrbit;const lastDragAt=useRef(0);
 useEffect(()=>{if(autoOrbit)cameraView.current={...cameraView.current,zoom:8.5,phi:1.18};},[autoOrbit]);
 const sandSource=qvmCounts?'receipt':'seed';
 const canvasRef=useRef<HTMLCanvasElement>(null);
 const motion=useRef({position:behaviorPosition,state,stage,impulse:0});
 const cameraView=useRef<View>({theta:.7,phi:1.05,zoom:10.6});
 const [visualSettings,setVisualSettings]=useState<{enabled:boolean;quality:'auto'|'low'|'high'}>({...DEFAULT_POCKET_3D});
 useEffect(()=>{
  const sync=()=>setVisualSettings(devicePocket3D());
  const onStorage=(event:StorageEvent)=>{if(event.key===POCKET_3D_KEY)sync();};
  sync();window.addEventListener(POCKET_3D_EVENT,sync);window.addEventListener('storage',onStorage);
  return()=>{window.removeEventListener(POCKET_3D_EVENT,sync);window.removeEventListener('storage',onStorage);};
 },[]);
 const [ready,setReady]=useState(false),[failed,setFailed]=useState(false);
 const [residentsOpen,setResidentsOpen]=useState(true);
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
    cameraView.current.theta-=dx*.009;lastDragAt.current=performance.now();
    cameraView.current.phi=clamp(cameraView.current.phi+dy*.008,.06,3.08);
   }else if(activePointers.size===2){
    const other=[...activePointers.entries()].find(([id])=>id!==event.pointerId)?.[1];
    if(other){
     const before=Math.hypot(prev.x-other.x,prev.y-other.y);
     const after=Math.hypot(event.clientX-other.x,event.clientY-other.y);
     if(before>18&&after>18)cameraView.current.zoom=clamp(cameraView.current.zoom*before/after,ZOOM_MIN,ZOOM_MAX);
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
   cameraView.current.zoom=clamp(cameraView.current.zoom*Math.exp(event.deltaY*.0016),ZOOM_MIN,ZOOM_MAX);
  };
  const keyboard=(event:KeyboardEvent)=>{
   if(event.target!==parent||isControl(event.target))return;
   if(event.key==='ArrowLeft'||event.key==='ArrowRight'){
    event.preventDefault();cameraView.current.theta+=(event.key==='ArrowLeft'?.17:-.17);
   }else if(event.key==='ArrowUp'||event.key==='ArrowDown'){
    event.preventDefault();cameraView.current.phi=clamp(cameraView.current.phi+(event.key==='ArrowUp'?-.14:.14),.06,3.08);
   }else if(event.key==='+'||event.key==='='){
    event.preventDefault();cameraView.current.zoom=clamp(cameraView.current.zoom/1.3,ZOOM_MIN,ZOOM_MAX);
   }else if(event.key==='-'){
    event.preventDefault();cameraView.current.zoom=clamp(cameraView.current.zoom*1.3,ZOOM_MIN,ZOOM_MAX);
   }else if(event.key==='Home'){
    event.preventDefault();cameraView.current={theta:.7,phi:1.05,zoom:10.6};
   }
  };
  // Existing sound-generator events: sound is a *visual stimulus*, not proof
  // of external microphone hearing or physical quantum/natural growth.
  const chirp=(e:Event)=>{const raw=Number((e as CustomEvent)?.detail?.intensity);motion.current.impulse=clamp(motion.current.impulse+(Number.isFinite(raw)?raw:.35)*.32,0,1.25);};
  const mute=()=>{motion.current.impulse=0;};
  const resetCamera=()=>{cameraView.current={theta:.7,phi:1.05,zoom:10.6};};
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
  window.addEventListener(POCKET_3D_CAMERA_RESET,resetCamera);
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
   window.removeEventListener(POCKET_3D_CAMERA_RESET,resetCamera);
  };
  void(async()=>{
   try{
    if(!window.WebGLRenderingContext)throw Error('WebGL unavailable');
    // Home: let the 3D Zeref finish cutting his layers first (both share one main thread on phones).
    if(autoOrbitRef.current){const t0=performance.now();while(!disposed&&performance.now()-t0<10000&&document.querySelector('[data-zeref-sprite3d="loading"]'))await new Promise(r=>setTimeout(r,250));if(disposed)return;}
    const THREE=await import('three');
    if(disposed)return;
    // User quality never overrides the OS reduced-motion safety boundary.
    let low=reduced||visualSettings.quality==='low'||(visualSettings.quality==='auto'&&window.innerWidth<600);
    const renderer=new THREE.WebGLRenderer({canvas,alpha:false,antialias:!low,powerPreference:'low-power'});
    renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,low?1:1.4));
    // Software GL (CI SwiftShader, very old phones): force the low tier so the main thread never starves.
    let soft=false;try{const gl=renderer.getContext();const dbg=gl.getExtension('WEBGL_debug_renderer_info');soft=!!dbg&&/swiftshader|llvmpipe|software/i.test(String(gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL)));}catch{}
    if(soft){low=true;renderer.setPixelRatio(1);}
    renderer.outputColorSpace=THREE.SRGBColorSpace;
    // Living Cosmos polish: filmic tone mapping for deeper, less flat contrast.
    renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.25;
    const scene=new THREE.Scene();
    scene.background=new THREE.Color(0x05040f);
    scene.fog=new THREE.FogExp2(0x0d0a26,.032);
    const camera=new THREE.PerspectiveCamera(46,1,.1,30000);
    scene.add(new THREE.HemisphereLight(0x94d9ff,0x20113b,1.8));
    const moonlight=new THREE.PointLight(0xa8eaff,24,12);
    moonlight.position.set(0,4,1);scene.add(moonlight);
    const glow=new THREE.PointLight(0xba82f4,13,11);glow.position.set(-2,2,-3);scene.add(glow);
    // Lost COSMOS look: dark cosmic sand floor instead of blue stone.
    const stone=new THREE.MeshStandardMaterial({color:0x1c1530,emissive:0x0a0618,roughness:1,metalness:.02});
    const floraMat=new THREE.MeshStandardMaterial({color:0x6fe7ff,emissive:0x2aa6d6,emissiveIntensity:.9,metalness:.3,roughness:.18,transparent:true,opacity:.9});
    const crystalMat=new THREE.MeshStandardMaterial({color:0xc6a2ff,emissive:0x7a4fe0,emissiveIntensity:.95,metalness:.3,roughness:.18,transparent:true,opacity:.92});
    const ground=new THREE.Mesh(new THREE.BoxGeometry(9.1,.22,9.1),stone);
    ground.position.y=-.17;scene.add(ground);
    const grid=new THREE.GridHelper(9,12,0x4983a4,0x284c74);
    grid.position.y=-.05;scene.add(grid);
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
     if(Math.hypot(x,z)<1.4)continue;
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
    starsGeom.setAttribute('position',new THREE.Float32BufferAttribute(points,3));
    scene.add(new THREE.Points(starsGeom,new THREE.PointsMaterial({color:0xb2dfff,size:.042,transparent:true,opacity:.75})));
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
    const dustN=low?90:220,dustGeom=new THREE.BufferGeometry(),dust=new Float32Array(dustN*3);
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
    const {stepResidents,texCache,disturbers}=addPocketResidents(THREE,scene,seedRandom,reduced);
    // God view: habitat on a small planet, orbiting its suns, inside a galaxy (Genesis Engine, recoloured).
    const god=addGodView(THREE,scene,{rand:randomFor(key+':system'),low,counts:qvmCounts,stage:motion.current.stage||stage||1});
    const godFocus=new THREE.Vector3();
    // Home: the sprite-built 3D Zeref lives here, standing on the habitat floor (one world, one camera).
    const zHolder=new THREE.Group();zHolder.scale.setScalar(.45);zHolder.position.set(0,1.68*.45-.07,0);zHolder.rotation.y=.7;scene.add(zHolder);
    if(typeof window!=='undefined')(window as any).__pocketCamera=cameraView;
    const sand=addPocketSand(THREE,scene,{seed:key,low,reduced});
    sand.field.setCounts(qvmCounts);
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
     if(document.hidden||!visible||now-lastPaint<(soft?120:low?55:33))return;
     lastPaint=now;
     if(!reduced)elapsed+=dt;
     nebulaMat.uniforms.time.value=elapsed;poolMat.uniforms.time.value=elapsed;
     if(!reduced){for(let i=0;i<dustN;i++){let y=dust[i*3+1]+dt*(.12+(i%5)*.03);if(y>4.8)y=0;dust[i*3+1]=y;dust[i*3]+=Math.sin(elapsed*.4+i)*dt*.05;}dustGeom.attributes.position.needsUpdate=true;}
     if(autoOrbitRef.current&&!reduced&&now-lastDragAt.current>2500)cameraView.current.theta+=dt*.09;
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
     stepResidents(elapsed,v.theta);
     sand.update(dt,[{x:glow.position.x,z:glow.position.z,r:1.2,s:1.6+motion.current.impulse*3},{x:0,z:0,r:1.1,s:1.2},...disturbers()]);
     const ze=(window as any).__zerefEmbed;
     if(ze?.root&&ze.root.parent!==zHolder){zHolder.add(ze.root);ze.claimed=true;}
     if(ze?.claimed){let d=-(v.theta-zHolder.rotation.y)*180/Math.PI;d=((d%360)+540)%360-180;ze.viewYaw=d;}
     const f=god.update(elapsed,v.zoom,focus,godFocus);
     (scene.fog as import('three').FogExp2).density=.032*Math.min(1,12/v.zoom);
     camera.near=Math.max(.05,v.zoom*.01);camera.updateProjectionMatrix();
     camera.position.set(f.x+v.zoom*Math.sin(v.phi)*Math.sin(v.theta),f.y+v.zoom*Math.cos(v.phi),f.z+v.zoom*Math.sin(v.phi)*Math.cos(v.theta));
     camera.lookAt(f);
     try{renderer.render(scene,camera);}catch{setReady(false);setFailed(true);return;}
     if(!rendered){rendered=true;setReady(true);}
    };
    frame=requestAnimationFrame(animate);
    cleanup=()=>{
     {const ze=(window as any).__zerefEmbed;if(ze?.root?.parent===zHolder){zHolder.remove(ze.root);ze.claimed=false;}}
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
     texCache.forEach(t=>t.dispose());sand.dispose();geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());renderer.dispose();
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
 <p className={styles.sandLabel} data-sand-source={sandSource}>{SAND_LABEL} · {sandSource==='receipt'?'recorded seed + this Beast\u2019s recorded Azure simulator counts':'recorded seed only · no simulator receipt for this Beast'}</p>
 <details className={styles.residentsBox} open={residentsOpen} onToggle={e=>setResidentsOpen((e.currentTarget as HTMLDetailsElement).open)}><summary aria-label={residentsOpen?"Minimize residents":"Show residents"}>{residentsOpen?"– Residents":"✦ Who lives here"}</summary>
 <ul className={styles.residents} aria-label="Artist-drawn Pocket residents" data-artist-residents={ARTIST_RESIDENTS.length}>
  {ARTIST_RESIDENTS.map(r=><li key={r.id} data-resident-id={r.id} data-resident-kind={r.kind}><img src={r.views.front} alt={`${r.name}: ${r.look}`} width={44} height={44} loading="lazy"/><span><b>{r.name}</b><small>{r.kind==='trainer'?'Trainer':'Beast'} · {r.origin}</small></span></li>)}
 </ul></details>
 </div>;
}
