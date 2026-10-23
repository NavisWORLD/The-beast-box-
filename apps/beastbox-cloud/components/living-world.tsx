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
import {worldThings,THING_LESSON,biomeParams,biomeAt,BIOME_PROPS,BIOME_FEEL,BIOME_NAMES,lwStream as lwS} from '@/lib/universe/living-world.mjs';
// Biome GLSL baked from seeded params (same rules as biomeAt in lib/universe/living-world.mjs).
function biomeGLSL(bp:any){const f=(ws:any[])=>ws.map(w=>`${w.a.toFixed(4)}*sin(dot(n,vec3(${w.k.map((x:number)=>x.toFixed(4)).join(',')}))+${w.p.toFixed(4)})`).join('+');const F=(x:number)=>x.toFixed(4);
 // ids: 0 ocean 1 plains 2 heartwood 3 beach 4 glacier 5 tundra 6 pine 7 ember 8 papersea 9 mushroom 10 peaks
 return `float bH(vec3 n){return ${f(bp.h)};}float bM(vec3 n){return ${f(bp.m)};}
 int biome(vec3 n){float h=bH(n),m=bM(n),c=1.0-abs(n.y)*1.15+${F(bp.tb)}+0.1*m-0.15*max(0.0,h);
  if(c<0.02)return 4;if(h<${F(bp.sea)})return 0;if(h>0.56)return 10;if(h<${F(bp.sea+0.1)}&&c>0.45)return 3;if(c>0.86)return 7;
  if(h<${F(bp.sea+0.26)}&&m>0.08)return c>0.5?9:8;if(c<0.36)return m>0.0?6:5;return h>0.22?2:1;}
 vec3 bCol(int b,vec3 n){float h=bH(n),k=bM(n);
  if(b==0)return mix(vec3(.05,.2,.5),vec3(.2,.6,.85),smoothstep(-.7,${F(bp.sea)},h))+vec3(.15,.05,.2)*pow(max(0.0,sin(k*90.0+h*70.0)),24.0);
  if(b==1)return mix(vec3(.45,.75,.3),vec3(.95,.8,.25),.25*step(.8,sin(h*60.0)));if(b==2)return vec3(.2,.45,.18);if(b==3)return vec3(.95,.86,.62);
  if(b==4)return mix(vec3(.85,.93,1.0),vec3(.55,.8,1.0),.3*sin(k*25.0)+.3);if(b==5)return mix(vec3(.55,.75,.72),vec3(.6,.5,.9),.5+.5*sin(k*35.0));
  if(b==6)return vec3(.1,.28,.2);if(b==7)return mix(vec3(.3,.15,.12),vec3(1.0,.42,.12),pow(.5+.5*sin(h*23.0+k*61.0+n.x*40.0),5.0));
  if(b==8)return mix(vec3(.85,.85,.78),vec3(.55,.7,.65),.5+.5*sin(k*30.0));if(b==9)return mix(vec3(.35,.25,.45),vec3(.75,.35,.6),.5+.5*sin(h*45.0));
  return mix(vec3(.55,.55,.62),vec3(.9,.9,1.0),smoothstep(.56,.9,h));}
 // borders blend: average the biome colour over a small neighbourhood
 vec3 biomeCol(int b0,vec3 n){vec3 t=normalize(cross(n,vec3(.3,1.0,.2)));vec3 s=cross(n,t);float e=.022;
  return (bCol(b0,n)*2.0+bCol(biome(normalize(n+t*e)),n)+bCol(biome(normalize(n-t*e)),n)+bCol(biome(normalize(n+s*e)),n)+bCol(biome(normalize(n-s*e)),n))/6.0;}`;}
import * as WFmod from '@/lib/universe/world-field.mjs';
const {createWorldField,stepWorldField,legendAt,fieldRGBA,createCreatureLoop,stepCreature,cellOf,LEGEND}=WFmod as any;
import {addVolcanoIsland,addCosmoSky,sheet as lfSheet,LF as LANDF} from '@/lib/universe/landforms-three';
import {createWorldCues,stepWorldCues} from '@/lib/universe/world-mechanics.mjs';
import {isSoftwareGL} from '@/lib/three/soft-gl';
import {addMechanics,createAsciiPass,underwaterColor} from '@/lib/universe/mechanics-three';
import {weatherFrom,createMover,stepMover,createWater,stepWater,waterTotal} from '@/lib/universe/world-mechanics.mjs';
import {LW_LABELS,gatheringPoints,spreadAngle,initialTraits,driftTraits,lattice12D,lwStream,unitFrom} from '@/lib/universe/living-world.mjs';
import {ARTIST_RESIDENTS} from '@/lib/companion/artist-residents.mjs';
import {cosmicEvents,cosmicLine,createWindow,stepWindow,windowLine,seededMood,spreadMood,napGroup,buildKind,advanceBuild,coexistLine,worldLine,learnBiome,worldRecord,toJsonl,windowEmissive,traitIcon,MOOD_ICON,ZEREF_ID} from '@/lib/universe/living-alive.mjs';
import {addCageSurface} from '@/lib/universe/surface-three';
import {createAliveGate} from '@/lib/universe/alive-props.mjs';
import {zoomBlend,zoomDistance,stepZoom,clampAboveGround,isMeadow} from '@/lib/universe/groundcover.mjs';
import {addHeaven} from '@/lib/worlds/heaven';
import {buildPlush,type PlushGenome} from './creature-plush-3d';
const ART='/universe/livingworld/';
// All event lines are Cosmic Emeth's (lib/universe/data/living_world_lines.json + biome_lore.json via living-alive.mjs).
const CX=ART+'coexist/'; // Cosmo's coexist art: models/{cairn,flower_ring,burrow}_stage{1,2,3}.glb, sprites/, moods.json
const PR=8;           // planet radius (world units)
const TRAV_H=.5;      // traveler height
type Traits={curiosity:number;sociality:number;calm:number;joy:number;experiences:number};
export default function LivingWorld({genome,beastKey,beastName,onClose,embedded=false,onExpand}:{genome?:PlushGenome|null;beastKey?:string|null;beastName?:string|null;onClose?:()=>void;embedded?:boolean;onExpand?:()=>void}){
 const host=useRef<HTMLDivElement>(null);const hudBiome=useRef<HTMLSpanElement>(null);const canvasRef=useRef<HTMLCanvasElement>(null);
 const [spawned,setSpawned]=useState(()=>{if(embedded)return false;try{return sessionStorage.getItem('lw:spawned')==='1';}catch{return false;}});const [watch,setWatch]=useState(embedded);const watchRef=useRef(false);watchRef.current=watch;const spawnRef=useRef(false);
 const [hud,setHud]=useState<{tick:number;simE:number|null;life:number;storms:number;cover:number;traits:Traits|null;blades:number;fps:number;learned?:Record<string,number>;awake?:number}>({tick:0,simE:null,life:0,storms:0,cover:0,traits:null,blades:0,fps:0});
 const [err,setErr]=useState<string|null>(null);const [line,setLine]=useState<string|null>(null);const lineRef=useRef(setLine);lineRef.current=setLine;
 useEffect(()=>{if(!line)return;const id=setTimeout(()=>setLine(null),4200);return()=>clearTimeout(id);},[line]);
 const [ascii,setAscii]=useState(false);const asciiRef=useRef(false);asciiRef.current=ascii;const [flying,setFlying]=useState(false);const flyRef=useRef(false);flyRef.current=flying;const joy=useRef({x:0,y:0,active:false,id:-1,cx:0,cy:0});const keys=useRef(new Set<string>());
 const [stick,setStick]=useState<{x:number;y:number}|null>(null);
 useEffect(()=>{if(embedded)return;try{sessionStorage.setItem('lw:spawned',spawned?'1':'0');}catch{}},[spawned,embedded]);
 useEffect(()=>{spawnRef.current=spawned;(window as any).__lwSpawned=spawned;},[spawned]);
 // rebuild only when the beast itself changes, not on every session poll (that rebuild was the ~10s 'respawn')
 const gKey=genome?JSON.stringify(genome):'';
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
   const aliveGate=createAliveGate();const camera=new THREE.PerspectiveCamera(55,1,.05,400);
   const L=new THREE.TextureLoader();const tex=(f:string,rep=false)=>{const t=L.load(ART+f);t.colorSpace=THREE.SRGBColorSpace;if(rep){t.wrapS=t.wrapT=THREE.RepeatWrapping;}return t;};
   const hemi=new THREE.HemisphereLight(0xb9a8ff,0x223322,1.1);scene.add(hemi);const sun=new THREE.DirectionalLight(0xfff1dd,1.6);sun.position.set(20,14,10);scene.add(sun);scene.add(sun.target);
   // a real sun: day/night from the wall clock (approach from Genesis X env sim: light = max(.1, h*.8+.2), ambient = max(.1, h*.3+.1))
   renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;sun.castShadow=true;sun.shadow.mapSize.set(phone?512:1024,phone?512:1024);
   {const c=sun.shadow.camera as any;c.left=c.bottom=-6;c.right=c.top=6;c.near=1;c.far=60;c.updateProjectionMatrix();}sun.shadow.bias=-.002;
   // star from the recorded-seed universe: the home planet's own star; colour from its temperature (blackBodyToRGB, Cory's Lost Cosmos file)
   const blackBodyToRGB=(temp:number)=>{temp/=100;let r:number,g:number,b:number;if(temp<=66){r=255;g=99.47*Math.log(temp)-161.12;b=temp<=19?0:138.52*Math.log(temp-10)-305.04;}else{r=329.7*Math.pow(temp-60,-.133);g=288.12*Math.pow(temp-60,-.0755);b=255;}const c=(x:number)=>Math.max(0,Math.min(255,x))/255;return new THREE.Color(c(r),c(g),c(b));};
   const homePl=[...(u.planets||[])].sort((a:any,b:any)=>(b.habitability||0)-(a.habitability||0))[0];const homeStar=(u.stars||[]).find((x:any)=>x.id===homePl?.star)||u.stars?.[0];
   const starCol=blackBodyToRGB(homeStar?.temperature_k||5800);sun.color.copy(starCol);(window as any).__lwStar={id:homeStar?.id,temperature_k:homeStar?.temperature_k,planet:homePl?.id};
   renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;
   // the Cage's sun glow + light shaft + bloom halo (lib/worlds/heaven, shared with the home Cage), standing over whoever you're close to
   const heaven=addHeaven(THREE,scene,{low:phone,rand:lwStream(u.seed+':heaven')});heaven.root.scale.setScalar(.4);
   // key light on the beast so it reads as brightly as in the Cage
   const beastLamp=new THREE.PointLight(0xfff1e6,7,TRAV_H*8,1.6);scene.add(beastLamp);
   const DAY_S=240;const sunDir=new THREE.Vector3(1,.3,.2).normalize();const SKY_DAY=new THREE.Color(0x86bfff),SKY_DUSK=new THREE.Color(0xff9a5a),SKY_NIGHT=new THREE.Color(0x05030f);
   const softGL=isSoftwareGL();// CI SwiftShader / GPU-less VMs: skip the heavy landform/mechanics layers so the main thread never starves (real GPUs incl. phones keep them)
   const cosmoSky=softGL?{update:(..._a:any[])=>{}}:addCosmoSky(THREE,scene,{radius:230,phone});const nova=lfSheet(THREE,LANDF+'vfx/supernova_4x4_256.png',{fps:10,loop:false});nova.sp.scale.setScalar(30);scene.add(nova.sp);(window as any).__lwNova=()=>{nova.sp.position.copy(sunDir).multiplyScalar(-150);nova.play();};const sunDisc=new THREE.Sprite(new THREE.SpriteMaterial({map:L.load(LANDF+'sky/sun_corona_512.png'),color:0xfff0c0,transparent:true,blending:THREE.AdditiveBlending,depthWrite:false,fog:false}));sunDisc.scale.setScalar(40);sunDisc.material.color.copy(starCol);scene.add(sunDisc);
   const starMesh=new THREE.Mesh(new THREE.SphereGeometry(6,32,20),new THREE.MeshBasicMaterial({color:starCol,toneMapped:false}));scene.add(starMesh);
   const moon=new THREE.Mesh(new THREE.SphereGeometry(2.2,24,16),new THREE.MeshStandardMaterial({color:0xd8dcef,emissive:0x40445a,roughness:1}));scene.add(moon);
   let starMat:any=null;
   // ---- stars + 12D lattice in the sky
   {const r=lwStream(u.seed+':sky');const n=phone?900:1800,p=new Float32Array(n*3);for(let i=0;i<n;i++){const v=unitFrom(r);const d=120+r()*80;p.set([v[0]!*d,v[1]!*d,v[2]!*d],i*3);}
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(p,3));starMat=new THREE.PointsMaterial({color:0xdde6ff,size:.6,sizeAttenuation:true,transparent:true});scene.add(new THREE.Points(g,starMat));}
   const lat=lattice12D(u.seed,phone?160:256);const lg=new THREE.BufferGeometry();lg.setAttribute('position',new THREE.Float32BufferAttribute(lat.verts.map(v=>v*7),3));lg.setIndex(lat.edges);
   const latObj=new THREE.LineSegments(lg,new THREE.LineBasicMaterial({color:0x8f7bff,transparent:true,opacity:.28,depthWrite:false}));latObj.position.set(0,0,0);
   const latPivot=new THREE.Group();latPivot.add(latObj);latObj.position.set(0,26,-30);scene.add(latPivot);
   // ---- planet ground: grass/soil tiles blended by a coverage field that spreads from gathering points
   const gpts=gatheringPoints(u,bKey).map(v=>new THREE.Vector3(...v));
   const UG:any={uRamp:{value:(()=>{const t=L.load('/universe/livingworld/landforms/ocean/water_depth_ramp_256x16.png');t.colorSpace=THREE.SRGBColorSpace;return t;})()},uFoam:{value:(()=>{const t=L.load('/universe/livingworld/landforms/ocean/foam_512.png');t.wrapS=t.wrapT=THREE.RepeatWrapping;return t;})()},uMap:{value:null},uUseMap:{value:0},uHeight:{value:null},uDisp:{value:0},uGlow:{value:null},uIdx:{value:null},uField:{value:0},uTiles:{value:null},uUseTiles:{value:0},uLeg:{value:Array.from({length:20},()=>new THREE.Vector3(9,9,9))},uMN:{value:(()=>{const t=L.load('/universe/livingworld/groundcover/textures/meadow_near_albedo_1024.png');t.colorSpace=THREE.SRGBColorSpace;t.wrapS=t.wrapT=THREE.RepeatWrapping;return t;})()},uMF:{value:(()=>{const t=L.load('/universe/livingworld/groundcover/textures/meadow_far_albedo_1024.png');t.colorSpace=THREE.SRGBColorSpace;t.wrapS=t.wrapT=THREE.RepeatWrapping;return t;})()},uGrass:{value:tex('ground_grass_tile_256.jpg',true)},uSoil:{value:tex('ground_soil_tile_256.jpg',true)},uMask:{value:tex('grass_edge_edge_mask.png',true)},
    uPts:{value:gpts},uPlay:{value:Array.from({length:8},()=>new THREE.Vector3())},uSpread:{value:spreadAngle(u)},uT:{value:0},uSun:{value:sun.position.clone().normalize()}};
   const COVER=`uniform sampler2D uHeight;uniform float uDisp;vec2 eqUV(vec3 n){return vec2(atan(n.z,n.x)/6.2832+.5,asin(clamp(n.y,-1.0,1.0))/3.1416+.5);}float disp(vec3 n){return uDisp>0.0?max(0.0,texture2D(uHeight,eqUV(n)).r-0.42)*uDisp:0.0;}uniform vec3 uPts[8];uniform float uSpread;float cover(vec3 n){float c=0.0;for(int i=0;i<8;i++){float a=acos(clamp(dot(n,uPts[i]),-1.0,1.0));c=max(c,smoothstep(uSpread,uSpread-0.35,a));}return c;}`;
   // beasts gather first on living land (plains/forest; tundra or pine near the poles), so pick the first seeded layout variant that puts the gathering point there
   const BP=(()=>{const g0=gpts[0];for(let i=0;i<64;i++){const bp=biomeParams(i?u.seed+':v'+i:u.seed);if(['plains','heartwood','pine','tundra'].includes(biomeAt(bp,[g0.x,g0.y,g0.z]) as string))return bp;}return biomeParams(u.seed);})();const BGL=biomeGLSL(BP);let biomeOf=(n:import('three').Vector3)=>biomeAt(BP,[n.x,n.y,n.z]) as string;
   const ground=new THREE.Mesh(new THREE.SphereGeometry(PR,phone?96:160,phone?64:110),new THREE.ShaderMaterial({uniforms:UG,
    vertexShader:`varying vec3 vN;varying vec2 vUv;varying vec3 vWp;${COVER}void main(){vN=normalize(position);vUv=uv*vec2(48.0,24.0);vec3 p=position+vN*disp(vN);vWp=p;gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.0);}`,
    fragmentShader:`uniform sampler2D uGrass,uSoil,uMask,uMap,uGlow,uIdx,uTiles,uMN,uMF,uRamp,uFoam;uniform float uT;uniform float uUseMap,uUseTiles,uField;uniform vec3 uSun,uLeg[20];varying vec3 vN;varying vec2 vUv;varying vec3 vWp;${COVER}${BGL}
     int legIdx(vec3 c){int bi=0;float bd=9.0;for(int i=0;i<20;i++){vec3 d=c-uLeg[i];float dd=dot(d,d);if(dd<bd){bd=dd;bi=i;}}return bi;}
     vec3 tri(sampler2D t,vec3 n){vec3 w=pow(abs(n),vec3(4.0));w/=w.x+w.y+w.z;vec3 p=n*${(PR/2).toFixed(1)};return texture2D(t,p.yz).rgb*w.x+texture2D(t,p.xz).rgb*w.y+texture2D(t,p.xy).rgb*w.z;}
     void main(){vec3 n=normalize(vN);int b=biome(n);float c=cover(n);float m=.5+.35*(tri(uMask,n*1.7).r-.5)+.25*(fract(sin(dot(floor(n*40.0),vec3(12.9,78.2,37.7)))*43758.5)-.5);float g=smoothstep(m-.2,m+.2,c*1.1);
      vec3 grassT=tri(uGrass,n),soilT=tri(uSoil,n);float det=.75+.6*dot(mix(soilT,grassT,g),vec3(.333));vec3 col=biomeCol(b,n)*det;
      // the spreading grass still grows: it thickens and brightens the living biomes
      vec3 gt=b==5||b==4?vec3(.8,.92,1.0):b==7?vec3(.55,.55,.55):b==3?vec3(.85,.9,.5):b==9?vec3(.75,.6,.9):vec3(1.0);
      if(b!=0&&b!=10)col=mix(col,col*1.1+grassT*gt*.4,g*(b==1||b==2||b==6?1.0:.6));
      if(uUseMap>.5){vec2 eq=eqUV(n);col=texture2D(uMap,eq).rgb*(.85+.3*det-.15)*(1.0+.12*g);
       // Cosmo's seamless biome tiles up close (atlas 5x4 in legend order, picked from the biome index map)
       if(uUseTiles>.5){float dc=distance(cameraPosition,vWp);float near=smoothstep(9.0,2.5,dc);if(uField>.5&&texture2D(uIdx,eq).a>.5)near=max(near,.85);if(near>0.0){int bi=legIdx(texture2D(uIdx,eq).rgb);vec2 tuv=fract(vec2(eq.x*96.0,eq.y*48.0));tuv=clamp(tuv,.02,.98);vec2 cell=vec2(float(bi-(bi/5)*5),float(bi/5));vec3 tc=texture2D(uTiles,(cell+vec2(tuv.x,1.0-tuv.y))/vec2(5.0,4.0)*vec2(1.0,1.0)+vec2(0.0,0.0)).rgb;col=mix(col,tc*(1.0+.12*g),near*.8);}}}
      // Cosmo's cage meadow (near ~2 m repeat x far 40-60 m macro, blended by distance) on every meadow biome, tinted by the biome colour
      if(uUseMap>.5){float dmM=distance(cameraPosition,vWp)/${(TRAV_H/1.7).toFixed(4)};float wM=1.0-smoothstep(90.0,170.0,dmM);if(wM>0.0){int bm=legIdx(texture2D(uIdx,eqUV(n)).rgb);
       // soft meadow mask: 5 dithered taps across the field cells so meadow edges blend instead of showing square tiles
       float mf=0.0;for(int k=0;k<5;k++){float ang=float(k)*2.39+fract(sin(dot(n,vec3(91.7,37.3,13.1)))*4375.5)*6.28;vec2 o=k==0?vec2(0.0):vec2(cos(ang),sin(ang))*vec2(1.0/96.0,1.0/48.0)*1.2;int bk=legIdx(texture2D(uIdx,eqUV(n)+o).rgb);mf+=(bk==3||bk==4||bk==5||bk==6||bk==11||bk==12||bk==13||bk==16||bk==18)?.2:0.0;}
       wM*=smoothstep(0.0,.8,mf);if(mf>0.0){vec3 nr=tri(uMN,n*3.4),fr=tri(uMF,n*.136);float fl=dot(fr,vec3(.333));vec3 md=mix(nr*(.55+fl*1.2),fr,smoothstep(15.0,60.0,dmM));
       vec3 tn=vec3(0.0);for(int i=0;i<20;i++)if(i==bm)tn=uLeg[i];col=mix(col,md*mix(vec3(1.0),tn*1.7,.45)*(1.05+.25*det),wM);}}}
      // Cosmo's ocean: depth from the height map (sea level .42) -> depth ramp (shore turquoise -> abyss indigo), shoreline foam
      if(uUseMap>.5){float hh=texture2D(uHeight,eqUV(n)).r;if(hh<.42){float dm=(.42-hh)*160.0;float tw=1.0-exp(-dm/12.0);vec3 wc=texture2D(uRamp,vec2(tw,.5)).rgb;
       float fo=texture2D(uFoam,eqUV(n)*vec2(60.0,30.0)+uT*.02).r*smoothstep(1.5,0.0,dm);col=mix(col,wc,mix(.55,.95,tw))+fo*.7;}}
      vec3 v=normalize(cameraPosition-n*${PR.toFixed(1)});float dif=max(0.0,dot(n,uSun));float l=.36+1.15*dif;col*=l;
      if(b==7)col+=vec3(.6,.2,.05)*pow(.5+.5*sin(bH(n)*50.0),8.0);if(b==10)col+=vec3(.2,.25,.4)*(1.0-dif);
      if(b==0)col+=vec3(.9,.95,1.0)*pow(max(0.0,dot(reflect(-uSun,n),v)),40.0)*.6;
      if(uUseMap>.5)col+=texture2D(uGlow,eqUV(n)).rgb*(1.0-smoothstep(-.1,.25,dot(n,uSun)))*1.1;
      float rim=pow(1.0-max(0.0,dot(n,v)),3.0);gl_FragColor=vec4(col+vec3(.35,.55,1.0)*rim*.45,1.0);}`}));
   scene.add(ground);
   {const sc=new THREE.Mesh(new THREE.SphereGeometry(PR+.012,phone?64:120,phone?40:80),new THREE.ShadowMaterial({opacity:.32}));sc.receiveShadow=true;scene.add(sc);}
   // Cosmo's painted maps swap in when present (2:1 equirect colour map); otherwise the procedural-from-seed biomes stay.
   // (the old maps/<name>_color.png slot is retired: Cosmo's biomes/*.webp maps + the seeded procedural biomes are the only source, so no 404s)
   // Cosmo v2 biome maps: colour + height (displaces the sphere) + glow + biome index; tiles up close; props scattered by biome from the seed
   // ---- Cory's engine runs the world: one CST loop (cst-integrator) drives a per-cell field; Cosmo's maps are only the first look
   const LW_TO_LEG:Record<string,string>={ocean:'deep_ocean',plains:'grassland',heartwood:'heartwood_forest',beach:'beach',glacier:'glacier',tundra:'crystal_moss',pine:'pine_forest',ember:'ember_fields',papersea:'paper_marsh',mushroom:'paper_marsh',peaks:'celestial_peaks',desert:'desert_dunes'};
   const WATER_IDS=new Set(['deep_ocean','shallow_ocean','jelly_geyser','frozen_sea']),HIGH_IDS=new Set(['mountain_rock','snow_cap','celestial_peaks','volcano']);
   let field:any=null,fieldTex:any=null,legRGB:number[][]=[];const recCounts=(u as any).runs?.[0]?.counts||null;
   const qid=bKey===ZEREF_ID?bKey:null; // world records are for Zeref (bb-deada969) only
   const beastLoop=createCreatureLoop('beast:'+bKey,u.seed,{counts:recCounts,qbeast_id:qid});const zerefLoop=createCreatureLoop('zeref',u.seed,{counts:recCounts}); // Zeref's state rides the loop; his records stay in his own (bb-deada969) pipeline
   const expKey='lw:exp:'+bKey;let expLog:any[]=(()=>{try{return JSON.parse(localStorage.getItem(expKey)||'[]')}catch{return []}})();if(expLog.length)beastLoop.prev=expLog[expLog.length-1].hash;
   const startField=()=>{if(field)return;const leg=legend;
    field=createWorldField({seed:u.seed,counts:recCounts,initial:(a:number[])=>{const v=new THREE.Vector3(a[0],a[1],a[2]);const id=cosmoBiome(v)||LW_TO_LEG[biomeAt(BP,a) as string]||'grassland';return {id,h:WATER_IDS.has(id)?-.2:HIGH_IDS.has(id)?.7:.2};}});
    legRGB=LEGEND.map((id:string)=>{const L=leg?.biomes?.find((b:any)=>b.id===id);const c=L?parseInt(L.rgb.slice(1),16):0;return [(c>>16)&255,(c>>8)&255,c&255];});
    fieldTex=new THREE.DataTexture(fieldRGBA(field,(i:number)=>legRGB[i]),field.W,field.H,THREE.RGBAFormat);fieldTex.magFilter=fieldTex.minFilter=THREE.NearestFilter;fieldTex.wrapS=THREE.RepeatWrapping;fieldTex.needsUpdate=true;
    if(leg){UG.uIdx.value=fieldTex;UG.uField.value=1;}
    biomeOf=(n)=>{const id=legendAt(field,[n.x,n.y,n.z]);return (COSMO_TO_LW[id]||'plains');};cosmoNameOf=(n)=>legendAt(field,[n.x,n.y,n.z]).replace(/_/g,' ').replace(/\b\w/g,(m:string)=>m.toUpperCase());
    (window as any).__lwField=()=>({tick:field.tick,changed:field.changed,tension:+field.storm.toFixed(3),lorenz:{...field.S.L},records:expLog.length,beast:beastLoop.S.ch,zeref:zerefLoop.S.ch});};
   // ---- the Cage surface everywhere: Cosmo's ground cover + trees, instanced, planted from the seed per biome (one renderer: lib/universe/surface-three)
   let surface:any=null;let island:any=null;let mech:any=null;let water:any=null;let weather:any={cloud:.3,rain:0,wind:[0,0]};const mover=createMover();const ascii=createAsciiPass(THREE,renderer,{phone});cleanup.push(()=>ascii.dispose());
   const buildSurface=()=>{if(surface||disposed)return;const tintOf:Record<string,[number,number,number]>={};for(const L of (legend?.biomes||[])){const c=parseInt(L.rgb.slice(1),16);tintOf[L.id]=[(c>>16)/255,((c>>8)&255)/255,(c&255)/255];}
    const tv=new THREE.Vector3();
    surface=addCageSurface(THREE,scene,{seed:u.seed+':surface',R:PR,mpu:TRAV_H/1.7,size:1.5,budget:phone?.22:.55,
     biomeAt:(d:number[])=>field?legendAt(field,d):(cosmoBiome(tv.set(d[0],d[1],d[2]))||'grassland'),lift:(n:any)=>hAt(n)-.004,tint:(b:string)=>tintOf[b]||null});
    // ASCII-CRAFT-style mechanics (engine-driven weather, flowing water, sea life, torch, mountains): additive, seeded
    mech=softGL?null:addMechanics(THREE,scene,{seed:u.seed,R:PR,mpu:TRAV_H/1.7,phone,unitFrom:(r:any)=>unitFrom(r) as number[],isWater:(v:any)=>WATER_IDS.has(field?legendAt(field,[v.x,v.y,v.z]):(cosmoBiome(v)||''))});
    if(field){water=createWater(field.W,field.H,Array.from(field.height));}
    // Cosmo's volcano island: IBM-seeded spot in the jelly sea (else deep/shallow ocean), away from the beast, bent onto the planet
    {const r=lwStream(u.seed+':island');const want=['jelly_geyser','deep_ocean','shallow_ocean'];let pick:any=null;
     for(const w of want){for(let i=0;i<160&&!pick;i++){const d=unitFrom(r) as number[];const v=new THREE.Vector3(d[0],d[1],d[2]);if(v.dot(gpts[0])>.82)continue;const id=field?legendAt(field,d):cosmoBiome(v);if(id===w)pick=v;}if(pick)break;}
     if(!pick)pick=new THREE.Vector3(...(unitFrom(r) as number[]));
     island=softGL?null:addVolcanoIsland(THREE,scene,{seed:u.seed,R:PR,mpu:TRAV_H/1.7,scale:.07,n:pick,phone});
     island.ready.then(()=>{(window as any).__lwIsland={n:pick.toArray().map((x:number)=>+x.toFixed(3)),biome:field?legendAt(field,pick.toArray()):cosmoBiome(pick),...island.state()};}).catch((e:any)=>{(window as any).__lwIslandErr=String(e);});}
    surface.ready.then((c:any)=>{if(disposed)return;blades.visible=false;(window as any).__lwSurface={counts:c,meshes:surface.meshes.length};}).catch((e:any)=>{(window as any).__lwSurfaceErr=String(e);});};
   let fieldAcc=0;
   const fieldStep=(dt:number,sunV:import('three').Vector3,activity:number)=>{if(!field)return;
    const heat=Math.min(1,Math.max(0,((homeStar?.temperature_k||5800)-3000)/6000));
    const ch=stepWorldField(field,dt,{sun:[sunV.x,sunV.y,sunV.z],starHeat:heat,activity,mood:{curiosity:traits.curiosity}});
    if(ch.length&&fieldTex){fieldTex.image.data.set(fieldRGBA(field,(i:number)=>legRGB[i]));fieldTex.needsUpdate=true;
     for(const ps of propSprites){const k=cellOf(field,[ps.n.x,ps.n.y,ps.n.z]);if(!ch.includes(k))continue;const id=LEGEND[field.idx[k]];ps.spr.visible=!!propSheets[id]&&ps.biome===id||!!propSheets[id];if(propSheets[id]&&ps.biome!==id){ps.biome=id;swapProp(ps,id);}}}
    storming=Math.max(storming,field.storm);
    fieldAcc+=dt;if(fieldAcc<1)return;const W1=fieldAcc;fieldAcc=0;
    const res=stepCreature(beastLoop,field,[bN.x,bN.y,bN.z],W1,traits,{others:[zerefLoop]});const zN=gpts[1]||gpts[0];stepCreature(zerefLoop,field,zN,W1,null,{others:[beastLoop]});
    if(res.drift)traits={...traits,...res.drift};
    for(const ev of res.events){if(ev.type==='affinity')say(beastNm+' feels a pull toward Zeref (affinity '+ev.affinity.toFixed(2)+').',6);}
    if(res.records.length){expLog=expLog.concat(res.records).slice(-400);try{localStorage.setItem(expKey,JSON.stringify(expLog));}catch{}(window as any).__lwExperiences=expLog;}};
   const propSheets:Record<string,any>={};let swapProp=(ps:any,id:string)=>{};
   const propSprites:any[]=[];let cosmoNameOf:(n:import('three').Vector3)=>string|null=()=>null;
   const BIO='/universe/livingworld/biomes/';let legend:any=null;let idxData:ImageData|null=null,hData:ImageData|null=null;const DISP=.14;
   const imgData=(url:string)=>new Promise<ImageData>((res,rej)=>{const im=new Image();im.crossOrigin='anonymous';im.onload=()=>{const c=document.createElement('canvas');c.width=im.width;c.height=im.height;const x=c.getContext('2d',{willReadFrequently:true})!;x.drawImage(im,0,0);res(x.getImageData(0,0,im.width,im.height));};im.onerror=rej;im.src=url;});
   const eqPx=(d:ImageData,n:import('three').Vector3)=>{const u2=Math.atan2(n.z,n.x)/(2*Math.PI)+.5,v2=Math.asin(Math.max(-1,Math.min(1,n.y)))/Math.PI+.5;const x=Math.min(d.width-1,Math.floor(u2*d.width)),y=Math.min(d.height-1,Math.floor((1-v2)*d.height));return (y*d.width+x)*4;};
   const hAt=(n:import('three').Vector3)=>{if(!hData)return 0;return Math.max(0,hData.data[eqPx(hData,n)]/255-.42)*UG.uDisp.value;};
   const COSMO_TO_LW:Record<string,string>={deep_ocean:'ocean',shallow_ocean:'ocean',beach:'beach',grassland:'plains',heartwood_forest:'heartwood',rainforest:'heartwood',savanna:'plains',desert_dunes:'desert',mountain_rock:'peaks',snow_cap:'glacier',glacier:'glacier',jelly_geyser:'beach',sunflower_ring:'plains',crystal_moss:'tundra',volcano:'ember',ember_fields:'ember',paper_marsh:'papersea',celestial_peaks:'peaks',pine_forest:'pine',frozen_sea:'glacier'};
   const cosmoBiome=(n:import('three').Vector3)=>{if(!idxData||!legend)return null;const i=eqPx(idxData,n);const r=idxData.data[i],g=idxData.data[i+1],b=idxData.data[i+2];let best=legend.biomes[0],bd=1e9;for(const L of legend.biomes){const c=parseInt(L.rgb.slice(1),16);const d=(r-(c>>16))**2+(g-((c>>8)&255))**2+(b-(c&255))**2;if(d<bd){bd=d;best=L;}}return best.id as string;};
   const texL=(f:string,srgb=true)=>new Promise<any>((res,rej)=>new THREE.TextureLoader().load(BIO+f,t=>{if(srgb)t.colorSpace=THREE.SRGBColorSpace;res(t);},undefined,rej));
   const cosmoReady=fetch(BIO+'home_biomes.json').then(r=>r.ok?r.json():null).then(async(lg:any)=>{if(!lg||disposed)return false;
    const [col,hgt,glw,idx,til,iD,hD]=await Promise.all([texL('home_color.webp'),texL('home_height.webp',false),texL('home_glow.webp'),texL(lg.index_map,false),texL(lg.tiles_atlas?.file||'tiles_atlas.webp'),imgData(BIO+lg.index_map),imgData(BIO+'home_height.webp')]);
    if(disposed)return false;idx.magFilter=idx.minFilter=THREE.NearestFilter;idx.generateMipmaps=false;til.wrapS=til.wrapT=THREE.ClampToEdgeWrapping;
    lg.biomes.forEach((L:any,i:number)=>{const c=parseInt(L.rgb.slice(1),16);UG.uLeg.value[i].set((c>>16)/255,((c>>8)&255)/255,(c&255)/255);});
    UG.uMap.value=col;UG.uHeight.value=hgt;UG.uGlow.value=glw;UG.uIdx.value=idx;UG.uTiles.value=til;UG.uUseMap.value=1;UG.uUseTiles.value=1;UG.uDisp.value=DISP;legend=lg;idxData=iD;hData=hD;(window as any).__lwCosmoMaps=true;startField();buildSurface();
    // biomeOf / names now come from the CST field (startField)
    // props: Cosmo's cutouts scattered by biome from the seed, sized from props.json height_m (explorer 1.70 m = TRAV_H)
    try{const pj=await fetch(BIO+'props.json').then(r=>r.json());Object.assign(propSheets,pj.sheets);
     swapProp=(ps:any,id:string)=>{const sh=pj.sheets[id];const fr=Object.values(sh.frames) as any[];const f=fr[(ps.spr.id*7)%fr.length];const img=ps.t.image;const t=new THREE.TextureLoader().load(BIO+sh.image,(tx)=>{const im:any=tx.image;const [x,y,w,h]=f.rect;tx.repeat.set(w/im.width,h/im.height);tx.offset.set(x/im.width,1-(y+h)/im.height);});t.colorSpace=THREE.SRGBColorSpace;ps.spr.material.map=t;ps.spr.material.needsUpdate=true;ps.t=t;ps.f=f;const hU=f.height_m*TRAV_H/1.7;ps.spr.scale.set(hU*f.rect[2]/f.rect[3],hU,1);void img;};const sheets:Record<string,any>={};const r=lwS(u.seed+':cosmo-props');const N=phone?70:160;const M_TO_U=TRAV_H/1.7;
     for(let i=0;i<N*3&&propSprites.length<N;i++){const v=new THREE.Vector3(...(unitFrom(r) as [number,number,number]));const bid=cosmoBiome(v);const sh=bid&&pj.sheets[bid];const pick=r();if(!sh)continue;
      const fr=Object.values(sh.frames) as any[];const f=fr[Math.floor(pick*fr.length)];if(!sheets[bid!]){const t=new THREE.TextureLoader().load(BIO+sh.image);t.colorSpace=THREE.SRGBColorSpace;sheets[bid!]=t;}
      const base=sheets[bid!];const t=base.clone();t.needsUpdate=true;const W0=sh.w||512,H0=sh.h||192;t.userData.rect=f.rect;
      const m=new THREE.SpriteMaterial({map:t,transparent:true,alphaTest:.4,depthWrite:true});const spr=new THREE.Sprite(m);const hU=f.height_m*M_TO_U;spr.scale.set(hU*f.rect[2]/f.rect[3],hU,1);spr.center.set(.5,1-(pj.anchor_y??168)/f.rect[3]);
      spr.position.copy(v).multiplyScalar(PR+hAt(v));scene.add(spr);propSprites.push({spr,t,f,n:v,biome:bid});}
     const fix=()=>{for(const ps of propSprites){const img=ps.t.image;if(!img||!img.width)continue;const [x,y,w,h]=ps.f.rect;ps.t.repeat.set(w/img.width,h/img.height);ps.t.offset.set(x/img.width,1-(y+h)/img.height);}};
     Object.values(sheets).forEach((t:any)=>{const done=()=>{fix();};if(t.image?.width)done();else{const iv=setInterval(()=>{if(t.image?.width){clearInterval(iv);done();}},200);cleanup.push(()=>clearInterval(iv));}});
     (window as any).__lwCosmoProps=propSprites.length;for(const th of things)th.node.position.copy(th.n).multiplyScalar(PR+hAt(th.n));}catch(e){(window as any).__lwCosmoPropsErr=String(e);}
    return true;}).catch(e=>{startField();buildSurface();(window as any).__lwCosmoMapsErr=String(e);return false;});
   // atmosphere rim, visible from orbit
   {const atm=new THREE.Mesh(new THREE.SphereGeometry(PR*1.07,64,40),new THREE.ShaderMaterial({transparent:true,depthWrite:false,side:THREE.BackSide,blending:THREE.AdditiveBlending,
     vertexShader:`varying vec3 vW;void main(){vW=(modelMatrix*vec4(position,1.0)).xyz;gl_Position=projectionMatrix*viewMatrix*vec4(vW,1.0);}`,
     fragmentShader:`varying vec3 vW;void main(){vec3 n=normalize(vW);vec3 v=normalize(cameraPosition-vW);float f=pow(1.0-abs(dot(n,v)),2.0);gl_FragColor=vec4(vec3(.35,.6,1.0)*f*1.1,f);}`}));scene.add(atm);}
   // other bodies: the first planets of the simulated universe, each with its own seeded biome look (water/temperature from its data)
   const COSMO_PLANETS=['crystal_moss','ember_world','glacier','jelly_geyser','paper_sea','sunflower_ring'];
   const bodies=(u.planets||[]).slice(0,phone?4:6).map((pl:any,i:number)=>{const bp=biomeParams(pl.id+':'+u.seed,{water:pl.water,temp:pl.temperature_k});
    const BU:any={uSun:UG.uSun,uMap:{value:null},uUseMap:{value:0},uHeight:{value:null},uDisp:{value:0}};
    {const cp=COSMO_PLANETS[i];new THREE.TextureLoader().load(BIO+cp+'_color.webp',t=>{t.colorSpace=THREE.SRGBColorSpace;BU.uMap.value=t;BU.uUseMap.value=1;},undefined,()=>{});new THREE.TextureLoader().load(BIO+cp+'_height.webp',t=>{BU.uHeight.value=t;BU.uDisp.value=.18;},undefined,()=>{});}const mesh=new THREE.Mesh(new THREE.SphereGeometry(1.2+Math.min(2.4,pl.radius_earth*.35),48,32),new THREE.ShaderMaterial({uniforms:BU,
     vertexShader:`varying vec3 vN;varying vec3 vW;uniform sampler2D uHeight;uniform float uDisp;void main(){vN=normalize(position);vec2 e=vec2(atan(vN.z,vN.x)/6.2832+.5,asin(clamp(vN.y,-1.0,1.0))/3.1416+.5);vec3 pp=position+vN*(uDisp>0.0?(texture2D(uHeight,e).r-.4)*uDisp*length(position):0.0);vW=(modelMatrix*vec4(pp,1.0)).xyz;gl_Position=projectionMatrix*viewMatrix*vec4(vW,1.0);}`,
     fragmentShader:`uniform vec3 uSun;uniform sampler2D uMap;uniform float uUseMap;varying vec3 vN;varying vec3 vW;${biomeGLSL(bp)}void main(){vec3 n=normalize(vN);vec3 c=(uUseMap>.5?texture2D(uMap,vec2(atan(n.z,n.x)/6.2832+.5,asin(clamp(n.y,-1.0,1.0))/3.1416+.5)).rgb:biomeCol(biome(n),n))*(.5+.9*max(0.0,dot(n,uSun)));gl_FragColor=vec4(c,1.0);}`}));
    const r=lwS(u.seed+':body:'+i);const a=r()*6.283,el=(r()-.5)*.9,d=45+i*14;mesh.position.set(Math.cos(a)*Math.cos(el)*d,Math.sin(el)*d,Math.sin(a)*Math.cos(el)*d);scene.add(mesh);return mesh;});
   // ---- flowing grass: instanced cross-quads from Cosmo's blade atlas; wind values from the JSON; scaled by coverage in-shader
   const W=frames.grass_blades.wind;let bladeCap=phone?6000:14000;
   const quad=new THREE.PlaneGeometry(.09,.32,1,3);quad.translate(0,.16,0);
   const cross=new THREE.BufferGeometry();{const a=quad.clone(),b=quad.clone();b.rotateY(Math.PI/2);const pos=[...a.attributes.position.array,...b.attributes.position.array],uv=[...a.attributes.uv.array,...b.attributes.uv.array];
    const ia=[...a.index!.array],ib=[...b.index!.array].map(i=>i+a.attributes.position.count);cross.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));cross.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));cross.setIndex([...ia,...ib]);}
   const bladeGeo=new THREE.InstancedBufferGeometry();bladeGeo.index=cross.index;bladeGeo.attributes.position=cross.attributes.position;bladeGeo.attributes.uv=cross.attributes.uv;
   const MAXB=14000;const iN=new Float32Array(MAXB*3),iR=new Float32Array(MAXB*2);{const r=lwStream(u.seed+':blades');for(let i=0;i<MAXB;i++){let v=unitFrom(r) as number[];for(let k=0;k<6&&['ocean','glacier','peaks'].includes(biomeAt(BP,v) as string);k++)v=unitFrom(r) as number[];iN.set(v,i*3);iR[i*2]=r();iR[i*2+1]=Math.floor(r()*8);}}
   bladeGeo.setAttribute('aN',new THREE.InstancedBufferAttribute(iN,3));bladeGeo.setAttribute('aR',new THREE.InstancedBufferAttribute(iR,2));bladeGeo.instanceCount=bladeCap;
   const bladeMat=new THREE.ShaderMaterial({uniforms:{...UG,uAtlas:{value:tex('grass_blade_atlas.png')},uAmp:{value:W.sway_amp_rad},uFreq:{value:W.freq_hz},uWave:{value:W.wave_len_world},uGust:{value:W.gust_amp},uGustF:{value:W.gust_freq_hz},uR:{value:PR}},
    side:THREE.DoubleSide,alphaTest:.5,
    vertexShader:`attribute vec3 aN;attribute vec2 aR;uniform vec3 uSun;uniform float uT,uAmp,uFreq,uWave,uGust,uGustF,uR;varying vec2 vUv;varying float vL;${COVER}
uniform vec3 uPlay[8];
     void main(){vec3 n=normalize(aN);float c=cover(n);float near=0.0;for(int i=0;i<8;i++)near=max(near,smoothstep(.22,.0,acos(clamp(dot(n,uPlay[i]),-1.0,1.0))));c*=1.0+near*.8;vec3 t=normalize(cross(abs(n.y)<.99?vec3(0,1,0):vec3(1,0,0),n));vec3 b=cross(n,t);
      float ca=cos(aR.x*6.283),sa=sin(aR.x*6.283);vec3 tx=t*ca+b*sa,tz=-t*sa+b*ca;
      vec3 p=position*(0.55+0.6*fract(aR.x*7.3))*c;float w=pow(uv.y,1.6);vec3 wp=n*(uR+disp(n));
      float ang=uAmp*w*sin(uT*6.2831*uFreq+dot(wp,normalize(vec3(1,.2,.4)))/uWave)+uGust*w*sin(uT*6.2831*uGustF+wp.x*.2);
      p.x+=sin(ang)*p.y;p.y*=cos(ang);
      vec3 world=wp+tx*p.x+n*p.y+tz*p.z;vUv=vec2((aR.y+uv.x)/8.0,uv.y);vL=.3+1.0*max(0.0,dot(n,uSun));
      gl_Position=projectionMatrix*viewMatrix*vec4(world,1.0);if(c<.02)gl_Position=vec4(2.0,2.0,2.0,1.0);}`,
    fragmentShader:`uniform sampler2D uAtlas;varying vec2 vUv;varying float vL;void main(){vec4 c=texture2D(uAtlas,vUv);if(c.a<.5)discard;gl_FragColor=vec4(c.rgb*vL,1.0);}`});
   const blades=new THREE.Mesh(bladeGeo,bladeMat);blades.frustumCulled=false;scene.add(blades);
   // ---- surface helpers: place an object at unit normal n facing tangent f
   const up=new THREE.Vector3(0,1,0),tmpQ=new THREE.Quaternion(),m4=new THREE.Matrix4();
   const place=(o:import('three').Object3D,n:import('three').Vector3,f:import('three').Vector3,lift=0)=>{o.position.copy(n).multiplyScalar(PR+lift+hAt(n));const x=new THREE.Vector3().crossVectors(n,f).normalize();const z=new THREE.Vector3().crossVectors(x,n);m4.makeBasis(x,n,z);o.quaternion.setFromRotationMatrix(m4);};
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
    else if(kind==='ice'){const c=m(new THREE.TetrahedronGeometry(.18,0),0xbfe6ff,.35);c.scale.y=1.8;c.position.y=.18;}
    else if(kind==='ember'){m(new THREE.ConeGeometry(.28,.35,7),0x3a1d14).position.y=.17;m(new THREE.SphereGeometry(.08,8,6),0xff6a1a,1.4).position.y=.36;}
    else if(kind==='mushroom'){m(new THREE.CylinderGeometry(.03,.04,.22,6),0xeeddcc).position.y=.11;const c=m(new THREE.SphereGeometry(.13,10,6,0,6.3,0,1.6),0xc04fa0,.5);c.position.y=.2;}
    else if(kind==='cactus'){m(new THREE.CapsuleGeometry(.05,.3,3,6),0x3f8a4a).position.y=.2;}
    else {m(new THREE.CylinderGeometry(.04,.06,.4,6),0x5a3a22).position.y=.2;m(new THREE.ConeGeometry(.22,.5,7),COL.tree,.1).position.y=.6;}
    return g;};
   // sky islands: floating rocks over the high ground, placed from the seed
   {const r=lwS(u.seed+':skyislands');for(let i=0;i<(phone?4:7);i++){let v=unitFrom(r) as number[];for(let k=0;k<20&&!['peaks','plains','heartwood'].includes(biomeAt(BP,v) as string);k++)v=unitFrom(r) as number[];
    const g=new THREE.Group();const rock=new THREE.Mesh(new THREE.ConeGeometry(.5,.9,7),new THREE.MeshStandardMaterial({color:0x6b6478,roughness:.9}));rock.rotation.x=Math.PI;rock.position.y=-.45;g.add(rock);
    const top=new THREE.Mesh(new THREE.CylinderGeometry(.5,.5,.12,7),new THREE.MeshStandardMaterial({color:0x5fae4a,emissive:0x1a3a10}));g.add(top);
    const n=new THREE.Vector3(...(v as [number,number,number]));place(g,n,new THREE.Vector3(1,0,0).addScaledVector(n,-n.x).normalize(),2.2+r()*1.5);g.scale.setScalar(.6+r()*.7);scene.add(g);}}
   const things=worldThings(u,phone?36:56).map((t0:any,ti:number)=>{const bm=biomeAt(BP,t0.n) as string;const ks=(BIOME_PROPS as any)[bm]||[t0.kind];const t={...t0,biome:bm,kind:ks[ti%ks.length]};const node=mkThing(t.kind);const n=new THREE.Vector3(...(t.n as [number,number,number]));const f=new THREE.Vector3(1,0,0).addScaledVector(n,-n.x).normalize();place(node,n,f);node.scale.setScalar(0.001);scene.add(node);return {...t,n,node,awake:false,grow:0,pulse:0,cool:0};});
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
   let bodyDrive:((dt:number,l:any,mp:any,look:any)=>void)|null=plush?(dt,l,mp,look)=>plush!.drive(dt,l,mp,look):null;let glbDispose=()=>{};
   if(gen)import('./creature-glb-beast').then(({loadBeastGlb})=>loadBeastGlb(THREE,gen,{tier:phone?'low':'med'})).then(gb=>{if(!gb||disposed){gb?.dispose();return;}
    const bb=new THREE.Box3().setFromObject(gb.root);const h=Math.max(.01,bb.max.y-bb.min.y);const k=TRAV_H*1.5/h;const holder=new THREE.Group();holder.scale.setScalar(k);holder.position.y=-bb.min.y*k;holder.add(gb.root);
    gb.root.traverse((o:any)=>{if(o.isMesh)o.castShadow=true;});if(plush)plush.root.visible=false;beastNode.add(holder);bodyDrive=(dt,l,mp,look)=>gb.drive(dt,l,mp,look);glbDispose=()=>gb.dispose();(window as any).__lwBeastGlb={plan:gb.plan,h,k};}).catch(e=>{(window as any).__lwBeastGlbErr=String(e);});
   cleanup.push(()=>glbDispose());
   plush?.root.traverse((o:any)=>{if(o.isMesh)o.castShadow=true;});
   const bN=gpts[0].clone(),bF=new THREE.Vector3(...unitFrom(lwStream(u.seed+':bf'))).addScaledVector(gpts[0],-1).normalize();bF.addScaledVector(bN,-bF.dot(bN)).normalize();
   const brain={speed:0,mode:'walk',sleep:0,lookCam:0,bob:0,heading:0,startle:0};
   const glow=new THREE.Sprite(new THREE.SpriteMaterial({map:tex('window_glow.png'),transparent:true,blending:THREE.AdditiveBlending,depthWrite:false}));glow.scale.setScalar(TRAV_H*1.5*.6);scene.add(glow);let glowBoost=0;
   // ---- traveler (Cosmo's sheets): walk 8-dir, idle, spawn-in
   const F=frames;const sheet=(f:string,cols:number,rows:number)=>{const t=tex(f);t.repeat.set(1/cols,1/rows);t.magFilter=THREE.NearestFilter;return t;};
   const tWalk=sheet(F.traveler_walk.file,F.traveler_walk.cols,8),tIdle=sheet(F.traveler_idle.file,F.traveler_idle.cols,1),tSpawn=sheet(F.traveler_spawn.file,F.traveler_spawn.cols,1);
   const trav=new THREE.Sprite(new THREE.SpriteMaterial({map:tIdle,transparent:true,depthWrite:false}));trav.scale.set(TRAV_H*1.15,TRAV_H*1.15,1);trav.center.set(F.anchor_px[0]/F.frame_size[0],1-F.anchor_px[1]/F.frame_size[1]);
   const travNode=new THREE.Group();travNode.add(trav);travNode.add(mkShadow(TRAV_H*.8));travNode.visible=false;scene.add(travNode);
   const explorer=new THREE.Group();travNode.add(explorer);let exMixer:any=null,exActs:Record<string,any>={},exCur='';const legs:any[]=[];
   {const M=(c:number,em=0)=>new THREE.MeshStandardMaterial({color:c,emissive:c,emissiveIntensity:em,roughness:.75});const H=TRAV_H;
    const add=(geo:any,mat:any,y:number,x=0,z=0)=>{const m=new THREE.Mesh(geo,mat);m.position.set(x,y,z);m.castShadow=true;explorer.add(m);return m;};
    for(const sx of [-1,1]){const lg=new THREE.Group();lg.position.set(sx*H*.08,H*.34,0);const m=new THREE.Mesh(new THREE.CylinderGeometry(H*.045,H*.04,H*.34,6),M(0x2a2238));m.position.y=-H*.17;m.castShadow=true;lg.add(m);explorer.add(lg);legs.push(lg);}
    add(new THREE.ConeGeometry(H*.2,H*.5,8),M(0x4b2f86),H*.58);add(new THREE.SphereGeometry(H*.13,12,10),M(0x1c1630),H*.86);
    add(new THREE.ConeGeometry(H*.15,H*.22,8),M(0x5b3aa0),H*1.02);for(const sx of [-1,1])add(new THREE.SphereGeometry(H*.025,6,6),M(0xffd75a,1.5),H*.87,sx*H*.05,H*.11);
    const lan=add(new THREE.OctahedronGeometry(H*.05,0),M(0x7ff3ff,1.8),H*.5,H*.22,H*.05);lan.castShadow=false;}
   fetch('/universe/livingworld/explorer.glb',{method:'HEAD'}).then(r=>{if(!r.ok)return;return import('three/examples/jsm/loaders/GLTFLoader.js').then(({GLTFLoader})=>new GLTFLoader().loadAsync('/universe/livingworld/explorer.glb')).then((g:any)=>{
    if(disposed)return;const root=g.scene;const bb=new THREE.Box3().setFromObject(root);const k=TRAV_H/Math.max(.01,bb.max.y-bb.min.y);root.scale.setScalar(k);root.position.y=-bb.min.y*k;root.traverse((o:any)=>{if(o.isMesh)o.castShadow=true;});
    explorer.clear();explorer.add(root);legs.length=0;exMixer=new THREE.AnimationMixer(root);for(const c of g.animations||[]){const nm=/walk/i.test(c.name)?'walk':/look/i.test(c.name)?'look':/idle/i.test(c.name)?'idle':c.name;exActs[nm]=exMixer.clipAction(c);}(window as any).__lwExplorerGlb=Object.keys(exActs);});}).catch(()=>{});
   // Zeref (bb-deada969) gets a visible body: his own rigged GLB + his own driver, standing at the second gathering point. Display only.
   const zHold=new THREE.Group();scene.add(zHold);let zDrv:any=null;
   {const zN=(gpts[1]||gpts[0]).clone().normalize();const r0=PR+hAt(zN);zHold.position.copy(zN).multiplyScalar(r0);zHold.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),zN);
    Promise.all([import('three/examples/jsm/loaders/GLTFLoader.js'),import('@/lib/creatures3d/zeref-glb-driver.mjs'),import('three/examples/jsm/libs/meshopt_decoder.module.js')]).then(([{GLTFLoader},zm,{MeshoptDecoder}]:any)=>new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).loadAsync(zm.ZEREF_GLB_URL).then((g:any)=>{
     if(disposed)return;const root=g.scene;const bb=new THREE.Box3().setFromObject(root);const k=TRAV_H*.75/Math.max(.01,bb.max.y-bb.min.y);root.scale.setScalar(k);root.position.y=-bb.min.y*k;
     root.traverse((o:any)=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;}});zHold.add(root);try{zDrv=zm.createZerefDriver(THREE,root,{seed:'zeref:'+u.seed});}catch{}(window as any).__lwZeref=true;})).catch((e:any)=>{(window as any).__lwZerefErr=String(e);});}
   const exPlay=(nm:string)=>{if(!exMixer||exCur===nm||!exActs[nm])return;exActs[exCur]?.fadeOut(.25);exActs[nm].reset().fadeIn(.25).play();exCur=nm;};
   const pN=new THREE.Vector3(),pF=new THREE.Vector3();let spawnT=-1,greetT=-1,wasSpawned=false;
   const setFrame=(t:import('three').Texture,cols:number,rows:number,col:number,row:number)=>{t.offset.set(col/cols,1-(row+1)/rows);};
   const ROWS=F.traveler_walk.rows as string[];const RG=frames.beast_run_to_greet;
   // ---- growth: SIMULATED ticks client-side
   let tickAcc=0;const TICK_S=2;
   let lwWet=0;const cues=createWorldCues();let cueN=0;
   const applyTick=()=>{if(field){let mo=0;for(let k=0;k<field.N;k+=7)mo+=field.moist[k];weather=weatherFrom(field,{moist:mo/Math.ceil(field.N/7)});
     if(water){stepWater(water,{rain:weather.rain});for(let k=0;k<field.N;k++)if(water.w[k]>.05)field.moist[k]=Math.min(1,field.moist[k]+.01*water.w[k]);
      lwWet=(Array.from(water.w) as number[]).filter((x:number)=>x>.05).length;(window as any).__lwWater={total:+waterTotal(water).toFixed(3),steps:water.steps,pooled:(Array.from(water.w) as number[]).filter((x:number)=>x>.05).length};}(window as any).__lwWeather=weather;}
    if(u.tick>=4000)return;const prev=u;u=grow(u,1);const ev=u.history[u.history.length-1]?.events||[];let exp=ev[0]?.kind||null;if(!exp&&u.storms.length>prev.storms.length)exp='storm';
    if(exp==='storm'){storming=1;puff=1;say(beastNm+' puffs up at the storm!',4);}
    // growth spreads faster where there is light and water (sunlit home, wet biome) — still SIMULATED
    {const hl=Math.max(0,gpts[0].dot(sunDir));const wet=({ocean:1,beach:.9,papersea:1,mushroom:1,plains:.8,heartwood:.9,pine:.7,tundra:.5,glacier:.3,ember:.2,peaks:.3} as any)[biomeOf(gpts[0])]??.6;growLW=Math.min(1.2,growLW+.004*hl*wet);try{localStorage.setItem('lw:growLW:'+bKey,String(growLW));}catch{}}
    traits=driftTraits(traits,u,bKey,exp||'day');glowBoost=1;alive.onTick(prev,u);UG.uSpread.value=Math.min(Math.PI,spreadAngle(u)+growLW);
    try{localStorage.setItem('lw:universe',JSON.stringify(u));localStorage.setItem('lw:traits:'+bKey,JSON.stringify(traits));}catch{}};
   // ---- input
   const kd=(e:KeyboardEvent)=>{keys.current.add(e.key.toLowerCase());if(e.key.toLowerCase()==='f')setFlying(v=>!v);},ku=(e:KeyboardEvent)=>{keys.current.delete(e.key.toLowerCase());};
   addEventListener('keydown',kd);addEventListener('keyup',ku);cleanup.push(()=>{removeEventListener('keydown',kd);removeEventListener('keyup',ku);});
   // orbit drag when not spawned
   let oy=.3,ox=0,drag:{x:number;y:number}|null=null;
   // zoom: wheel on desktop, two-finger pinch on iPhone (pointer events; the canvas is touch-action:none)
   let zT=1,zC=1,zMode='';const ptrs=new Map<number,{x:number;y:number}>();let pinch0=0;
   const pinchD=()=>{const a=[...ptrs.values()];return a.length<2?0:Math.hypot(a[0].x-a[1].x,a[0].y-a[1].y);};
   const wheel=(e:WheelEvent)=>{e.preventDefault();zT=stepZoom(zT,{wheel:e.deltaY*(e.deltaMode===1?16:1)});};canvas.addEventListener('wheel',wheel,{passive:false});cleanup.push(()=>canvas.removeEventListener('wheel',wheel));
   const pdz=(e:PointerEvent)=>{ptrs.set(e.pointerId,{x:e.clientX,y:e.clientY});if(ptrs.size===2){pinch0=pinchD();drag=null;}},pmz=(e:PointerEvent)=>{if(!ptrs.has(e.pointerId))return;ptrs.set(e.pointerId,{x:e.clientX,y:e.clientY});if(ptrs.size===2&&pinch0>0){const d=pinchD();zT=stepZoom(zT,{pinch:d/pinch0});pinch0=d;}},puz=(e:PointerEvent)=>{ptrs.delete(e.pointerId);if(ptrs.size<2)pinch0=0;};
   canvas.addEventListener('pointerdown',pdz);addEventListener('pointermove',pmz);addEventListener('pointerup',puz);addEventListener('pointercancel',puz);cleanup.push(()=>{canvas.removeEventListener('pointerdown',pdz);removeEventListener('pointermove',pmz);removeEventListener('pointerup',puz);removeEventListener('pointercancel',puz);});
   (window as any).__lwSetZoom=(z:number)=>{zT=Math.max(0,Math.min(1,z));};
   const pd=(e:PointerEvent)=>{if((!spawnRef.current||zC>.55)&&ptrs.size<2)drag={x:e.clientX,y:e.clientY};},pm=(e:PointerEvent)=>{if(drag&&ptrs.size<2){ox-=(e.clientX-drag.x)*.006;oy=Math.max(-1.3,Math.min(1.3,oy+(e.clientY-drag.y)*.006));drag={x:e.clientX,y:e.clientY};}},pu=()=>{drag=null;};
   canvas.addEventListener('pointerdown',pd);addEventListener('pointermove',pm);addEventListener('pointerup',pu);cleanup.push(()=>{canvas.removeEventListener('pointerdown',pd);removeEventListener('pointermove',pm);removeEventListener('pointerup',pu);});
   // E2 (Cosmo): a TAP (not a drag) on your beast opens Look Closer. Only the beast mesh counts; drags keep rotating.
   {const tapRay=new THREE.Raycaster(),tapNdc=new THREE.Vector2();let t0:{x:number;y:number;t:number}|null=null;
    const tpd=(e:PointerEvent)=>{t0={x:e.clientX,y:e.clientY,t:performance.now()};};
    const tpu=(e:PointerEvent)=>{const d=t0;t0=null;if(!d||!plush||Math.hypot(e.clientX-d.x,e.clientY-d.y)>8||performance.now()-d.t>450)return;
     const rc=canvas.getBoundingClientRect();tapNdc.set((e.clientX-rc.left)/rc.width*2-1,-(e.clientY-rc.top)/rc.height*2+1);tapRay.setFromCamera(tapNdc,camera);
     if(tapRay.intersectObject(beastNode,true).length)window.dispatchEvent(new CustomEvent('beastbox:look-closer',{detail:{id:'beast'}}));};
    canvas.addEventListener('pointerdown',tpd);canvas.addEventListener('pointerup',tpu);cleanup.push(()=>{canvas.removeEventListener('pointerdown',tpd);canvas.removeEventListener('pointerup',tpu);});}
   const resize=()=>{if(!host.current)return;const r=host.current.getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/Math.max(1,r.height);camera.updateProjectionMatrix();};
   const ro=new ResizeObserver(resize);ro.observe(host.current!);resize();cleanup.push(()=>ro.disconnect());
   // perf: measure fps for 3s windows and shrink the blade count if the phone can't hold ~50fps
   // test/debug hook: walk the traveler to the first seeded spot of a biome (used for screenshots)
   (window as any).__lwGoZeref=()=>{const z=(gpts[1]||gpts[0]).clone().normalize();const t=new THREE.Vector3(0,1,0).cross(z).normalize();pN.copy(z).addScaledVector(t,-.06).normalize();pF.copy(z).sub(pN).addScaledVector(pN,-pN.dot(z.clone().sub(pN))).normalize();return true;};(window as any).__lwGoBiome=(b:string)=>{const r=lwS(u.seed+':goto');for(let i=0;i<4000;i++){const v=unitFrom(r) as number[];if(biomeOf(new THREE.Vector3(v[0],v[1],v[2]))===b){pN.set(v[0],v[1],v[2]);pF.set(1,0,0).addScaledVector(pN,-pN.x).normalize();return true;}}return false;};
   // physics + events state: gravity hop on the sphere, wind, storm puff, sunrise, meetings; greeting once per visit
   let exWalk=0,exBack=false,exRun=false;
   let bY=0,bVY=0,puff=0,storming=0,windS=.3,greeted=false,lastSunH=0,evCool=0;const G_SURF=4.2;const windV=new THREE.Vector3(1,0,.4).normalize();const metCool:Record<string,number>={};
   const beastNm=beastName||'Your beast';const say=(s:string,cd=6)=>{if(evCool>0)return;evCool=cd;lineRef.current(s);};
   const hop=(v:number)=>{if(bY<=0.001)bVY=v;};
   let growLW=(()=>{try{return +(localStorage.getItem('lw:growLW:'+bKey)||0)||0;}catch{return 0;}})();
   const TKEY='lw:trav:'+bKey;let travSaveT=0;
   let biomeT=0,curBiome='plains';const bFeel=()=>(BIOME_FEEL as any)[curBiome]?.speed??1;
   // ================= fuller + more alive (Oct 22 2026): event lines, window, coexisting, biome lore, Zeref records
   const alive=(()=>{
    const seed=u.seed;let nLine=0;
    // ---- Zeref's experience stream (bb-deada969 only): canonical zeref-experience/v1, chained, kept on this device
    const ZKEY='lw:exp:world:'+ZEREF_ID;let zLog:any[]=(()=>{try{return JSON.parse(localStorage.getItem(ZKEY)||'[]');}catch{return [];}})();
    const zN0=(gpts[1]||gpts[0]).clone().normalize();
    const zBiome=()=>field?legendAt(field,[zN0.x,zN0.y,zN0.z]):null;
    const zRec=(ev:any)=>{try{const prev=zLog.length?zLog[zLog.length-1].hash:null;const rec=worldRecord(ev,{step:zLog.length+1,world_tick:u.tick,biome:zBiome(),mood:null,prev});zLog.push(rec);if(zLog.length>2000)zLog=zLog.slice(-2000);
     localStorage.setItem(ZKEY,JSON.stringify(zLog));}catch{}(window as any).__lwZerefExperiences=zLog;};
    (window as any).__lwZerefExperiences=zLog;(window as any).__lwZerefJsonl=()=>toJsonl(zLog);
    const zLore:Record<string,number>=(()=>{try{return JSON.parse(localStorage.getItem('lw:lore:zeref')||'{}');}catch{return {};}})();
    // ---- Cosmo's sprites
    const sheet=(f:string,cols:number,rows:number)=>{const tx=L.load(CX+'sprites/'+f);tx.colorSpace=THREE.SRGBColorSpace;tx.repeat.set(1/cols,1/rows);tx.magFilter=THREE.NearestFilter;return tx;};
    const iconBase=sheet('mood_icons.png',4,6),ringBase=sheet('mood_spread_ring.png',8,1),zzzBase=sheet('nap_zzz.png',4,1);
    let moods:any=null;fetch(CX+'moods.json').then(r=>r.ok?r.json():null).then(j=>{moods=j;}).catch(()=>{});
    const moodRow=(id:string|null)=>moods?.moods?.find((m:any)=>m.id===id)?.row??null;
    const moodCol=(id:string|null)=>new THREE.Color(moods?.moods?.find((m:any)=>m.id===id)?.color||'#ffffff');
    const mkIcon=()=>{const tx=iconBase.clone();tx.needsUpdate=true;const sp=new THREE.Sprite(new THREE.SpriteMaterial({map:tx,transparent:true,depthWrite:false}));sp.scale.setScalar(.22);sp.visible=false;return sp;};
    const setIcon=(sp:any,id:string|null,tt:number)=>{const row=moodRow(id);if(row==null){sp.visible=false;return;}sp.visible=true;const m=sp.material.map;m.offset.set((Math.floor(tt*6)%4)/4,1-(row+1)/6);};
    // residents: seeded mood, icon, lore memory, nap zzz
    for(const r of residents as any[]){r.mood=seededMood(seed,r.name);r.icon=mkIcon();r.icon.position.y=.75*((ARTIST_RESIDENTS as any[]).find((a:any)=>a.name===r.name)?.scale||1)+.15;r.node.add(r.icon);
     r.lore=(()=>{try{return JSON.parse(localStorage.getItem('lw:lore:res:'+r.name)||'{}');}catch{return {};}})();r.nap=0;
     const zt=zzzBase.clone();zt.needsUpdate=true;r.zzz=new THREE.Sprite(new THREE.SpriteMaterial({map:zt,transparent:true,depthWrite:false}));r.zzz.scale.setScalar(.25);r.zzz.position.y=r.icon.position.y+.12;r.zzz.visible=false;r.node.add(r.zzz);}
    const beastIcon=mkIcon();beastIcon.position.y=TRAV_H*1.5+.2;beastNode.add(beastIcon);
    const beastLore:Record<string,number>=(()=>{try{return JSON.parse(localStorage.getItem('lw:lore:'+bKey)||'{}');}catch{return {};}})();
    // spread rings (additive, tinted by the mood colour, grow from source toward receiver)
    const rings:any[]=[];
    const ring=(from:any,to:any,moodId:string)=>{const tx=ringBase.clone();tx.needsUpdate=true;const sp=new THREE.Sprite(new THREE.SpriteMaterial({map:tx,color:moodCol((MOOD_ICON as any)[moodId]||moodId),transparent:true,depthWrite:false,blending:THREE.AdditiveBlending}));
     scene.add(sp);rings.push({sp,from:from.clone(),to:to.clone(),t:0});};
    // ---- builds with Cosmo's staged models (swap at progress .33/.66, 0.5 s scale lerp)
    const MODEL_K=TRAV_H/1.7; // models are metres; explorer is 1.70 m = TRAV_H
    const proto:Record<string,any>={};const clips:Record<string,any>={};
    import('three/examples/jsm/loaders/GLTFLoader.js').then(({GLTFLoader})=>{const gl=new GLTFLoader();
     for(const k of ['cairn','flower_ring','burrow'])for(let st=1;st<=3;st++)gl.loadAsync(CX+'models/'+k+'_stage'+st+'.glb').then((g:any)=>{if(disposed)return;proto[k+st]=g.scene;clips[k+st]=g.animations;for(const b of builds)if(b.kind===k&&b.stage+1===st)showStage(b);}).catch(()=>{});}).catch(()=>{});
    const builds:any[]=[];const mixers:any[]=[];
    const showStage=(b:any)=>{const pr=proto[b.kind+(b.stage+1)];if(!pr)return;if(b.model)b.node.remove(b.model);b.model=pr.clone(true);b.model.scale.setScalar(MODEL_K);b.node.add(b.model);b.grow=.4;
     b.win=null;b.model.traverse((o:any)=>{if(o.name==='window'&&o.isMesh){o.material=o.material.clone();b.win=o;}});
     const cl=(clips[b.kind+(b.stage+1)]||[]).find((c:any)=>c.name==='window_pulse');if(cl){const mx=new THREE.AnimationMixer(b.model);mx.clipAction(cl).play();b.mixer=mx;mixers.push(mx);}};
    const geo=(a:any,c:any)=>Math.acos(Math.max(-1,Math.min(1,a.dot(c))))*PR;
    const say2=(who:string|null,l:string|null,cd=5)=>{if(l)say(who?who+': '+l:l,cd);};
    // ---- window: real signals only (opt-in mic loudness number, pointer near the beast, coming back to the page). No timer.
    const win=createWindow();let mic:any=null,pointerNear=false,returned=0,hiddenAt=0,winBoost=0;
    const onMic=(e:any)=>{const d=e?.detail;if(d&&d.kind==='microphone')mic={level:Math.max(0,Math.min(1,Number(d.level)||0)),active:!!d.active};};
    const onMove=(e:PointerEvent)=>{const rc=canvas.getBoundingClientRect();const v=beastNode.position.clone().project(camera);const sx=rc.left+(v.x*.5+.5)*rc.width,sy=rc.top+(-v.y*.5+.5)*rc.height;pointerNear=v.z<1&&Math.hypot(e.clientX-sx,e.clientY-sy)<90;};
    const onVis=()=>{if(document.hidden)hiddenAt=performance.now();else if(hiddenAt){returned=(performance.now()-hiddenAt)/1000;hiddenAt=0;}};
    addEventListener('beastbox:local-sensor-level',onMic as any);canvas.addEventListener('pointermove',onMove);document.addEventListener('visibilitychange',onVis);
    cleanup.push(()=>{removeEventListener('beastbox:local-sensor-level',onMic as any);canvas.removeEventListener('pointermove',onMove);document.removeEventListener('visibilitychange',onVis);});
    const metAt:Record<string,number>={};let napT=0,meetN=0;
    // test/debug hook for screenshots: a build next to the beast at a given progress. NOT a world event: writes no record, says nothing.
    (window as any).__lwBuildDemo=(kind='burrow',progress=1)=>{const at=bN.clone().addScaledVector(bF,1.2/PR).normalize();const b:any={id:'demo-'+kind,kind,progress,stage:progress<.33?0:progress<.66?1:2,at,by:['demo'],tick:u.tick,demo:true};builds.push(b);
     b.node=new THREE.Group();const f=bF.clone();place(b.node,at,f);b.node.position.copy(at).multiplyScalar(PR+hAt(at));scene.add(b.node);showStage(b);return b.stage;};
    return {
     // 1) cosmic: same grow() events as the traits; Zeref says Emeth's line; 5) Zeref records each one
     onTick(prev:any,next:any){const cev=cosmicEvents(prev,next);if(!cev.length)return;if(cev.some((e:any)=>e.type==='supernova'))(window as any).__lwNova?.();const cl=cosmicLine(cev,seed,next.tick);if(cl){lineRef.current('Zeref: '+cl.line);evCool=6;}
      for(const e of cev){zRec(e);if(e.type!=='storm_born')traits=driftTraits(traits,u,bKey,'wonder');}},
     // 3) two residents are close: meet (once per pair per 40 s), maybe spread a mood
     meet(r:any,o:any,tt:number){const k=[r.name,o.name].sort().join('|');if(metAt[k]>tt)return;metAt[k]=tt+40;meetN++;
      const ev={type:'meet',a:r.name,b:o.name};zRec(ev);say2(r.name,coexistLine(ev,seed,meetN),5);
      const sp=spreadMood(r,o,seed,meetN);if(sp){zRec(sp);ring(r.n,o.n,sp.mood);say2(r.name,coexistLine(sp,seed,meetN),4);if(sp.gather)o.pause=Math.max(o.pause||0,3);}},
     // 3) a resident works on something where it touched a thing
     build(r:any){if(!field)return;const lg=legendAt(field,[r.n.x,r.n.y,r.n.z]);const kind=buildKind(seed,r.name,lg);
      const ev=advanceBuild(builds,{builder:r.name,kind,at:r.n.clone(),dist:geo,tick:u.tick});if(!ev)return;
      const b=builds.find(x=>x.id===ev.id)!;if(!b.node){b.node=new THREE.Group();const f=new THREE.Vector3(1,0,0).addScaledVector(b.at,-b.at.x).normalize();place(b.node,b.at,f);b.node.position.copy(b.at).multiplyScalar(PR+hAt(b.at));scene.add(b.node);}
      showStage(b);zRec(ev);if(ev.stage===0||ev.finished)say2(r.name,coexistLine(ev,seed,builds.length),5);},
     frame(dt:number,tt:number){
      // 2) window
      const kind=stepWindow(win,dt,{mic,pointerNear,returned});returned=0;if(kind){const wl=windowLine(kind,seed,win.n);if(wl){lineRef.current(beastNm+': '+wl);evCool=4;}winBoost=1;glowBoost=1;}
      winBoost=Math.max(0,winBoost-dt*.4);
      for(const b of builds){if(b.model){b.grow=Math.min(1,(b.grow??1)+dt*1.2);b.model.scale.setScalar(MODEL_K*b.grow);}if(b.win?.material)b.win.material.emissiveIntensity=windowEmissive(tt,winBoost);}
      for(const mx of mixers)mx.update(dt);
      // 3) icons, naps, rings
      for(const r of residents as any[]){setIcon(r.icon,r.nap>0?null:(MOOD_ICON as any)[r.mood],tt+r.wob);if(r.nap>0){r.nap-=dt;r.pause=Math.max(r.pause||0,.2);r.zzz.visible=true;r.zzz.material.map.offset.x=(Math.floor(tt*4)%4)/4;}else r.zzz.visible=false;}
      setIcon(beastIcon,traitIcon(traits),tt);
      for(let i=rings.length-1;i>=0;i--){const g=rings[i];g.t+=dt;const fr=Math.floor(g.t*12);if(fr>=8){scene.remove(g.sp);rings.splice(i,1);continue;}g.sp.material.map.offset.x=fr/8;
       const pos=g.from.clone().lerp(g.to,g.t*12/8).normalize();g.sp.position.copy(pos).multiplyScalar(PR+.35);g.sp.scale.setScalar(.4+.8*fr/8);}
      napT-=dt;if(napT<=0){napT=2;const R=residents as any[];const night=R.map(r=>r.n.dot(sunDir)<-.05&&r.nap<=0);const d=R.map(a=>R.map(b=>geo(a.n,b.n)));const g=napGroup(d,night,{reach:1.2,min:3});
       if(g){for(const i of g){R[i].nap=20;}const ev={type:'group_nap',who:g.map(i=>R[i].name)};zRec(ev);say2(null,coexistLine(ev,seed,u.tick),6);}}
      // 4) biome lore on first entry: beast, residents, Zeref
      if(field&&Math.floor(tt*2)!==Math.floor((tt-dt)*2)){
       const lb=learnBiome(beastLore,legendAt(field,[bN.x,bN.y,bN.z]));if(lb){traits=driftTraits(traits,u,bKey,lb.trait);traits=driftTraits(traits,u,bKey,'wonder');try{localStorage.setItem('lw:lore:'+bKey,JSON.stringify(beastLore));}catch{}lineRef.current(beastNm+': '+lb.line);evCool=6;}
       for(const r of residents as any[]){const lr=learnBiome(r.lore,legendAt(field,[r.n.x,r.n.y,r.n.z]));if(lr){try{localStorage.setItem('lw:lore:res:'+r.name,JSON.stringify(r.lore));}catch{}say2(r.name,lr.line,4);}}
       const lz=learnBiome(zLore,legendAt(field,[zN0.x,zN0.y,zN0.z]));if(lz){try{localStorage.setItem('lw:lore:zeref',JSON.stringify(zLore));}catch{}zRec({type:'biome_first_entry',lore:lz.lore,lesson:lz.lesson});}
      }
      (window as any).__lwAlive={builds:builds.map(b=>({kind:b.kind,stage:b.stage,progress:b.progress,model:!!b.model,window:!!b.win,emissive:b.win?.material?.emissiveIntensity??null})),moods:(residents as any[]).map(r=>({name:r.name,mood:r.mood,nap:r.nap>0})),rings:rings.length,zerefRecords:zLog.length,window:{...win}};
     }};
   })();
   let fpsT=0,fpsN=0,fps=0,last=performance.now(),t=0,hudT=0;const camTarget=new THREE.Vector3(),camPos=new THREE.Vector3(0,6,22);const cW=new THREE.Vector3(),cT=new THREE.Vector3(),cN=new THREE.Vector3(0,1,0),camLook=new THREE.Vector3();
   const frame=()=>{raf=requestAnimationFrame(frame);const now=performance.now();const dt=Math.min(.05,(now-last)/1000);last=now;t+=dt;UG.uT.value=t;
    fpsT+=dt;fpsN++;if(fpsT>=3){fps=fpsN/fpsT;fpsT=0;fpsN=0;if(fps<48&&bladeCap>2000){bladeCap=Math.floor(bladeCap*.75);bladeGeo.instanceCount=bladeCap;}(window as any).__lwPerf={fps:+fps.toFixed(1),blades:bladeCap};}
    tickAcc+=dt;if(tickAcc>=TICK_S){tickAcc=0;applyTick();}
    {const a=(((Date.now()/1000+((window as any).__lwDayOffset||0))%DAY_S+DAY_S)%DAY_S)/DAY_S*Math.PI*2;sunDir.set(Math.cos(a),.35*Math.sin(a*.5+1),Math.sin(a)).normalize();UG.uSun.value.copy(sunDir);
     const fN=spawnRef.current?pN:bN;if((window as any).__lwNoon)sunDir.copy(fN).multiplyScalar((window as any).__lwNoon==='night'?-1:1).add(new THREE.Vector3(.5,.6,.2)).normalize();UG.uSun.value.copy(sunDir);const h=fN.dot(sunDir);const focus=fN.clone().multiplyScalar(PR);sun.position.copy(focus).addScaledVector(sunDir,25);sun.target.position.copy(focus);
     const dayL=Math.max(.1,h*.8+.2);sun.intensity=2.2*dayL;sun.color.copy(starCol).lerp(SKY_DUSK,Math.max(0,1-Math.abs(h)/.2)*.35);hemi.intensity=1.4*Math.max(.12,h*.3+.25);
     sunDisc.position.copy(sunDir).multiplyScalar(160);starMesh.position.copy(sunDisc.position);moon.position.copy(sunDir).multiplyScalar(-70).add(new THREE.Vector3(0,12,0));
     const ground3=zC<.6;const day=ground3?THREE.MathUtils.smoothstep(h,-.12,.35):0;const dusk=ground3?Math.max(0,1-Math.abs(h)/.18)*.7:0;
     (scene.background as any).copy(SKY_NIGHT).lerp(SKY_DAY,day).lerp(SKY_DUSK,dusk*(1-day*.5));cosmoSky.update(t,1-day*.97,camera.position);nova.update(dt);if(nova.playing)nova.sp.scale.setScalar(30+40*Math.min(1,nova.sp.material.map!.offset.x+1-nova.sp.material.map!.offset.y));island?.update(dt,camera.position);if(starMat)starMat.opacity=1-day*.95;
     // wind: heated by the sun, gusts with storms; drives grass sway and fur
     windS=.25+.35*Math.max(0,h)+storming*.6;windV.applyAxisAngle(fN,dt*.03);try{zDrv?.update(dt);}catch{}zHold.rotateY(dt*.05);fieldStep(dt,sunDir,Math.min(1,joy.current.active?1:0)+(spawnRef.current?.3:0));if(field?.mp){windV.x+=(field.mp.wind.x-windV.x)*dt*.2;windV.z+=(field.mp.wind.z-windV.z)*dt*.2;}storming=Math.max(0,storming-dt*.15);bladeMat.uniforms.uGust.value=W.gust_amp*(.6+windS*1.4);
     // sunrise at the beast: wonder
     const hb=bN.dot(sunDir);if(lastSunH<0&&hb>=0){say(beastNm+' stops to watch the sunrise, eyes wide.',8);hop(1.6);traits=driftTraits(traits,u,bKey,'day');}else if(lastSunH>0&&hb<=0){say('Night falls. '+beastNm+' curls its tail and looks at the stars.',8);traits=driftTraits(traits,u,bKey,'rest');}lastSunH=hb;
     for(const r of residents as any[]){const lit=.45+.55*THREE.MathUtils.smoothstep(r.n.dot(sunDir),-.15,.3);(r.node.children[0] as any).material.color.setScalar(lit);}}
    // gravity on the sphere: hops fall back under surface gravity
    evCool=Math.max(0,evCool-dt);puff=Math.max(0,puff-dt*.6);bVY-=G_SURF*dt;bY=Math.max(0,bY+bVY*dt);if(bY<=0&&bVY<0)bVY=0;
    // creatures learn from each new biome they enter (beast: persisted with its learned things)
    biomeT-=dt;if(biomeT<=0){biomeT=.5;const bb=biomeOf(bN);curBiome=bb;if(!learned['biome:'+bb]){learned['biome:'+bb]=1;const ls=(BIOME_FEEL as any)[bb]?.lesson;if(ls)traits=driftTraits(traits,u,bKey,ls);try{localStorage.setItem('lw:learned:'+bKey,JSON.stringify(learned));}catch{}/* the first-entry line now comes from Emeth's biome lore (alive.frame) */}
     if(hudBiome.current)hudBiome.current.textContent='Biome: '+(cosmoNameOf(spawnRef.current?pN:bN)||(BIOME_NAMES as any)[spawnRef.current?biomeOf(pN):bb]);(window as any).__lwBiome={beast:bb,you:biomeOf(pN),home:biomeOf(gpts[0]),bN:bN.toArray(),g0:gpts[0].toArray()};}
    latPivot.rotation.y+=dt*.02;latObj.rotation.x+=dt*.03;latObj.rotation.z+=dt*.017;
    // residents wander
    const play=UG.uPlay.value;play[0].copy(bN);residents.slice(0,6).forEach((r,i)=>play[i+1].copy(r.n));play[7].copy(spawnRef.current?pN:bN);
    // things wake when the spreading grass reaches them; touched things grow / pulse
    for(const th of things){if(!th.awake){const c=gpts.some(g=>ang(th.n,g)/PR<UG.uSpread.value-.2);if(c){th.awake=true;th.grow=1;}}
     th.cool=Math.max(0,th.cool-dt);th.pulse=Math.max(0,th.pulse-dt*.8);const s0=th.node.scale.x,tg=th.awake?th.size*th.grow*(1+th.pulse*.25):0.001;th.node.scale.setScalar(s0+(tg-s0)*Math.min(1,dt*2));}
    // residents explore things and each other; everything can touch everything
    socialCool=Math.max(0,socialCool-dt);
    for(const r of residents as any[]){r.pause=Math.max(0,(r.pause||0)-dt);
     const nt=nearestThing(r.n);if(nt&&nt.d<.35&&r.pause<=0){if(touch(nt.t,r.name)){r.pause=1.5;alive.build(r);}}
     else if(nt&&nt.d<4&&Math.sin(t*.2+r.wob)>0)steerTo(r.n,r.f,nt.t.n,dt*1.5);else turn(r.n,r.f,Math.sin(t*.4+r.wob)*dt*.8);
     for(const o of residents as any[])if(o!==r&&ang(r.n,o.n)<.5){steerTo(r.n,r.f,r.n.clone().multiplyScalar(2).sub(o.n),dt*2);if(socialCool<=0&&!spawnRef.current){socialCool=25;lineRef.current(r.name+' and '+o.name+' bumped noses.');}alive.meet(r,o,t);}
     if(ang(r.n,bN)<.6){steerTo(r.n,r.f,r.n.clone().multiplyScalar(2).sub(bN),dt*2);if(!(metCool[r.name]>t)){metCool[r.name]=t+40;say(beastNm+' met '+r.name+' and sniffed hello.',5);hop(1.2);traits=driftTraits(traits,u,bKey,'greet');}}
     if(r.pause<=0){const rb=biomeOf(r.n);walkOn(r.n,r.f,r.spd*dt*((BIOME_FEEL as any)[rb]?.speed??1));if(rb==='ocean')steerTo(r.n,r.f,gpts[0],dt*2);}place(r.node,r.n,r.f);}
    alive.frame(dt,t);
    // beast: wander by traits; when you're spawned in, run to greet (timing from JSON)
    const sp=spawnRef.current;let restored=false;if(sp&&!wasSpawned){try{const st=JSON.parse(localStorage.getItem(TKEY)||'null');if(st&&st.n&&st.f){pN.fromArray(st.n).normalize();pF.fromArray(st.f);pF.addScaledVector(pN,-pF.dot(pN)).normalize();restored=pF.lengthSq()>.5;}}catch{}}
    if(sp&&!wasSpawned&&!restored){pN.copy(bN).applyAxisAngle(bF,.0).addScaledVector(bF,-3/PR).normalize();pF.copy(bF);pF.addScaledVector(pN,-pF.dot(pN)).normalize();spawnT=0;greetT=-1;travNode.visible=true;}
    if(sp&&!wasSpawned&&restored){travNode.visible=true;spawnT=-1;lineRef.current('Back where you left off.');}
    else if(sp&&!wasSpawned)lineRef.current('A new traveler on the grass.');
    if(sp){travSaveT-=dt;if(travSaveT<=0){travSaveT=1;try{localStorage.setItem(TKEY,JSON.stringify({n:pN.toArray(),f:pF.toArray()}));}catch{}}}
    if(!sp&&wasSpawned){travNode.visible=false;lineRef.current('Grass will keep growing while you’re gone.');}wasSpawned=sp;
    let bSpeed=0;
    if(sp&&spawnT>=0){bSpeed=0;}// your beast spots you and freezes while you arrive
    else if(sp){const side=new THREE.Vector3().crossVectors(pN,pF).normalize();const goal=pN.clone().addScaledVector(pF,.9/PR).addScaledVector(side,.5/PR).normalize();const toP=goal.clone().sub(bN);const dist=Math.acos(Math.min(1,bN.dot(goal)))*PR+1.5*TRAV_H-.05;const dir=toP.addScaledVector(bN,-toP.dot(bN));
     if((!greeted||dist>6)&&dist>1.5*TRAV_H){if(dir.lengthSq()>1e-8){bF.copy(dir.normalize());}const v=1.6*Math.max(.7,bFeel());walkOn(bN,bF,v*dt);bSpeed=1;if(!greeted)greetT=-1;}
     else if(!greeted){greeted=true;greetT=0;lineRef.current('YOU’RE HERE. Rawr! Come see what I built.');traits=driftTraits(traits,u,bKey,'greet');brain.mode='glance';hop(1.4);}
     else if(greetT<0||greetT>2){bSpeed=wander();}
     if(greetT>=0)greetT+=dt;}
    else{bSpeed=wander();}
    function wander(){const nt=nearestThing(bN);if(nt&&nt.d<.4){if(touch(nt.t,'beast')){const k=nt.t.kind;learned[k]=(learned[k]||0)+1;traits=driftTraits(traits,u,bKey,(THING_LESSON as any)[k]||'day');try{localStorage.setItem('lw:learned:'+bKey,JSON.stringify(learned));}catch{}}}
     if(nt&&nt.d<5*(.3+traits.curiosity))steerTo(bN,bF,nt.t.n,dt*1.2);const v=(.2+.35*traits.curiosity)*bFeel();walkOn(bN,bF,v*dt);if(curBiome==='ocean')steerTo(bN,bF,gpts[0],dt*3);return .35;}
    if(sp&&spawnT<0){const nt=nearestThing(pN);if(nt&&nt.d<.5&&touch(nt.t,'you'))lineRef.current('You touched a '+nt.t.kind+'. It answers.');}
    brain.speed+=(bSpeed-brain.speed)*Math.min(1,dt*4);brain.bob+=dt*(4+brain.speed*8);brain.mode=brain.speed>.5?'run':greetT>=0&&greetT<RG.count/RG.fps?'glance':'walk';
    place(beastNode,bN,bF);
    if(bodyDrive){const greetHop=greetT>=0&&greetT<(RG.segments.greet[1]-RG.segments.greet[0]+1)/RG.fps?Math.sin(greetT/((RG.segments.greet[1]-RG.segments.greet[0]+1)/RG.fps)*Math.PI)*.15:0;beastNode.position.addScaledVector(bN,greetHop);
     beastNode.position.addScaledVector(bN,bY);beastNode.scale.setScalar(1+puff*.18);
     bodyDrive(dt,brain,{stiffness:.7+traits.calm*.6,damping:1,turbulence:storming*.4,wind:{x:windV.x*windS,z:windV.z*windS},mood:{joy:traits.joy,fear:1-traits.calm,curiosity:traits.curiosity,calm:traits.calm,mischief:.3}},sp?{x:travNode.position.x,y:travNode.position.y+TRAV_H*.8,z:travNode.position.z}:null);}
    glowBoost=Math.max(0,glowBoost-dt*.8);(glow.material as any).opacity=.35+.35*(.5+.5*Math.sin(t*6.2831*.25))+glowBoost*.3;
    glow.position.copy(beastNode.position).addScaledVector(bN,TRAV_H*1.6).addScaledVector(new THREE.Vector3().crossVectors(bN,bF).normalize(),-TRAV_H*.6);
    // traveler + camera
    if(sp){let ix=joy.current.x,iy=joy.current.y;const K=keys.current;if(K.has('w')||K.has('arrowup'))iy=-1;if(K.has('s')||K.has('arrowdown'))iy=1;if(K.has('a')||K.has('arrowleft'))ix=-1;if(K.has('d')||K.has('arrowright'))ix=1;
     const mag=Math.min(1,Math.hypot(ix,iy));exBack=iy>.3;
     if(spawnT>=0){spawnT+=dt;const fr=Math.min(F.traveler_spawn.count-1,Math.floor(spawnT*F.traveler_spawn.fps));trav.visible=true;explorer.visible=false;trav.material.map=tSpawn;setFrame(tSpawn,F.traveler_spawn.cols,1,fr,0);if(spawnT>F.traveler_spawn.count/F.traveler_spawn.fps)spawnT=-1;}
     else if(mag>.08){turn(pN,pF,-ix*dt*2.2*(iy>.3?-1:1));const fwd=-iy;exRun=mag>.85;walkOn(pN,pF,(fwd>=0?1:-1)*Math.max(.25,Math.abs(fwd))*(exRun?3.5:1.2)*(TRAV_H/1.7)*Math.min(1,mag/.85)*dt*Math.max(.6,(BIOME_FEEL as any)[biomeOf(pN)]?.speed??1));
      const ang=Math.atan2(ix,-iy);const oct=((Math.round(ang/(Math.PI/4))%8)+8)%8;const ROW8=['N','NE','E','SE','S','SW','W','NW'][oct];const row=ROWS.indexOf(ROW8);
      trav.material.map=tWalk;setFrame(tWalk,F.traveler_walk.cols,8,Math.floor(t*F.traveler_walk.fps)%F.traveler_walk.cols,row<0?4:row);exWalk=mag;}
     else{trav.material.map=tIdle;setFrame(tIdle,F.traveler_idle.cols,1,Math.floor(t*F.traveler_idle.fps)%F.traveler_idle.cols,0);}
     if(spawnT<0){trav.visible=false;explorer.visible=true;exPlay(exWalk>.08?(exRun&&exActs.run?'run':'walk'):(greetT>=0&&greetT<2&&exActs.wave?'wave':(Math.sin(t*.13)>.85&&exActs.look?'look':'idle')));const sw=Math.sin(t*9)*.6*Math.min(1,exWalk);if(legs.length===2){legs[0].rotation.x=sw;legs[1].rotation.x=-sw;}explorer.position.y=Math.abs(Math.sin(t*9))*.02*Math.min(1,exWalk);
      // face the way you walk; backwards input turns the body around
      explorer.rotation.y=(exWalk>.08&&exBack?Math.PI:0)+(exMixer?0:0);}
     exMixer?.update(dt);exWalk=0;
     place(travNode,pN,pF);
     {const inW=WATER_IDS.has(field?legendAt(field,[pN.x,pN.y,pN.z]):(cosmoBiome(pN)||''));mover.fly=flyRef.current;stepMover(mover,{dt,inWater:inW,ground:hAt(pN),mpu:TRAV_H/1.7});
      travNode.position.addScaledVector(pN,mover.y-hAt(pN)*0);(window as any).__lwMove={y:+mover.y.toFixed(3),w:{walk:+mover.w.walk.toFixed(2),swim:+mover.w.swim.toFixed(2),fly:+mover.w.fly.toFixed(2)},inWater:inW};}
     // over-the-shoulder (art target 08_explore_daynight): behind and right of you, looking ahead
     const shS=new THREE.Vector3().crossVectors(pN,pF).normalize();camTarget.copy(pN).multiplyScalar(PR+TRAV_H*.9).addScaledVector(pF,1.6);cW.copy(pN).multiplyScalar(PR+TRAV_H*2.6).addScaledVector(pF,-2.7).addScaledVector(shS,-.55);camTarget.addScaledVector(pN,mover.y);cW.addScaledVector(pN,mover.y*(1-.4*mover.w.swim));cT.copy(camTarget);cN.copy(pN);}
    else{// close framing around your beast (the old watch view); the old orbit is now the far end of the same zoom
     const side=new THREE.Vector3().crossVectors(bN,bF).normalize();const sw=Math.sin(t*.15);cW.copy(bN).multiplyScalar(PR+1.5).addScaledVector(bF,-2.6*Math.cos(sw)).addScaledVector(side,2.2*sw);
     cT.copy(beastNode.position).addScaledVector(bN,TRAV_H*.6);cN.copy(bN);}
    // ---- one continuous zoom: close over-the-shoulder (z=0) to full planet orbit (z=1); pinch / wheel / buttons all move zT
    const mode=sp?'s':watchRef.current?'w':'o';if(mode!==zMode){zMode=mode;zT=mode==='s'?0:mode==='w'?.12:1;}
    zC+=(zT-zC)*Math.min(1,dt*5);const zb=zoomBlend(zC);(window as any).__lwZoom={z:+zC.toFixed(3),target:zT,orbit:+zb.orbit.toFixed(3)};
    {const oW=cN.clone().multiplyScalar(1.2).add(new THREE.Vector3(Math.cos(oy)*Math.sin(ox),Math.sin(oy),Math.cos(oy)*Math.cos(ox))).normalize().multiplyScalar(PR*4.3);
     const dir=cW.clone().normalize().lerp(oW.clone().normalize(),zb.orbit).normalize();const ground0=PR+DISP+TRAV_H*.45;
     const len=clampAboveGround(zoomDistance(zC,cW.length(),oW.length()),0,0);const want=dir.multiplyScalar(Math.max(len,ground0));
     // keep the close view's offset from the focus at low zoom (log-scaled pull-back), so close-up stays over the shoulder
     if(zb.orbit<.5){const off=cW.clone().sub(cN.clone().multiplyScalar(PR));const k=(len-cW.length())/Math.max(.001,oW.length()-cW.length());want.lerp(cN.clone().multiplyScalar(PR).add(off.multiplyScalar(1+k*6)),1-zb.orbit*2);}
     camPos.lerp(want,Math.min(1,dt*(sp?4:2.5)));camPos.setLength(clampAboveGround(camPos.length(),ground0,0));
     const tgt=cT.clone().lerp(cN.clone().multiplyScalar(PR*.15),zb.orbit);camLook.lerp(tgt,Math.min(1,dt*4));
     camera.position.copy(camPos);camera.up.copy(cN).lerp(new THREE.Vector3(0,1,0),zb.orbit).normalize();camera.lookAt(camLook);}
    // Alive props: real events only (a breath peak in view, a creature entering a crystal's 3 m, flowers visibly turning) -> one of Emeth's lines, picked by seed.
    {const evs=surface?.update(t,{sunDir,creatures:[bN,...residents.map((r:any)=>r.n)],cam:camera.position})||[];for(const k of evs){const f=aliveGate.fire(k,String(u.seed),t);if(f){lineRef.current(f.line);break;}}}heaven.update(t);heaven.root.visible=zC<.55&&cN.dot(sunDir)>-.08;heaven.root.position.copy(cN).multiplyScalar(PR+hAt(cN));heaven.root.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),cN);
    beastLamp.position.copy(beastNode.position).addScaledVector(bN,TRAV_H*1.4);beastLamp.intensity=(1-zb.orbit)*7;
    {const night=1-THREE.MathUtils.smoothstep(cN.dot(sunDir),-.12,.35);const dusk=Math.max(0,1-Math.abs(cN.dot(sunDir))/.18)*.7;
     mech?.update(t,dt,{focus:cN.clone().multiplyScalar(PR+hAt(cN)),up:cN,camPos:camera.position,rain:(window as any).__lwWeatherForce?.rain??weather.rain,cloud:(window as any).__lwWeatherForce?.cloud??weather.cloud,wind:weather.wind,night,dusk,ground3:zC<.6,
      torch:sp?travNode.position.clone().addScaledVector(pN,TRAV_H*.7).addScaledVector(new THREE.Vector3().crossVectors(pN,pF).normalize(),-TRAV_H*.25):null,beast:beastNode.position.clone().addScaledVector(bN,TRAV_H*.5)});
     // underwater: Cosmo's ramp tints fog + background by depth when the camera is in the sea
     const sw=sp?mover.w.swim:0;if(sw>.4){const dM=Math.max(0,-mover.y)/(TRAV_H/1.7);const tD=Math.min(1,dM/60+.15);const uc=underwaterColor(THREE,tD);
      if(!(scene.fog as any)?.isFogExp2)scene.fog=new THREE.FogExp2(uc.getHex(),.1);(scene.fog as any).color.copy(uc);(scene.fog as any).density=THREE.MathUtils.lerp(.035,.09,tD)/(TRAV_H/1.7)*sw*.5;(scene.background as any).lerp(uc,sw);}
     else if((scene.fog as any)?.isFogExp2)scene.fog=null;(window as any).__lwUnder=sw>.4;}
     // Emeth's world lines, fired by the real loop's state edges (sun height, weather, swim/fly, lava, water paths)
     {const ck=stepWorldCues(cues,{sunH:(spawnRef.current?pN:bN).dot(sunDir),rain:weather.rain,under:(window as any).__lwUnder===true,fly:sp?mover.w.fly:0,bursts:island?.state?.().bursts||0,wet:lwWet});if(ck){cueN++;const wl=worldLine(ck,u.seed,cueN);if(wl)say(beastNm+': '+wl,5);(window as any).__lwCue={kind:ck,n:cueN};}}
    if(asciiRef.current)ascii.render(scene,camera);else renderer.render(scene,camera);
    hudT+=dt;if(hudT>.5){hudT=0;const last=u.history?.[u.history.length-1];setHud({tick:u.tick,simE:last?.sim_E??null,life:u.life.length,storms:u.storms.length,cover:Math.min(1,UG.uSpread.value/Math.PI),traits,learned:{...learned},awake:things.filter((x:any)=>x.awake).length,blades:bladeCap,fps:+fps.toFixed(0)});}
   };
   frame();(window as any).__lw={spawn:()=>setSpawned(true),toSea:()=>{if(!island)return false;const v=island.anchor('sea_level').clone().normalize();const r=lwStream(u.seed+':sea-test');for(let i=0;i<400;i++){const d=unitFrom(r) as number[];const w=new THREE.Vector3(d[0],d[1],d[2]);if(w.dot(v)>.8&&WATER_IDS.has(field?legendAt(field,d):(cosmoBiome(w)||''))&&w.dot(v)<.97){pN.copy(w);pF.copy(v).addScaledVector(w,-v.dot(w)).normalize();return true;}}return false;}};
   cleanup.push(()=>{renderer.dispose();plush?.dispose();scene.traverse((o:any)=>{o.geometry?.dispose?.();o.material?.dispose?.();});});
  })().catch(e=>{if(!disposed)setErr(String(e?.message||e));});
  return()=>{disposed=true;cancelAnimationFrame(raf);cleanup.forEach(f=>{try{f();}catch{}});};
 },[gKey,beastKey]);// eslint-disable-line react-hooks/exhaustive-deps
 // touch joystick
 const jd=(e:React.PointerEvent)=>{(e.target as Element).setPointerCapture(e.pointerId);joy.current={x:0,y:0,active:true,id:e.pointerId,cx:e.clientX,cy:e.clientY};setStick({x:0,y:0});};
 const jm=(e:React.PointerEvent)=>{const j=joy.current;if(!j.active||e.pointerId!==j.id)return;const dx=(e.clientX-j.cx)/50,dy=(e.clientY-j.cy)/50;const m=Math.max(1,Math.hypot(dx,dy));j.x=dx/m;j.y=dy/m;setStick({x:j.x,y:j.y});};
 const ju=()=>{joy.current={...joy.current,x:0,y:0,active:false};setStick(null);};
 const T=hud.traits;
 return <div ref={host} className="lw-root" data-living-world={spawned?'spawned':'orbit'} data-lw-embedded={embedded?'':undefined} style={{pointerEvents:'auto',position:embedded?'absolute':'fixed',inset:0,zIndex:embedded?1:2147483000,borderRadius:embedded?18:0,overflow:'hidden',background:'#05030f',touchAction:embedded&&!spawned?'pan-y':'none',fontSize:embedded?11:13,color:'#efeaff',font:'13px/1.35 system-ui,sans-serif'}}>
  <canvas ref={canvasRef} style={{position:'absolute',inset:0,width:'100%',height:'100%',display:'block',touchAction:'none'}}/>
  <div data-lw-chips style={{position:'absolute',top:'calc(env(safe-area-inset-top) + 10px)',left:10,right:10,display:'flex',flexWrap:'wrap',gap:6,pointerEvents:'none'}}>
   <span style={pill('#2b6cb0')} data-lw-spark>{LW_LABELS.spark}</span><span style={pill('#9b2c2c')} data-lw-growth>{LW_LABELS.growth}</span><span style={pill('#553c9a')} data-lw-model>{LW_LABELS.model}</span><span style={pill('#276749')} data-lw-biome ref={hudBiome}>Biome</span>
  </div>
  <div style={{position:'absolute',left:10,right:10,bottom:'calc(env(safe-area-inset-bottom) + 10px)',display:'flex',justifyContent:'space-between',alignItems:'flex-end',gap:8,pointerEvents:'none'}}>
   <div data-lw-card style={{background:'rgba(10,6,30,.72)',borderRadius:12,padding:'8px 10px',maxWidth:'62%',pointerEvents:'auto',display:embedded&&!spawned?'none':undefined}}>
    <b>{beastName||'Your beast'}</b> {genome||(typeof window!=='undefined'&&(window as any).__beastGenome)?'':'(no saved beast yet — hatch one in the Cage)'}<br/>
    <details data-lw-details style={{fontSize:12}}><summary style={{cursor:'pointer',opacity:.8}}>Details</summary>
    tick {hud.tick} · sim E {hud.simE??'—'} · life {hud.life} · storms {hud.storms} · grass {Math.round(hud.cover*100)}%<br/>
    {hud.learned?<>things awake {hud.awake??0} · learned {Object.entries(hud.learned).map(([k,v])=>k+' '+v).join(' · ')||'—'}<br/></>:null}
    {T?<>curious {T.curiosity.toFixed(2)} · social {T.sociality.toFixed(2)} · calm {T.calm.toFixed(2)} · joy {T.joy.toFixed(2)} · {T.experiences} experiences</>:null}
    </details>
    {err?<div style={{color:'#ffb4b4'}}>Couldn’t load the world: {err}</div>:null}
   </div>
   <div style={{display:'flex',flexDirection:'column',gap:6,pointerEvents:'auto'}}>
    {!spawned?<><button type="button" data-lw-spawn onClick={()=>setSpawned(true)} style={btn('#6b46c1')}>✦ Spawn in</button><button type="button" data-lw-watch onClick={()=>setWatch(w=>!w)} style={btn('#2c5282')}>{watch?'🌍 Orbit view':'👁 Watch your beast'}</button></>:<><button type="button" data-lw-fly onClick={()=>setFlying(v=>!v)} style={btn(flying?'#2b6cb0':'#333')}>{flying?'🪽 Flying':'🪽 Fly'}</button><button type="button" data-lw-exit onClick={()=>setSpawned(false)} style={btn('#444')}>Exit to orbit</button></>}{!embedded||spawned?<button type="button" data-lw-ascii onClick={()=>setAscii(v=>!v)} style={btn(ascii?'#2f855a':'#333')}>{ascii?'▦ ASCII on':'▦ ASCII'}</button>:null}
    {embedded&&onExpand?<button type="button" data-lw-expand onClick={onExpand} style={btn('#553c9a')}>⤢ Full screen</button>:null}
    {onClose?<button type="button" data-lw-close onClick={onClose} style={btn('#222')}>Close world</button>:null}
   </div>
  </div>
  {spawned?<div data-lw-hand aria-hidden style={{position:'absolute',left:'calc(env(safe-area-inset-left) + 14px)',bottom:'calc(env(safe-area-inset-bottom) + 250px)',width:70,height:110,pointerEvents:'none',animation:'lwbob 1.1s ease-in-out infinite'}}>
   <style>{'@keyframes lwbob{0%,100%{transform:translateY(0) rotate(-8deg)}50%{transform:translateY(-7px) rotate(-4deg)}}'}</style>
   <img src="/universe/livingworld/asciimode/glow_sprite_torch_256.png" alt="" style={{position:'absolute',left:-25,top:-30,width:120,height:120,mixBlendMode:'screen'}}/>
   <div style={{position:'absolute',left:28,top:26,width:12,height:58,borderRadius:4,background:'linear-gradient(#7a4a24,#4a2a12)'}}/><div style={{position:'absolute',left:22,top:66,width:30,height:30,borderRadius:'40% 40% 46% 46%',background:'#c99a7a',boxShadow:'0 0 18px rgba(255,190,110,.6)'}}/></div>:null}
  {line?<div data-lw-line style={{position:'absolute',left:'50%',top:'calc(env(safe-area-inset-top) + 70px)',transform:'translateX(-50%)',background:'rgba(20,10,50,.82)',borderRadius:12,padding:'8px 14px',fontSize:15,maxWidth:'86%',textAlign:'center',pointerEvents:'none'}}>{line}</div>:null}
  {spawned?<div data-lw-joystick onPointerDown={jd} onPointerMove={jm} onPointerUp={ju} onPointerCancel={ju}
   style={{position:'absolute',left:'calc(50% - 60px)',bottom:'calc(env(safe-area-inset-bottom) + 120px)',width:120,height:120,borderRadius:'50%',background:'rgba(255,255,255,.08)',border:'2px solid rgba(255,255,255,.25)',touchAction:'none'}}>
   <div style={{position:'absolute',left:60-22+(stick?.x||0)*38,top:60-22+(stick?.y||0)*38,width:44,height:44,borderRadius:'50%',background:'rgba(200,180,255,.55)'}}/>
  </div>:null}
 </div>;
}
const pill=(c:string)=>({background:c,borderRadius:999,padding:'3px 8px',fontSize:11,opacity:.92}) as const;
const btn=(c:string)=>({background:c,color:'#fff',border:0,borderRadius:10,padding:'10px 14px',fontSize:14,fontWeight:600}) as const;
