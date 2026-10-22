'use client';
/**
 * Living World (Oct 22 2026): the user's beast lives ON the tiny-universe planet with the resident creatures.
 * Genesis = recorded ibm_marrakesh hardware counts (tiny-universe-genesis.json). Growth = SIMULATED Rigetti-style
 * Bell simulator (lib/universe/tiny-universe.mjs grow()), ticking client-side. Grass spreads from gathering points as
 * the simulated universe grows until it covers the whole planet. "Spawn in" puts you on the ground as a traveler
 * (Cosmo's art pack) with a touch joystick + WASD and a third-person camera.
 */
import {useEffect,useRef,useState} from 'react';
import {grow} from '@/lib/universe/tiny-universe.mjs';
import {worldThings,THING_LESSON} from '@/lib/universe/living-world.mjs';
import {LW_LABELS,gatheringPoints,spreadAngle,initialTraits,driftTraits,lattice12D,lwStream,unitFrom} from '@/lib/universe/living-world.mjs';
import {ARTIST_RESIDENTS} from '@/lib/companion/artist-residents.mjs';
import {buildPlush,type PlushGenome} from './creature-plush-3d';
const ART='/universe/livingworld/';
// Lines from Cosmic Emeth's 'Shared World' chapter (lost_cosmos tiny_universe_bible.md).
const WINDOW_LINES=['Your world is loud today. I like it.','*presses nose to the window* Are you okay out there?'];
const PR=8;           // planet radius (world units)
const TRAV_H=.5;      // traveler height
type Traits={curiosity:number;sociality:number;calm:number;joy:number;experiences:number};
export default function LivingWorld({genome,beastKey,beastName,onClose}:{genome?:PlushGenome|null;beastKey?:string|null;beastName?:string|null;onClose?:()=>void}){
 const host=useRef<HTMLDivElement>(null);const canvasRef=useRef<HTMLCanvasElement>(null);
 const [spawned,setSpawned]=useState(false);const spawnRef=useRef(false);
 const [hud,setHud]=useState<{tick:number;simE:number|null;life:number;storms:number;cover:number;traits:Traits|null;blades:number;fps:number;learned?:Record<string,number>;awake?:number}>({tick:0,simE:null,life:0,storms:0,cover:0,traits:null,blades:0,fps:0});
 const [err,setErr]=useState<string|null>(null);const [line,setLine]=useState<string|null>(null);const lineRef=useRef(setLine);lineRef.current=setLine;
 useEffect(()=>{if(!line)return;const id=setTimeout(()=>setLine(null),4200);return()=>clearTimeout(id);},[line]);
 const joy=useRef({x:0,y:0,active:false,id:-1,cx:0,cy:0});const keys=useRef(new Set<string>());
 const [stick,setStick]=useState<{x:number;y:number}|null>(null);
 useEffect(()=>{spawnRef.current=spawned;(window as any).__lwSpawned=spawned;},[spawned]);
 useEffect(()=>{
  let disposed=false,raf=0;const cleanup:(()=>void)[]=[];
  (async()=>{
   const THREE=await import('three');
   const [g0,frames]=await Promise.all([fetch('/universe/tiny-universe-genesis.json').then(r=>r.json()),fetch(ART+'livingworld_frames.json').then(r=>r.json())]);
   if(disposed)return;
   const bKey=beastKey||genome?.seed||'guest';
   let u:any=g0;try{const s=JSON.parse(localStorage.getItem('lw:universe')||'null');if(s?.seed===g0.seed&&s.schema===g0.schema)u=s;}catch{}
   let traits:Traits=(()=>{try{const t=JSON.parse(localStorage.getItem('lw:traits:'+bKey)||'null');if(t&&typeof t.calm==='number')return t;}catch{}return initialTraits(u,bKey);})();
   const canvas=canvasRef.current!;
   const phone=matchMedia('(max-width: 820px)').matches||/iPhone|iPad|Android/.test(navigator.userAgent);
   const renderer=new THREE.WebGLRenderer({canvas,antialias:!phone,powerPreference:'high-performance'});
   renderer.setPixelRatio(Math.min(devicePixelRatio||1,phone?2:2));renderer.outputColorSpace=THREE.SRGBColorSpace;
   const scene=new THREE.Scene();scene.background=new THREE.Color(0x05030f);
   const camera=new THREE.PerspectiveCamera(55,1,.05,400);
   const L=new THREE.TextureLoader();const tex=(f:string,rep=false)=>{const t=L.load(ART+f);t.colorSpace=THREE.SRGBColorSpace;if(rep){t.wrapS=t.wrapT=THREE.RepeatWrapping;}return t;};
   scene.add(new THREE.HemisphereLight(0xb9a8ff,0x223322,1.1));const sun=new THREE.DirectionalLight(0xfff1dd,1.6);sun.position.set(20,14,10);scene.add(sun);
   // ---- stars + 12D lattice in the sky
   {const r=lwStream(u.seed+':sky');const n=phone?900:1800,p=new Float32Array(n*3);for(let i=0;i<n;i++){const v=unitFrom(r);const d=120+r()*80;p.set([v[0]!*d,v[1]!*d,v[2]!*d],i*3);}
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(p,3));scene.add(new THREE.Points(g,new THREE.PointsMaterial({color:0xdde6ff,size:.6,sizeAttenuation:true})));}
   const lat=lattice12D(u.seed,phone?160:256);const lg=new THREE.BufferGeometry();lg.setAttribute('position',new THREE.Float32BufferAttribute(lat.verts.map(v=>v*7),3));lg.setIndex(lat.edges);
   const latObj=new THREE.LineSegments(lg,new THREE.LineBasicMaterial({color:0x8f7bff,transparent:true,opacity:.28,depthWrite:false}));latObj.position.set(0,0,0);
   const latPivot=new THREE.Group();latPivot.add(latObj);latObj.position.set(0,26,-30);scene.add(latPivot);
   // ---- planet ground: grass/soil tiles blended by a coverage field that spreads from gathering points
   const gpts=gatheringPoints(u,bKey).map(v=>new THREE.Vector3(...v));
   const UG={uGrass:{value:tex('ground_grass_tile_256.jpg',true)},uSoil:{value:tex('ground_soil_tile_256.jpg',true)},uMask:{value:tex('grass_edge_edge_mask.png',true)},
    uPts:{value:gpts},uPlay:{value:Array.from({length:8},()=>new THREE.Vector3())},uSpread:{value:spreadAngle(u)},uT:{value:0},uSun:{value:sun.position.clone().normalize()}};
   const COVER=`uniform vec3 uPts[8];uniform float uSpread;float cover(vec3 n){float c=0.0;for(int i=0;i<8;i++){float a=acos(clamp(dot(n,uPts[i]),-1.0,1.0));c=max(c,smoothstep(uSpread,uSpread-0.35,a));}return c;}`;
   const ground=new THREE.Mesh(new THREE.SphereGeometry(PR,phone?96:160,phone?64:110),new THREE.ShaderMaterial({uniforms:UG,
    vertexShader:`varying vec3 vN;varying vec2 vUv;void main(){vN=normalize(position);vUv=uv*vec2(48.0,24.0);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
    fragmentShader:`uniform sampler2D uGrass,uSoil,uMask;uniform vec3 uSun;varying vec3 vN;varying vec2 vUv;${COVER}
     vec3 tri(sampler2D t,vec3 n){vec3 w=pow(abs(n),vec3(4.0));w/=w.x+w.y+w.z;vec3 p=n*${(PR/2).toFixed(1)};return texture2D(t,p.yz).rgb*w.x+texture2D(t,p.xz).rgb*w.y+texture2D(t,p.xy).rgb*w.z;}
     void main(){float c=cover(vN);float m=.5+.35*(tri(uMask,vN*1.7).r-.5)+.25*(fract(sin(dot(floor(vN*40.0),vec3(12.9,78.2,37.7)))*43758.5)-.5);float g=smoothstep(m-.2,m+.2,c*1.1);vec3 col=mix(tri(uSoil,vN),tri(uGrass,vN),g);
      float l=1.7+1.0*max(0.0,dot(vN,uSun));float rim=pow(1.0-abs(dot(vN,normalize(cameraPosition-vN*8.0))),3.0);gl_FragColor=vec4(col*l+vec3(.25,.18,.55)*rim*.6,1.0);}`}));
   scene.add(ground);
   // ---- flowing grass: instanced cross-quads from Cosmo's blade atlas; wind values from the JSON; scaled by coverage in-shader
   const W=frames.grass_blades.wind;let bladeCap=phone?6000:14000;
   const quad=new THREE.PlaneGeometry(.09,.32,1,3);quad.translate(0,.16,0);
   const cross=new THREE.BufferGeometry();{const a=quad.clone(),b=quad.clone();b.rotateY(Math.PI/2);const pos=[...a.attributes.position.array,...b.attributes.position.array],uv=[...a.attributes.uv.array,...b.attributes.uv.array];
    const ia=[...a.index!.array],ib=[...b.index!.array].map(i=>i+a.attributes.position.count);cross.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));cross.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));cross.setIndex([...ia,...ib]);}
   const bladeGeo=new THREE.InstancedBufferGeometry();bladeGeo.index=cross.index;bladeGeo.attributes.position=cross.attributes.position;bladeGeo.attributes.uv=cross.attributes.uv;
   const MAXB=14000;const iN=new Float32Array(MAXB*3),iR=new Float32Array(MAXB*2);{const r=lwStream(u.seed+':blades');for(let i=0;i<MAXB;i++){iN.set(unitFrom(r) as number[],i*3);iR[i*2]=r();iR[i*2+1]=Math.floor(r()*8);}}
   bladeGeo.setAttribute('aN',new THREE.InstancedBufferAttribute(iN,3));bladeGeo.setAttribute('aR',new THREE.InstancedBufferAttribute(iR,2));bladeGeo.instanceCount=bladeCap;
   const bladeMat=new THREE.ShaderMaterial({uniforms:{...UG,uAtlas:{value:tex('grass_blade_atlas.png')},uAmp:{value:W.sway_amp_rad},uFreq:{value:W.freq_hz},uWave:{value:W.wave_len_world},uGust:{value:W.gust_amp},uGustF:{value:W.gust_freq_hz},uR:{value:PR}},
    side:THREE.DoubleSide,alphaTest:.5,
    vertexShader:`attribute vec3 aN;attribute vec2 aR;uniform float uT,uAmp,uFreq,uWave,uGust,uGustF,uR;varying vec2 vUv;varying float vL;${COVER}
uniform vec3 uPlay[8];
     void main(){vec3 n=normalize(aN);float c=cover(n);float near=0.0;for(int i=0;i<8;i++)near=max(near,smoothstep(.22,.0,acos(clamp(dot(n,uPlay[i]),-1.0,1.0))));c*=1.0+near*.8;vec3 t=normalize(cross(abs(n.y)<.99?vec3(0,1,0):vec3(1,0,0),n));vec3 b=cross(n,t);
      float ca=cos(aR.x*6.283),sa=sin(aR.x*6.283);vec3 tx=t*ca+b*sa,tz=-t*sa+b*ca;
      vec3 p=position*(0.55+0.6*fract(aR.x*7.3))*c;float w=pow(uv.y,1.6);vec3 wp=n*uR;
      float ang=uAmp*w*sin(uT*6.2831*uFreq+dot(wp,normalize(vec3(1,.2,.4)))/uWave)+uGust*w*sin(uT*6.2831*uGustF+wp.x*.2);
      p.x+=sin(ang)*p.y;p.y*=cos(ang);
      vec3 world=wp+tx*p.x+n*p.y+tz*p.z;vUv=vec2((aR.y+uv.x)/8.0,uv.y);vL=.8+.5*max(0.0,dot(n,normalize(vec3(20,14,10))));
      gl_Position=projectionMatrix*viewMatrix*vec4(world,1.0);if(c<.02)gl_Position=vec4(2.0,2.0,2.0,1.0);}`,
    fragmentShader:`uniform sampler2D uAtlas;varying vec2 vUv;varying float vL;void main(){vec4 c=texture2D(uAtlas,vUv);if(c.a<.5)discard;gl_FragColor=vec4(c.rgb*vL,1.0);}`});
   const blades=new THREE.Mesh(bladeGeo,bladeMat);blades.frustumCulled=false;scene.add(blades);
   // ---- surface helpers: place an object at unit normal n facing tangent f
   const up=new THREE.Vector3(0,1,0),tmpQ=new THREE.Quaternion(),m4=new THREE.Matrix4();
   const place=(o:import('three').Object3D,n:import('three').Vector3,f:import('three').Vector3,lift=0)=>{o.position.copy(n).multiplyScalar(PR+lift);const x=new THREE.Vector3().crossVectors(n,f).normalize();const z=new THREE.Vector3().crossVectors(x,n);m4.makeBasis(x,n,z);o.quaternion.setFromRotationMatrix(m4);};
   const shadowTex=tex('beast_contact_shadow.png');
   const mkShadow=(w:number)=>{const s=new THREE.Mesh(new THREE.PlaneGeometry(w,w/4),new THREE.MeshBasicMaterial({map:shadowTex,transparent:true,depthWrite:false,blending:THREE.MultiplyBlending,premultipliedAlpha:true}));s.rotation.x=-Math.PI/2;s.position.y=.01;return s;};
   const walkOn=(n:import('three').Vector3,f:import('three').Vector3,dist:number)=>{const ax=new THREE.Vector3().crossVectors(n,f).normalize();tmpQ.setFromAxisAngle(ax,dist/PR);n.applyQuaternion(tmpQ).normalize();f.applyQuaternion(tmpQ);f.addScaledVector(n,-f.dot(n)).normalize();};
   const turn=(n:import('three').Vector3,f:import('three').Vector3,a:number)=>{f.applyAxisAngle(n,a).normalize();};
   // ---- residents (Cory's artist creatures) roam the surface
   const rr=lwStream(u.seed+':residents');
   const residents=(ARTIST_RESIDENTS as any[]).map((r:any)=>{const node=new THREE.Group();const sp=new THREE.Sprite(new THREE.SpriteMaterial({map:L.load(r.views.front),transparent:true,depthWrite:false}));
    (sp.material.map as any).colorSpace=THREE.SRGBColorSpace;const h=.75*r.scale;sp.scale.set(h,h,1);sp.center.set(.5,.05);node.add(sp);node.add(mkShadow(h*.9));scene.add(node);
    const n=new THREE.Vector3(...(unitFrom(rr) as [number,number,number]));const f=new THREE.Vector3(...(unitFrom(rr) as [number,number,number]));f.addScaledVector(n,-f.dot(n)).normalize();return {node,n,f,spd:.25+rr()*.35,wob:rr()*10,name:r.name};});
   residents.slice(0,7).forEach((r,i)=>gpts[i+1].copy(r.n));// grass starts under the beasts' feet
   // ---- things to explore: seeded flowers, crystals, cairns, ponds, burrows, trees; they wake as the grass reaches them
   const COL:Record<string,number>={flower:0xff7ad9,crystal:0x7fe8ff,cairn:0xb9b0c8,pond:0x3a7bd5,burrow:0x2a1c14,tree:0x2f8f5b};
   const mkThing=(kind:string)=>{const g=new THREE.Group();const m=(geo:any,c:number,em=0)=>{const x=new THREE.Mesh(geo,new THREE.MeshStandardMaterial({color:c,emissive:c,emissiveIntensity:em,roughness:.7}));g.add(x);return x;};
    if(kind==='flower'){m(new THREE.CylinderGeometry(.015,.02,.25,5),0x3b9b4b).position.y=.125;m(new THREE.IcosahedronGeometry(.07,0),COL.flower,.4).position.y=.27;}
    else if(kind==='crystal'){const c=m(new THREE.OctahedronGeometry(.13,0),COL.crystal,.8);c.scale.y=2;c.position.y=.2;}
    else if(kind==='cairn'){for(let i=0;i<3;i++){const st=m(new THREE.DodecahedronGeometry(.09-i*.02,0),COL.cairn);st.position.y=.08+i*.12;}}
    else if(kind==='pond'){const c=m(new THREE.CircleGeometry(.4,20),COL.pond,.25);c.rotation.x=-Math.PI/2;c.position.y=.02;}
    else if(kind==='burrow'){const c=m(new THREE.CircleGeometry(.16,16),COL.burrow);c.rotation.x=-Math.PI/2;c.position.y=.015;const t=m(new THREE.TorusGeometry(.17,.04,6,16),0x5a4030);t.rotation.x=-Math.PI/2;t.position.y=.03;}
    else {m(new THREE.CylinderGeometry(.04,.06,.4,6),0x5a3a22).position.y=.2;m(new THREE.ConeGeometry(.22,.5,7),COL.tree,.1).position.y=.6;}
    return g;};
   const things=worldThings(u,phone?36:56).map((t:any)=>{const node=mkThing(t.kind);const n=new THREE.Vector3(...(t.n as [number,number,number]));const f=new THREE.Vector3(1,0,0).addScaledVector(n,-n.x).normalize();place(node,n,f);node.scale.setScalar(0.001);scene.add(node);return {...t,n,node,awake:false,grow:0,pulse:0,cool:0};});
   const learned:Record<string,number>=(()=>{try{return JSON.parse(localStorage.getItem('lw:learned:'+bKey)||'{}');}catch{return {};}})();
   const ang=(a:import('three').Vector3,b:import('three').Vector3)=>Math.acos(Math.max(-1,Math.min(1,a.dot(b))))*PR;
   const nearestThing=(n:import('three').Vector3)=>{let best:any=null,bd=1e9;for(const t of things)if(t.awake){const d=ang(n,t.n);if(d<bd){bd=d;best=t;}}return best?{t:best,d:bd}:null;};
   const touch=(t:any,who:string)=>{if(t.cool>0)return false;t.cool=2.5;t.level++;t.pulse=1;t.grow=Math.min(1.8,1+t.level*.08);return true;};
   const steerTo=(n:import('three').Vector3,f:import('three').Vector3,goal:import('three').Vector3,k:number)=>{const d=goal.clone().sub(n);d.addScaledVector(n,-d.dot(n));if(d.lengthSq()<1e-10)return;d.normalize();f.lerp(d,Math.min(1,k)).addScaledVector(n,-f.dot(n)).normalize();};
   let socialCool=0;
   // ---- the user's beast (real 3D plush from its genome), ~1.5x traveler height, on the ground with contact shadow
   const beastNode=new THREE.Group();scene.add(beastNode);let plush:ReturnType<typeof buildPlush>|null=null;
   const gen=genome||((window as any).__beastGenome as PlushGenome|null);
   if(gen){try{plush=buildPlush(THREE,gen,{low:phone});const bb=new THREE.Box3().setFromObject(plush.root);const h=Math.max(.01,bb.max.y-bb.min.y);const k=TRAV_H*1.5/h;const holder=new THREE.Group();holder.scale.setScalar(k);holder.position.y=-bb.min.y*k;holder.add(plush.root);beastNode.add(holder);(window as any).__lwBeast={h,k};}catch(e){plush=null;(window as any).__lwBeastErr=String(e);}}
   beastNode.add(mkShadow(TRAV_H*1.4));
   const bN=gpts[0].clone(),bF=new THREE.Vector3(...unitFrom(lwStream(u.seed+':bf'))).addScaledVector(gpts[0],-1).normalize();bF.addScaledVector(bN,-bF.dot(bN)).normalize();
   const brain={speed:0,mode:'walk',sleep:0,lookCam:0,bob:0,heading:0,startle:0};
   const glow=new THREE.Sprite(new THREE.SpriteMaterial({map:tex('window_glow.png'),transparent:true,blending:THREE.AdditiveBlending,depthWrite:false}));glow.scale.setScalar(TRAV_H*1.5*.6);scene.add(glow);let glowBoost=0;
   // ---- traveler (Cosmo's sheets): walk 8-dir, idle, spawn-in
   const F=frames;const sheet=(f:string,cols:number,rows:number)=>{const t=tex(f);t.repeat.set(1/cols,1/rows);t.magFilter=THREE.NearestFilter;return t;};
   const tWalk=sheet(F.traveler_walk.file,F.traveler_walk.cols,8),tIdle=sheet(F.traveler_idle.file,F.traveler_idle.cols,1),tSpawn=sheet(F.traveler_spawn.file,F.traveler_spawn.cols,1);
   const trav=new THREE.Sprite(new THREE.SpriteMaterial({map:tIdle,transparent:true,depthWrite:false}));trav.scale.set(TRAV_H*1.15,TRAV_H*1.15,1);trav.center.set(F.anchor_px[0]/F.frame_size[0],1-F.anchor_px[1]/F.frame_size[1]);
   const travNode=new THREE.Group();travNode.add(trav);travNode.add(mkShadow(TRAV_H*.8));travNode.visible=false;scene.add(travNode);
   const pN=new THREE.Vector3(),pF=new THREE.Vector3();let spawnT=-1,greetT=-1,wasSpawned=false;
   const setFrame=(t:import('three').Texture,cols:number,rows:number,col:number,row:number)=>{t.offset.set(col/cols,1-(row+1)/rows);};
   const ROWS=F.traveler_walk.rows as string[];const RG=frames.beast_run_to_greet;
   // ---- growth: SIMULATED ticks client-side
   let tickAcc=0;const TICK_S=2;
   const applyTick=()=>{if(u.tick>=4000)return;const prev=u;u=grow(u,1);const ev=u.history[u.history.length-1]?.events||[];let exp=ev[0]?.kind||null;if(!exp&&u.storms.length>prev.storms.length)exp='storm';
    traits=driftTraits(traits,u,bKey,exp||'day');glowBoost=1;if(!spawnRef.current&&u.tick%15===0)lineRef.current(WINDOW_LINES[(u.tick/15)%WINDOW_LINES.length]);UG.uSpread.value=spreadAngle(u);
    try{localStorage.setItem('lw:universe',JSON.stringify(u));localStorage.setItem('lw:traits:'+bKey,JSON.stringify(traits));}catch{}};
   // ---- input
   const kd=(e:KeyboardEvent)=>{keys.current.add(e.key.toLowerCase());},ku=(e:KeyboardEvent)=>{keys.current.delete(e.key.toLowerCase());};
   addEventListener('keydown',kd);addEventListener('keyup',ku);cleanup.push(()=>{removeEventListener('keydown',kd);removeEventListener('keyup',ku);});
   // orbit drag when not spawned
   let oy=.3,ox=0,drag:{x:number;y:number}|null=null;
   const pd=(e:PointerEvent)=>{if(!spawnRef.current)drag={x:e.clientX,y:e.clientY};},pm=(e:PointerEvent)=>{if(drag){ox-=(e.clientX-drag.x)*.006;oy=Math.max(-1.3,Math.min(1.3,oy+(e.clientY-drag.y)*.006));drag={x:e.clientX,y:e.clientY};}},pu=()=>{drag=null;};
   canvas.addEventListener('pointerdown',pd);addEventListener('pointermove',pm);addEventListener('pointerup',pu);cleanup.push(()=>{canvas.removeEventListener('pointerdown',pd);removeEventListener('pointermove',pm);removeEventListener('pointerup',pu);});
   const resize=()=>{const r=host.current!.getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/Math.max(1,r.height);camera.updateProjectionMatrix();};
   const ro=new ResizeObserver(resize);ro.observe(host.current!);resize();cleanup.push(()=>ro.disconnect());
   // perf: measure fps for 3s windows and shrink the blade count if the phone can't hold ~50fps
   let fpsT=0,fpsN=0,fps=0,last=performance.now(),t=0,hudT=0;const camTarget=new THREE.Vector3(),camPos=new THREE.Vector3(0,6,22);
   const frame=()=>{raf=requestAnimationFrame(frame);const now=performance.now();const dt=Math.min(.05,(now-last)/1000);last=now;t+=dt;UG.uT.value=t;
    fpsT+=dt;fpsN++;if(fpsT>=3){fps=fpsN/fpsT;fpsT=0;fpsN=0;if(fps<48&&bladeCap>2000){bladeCap=Math.floor(bladeCap*.75);bladeGeo.instanceCount=bladeCap;}(window as any).__lwPerf={fps:+fps.toFixed(1),blades:bladeCap};}
    tickAcc+=dt;if(tickAcc>=TICK_S){tickAcc=0;applyTick();}
    latPivot.rotation.y+=dt*.02;latObj.rotation.x+=dt*.03;latObj.rotation.z+=dt*.017;
    // residents wander
    const play=UG.uPlay.value;play[0].copy(bN);residents.slice(0,6).forEach((r,i)=>play[i+1].copy(r.n));play[7].copy(spawnRef.current?pN:bN);
    // things wake when the spreading grass reaches them; touched things grow / pulse
    for(const th of things){if(!th.awake){const c=gpts.some(g=>ang(th.n,g)/PR<UG.uSpread.value-.2);if(c){th.awake=true;th.grow=1;}}
     th.cool=Math.max(0,th.cool-dt);th.pulse=Math.max(0,th.pulse-dt*.8);const s0=th.node.scale.x,tg=th.awake?th.size*th.grow*(1+th.pulse*.25):0.001;th.node.scale.setScalar(s0+(tg-s0)*Math.min(1,dt*2));}
    // residents explore things and each other; everything can touch everything
    socialCool=Math.max(0,socialCool-dt);
    for(const r of residents as any[]){r.pause=Math.max(0,(r.pause||0)-dt);
     const nt=nearestThing(r.n);if(nt&&nt.d<.35&&r.pause<=0){if(touch(nt.t,r.name))r.pause=1.5;}
     else if(nt&&nt.d<4&&Math.sin(t*.2+r.wob)>0)steerTo(r.n,r.f,nt.t.n,dt*1.5);else turn(r.n,r.f,Math.sin(t*.4+r.wob)*dt*.8);
     for(const o of residents as any[])if(o!==r&&ang(r.n,o.n)<.5){steerTo(r.n,r.f,r.n.clone().multiplyScalar(2).sub(o.n),dt*2);if(socialCool<=0&&!spawnRef.current){socialCool=25;lineRef.current(r.name+' and '+o.name+' bumped noses.');}}
     if(ang(r.n,bN)<.6){steerTo(r.n,r.f,r.n.clone().multiplyScalar(2).sub(bN),dt*2);}
     if(r.pause<=0)walkOn(r.n,r.f,r.spd*dt);place(r.node,r.n,r.f);}
    // beast: wander by traits; when you're spawned in, run to greet (timing from JSON)
    const sp=spawnRef.current;if(sp&&!wasSpawned){pN.copy(bN).applyAxisAngle(bF,.0).addScaledVector(bF,-3/PR).normalize();pF.copy(bF);pF.addScaledVector(pN,-pF.dot(pN)).normalize();spawnT=0;greetT=-1;travNode.visible=true;}
    if(sp&&!wasSpawned)lineRef.current('A new traveler on the grass.');
    if(!sp&&wasSpawned){travNode.visible=false;lineRef.current('Grass will keep growing while you’re gone.');}wasSpawned=sp;
    let bSpeed=0;
    if(sp&&spawnT>=0){bSpeed=0;}// your beast spots you and freezes while you arrive
    else if(sp){const side=new THREE.Vector3().crossVectors(pN,pF).normalize();const goal=pN.clone().addScaledVector(pF,.9/PR).addScaledVector(side,.5/PR).normalize();const toP=goal.clone().sub(bN);const dist=Math.acos(Math.min(1,bN.dot(goal)))*PR+1.5*TRAV_H-.05;const dir=toP.addScaledVector(bN,-toP.dot(bN));
     if(dist>1.5*TRAV_H){if(dir.lengthSq()>1e-8){bF.copy(dir.normalize());}const v=1.6;walkOn(bN,bF,v*dt);bSpeed=1;greetT=-1;}
     else if(greetT<0){greetT=0;lineRef.current('YOU’RE HERE. Rawr! Come see what I built.');traits=driftTraits(traits,u,bKey,'greet');brain.mode='glance';}
     if(greetT>=0)greetT+=dt;}
    else{const nt=nearestThing(bN);if(nt&&nt.d<.4){if(touch(nt.t,'beast')){const k=nt.t.kind;learned[k]=(learned[k]||0)+1;traits=driftTraits(traits,u,bKey,(THING_LESSON as any)[k]||'day');try{localStorage.setItem('lw:learned:'+bKey,JSON.stringify(learned));}catch{}}}
     if(nt&&nt.d<5*(.3+traits.curiosity))steerTo(bN,bF,nt.t.n,dt*1.2);const v=.2+.35*traits.curiosity;walkOn(bN,bF,v*dt);bSpeed=.35;}
    if(sp&&spawnT<0){const nt=nearestThing(pN);if(nt&&nt.d<.5&&touch(nt.t,'you'))lineRef.current('You touched a '+nt.t.kind+'. It answers.');}
    brain.speed+=(bSpeed-brain.speed)*Math.min(1,dt*4);brain.bob+=dt*(4+brain.speed*8);brain.mode=brain.speed>.5?'run':greetT>=0&&greetT<RG.count/RG.fps?'glance':'walk';
    place(beastNode,bN,bF);
    if(plush){const greetHop=greetT>=0&&greetT<(RG.segments.greet[1]-RG.segments.greet[0]+1)/RG.fps?Math.sin(greetT/((RG.segments.greet[1]-RG.segments.greet[0]+1)/RG.fps)*Math.PI)*.15:0;beastNode.position.addScaledVector(bN,greetHop);
     plush.drive(dt,brain,{stiffness:.7+traits.calm*.6,damping:1,turbulence:0,wind:{x:.2,z:.1},mood:{joy:traits.joy,fear:1-traits.calm,curiosity:traits.curiosity,calm:traits.calm,mischief:.3}},sp?{x:travNode.position.x,y:travNode.position.y+TRAV_H*.8,z:travNode.position.z}:null);}
    glowBoost=Math.max(0,glowBoost-dt*.8);(glow.material as any).opacity=.35+.35*(.5+.5*Math.sin(t*6.2831*.25))+glowBoost*.3;
    glow.position.copy(beastNode.position).addScaledVector(bN,TRAV_H*1.6).addScaledVector(new THREE.Vector3().crossVectors(bN,bF).normalize(),-TRAV_H*.6);
    // traveler + camera
    if(sp){let ix=joy.current.x,iy=joy.current.y;const K=keys.current;if(K.has('w')||K.has('arrowup'))iy=-1;if(K.has('s')||K.has('arrowdown'))iy=1;if(K.has('a')||K.has('arrowleft'))ix=-1;if(K.has('d')||K.has('arrowright'))ix=1;
     const mag=Math.min(1,Math.hypot(ix,iy));
     if(spawnT>=0){spawnT+=dt;const fr=Math.min(F.traveler_spawn.count-1,Math.floor(spawnT*F.traveler_spawn.fps));trav.material.map=tSpawn;setFrame(tSpawn,F.traveler_spawn.cols,1,fr,0);if(spawnT>F.traveler_spawn.count/F.traveler_spawn.fps)spawnT=-1;}
     else if(mag>.08){turn(pN,pF,-ix*dt*2.2*(iy>.3?-1:1));const fwd=-iy;walkOn(pN,pF,(fwd>=0?1:-1)*Math.max(.25,Math.abs(fwd))*mag*1.8*dt);
      const ang=Math.atan2(ix,-iy);const oct=((Math.round(ang/(Math.PI/4))%8)+8)%8;const ROW8=['N','NE','E','SE','S','SW','W','NW'][oct];const row=ROWS.indexOf(ROW8);
      trav.material.map=tWalk;setFrame(tWalk,F.traveler_walk.cols,8,Math.floor(t*F.traveler_walk.fps)%F.traveler_walk.cols,row<0?4:row);}
     else{trav.material.map=tIdle;setFrame(tIdle,F.traveler_idle.cols,1,Math.floor(t*F.traveler_idle.fps)%F.traveler_idle.cols,0);}
     place(travNode,pN,pF);
     camTarget.copy(pN).multiplyScalar(PR+TRAV_H*.7);const want=pN.clone().multiplyScalar(PR+1.9).addScaledVector(pF,-3.2);camPos.lerp(want,Math.min(1,dt*5));camera.position.copy(camPos);camera.up.copy(pN);camera.lookAt(camTarget);}
    else{const target=bN.clone().multiplyScalar(PR);const d=PR*4.3;const want=bN.clone().multiplyScalar(1.2).add(new THREE.Vector3(Math.cos(oy)*Math.sin(ox),Math.sin(oy),Math.cos(oy)*Math.cos(ox))).normalize().multiplyScalar(d);
     camPos.lerp(want,Math.min(1,dt*3));camera.position.copy(camPos);camera.up.set(0,1,0);camera.lookAt(target.multiplyScalar(.15));}
    renderer.render(scene,camera);
    hudT+=dt;if(hudT>.5){hudT=0;const last=u.history?.[u.history.length-1];setHud({tick:u.tick,simE:last?.sim_E??null,life:u.life.length,storms:u.storms.length,cover:Math.min(1,UG.uSpread.value/Math.PI),traits,learned:{...learned},awake:things.filter((x:any)=>x.awake).length,blades:bladeCap,fps:+fps.toFixed(0)});}
   };
   frame();(window as any).__lw={spawn:()=>setSpawned(true)};
   cleanup.push(()=>{renderer.dispose();plush?.dispose();scene.traverse((o:any)=>{o.geometry?.dispose?.();o.material?.dispose?.();});});
  })().catch(e=>{if(!disposed)setErr(String(e?.message||e));});
  return()=>{disposed=true;cancelAnimationFrame(raf);cleanup.forEach(f=>{try{f();}catch{}});};
 },[genome,beastKey]);
 // touch joystick
 const jd=(e:React.PointerEvent)=>{(e.target as Element).setPointerCapture(e.pointerId);joy.current={x:0,y:0,active:true,id:e.pointerId,cx:e.clientX,cy:e.clientY};setStick({x:0,y:0});};
 const jm=(e:React.PointerEvent)=>{const j=joy.current;if(!j.active||e.pointerId!==j.id)return;const dx=(e.clientX-j.cx)/50,dy=(e.clientY-j.cy)/50;const m=Math.max(1,Math.hypot(dx,dy));j.x=dx/m;j.y=dy/m;setStick({x:j.x,y:j.y});};
 const ju=()=>{joy.current={...joy.current,x:0,y:0,active:false};setStick(null);};
 const T=hud.traits;
 return <div ref={host} className="lw-root" data-living-world={spawned?'spawned':'orbit'} style={{position:'fixed',inset:0,zIndex:1000,background:'#05030f',touchAction:'none',color:'#efeaff',font:'13px/1.35 system-ui,sans-serif'}}>
  <canvas ref={canvasRef} style={{position:'absolute',inset:0,width:'100%',height:'100%',display:'block'}}/>
  <div style={{position:'absolute',top:'calc(env(safe-area-inset-top) + 10px)',left:10,right:10,display:'flex',flexWrap:'wrap',gap:6,pointerEvents:'none'}}>
   <span style={pill('#2b6cb0')} data-lw-spark>{LW_LABELS.spark}</span><span style={pill('#9b2c2c')} data-lw-growth>{LW_LABELS.growth}</span><span style={pill('#553c9a')} data-lw-model>{LW_LABELS.model}</span>
  </div>
  <div style={{position:'absolute',left:10,right:10,bottom:'calc(env(safe-area-inset-bottom) + 10px)',display:'flex',justifyContent:'space-between',alignItems:'flex-end',gap:8,pointerEvents:'none'}}>
   <div style={{background:'rgba(10,6,30,.72)',borderRadius:12,padding:'8px 10px',maxWidth:'62%',pointerEvents:'auto'}}>
    <b>{beastName||'Your beast'}</b> {genome||(typeof window!=='undefined'&&(window as any).__beastGenome)?'':'(no saved beast yet — hatch one in the Cage)'}<br/>
    tick {hud.tick} · sim E {hud.simE??'—'} · life {hud.life} · storms {hud.storms} · grass {Math.round(hud.cover*100)}%<br/>
    {hud.learned?<>things awake {hud.awake??0} · learned {Object.entries(hud.learned).map(([k,v])=>k+' '+v).join(' · ')||'—'}<br/></>:null}
    {T?<>curious {T.curiosity.toFixed(2)} · social {T.sociality.toFixed(2)} · calm {T.calm.toFixed(2)} · joy {T.joy.toFixed(2)} · {T.experiences} experiences</>:null}
    {err?<div style={{color:'#ffb4b4'}}>Couldn’t load the world: {err}</div>:null}
   </div>
   <div style={{display:'flex',flexDirection:'column',gap:6,pointerEvents:'auto'}}>
    {!spawned?<button type="button" data-lw-spawn onClick={()=>setSpawned(true)} style={btn('#6b46c1')}>✦ Spawn in</button>:<button type="button" data-lw-exit onClick={()=>setSpawned(false)} style={btn('#444')}>Exit to orbit</button>}
    {onClose?<button type="button" data-lw-close onClick={onClose} style={btn('#222')}>Close world</button>:null}
   </div>
  </div>
  {line?<div data-lw-line style={{position:'absolute',left:'50%',top:'calc(env(safe-area-inset-top) + 70px)',transform:'translateX(-50%)',background:'rgba(20,10,50,.82)',borderRadius:12,padding:'8px 14px',fontSize:15,maxWidth:'86%',textAlign:'center',pointerEvents:'none'}}>{line}</div>:null}
  {spawned?<div data-lw-joystick onPointerDown={jd} onPointerMove={jm} onPointerUp={ju} onPointerCancel={ju}
   style={{position:'absolute',left:'calc(50% - 60px)',bottom:'calc(env(safe-area-inset-bottom) + 120px)',width:120,height:120,borderRadius:'50%',background:'rgba(255,255,255,.08)',border:'2px solid rgba(255,255,255,.25)',touchAction:'none'}}>
   <div style={{position:'absolute',left:60-22+(stick?.x||0)*38,top:60-22+(stick?.y||0)*38,width:44,height:44,borderRadius:'50%',background:'rgba(200,180,255,.55)'}}/>
  </div>:null}
 </div>;
}
const pill=(c:string)=>({background:c,borderRadius:999,padding:'3px 8px',fontSize:11,opacity:.92}) as const;
const btn=(c:string)=>({background:c,color:'#fff',border:0,borderRadius:10,padding:'10px 14px',fontSize:14,fontWeight:600}) as const;
