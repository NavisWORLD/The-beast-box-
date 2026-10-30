'use client';
/**
 * Living World (Oct 22 2026): the user's beast lives ON the tiny-universe planet with the resident creatures.
 * Genesis = recorded ibm_marrakesh hardware counts (tiny-universe-genesis.json). Growth = SIMULATED Rigetti-style
 * Bell simulator (lib/universe/tiny-universe.mjs grow()), ticking client-side. Grass spreads from gathering points as
 * the simulated universe grows until it covers the whole planet. "Spawn in" puts you on the ground as a traveler
 * (Cosmo's art pack) with a touch joystick + WASD and a third-person camera.
 */
import {useEffect,useRef,useState} from 'react';
import {useCageCreature} from './use-cage-creature';
import {insideCreatureVisible} from '../lib/world/cage-creature.mjs';
import {createPortal} from 'react-dom';
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
import {addBeachShore} from '@/lib/universe/beach-shore-three';
import {addOceanLife} from '@/lib/universe/ocean-life-three';
import {noticeLine,noticeGate} from '@/lib/universe/zoom-lines.mjs';
import {growthChip,growthNoteKey,growthDriveKey,growthNoteLine} from '@/lib/universe/growth-copy.mjs';
import {addMechanics,createAsciiPass,underwaterColor} from '@/lib/universe/mechanics-three';
import {weatherFrom,createMover,stepMover,createWater,stepWater,waterTotal} from '@/lib/universe/world-mechanics.mjs';
import {createFoamField,syncFoam,foamBytes,foamStats} from '@/lib/universe/foam-field.mjs';
import {SEA_GLSL,seaFrom} from '@/lib/universe/sea-state.mjs';
import {CAUSTIC_GLSL,CAUSTIC_TAP_GLSL,CAUSTIC_LITE_GLSL,CAUSTIC_GATE_GLSL,CAUSTIC,causticColour} from '@/lib/universe/caustics.mjs';
import {atmoClass,limbRim,limbAt,hazeFor} from '@/lib/universe/atmosphere-look.mjs';
import {VL_ATMOSPHERE,pairTableGLSL} from '@/lib/universe/vislife-look.mjs';
import {receipt,VL_OUTPUT_LABELS,VL_TEXT} from '@/lib/universe/visual-life-labels.mjs';
import {provenance as vlProvenance} from '@/lib/universe/visual-life-provenance.mjs';
import {detectEvents,recipe as evRecipe,noiseSamples} from '@/lib/universe/event-sounds.mjs';
import {LW_LABELS,gatheringPoints,spreadAngle,initialTraits,driftTraits,lattice12D,lwStream,unitFrom} from '@/lib/universe/living-world.mjs';
import {ARTIST_RESIDENTS} from '@/lib/companion/artist-residents.mjs';
import {RESIDENT_LIFE_KEY,lifeTransform,hopSeconds} from '@/lib/universe/sprite-life.mjs';
import {creatureVoice,roadsterVoice,voiceTurn,voiceCategory,seaLifeVoice,SEA_VOICE_KEY} from '@/lib/universe/creature-voices.mjs';
import {voiceCast,castLine,createRoadsterVoice} from '@/lib/universe/voice-cast.mjs';
import {readActiveBeast} from '@/lib/companion/beast-name.mjs';
import {cosmicEvents,cosmicLine,createWindow,stepWindow,windowLine,seededMood,spreadMood,napGroup,buildKind,advanceBuild,coexistLine,worldLine,placeLine,learnBiome,worldRecord,toJsonl,windowEmissive,traitIcon,MOOD_ICON,ZEREF_ID} from '@/lib/universe/living-alive.mjs';
import {addCageSurface} from '@/lib/universe/surface-three';
import {ROADSTER_LABEL,bodyVariantIndex,wheelOmega,steerAngle,driveState,bodyBob,headlamp,underglow} from '@/lib/universe/roadster-view.mjs';
import {FLIGHT,FLIGHT_LABEL,liftOff,stepFlight,flightInfo,landingAssist,ascentAssist,orbitElements,skyFade,norm} from '@/lib/universe/roadster-flight.mjs';
import {growthNodesAt,GROWTH} from '@/lib/universe/seeded-growth-nodes.mjs';
import {snapNodesToHabitat,TINT_BIOMES} from '@/lib/universe/growth-view.mjs';
import {REDUCED_MOTION_KEY} from '@/components/use-universe-motion';
import {createAliveGate} from '@/lib/universe/alive-props.mjs';
import {seededLandscapes,withHomeLandscapes,landscapeNotice,landscapeTapLine} from '@/lib/universe/seeded-landscapes.mjs';
import {addLandscapes} from '@/lib/universe/landscape-three';
import {zoomBlend,zoomDistance,stepZoom,clampAboveGround,isMeadow} from '@/lib/universe/groundcover.mjs';
import {addHeaven} from '@/lib/worlds/heaven';
import {buildPlush,type PlushGenome} from './creature-plush-3d';
import {loadCreatureModel} from './creature-model-slot';
import {heavyAllowed} from '../lib/creatures3d/creature-model-slot.mjs';
import RES_PAINTS from '@/lib/creatures3d/resident-paints.json';
import {skyAt} from '@/lib/universe/sky-state.mjs';
import {palette as heroPalette,heroLegend} from '@/lib/universe/hero-palette.mjs';
import {stageBooms,limbPoint} from '@/lib/universe/event-staging.mjs';
import {addSkyDome,addFlatGround,addSkyWorld,LOOK2} from '@/lib/universe/one-world-look';import {localSunDir} from '@/lib/universe/one-sun.mjs';
import {createPostChain} from '@/lib/universe/post-chain-three';
import {activeTier,writeTierOverride,nextTier,qualityLabel} from '@/lib/universe/post-tiers.mjs';
import {readViewMode,writeViewMode,nextViewMode,viewModeLabel,viewModeCamera,VIEW_MODE_EVENT} from '@/lib/world/view-mode.mjs';
import {oneSunAt,ONE_SUN,COMPANION_DISC,SKY_LINES} from '@/lib/universe/one-sun.mjs';const COMPANION_DISC_DIR=[-0.9439,0.1392,0.2994];
import {skyConfigFor,sunSource,skyBooms,skyMoons,boomSpriteScale,boomBearing,SKY_VIEW,engineChannels} from '@/lib/universe/sky-view.mjs';
import {planetName} from '@/lib/universe/friendly-names.mjs';
const smoothstepJS=(a:number,b:number,x:number)=>{const t=Math.min(1,Math.max(0,(x-a)/(b-a)));return t*t*(3-2*t);};
const ART='/universe/livingworld/';
// All event lines are Cosmic Emeth's (lib/universe/data/living_world_lines.json + biome_lore.json via living-alive.mjs).
const CX=ART+'coexist/'; // Cosmo's coexist art: models/{cairn,flower_ring,burrow}_stage{1,2,3}.glb, sprites/, moods.json
const PR=8;           // planet radius (world units)
const TRAV_H=.5;      // traveler height
type Traits={curiosity:number;sociality:number;calm:number;joy:number;experiences:number};
export default function LivingWorld({genome,beastKey,beastName,onClose,embedded=false,onExpand,door=false,onOrbitOut,menuHost=null,infoHost=null}:{menuHost?:HTMLElement|null;infoHost?:HTMLElement|null;genome?:PlushGenome|null;beastKey?:string|null;beastName?:string|null;onClose?:()=>void;embedded?:boolean;onExpand?:()=>void;door?:boolean;onOrbitOut?:()=>void}){
 // door: mounted inside /universe as the pocket world's end of the one continuous zoom (orbit view, no storage, no full-screen takeover)
 const [viewMode,setViewMode]=useState<string>('first');const viewRef=useRef('first');viewRef.current=viewMode;useEffect(()=>{try{setViewMode(readViewMode(localStorage));}catch{}},[]);
 const [qTier,setQTier]=useState<string|null>(null);const qTierRef=useRef<string|null>(null);qTierRef.current=qTier;
 const [creatureOn]=useCageCreature();const creatureRef=useRef(creatureOn);creatureRef.current=creatureOn;
 const orbitOutRef=useRef(onOrbitOut);orbitOutRef.current=onOrbitOut;const [beachCam,setBeachCam]=useState(false);const seaJump=useRef(0);const beachCamRef=useRef(false);beachCamRef.current=beachCam;
 const host=useRef<HTMLDivElement>(null);const hudBiome=useRef<HTMLSpanElement>(null);const hudSea=useRef<HTMLSpanElement>(null);const hudVL=useRef<HTMLSpanElement>(null);const hudGN=useRef<HTMLSpanElement>(null);const hudHome=useRef<HTMLSpanElement>(null);const hudGNx=useRef<HTMLParagraphElement>(null);const canvasRef=useRef<HTMLCanvasElement>(null);
 const [spawned,setSpawned]=useState(()=>{if(embedded||door)return false;try{return sessionStorage.getItem('lw:spawned')==='1';}catch{return false;}});const [watch,setWatch]=useState(embedded);const watchRef=useRef(false);watchRef.current=watch;const spawnRef=useRef(false);
 const [hud,setHud]=useState<{tick:number;simE:number|null;life:number;storms:number;cover:number;traits:Traits|null;blades:number;fps:number;learned?:Record<string,number>;awake?:number}>({tick:0,simE:null,life:0,storms:0,cover:0,traits:null,blades:0,fps:0});
 /* Visual Life Pass B6: event sounds, OFF until the person turns the one toggle on; the AudioContext is created in that tap */
 const [prov,setProv]=useState<any>(null);const [sndOn,setSndOn]=useState(false);const sndRef=useRef<any>({on:false,ctx:null});
 useEffect(()=>()=>{try{sndRef.current.ctx?.close();}catch{}sndRef.current={on:false,ctx:null};},[]);
 const toggleSound=()=>{const s=sndRef.current;if(s.on){s.on=false;setSndOn(false);try{s.ctx?.suspend();}catch{}return;}try{const AC=(window as any).AudioContext||(window as any).webkitAudioContext;if(!s.ctx&&AC)s.ctx=new AC();s.ctx?.resume?.();}catch{}s.on=!!s.ctx;setSndOn(!!s.ctx);};
 const [err,setErr]=useState<string|null>(null);const [booted,setBooted]=useState(false);const [line,setLine]=useState<string|null>(null);const lineRef=useRef(setLine);lineRef.current=setLine;
 useEffect(()=>{if(!line)return;const id=setTimeout(()=>setLine(null),4200);return()=>clearTimeout(id);},[line]);
 const [ascii,setAscii]=useState(false);const asciiRef=useRef(false);asciiRef.current=ascii;const [visit,setVisit]=useState<{id:string;star?:string}|null>(null);const [roadster,setRoadster]=useState(false);const roadsterRef=useRef(false);roadsterRef.current=roadster;const [flying,setFlying]=useState(false);const flyRef=useRef(false);flyRef.current=flying;const joy=useRef({x:0,y:0,active:false,id:-1,cx:0,cy:0});const keys=useRef(new Set<string>());const rfRef=useRef({want:false,thrust:false,brake:false,assist:'' as ''|'land'|'ascent',on:false});const [rfUi,setRfUi]=useState(false);const hudRef=useRef<HTMLDivElement>(null);
 const [stick,setStick]=useState<{x:number;y:number}|null>(null);
 useEffect(()=>{if(embedded||door)return;try{sessionStorage.setItem('lw:spawned',spawned?'1':'0');}catch{}},[spawned,embedded]);
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
   // ?planet=<id>: take your beast to another planet of the recorded-seed universe. The terrain is re-generated by the same generators from a seed derived from the recorded one plus this planet's own water and temperature (SEEDED, not a measured surface). Nothing from a visit is saved, so the home world and your beast's saved state stay as they were; growth nodes stay a home-world feature.
   const seed0=g0.seed;const homeId0=[...(u.planets||[])].sort((a:any,b:any)=>(b.habitability||0)-(a.habitability||0))[0]?.id;
   const visitPl:any=(()=>{try{const q=new URLSearchParams(location.search).get('planet');return q&&q!==homeId0?(u.planets||[]).find((p:any)=>p.id===q)||null:null;}catch{return null;}})();
   const VISIT=!!visitPl;const lwStore:Pick<Storage,'setItem'>=VISIT?{setItem:()=>{}}:localStorage;
   if(VISIT){u={...u,seed:u.seed+':visit:'+visitPl.id};setVisit({id:visitPl.id,star:visitPl.star});}
   let traits:Traits=(()=>{try{const t=JSON.parse(localStorage.getItem('lw:traits:'+bKey)||'null');if(t&&typeof t.calm==='number')return t;}catch{}return initialTraits(u,bKey);})();
   const canvas=canvasRef.current!;
   const phone=matchMedia('(max-width: 820px)').matches||/iPhone|iPad|Android/.test(navigator.userAgent);
   const renderer=new THREE.WebGLRenderer({canvas,antialias:!phone,powerPreference:'high-performance'});
   renderer.setPixelRatio(Math.min(devicePixelRatio||1,phone?2:2));renderer.outputColorSpace=THREE.SRGBColorSpace;
   const scene=new THREE.Scene();(window as any).__lwScene=scene;scene.background=new THREE.Color(0x05030f);
   const aliveGate=createAliveGate();const camera=new THREE.PerspectiveCamera(55,1,.05,400);(window as any).__lwCam=camera;
   const L=new THREE.TextureLoader();const tex=(f:string,rep=false)=>{const t=L.load(ART+f);t.colorSpace=THREE.SRGBColorSpace;if(rep){t.wrapS=t.wrapT=THREE.RepeatWrapping;}return t;};
   const hemi=new THREE.HemisphereLight(0xb9a8ff,0x223322,1.1);scene.add(hemi);const sun=new THREE.DirectionalLight(0xfff1dd,1.6);sun.position.set(20,14,10);scene.add(sun);scene.add(sun.target);
   // a real sun: day/night from the wall clock (approach from Genesis X env sim: light = max(.1, h*.8+.2), ambient = max(.1, h*.3+.1))
   renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;sun.castShadow=true;sun.shadow.mapSize.set(phone?512:1024,phone?512:1024);
   {const c=sun.shadow.camera as any;c.left=c.bottom=-6;c.right=c.top=6;c.near=1;c.far=60;c.updateProjectionMatrix();}sun.shadow.bias=-.002;
   // star from the recorded-seed universe: the home planet's own star; colour from its temperature (blackBodyToRGB, Cory's Lost Cosmos file)
   const blackBodyToRGB=(temp:number)=>{temp/=100;let r:number,g:number,b:number;if(temp<=66){r=255;g=99.47*Math.log(temp)-161.12;b=temp<=19?0:138.52*Math.log(temp-10)-305.04;}else{r=329.7*Math.pow(temp-60,-.133);g=288.12*Math.pow(temp-60,-.0755);b=255;}const c=(x:number)=>Math.max(0,Math.min(255,x))/255;return new THREE.Color(c(r),c(g),c(b));};
   const homePl=VISIT?visitPl:[...(u.planets||[])].sort((a:any,b:any)=>(b.habitability||0)-(a.habitability||0))[0];const homeStar=(u.stars||[]).find((x:any)=>x.id===homePl?.star)||u.stars?.[0];
   const starCol=blackBodyToRGB(homeStar?.temperature_k||5800);sun.color.copy(starCol);(window as any).__lwStar={id:homeStar?.id,temperature_k:homeStar?.temperature_k,planet:homePl?.id};
   /* the engine's sky (PR 5): config from the same shading data the orbit globe uses; booms replayed from engine history */
   const skyCfg=skyConfigFor(homePl,homeStar);const skyBoomList=skyBooms(u,homePl,homeStar,(u as any).tick||0);const hemiBase=new THREE.Color(0xb9a8ff);
   renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=.85; /* FIX_NOTES 43c74d3: 1.15 stacked with the lights and blew out the day */
   // the Cage's sun glow + light shaft + bloom halo (lib/worlds/heaven, shared with the home Cage), standing over whoever you're close to
   const heaven=addHeaven(THREE,scene,{low:phone,rand:lwStream(u.seed+':heaven'),noLight:true});heaven.root.scale.setScalar(.4);
   // key light on the beast so it reads as brightly as in the Cage
   const beastLamp=new THREE.PointLight(0xfff1e6,7,TRAV_H*8,1.6);scene.add(beastLamp);
   const DAY_S=240;const sunDir=new THREE.Vector3(1,.3,.2).normalize();const SKY_DAY=new THREE.Color(0x86bfff),SKY_DUSK=new THREE.Color(0xff9a5a),SKY_NIGHT=new THREE.Color(0x05030f);
   const softGL=isSoftwareGL();
   // P1 post chain (Cosmo's p1post pack, SEEDED): render -> god rays -> bloom -> optics -> output. LOW keeps today's single render.
   let post:any=null;const tier0=activeTier(localStorage,{phone,softGL,cores:navigator.hardwareConcurrency,memoryGB:(navigator as any).deviceMemory,reducedMotion:matchMedia('(prefers-reduced-motion: reduce)').matches});qTierRef.current=tier0;setTimeout(()=>setQTier(tier0),0);
   const postFor=(t:string)=>{if(t==='LOW'){post?.dispose();post=null;renderer.toneMappingExposure=.85;(window as any).__lwPost={tier:'LOW',passes:['RenderPass']};return;}if(post){post.setTier(t);return;}void createPostChain(THREE,renderer,scene,camera,t).then(pc=>{post=pc;}).catch(()=>{post=null;});};postFor(tier0);let postTierSeen=tier0;// CI SwiftShader / GPU-less VMs: skip the heavy landform/mechanics layers so the main thread never starves (real GPUs incl. phones keep them)
   const lk2Sky=addSkyDome(THREE,scene),lk2Ground=addFlatGround(THREE,scene,lwStream(u.seed+':ridges')),lk2World=addSkyWorld(THREE,scene);let fpOn=false;
   const cosmoSky=softGL?{update:(..._a:any[])=>{}}:addCosmoSky(THREE,scene,{radius:230,phone});const nova=lfSheet(THREE,LANDF+'vfx/supernova_4x4_256.png',{fps:10,loop:false});nova.sp.scale.setScalar(30);scene.add(nova.sp);(window as any).__lwNova=()=>{nova.sp.position.copy(sunDir).multiplyScalar(-150);nova.play();};const sunDisc=new THREE.Sprite(new THREE.SpriteMaterial({map:L.load(LANDF+'sky/sun_corona_512.png'),color:0xfff0c0,transparent:true,blending:THREE.AdditiveBlending,depthWrite:false,fog:false}));sunDisc.scale.setScalar(40);sunDisc.material.color.copy(starCol);scene.add(sunDisc);
   const starMesh=new THREE.Mesh(new THREE.SphereGeometry(6,32,20),new THREE.MeshBasicMaterial({color:starCol,toneMapped:false}));scene.add(starMesh);
   const moon=new THREE.Mesh(new THREE.SphereGeometry(2.2,24,16),new THREE.MeshStandardMaterial({color:0xd8dcef,emissive:0x40445a,roughness:1}));scene.add(moon);
   const boomTex=(()=>{const c=document.createElement('canvas');c.width=c.height=128;const g=c.getContext('2d')!;const im=g.createImageData(128,128);for(let y=0;y<128;y++)for(let x=0;x<128;x++){const r=Math.hypot(x-63.5,y-63.5)/64,R=1/3;const a=Math.exp(-Math.pow(r/R,1.4))+0.18*Math.exp(-(r/(3*R)))*(r<1?1:0);const k=Math.max(0,Math.min(1,a*(r<1?1-r*r*r:0)))*255;const i=(y*128+x)*4;im.data[i]=im.data[i+1]=im.data[i+2]=255;im.data[i+3]=k;}g.putImageData(im,0,0);const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t;})();
   const boomGlow=new THREE.Sprite(new THREE.SpriteMaterial({map:boomTex,transparent:true,blending:THREE.AdditiveBlending,depthWrite:false,fog:false}));boomGlow.visible=false;scene.add(boomGlow);
   /* Visual Life Pass B4: ONE ring shell for the boom (pack mood_31: cream outer edge, teal inner edge, violet-grey shadow body), driven by boomState phase/shellFrac; plus an orbit bloom on the limb nearest the bearing */
   const ringTex=(()=>{const c=document.createElement('canvas');c.width=c.height=256;const g=c.getContext('2d')!;const im=g.createImageData(256,256);for(let y=0;y<256;y++)for(let x=0;x<256;x++){const r=Math.hypot(x-127.5,y-127.5)/128;const a=Math.exp(-Math.pow((r-.86)/.045,2));const i=(y*256+x)*4;im.data[i]=im.data[i+1]=im.data[i+2]=255;im.data[i+3]=Math.max(0,Math.min(1,a))*255;}g.putImageData(im,0,0);const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t;})();
   const bodyTex=(()=>{const c=document.createElement('canvas');c.width=c.height=128;const g=c.getContext('2d')!;const im=g.createImageData(128,128);for(let y=0;y<128;y++)for(let x=0;x<128;x++){const r=Math.hypot(x-63.5,y-63.5)/64;const a=(1-smoothstepJS(.5,.9,r))*smoothstepJS(0,.5,r);const i=(y*128+x)*4;im.data[i]=im.data[i+1]=im.data[i+2]=255;im.data[i+3]=Math.max(0,Math.min(1,a))*255;}g.putImageData(im,0,0);const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t;})();
   const mkSp=(map:any,blend:any)=>{const sp=new THREE.Sprite(new THREE.SpriteMaterial({map,transparent:true,blending:blend,depthWrite:false,fog:false}));sp.visible=false;scene.add(sp);return sp;};
   const ringOut=mkSp(ringTex,THREE.AdditiveBlending),ringIn=mkSp(ringTex,THREE.AdditiveBlending),ringBody=mkSp(bodyTex,THREE.NormalBlending),orbBloom=mkSp(boomTex,THREE.AdditiveBlending),orbHalo=mkSp(boomTex,THREE.AdditiveBlending);
   let vlBoomList:any=null,vlBoomTick=0,vlSunUp=0,vlBoom:any=null;
   const skyMoonMeshes:any[]=[moon];
   let starMat:any=null;
   // ---- stars + 12D lattice in the sky (when the viewer pulls back past the orbit, this shell follows the camera and grows with its distance, so it never shows as a ball)
   let lwStars:any=null;
   {const r=lwStream(u.seed+':sky');const n=phone?900:1800,p=new Float32Array(n*3);for(let i=0;i<n;i++){const v=unitFrom(r);const d=120+r()*80;p.set([v[0]!*d,v[1]!*d,v[2]!*d],i*3);}
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(p,3));starMat=new THREE.PointsMaterial({color:0xdde6ff,size:.6,sizeAttenuation:true,transparent:true});lwStars=new THREE.Points(g,starMat);scene.add(lwStars);}
   const lat=lattice12D(u.seed,phone?160:256);const lg=new THREE.BufferGeometry();lg.setAttribute('position',new THREE.Float32BufferAttribute(lat.verts.map(v=>v*7),3));lg.setIndex(lat.edges);
   const latObj=new THREE.LineSegments(lg,new THREE.LineBasicMaterial({color:0x8f7bff,transparent:true,opacity:.28,depthWrite:false}));latObj.position.set(0,0,0);
   const latPivot=new THREE.Group();latPivot.add(latObj);latObj.position.set(0,26,-30);scene.add(latPivot);
   // ---- planet ground: grass/soil tiles blended by a coverage field that spreads from gathering points
   const gpts=gatheringPoints(u,bKey).map(v=>new THREE.Vector3(...v));
   const UG:any={uRamp:{value:(()=>{const t=L.load('/universe/livingworld/landforms/ocean/water_depth_ramp_256x16.png');t.colorSpace=THREE.SRGBColorSpace;return t;})()},uFoam:{value:(()=>{const t=L.load('/universe/livingworld/landforms/ocean/foam_512.png');t.wrapS=t.wrapT=THREE.RepeatWrapping;return t;})()},uFoamF:{value:null},uFoamOn:{value:0},uCausOn:{value:0},uHeroOn:{value:0},uHero:{value:Array.from({length:20},()=>new THREE.Vector3(0,0,0))},uHW:{value:[new THREE.Vector3(),new THREE.Vector3(),new THREE.Vector3()]},uBoomLit:{value:0},uBoomDeep:{value:.22},uBoomCol:{value:new THREE.Vector3(1,1,1)},uBoomDir:{value:new THREE.Vector3(0,1,0)},uHazeOn:{value:0},uHazeCol:{value:new THREE.Vector3(.8,.85,.9)},uHazeD:{value:0},uHazeCap:{value:.92},uCausHeavy:{value:0},uSeaT:{value:0},uSeaDir:{value:0},uSeaAmp:{value:.012},uSeaChop:{value:.25},uCausC0:{value:new THREE.Vector3(...causticColour(.5))},uCausC1:{value:new THREE.Vector3(...causticColour(8))},uFoamDrift:{value:new THREE.Vector2(0,0)},uMap:{value:null},uUseMap:{value:0},uHeight:{value:null},uDisp:{value:0},uGlow:{value:null},uIdx:{value:null},uField:{value:0},uTiles:{value:null},uUseTiles:{value:0},uLeg:{value:Array.from({length:20},()=>new THREE.Vector3(9,9,9))},uMN:{value:(()=>{const t=L.load('/universe/livingworld/groundcover/textures/meadow_near_albedo_1024.png');t.colorSpace=THREE.SRGBColorSpace;t.wrapS=t.wrapT=THREE.RepeatWrapping;return t;})()},uMF:{value:(()=>{const t=L.load('/universe/livingworld/groundcover/textures/meadow_far_albedo_1024.png');t.colorSpace=THREE.SRGBColorSpace;t.wrapS=t.wrapT=THREE.RepeatWrapping;return t;})()},uGrass:{value:tex('ground_grass_tile_256.jpg',true)},uSoil:{value:tex('ground_soil_tile_256.jpg',true)},uMask:{value:tex('grass_edge_edge_mask.png',true)},
    uPts:{value:gpts},uLift:{value:0},uPlay:{value:Array.from({length:8},()=>new THREE.Vector3())},uSpread:{value:spreadAngle(u)},uT:{value:0},uShow:{value:0},uSun:{value:sun.position.clone().normalize()}};
   const COVER=`uniform sampler2D uHeight;uniform float uDisp;vec2 eqUV(vec3 n){return vec2(atan(n.z,n.x)/6.2832+.5,asin(clamp(n.y,-1.0,1.0))/3.1416+.5);}float disp(vec3 n){return uDisp>0.0?max(0.0,texture2D(uHeight,eqUV(n)).r-0.42)*uDisp:0.0;}uniform vec3 uPts[8];uniform float uSpread;float cover(vec3 n){float c=0.0;for(int i=0;i<8;i++){float a=acos(clamp(dot(n,uPts[i]),-1.0,1.0));c=max(c,smoothstep(uSpread,uSpread-0.35,a));}return c;}`;
   // beasts gather first on living land (plains/forest; tundra or pine near the poles), so pick the first seeded layout variant that puts the gathering point there
   const BP=VISIT?biomeParams(visitPl.id+':'+seed0,{water:visitPl.water,temp:visitPl.temperature_k}):(()=>{const g0=gpts[0];for(let i=0;i<64;i++){const bp=biomeParams(i?u.seed+':v'+i:u.seed);if(['plains','heartwood','pine','tundra'].includes(biomeAt(bp,[g0.x,g0.y,g0.z]) as string))return bp;}return biomeParams(u.seed);})();const BGL=biomeGLSL(BP);let biomeOf=(n:import('three').Vector3)=>biomeAt(BP,[n.x,n.y,n.z]) as string;
   const ground=new THREE.Mesh(new THREE.SphereGeometry(PR,phone?96:160,phone?64:110),new THREE.ShaderMaterial({uniforms:UG,
    vertexShader:`varying vec3 vN;varying vec2 vUv;varying vec3 vWp;${COVER}void main(){vN=normalize(position);vUv=uv*vec2(48.0,24.0);vec3 p=position+vN*disp(vN);vWp=p;gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.0);}`,
    fragmentShader:`uniform sampler2D uGrass,uSoil,uMask,uMap,uGlow,uIdx,uTiles,uMN,uMF,uRamp,uFoam,uFoamF;uniform vec2 uFoamDrift;uniform float uHazeOn,uHazeD,uHazeCap,uBoomLit,uBoomDeep;uniform vec3 uBoomCol,uBoomDir,uHero[20],uHW[3];uniform float uHeroOn;uniform vec3 uHazeCol;uniform float uFoamOn,uCausOn,uCausHeavy,uSeaT,uSeaDir,uSeaAmp,uSeaChop;uniform vec3 uCausC0,uCausC1;${SEA_GLSL}
${CAUSTIC_GLSL}
${CAUSTIC_TAP_GLSL}
${CAUSTIC_LITE_GLSL}
${CAUSTIC_GATE_GLSL}
uniform float uT,uShow;uniform float uUseMap,uUseTiles,uField;uniform vec3 uSun,uLeg[20];uniform float uLift;varying vec3 vN;varying vec2 vUv;varying vec3 vWp;${COVER}${BGL}
     int legIdx(vec3 c){int bi=0;float bd=9.0;for(int i=0;i<20;i++){vec3 d=c-uLeg[i];float dd=dot(d,d);if(dd<bd){bd=dd;bi=i;}}return bi;}
     vec3 tri(sampler2D t,vec3 n){vec3 w=pow(abs(n),vec3(4.0));w/=w.x+w.y+w.z;vec3 p=n*${(PR/2).toFixed(1)};return texture2D(t,p.yz).rgb*w.x+texture2D(t,p.xz).rgb*w.y+texture2D(t,p.xy).rgb*w.z;}
     void main(){vec3 n=normalize(vN);int b=biome(n);float c=cover(n);float m=.5+.35*(tri(uMask,n*1.7).r-.5)+.25*(fract(sin(dot(floor(n*40.0),vec3(12.9,78.2,37.7)))*43758.5)-.5);float g=smoothstep(m-.2,m+.2,c*1.1);
      vec3 grassT=tri(uGrass,n),soilT=tri(uSoil,n);float det=.75+.6*dot(mix(soilT,grassT,g),vec3(.333));vec3 col=biomeCol(b,n)*det;
      // the spreading grass still grows: it thickens and brightens the living biomes
      vec3 gt=b==5||b==4?vec3(.8,.92,1.0):b==7?vec3(.55,.55,.55):b==3?vec3(.85,.9,.5):b==9?vec3(.75,.6,.9):vec3(1.0);
      if(b!=0&&b!=10)col=mix(col,col*1.1+grassT*gt*.4,g*(b==1||b==2||b==6?1.0:.6));
      if(uUseMap>.5){vec2 eq=eqUV(n);col=texture2D(uMap,eq).rgb*(.85+.3*det-.15)*(1.0+.12*g);
       // Cosmo's seamless biome tiles up close (atlas 5x4 in legend order, picked from the biome index map)
       if(uUseTiles>.5){float dc=distance(cameraPosition,vWp);float near=smoothstep(9.0,2.5,dc);if(uField>.5){/* cells the live world field has changed (alpha 1) used to switch to flat tile art with a hard cell-shaped edge (the flat wedges and streaks seen from orbit): feather across neighbouring cells with 5 dithered taps */float fa=0.0;for(int k=0;k<5;k++){float ang=float(k)*2.39+fract(sin(dot(vWp,vec3(91.7,37.3,13.1)))*4375.5)*6.28;vec2 o=k==0?vec2(0.0):vec2(cos(ang)/64.0,sin(ang)/32.0)*1.1;fa+=texture2D(uIdx,eq+o).a>.5?.2:0.0;}near=max(near,.85*smoothstep(.0,.8,fa));}/* the ocean has its own depth-ramp pass below: biome tile art over water (flat navy/purple patches, ember streaks, hard cell wedges) is skipped where the height map is under sea level */if(uUseMap>.5)near*=smoothstep(.40,.44,texture2D(uHeight,eq).r);if(near>0.0){int bi=legIdx(texture2D(uIdx,eq).rgb);vec2 tu0=vec2(eq.x*96.0,eq.y*48.0);vec2 tuv=fract(tu0);tuv=clamp(tuv,.02,.98);vec2 cell=vec2(float(bi-(bi/5)*5),float(bi/5));vec3 tc=textureGrad(uTiles,(cell+vec2(tuv.x,1.0-tuv.y))/vec2(5.0,4.0),dFdx(tu0)*vec2(.2,.25),dFdy(tu0)*vec2(.2,.25)).rgb;col=mix(col,tc*(1.0+.12*g),near*.8);}}}
      // Cosmo's cage meadow (near ~2 m repeat x far 40-60 m macro, blended by distance) on every meadow biome, tinted by the biome colour
      if(uUseMap>.5){float dmM=distance(cameraPosition,vWp)/${(TRAV_H/1.7).toFixed(4)};float wM=1.0-smoothstep(90.0,170.0,dmM);if(wM>0.0){int bm=legIdx(texture2D(uIdx,eqUV(n)).rgb);
       // soft meadow mask: 5 dithered taps across the field cells so meadow edges blend instead of showing square tiles
       float mf=0.0;for(int k=0;k<5;k++){float ang=float(k)*2.39+fract(sin(dot(n,vec3(91.7,37.3,13.1)))*4375.5)*6.28;vec2 o=k==0?vec2(0.0):vec2(cos(ang),sin(ang))*vec2(1.0/96.0,1.0/48.0)*1.2;int bk=legIdx(texture2D(uIdx,eqUV(n)+o).rgb);mf+=(bk==3||bk==4||bk==5||bk==6||bk==11||bk==12||bk==13||bk==16||bk==18)?.2:0.0;}
       wM*=smoothstep(0.0,.8,mf);if(mf>0.0){vec3 nr=tri(uMN,n*3.4),fr=tri(uMF,n*.136);float fl=dot(fr,vec3(.333));vec3 md=mix(nr*(.55+fl*1.2),fr,smoothstep(15.0,60.0,dmM));
       vec3 tn=vec3(0.0);for(int i=0;i<20;i++)if(i==bm)tn=uLeg[i];col=mix(col,md*mix(vec3(1.0),tn*1.7,.45)*(1.05+.25*det),wM);}}}
      /* Visual Life Pass B5: ONE hero palette (pack, from the engine's planet numbers) as a per-biome recolour that keeps the tile detail; the same uniforms serve orbit and first person */
      if(uUseMap>.5&&uHeroOn>.5){vec2 hq=eqUV(n);if(texture2D(uHeight,hq).r>=.42){vec3 hc=texture2D(uMap,hq).rgb;int hb=legIdx(hc);vec3 hl=vec3(0.0),ho=vec3(1.0);for(int i=0;i<20;i++)if(i==hb){hl=uHero[i];ho=uLeg[i];}col=mix(col,col*clamp(hl/max(ho,vec3(.05)),vec3(.45),vec3(1.8)),.6);}}
      // Cosmo's ocean: depth from the height map (sea level .42) -> depth ramp (shore turquoise -> abyss indigo), shoreline foam
      if(uUseMap>.5){float hh=texture2D(uHeight,eqUV(n)).r;if(hh<.42){float dm=(.42-hh)*160.0;float tw=1.0-exp(-dm/12.0);vec3 wc=texture2D(uRamp,vec2(tw,.5)).rgb;
       if(uHeroOn>.5)wc=mix(wc,tw<.5?mix(uHW[0],uHW[1],tw*2.0):mix(uHW[1],uHW[2],tw*2.0-1.0),.5);float fo=texture2D(uFoam,eqUV(n)*vec2(60.0,30.0)+uT*.02).r*smoothstep(1.5,0.0,dm);col=mix(col,wc,mix(.55,.95,tw))+fo*.7;
       /* Visual Life Pass B2: caustics on the shallow floor from the ONE sea wave function, gated by the sun (per fragment) and the pack depth fall-off */
       if(uCausOn>.5&&dm<${CAUSTIC.cutoffM.toFixed(1)}){float cs=dot(n,uSun);float cg=max(causticGate(cs),${CAUSTIC.nightMul.toFixed(3)}*(1.0-smoothstep(-.12,.35,cs)));float cI=uCausHeavy>.5?causticAt(n,uSeaT,uSeaDir,uSeaAmp,uSeaChop,dm):causticLite(seaWaveHeight(n.x,n.y,n.z,uSeaT,uSeaDir,uSeaAmp,uSeaChop),uSeaAmp)*exp(-dm/${CAUSTIC.decayM.toFixed(3)});col+=mix(uCausC0,uCausC1,tw)*cI*cg*(1.0-tw)*.55;}
       /* Visual Life Pass B1: the engine's FOAM FIELD (born at crests and the shore, carried by the engine wind, fading with age) drawn with the same foam detail, over the old foam */
       if(uFoamOn>.5){float ffa=texture2D(uFoamF,eqUV(n)).r;float ffd=texture2D(uFoam,(eqUV(n)+uFoamDrift)*vec2(60.0,30.0)).r;col+=vec3(.92,.97,1.0)*ffa*(.35+.65*ffd)*.85;}
       /* Visual Life Pass B4: the water lit by the boom (pack mix by the engine's 1/d^2 sky term; the far side stays dark, deep water takes far less) */
       if(uBoomLit>.001){col=mix(col,uBoomCol,uBoomLit*smoothstep(-.05,.35,dot(n,uBoomDir))*mix(1.0,uBoomDeep,tw));}}}
      if(uUseMap>.5&&uUseTiles>.5){vec2 tq=eqUV(n);float th=texture2D(uHeight,tq).r;float tdc=distance(cameraPosition,vWp);float tnr=smoothstep(14.0,3.0,tdc);if(th>=.42&&tnr>0.0){
       float thx=texture2D(uHeight,tq+vec2(1.0/2048.0,0.0)).r-th;float thy=texture2D(uHeight,tq+vec2(0.0,1.0/1024.0)).r-th;float tsl=clamp(length(vec2(thx,thy))*110.0,0.0,1.0);
       vec2 tq2=tq*vec2(150.0,75.0);vec2 tt=clamp(fract(tq2),.02,.98);vec2 tgx=dFdx(tq2)*vec2(.2,.25),tgy=dFdy(tq2)*vec2(.2,.25);/* gradients from the UNWRAPPED uv: fract() would jump at every tile edge and the GPU would pick the lowest mip there (Cosmo's grid-line diagnosis) */vec3 trk=textureGrad(uTiles,(vec2(3.0,1.0)+vec2(tt.x,1.0-tt.y))/vec2(5.0,4.0),tgx,tgy).rgb;vec3 tsn=textureGrad(uTiles,(vec2(4.0,1.0)+vec2(tt.x,1.0-tt.y))/vec2(5.0,4.0),tgx,tgy).rgb;
       col=mix(col,trk*(1.0+.1*g),smoothstep(.3,.7,tsl)*tnr*.75);col=mix(col,tsn,smoothstep(.7,.86,th)*(1.0-.5*tsl)*tnr*.8);
       col*=1.0+(thx*-1.0+thy*0.6)*40.0*tnr;}}
      vec3 v=normalize(cameraPosition-n*${PR.toFixed(1)});float dif=max(0.0,dot(n,uSun));float l=.46+1.15*dif+uLift*.55*(1.0-dif);col*=l;
      if(b==7)col+=vec3(.6,.2,.05)*pow(.5+.5*sin(bH(n)*50.0),8.0);if(b==10)col+=vec3(.2,.25,.4)*(1.0-dif);
      if(b==0)col+=vec3(.9,.95,1.0)*pow(max(0.0,dot(reflect(-uSun,n),v)),40.0)*.6;
      if(uUseMap>.5)col+=texture2D(uGlow,eqUV(n)).rgb*(1.0-smoothstep(-.1,.25,dot(n,uSun)))*1.1;
      /* Visual Life Pass B3: haze toward the sky horizon (pack curve 1-exp(-(d*density)^2), capped; density x fog multiplier from engine moisture and storm); first person only */
      if(uHazeOn>.5){float hd=distance(cameraPosition,vWp)*uHazeD;col=mix(col,uHazeCol,min(uHazeCap,1.0-exp(-hd*hd)));}
      float rim=pow(1.0-max(0.0,dot(n,v)),3.0);/* until Cosmo's maps (or the decision to use the seeded fallback) arrive, show a plain unlit planet: the procedural biome bands, ember stripes and white caps were flashing for several seconds on slow loads and read as stripes/seams */vec3 rimC=vec3(.35,.55,1.0)*rim*.45;gl_FragColor=vec4(mix(vec3(.05,.08,.15)*(.5+.9*dif)+rimC,col+rimC,uShow),1.0);}`}));
   scene.add(ground);
   {const sc=new THREE.Mesh(new THREE.SphereGeometry(PR+.012,phone?64:120,phone?40:80),new THREE.ShadowMaterial({opacity:.32,depthWrite:false}));sc.receiveShadow=true;sc.renderOrder=1; /* depthWrite off: this catcher sits at PR+.012, above the fish/birds/turtles (PR+.002..+.005), so with depth writes it hid them */scene.add(sc);}
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
    foamF=createFoamField(field);foamTex=new THREE.DataTexture(new Uint8Array(field.N*4),field.W,field.H,THREE.RGBAFormat);foamTex.magFilter=foamTex.minFilter=THREE.LinearFilter;foamTex.wrapS=THREE.RepeatWrapping;foamTex.needsUpdate=true;UG.uFoamF.value=foamTex;UG.uFoamOn.value=1;UG.uCausOn.value=1;UG.uCausHeavy.value=heavyAllowed({phone,deviceMemory:(navigator as any).deviceMemory,cores:navigator.hardwareConcurrency})?1:0;
    biomeOf=(n)=>{const id=legendAt(field,[n.x,n.y,n.z]);return (COSMO_TO_LW[id]||'plains');};cosmoNameOf=(n)=>legendAt(field,[n.x,n.y,n.z]).replace(/_/g,' ').replace(/\b\w/g,(m:string)=>m.toUpperCase());
    (window as any).__lwField=()=>({tick:field.tick,changed:field.changed,tension:+field.storm.toFixed(3),lorenz:{...field.S.L},records:expLog.length,beast:beastLoop.S.ch,zeref:zerefLoop.S.ch});};
   // ---- the Cage surface everywhere: Cosmo's ground cover + trees, instanced, planted from the seed per biome (one renderer: lib/universe/surface-three)
   let ocean:any=null;let surface:any=null;let lwLand:any=null;let lmPrev:string|null=null,lmGate:any=null,lmN=0;const landGoal=new THREE.Vector3();let island:any=null;let beach:any=null;let lwArea:string|null=null;let placeN=0;let roamGoal:any=null;let beachLift=0;let roamT=20;const roamR=lwStream(u.seed+':roam');const tourR=lwStream(u.seed+':flyover');let tourI=-1,tourT=0;const tourN=new THREE.Vector3();let touring=false;let mech:any=null;let water:any=null;let weather:any={cloud:.3,rain:0,wind:[0,0]};const mover=createMover();const ascii=createAsciiPass(THREE,renderer,{phone});cleanup.push(()=>ascii.dispose());
   // test-only URL params (default behaviour unchanged): ?hold=1 freezes the camera (no drift, no zoom) and holds the time of day; ?growthdebug=1 shows a readout of the nearest growth node and tap counts
    const HOLD=/[?&]hold=1\b/.test(location.search),GDBG=/[?&]growthdebug=1\b/.test(location.search);const hz:{m:string;z:number;a:number|null}={m:'',z:0,a:null};const gTaps:Record<string,number>={};let gDbgEl:HTMLElement|null=null,gDbgT=0;
    (window as any).__lwTestParams={hold:HOLD,growthdebug:GDBG};
   let growthUi:()=>void=()=>{};let gSnap:any[]=[];const growthNow=()=>{const sn=new Map(gSnap.map((n:any)=>[n.id,n]));return growthNodesAt(u,u.tick).filter((n:any)=>sn.has(n.id)).map((n:any)=>({...n,lat:sn.get(n.id).lat,lon:sn.get(n.id).lon,view_snapped:sn.get(n.id).view_snapped}));};
   const buildSurface=()=>{if(surface||disposed)return;const tintOf:Record<string,[number,number,number]>={};for(const L of (legend?.biomes||[])){const c=parseInt(L.rgb.slice(1),16);tintOf[L.id]=[(c>>16)/255,((c>>8)&255)/255,(c&255)/255];}
    const tv=new THREE.Vector3();
    // Growth nodes (SEEDED placement from the recorded-IBM seed, SIMULATED tick). The home world's nodes (including the SEEDED home-world exception) are moved by the VIEW to the nearest habitat the tint pack covers.
    // ?growth=off turns the layer off (every list then builds exactly as before).
    const biomeFn=(d:number[])=>field?legendAt(field,d):(cosmoBiome(tv.set(d[0],d[1],d[2]))||'grassland');
    const gOn=!VISIT&&!/[?&]growth=off\b/.test(location.search);
    if(gOn){try{gSnap=snapNodesToHabitat(growthNodesAt(u,u.tick),(d:number[])=>TINT_BIOMES.includes(biomeFn(d)));}catch{gSnap=[];}}
    surface=addCageSurface(THREE,scene,{growth:gOn&&gSnap.length?{nodes:growthNow(),tick:u.tick,cellRad:GROWTH.cellRad}:undefined,seed:u.seed+':surface',R:PR,mpu:TRAV_H/1.7,size:1.5,budget:phone?.22:.55,
     biomeAt:(d:number[])=>field?legendAt(field,d):(cosmoBiome(tv.set(d[0],d[1],d[2]))||'grassland'),lift:(n:any)=>hAt(n)-.004,tint:(b:string)=>tintOf[b]||null});
    // Landscapes (SEEDED, Oct 24 2026): the engine's places for THIS planet, drawn from Cosmo's look pack. ?landscapes=off turns the layer off; ?place=1 stands the beast on the first one.
    if(!/[?&]landscapes=off\b/.test(location.search)){try{const lsAll=seededLandscapes(u,{home:homeId0,biomeAt:(p:any,d:number[])=>p.id===homePl?.id?biomeFn(d):null}).filter((l:any)=>l.planet===homePl?.id);
     if(lsAll.length){lwLand=addLandscapes(THREE,scene,{landscapes:lsAll,R:PR,mpu:TRAV_H/1.7,hAt,phone,seed:u.seed});(window as any).__lwLifeView=withHomeLandscapes(u,lsAll);(window as any).__lwLandscapes=()=>lwLand?.snapshot();
      if(/[?&]place=1\b/.test(location.search)){const a=lsAll[0].anchors.play;const pin=()=>{bN.set(a[0],a[1],a[2]).normalize();bF.set(0,1,0).addScaledVector(bN,-bN.y).normalize();if(bF.lengthSq()<1e-6)bF.set(1,0,0);};pin();(window as any).__lwPlacePin=pin;}}}catch(e){console.warn('landscapes',e);}}
    // ASCII-CRAFT-style mechanics (engine-driven weather, flowing water, sea life, torch, mountains): additive, seeded
    mech=softGL?null:addMechanics(THREE,scene,{seed:u.seed,R:PR,mpu:TRAV_H/1.7,phone,unitFrom:(r:any)=>unitFrom(r) as number[],isWater:(v:any)=>WATER_IDS.has(field?legendAt(field,[v.x,v.y,v.z]):(cosmoBiome(v)||''))});
    if(field){water=createWater(field.W,field.H,Array.from(field.height));}
    // Cosmo's volcano island: IBM-seeded spot in the jelly sea (else deep/shallow ocean), away from the beast, bent onto the planet
    {const r=lwStream(u.seed+':island');const want=['jelly_geyser','deep_ocean','shallow_ocean'];let pick:any=null;
     for(const w of want){for(let i=0;i<160&&!pick;i++){const d=unitFrom(r) as number[];const v=new THREE.Vector3(d[0],d[1],d[2]);if(v.dot(gpts[0])>.82)continue;const id=field?legendAt(field,d):cosmoBiome(v);if(id===w)pick=v;}if(pick)break;}
     if(!pick)pick=new THREE.Vector3(...(unitFrom(r) as number[]));
     island=softGL?null:addVolcanoIsland(THREE,scene,{seed:u.seed,R:PR,mpu:TRAV_H/1.7,scale:.07,n:pick,phone});
     island?.ready.then(()=>{(window as any).__lwIsland={n:pick.toArray().map((x:number)=>+x.toFixed(3)),biome:field?legendAt(field,pick.toArray()):cosmoBiome(pick),...island.state()};}).catch((e:any)=>{(window as any).__lwIslandErr=String(e);});}
    // Pocket beach (Cosmo's beach v1): its own south shore per Studio's pocket-world map (Cage centre, beach south), on a seeded
    // 'beach' cell of the world field (else shallow sea) in the southern band, free-standing so its skirt blends into the ocean; terrain, not a tab
    {const r=lwStream(u.seed+':beach');let pick:any=null;for(const w of ['beach','shallow_ocean']){for(let i=0;i<400&&!pick;i++){const d=unitFrom(r) as number[];const v=new THREE.Vector3(d[0],d[1],d[2]);if(v.y>-.25||v.y<-.8)continue;if(island&&v.dot(island.anchor('crater_center').clone().normalize())>.995)continue;const id=field?legendAt(field,d):cosmoBiome(v);if(id===w)pick=v;}if(pick)break;}
     if(!pick)pick=new THREE.Vector3(...(unitFrom(r) as number[]));
     beach=addBeachShore(THREE,scene,{seed:u.seed,R:PR,mpu:TRAV_H/1.7,scale:.07,n:pick,phone,slotBiome:(d:number[])=>field?legendAt(field,d):(cosmoBiome(new THREE.Vector3(d[0],d[1],d[2]))||null)});(window as any).__lwBeach={biome:field?legendAt(field,pick.toArray()):cosmoBiome(pick),...beach.state()};
     beach.ready.then((ok:boolean)=>{(window as any).__lwBeach={biome:field?legendAt(field,pick.toArray()):cosmoBiome(pick),...beach.state(),glb:ok};});}
    // seeded ocean life (fish schools, rays, whales, plankton glow): only in water cells of the world field
    try{if(!(window as any).__lwNoOcean)ocean=addOceanLife(THREE,scene,{seed:u.seed,R:PR,mpu:TRAV_H/1.7,phone,life:Math.max(.4,Math.min(1.6,.6+((u.life||[]).length||0)*.15)),isWater:(d:number[])=>{const id=field?legendAt(field,d):(cosmoBiome(tv.set(d[0],d[1],d[2]))||'');return WATER_IDS.has(id)?id:null;}});cleanup.push(()=>ocean?.dispose());(window as any).__lwOcean=ocean.state();{const w0=ocean.data.schools.find((x:any)=>x.kind==='whale')||ocean.data.schools[0];if(w0)(window as any).__lwOceanN=new THREE.Vector3(w0.n[0],w0.n[1],w0.n[2]);}}catch(e){(window as any).__lwOceanErr=String(e);}
    (window as any).__lwGrowthInfo=()=>surface?.growthInfo?.();try{growthUi();}catch{}surface.ready.then((c:any)=>{if(disposed)return;blades.visible=false;(window as any).__lwSurface={counts:c,meshes:surface.meshes.length};}).catch((e:any)=>{(window as any).__lwSurfaceErr=String(e);});};
   (window as any).__lwVisualLifeProvenance=()=>vlProvenance((window as any).__lwVisualLife);
   let fieldAcc=0;let foamF:any=null,foamTex:any=null,foamTick=-1;let vlAir:any=null;let vlPal:any=null;const vlHud=()=>{if(!foamF)return;const e=hudVL.current;const fs=foamStats(foamF,field);const sunDeg=Math.asin(Math.max(-1,Math.min(1,sunDir.dot(bN))))*180/Math.PI;
    /* one chip; every line is authored text bound to a real engine number, all SIMULATED (stepped by the world loop); a line without its number is dropped */
    const hz=vlAir;const lines=[receipt('foam',{wind:fs.wind}),sunDeg>0&&UG.uCausOn.value===1?receipt('caustics',{sun:sunDeg}):null,hz?receipt('haze',{density:hz.atmo}):null,hz&&hz.mul>1.05?receipt('fog',{moisture:hz.moisture,tension:hz.storm}):null].filter(Boolean);
    const bl=vlBoom?receipt('boom_light',{}):null;const bnm=(hudBiome.current?.textContent||'').replace(/^Biome: /,'');const pl=vlPal&&bnm?receipt('palette',{temperature:Math.round(vlPal.temperature)+' K',biome:bnm}):null;if(e){e.style.display=lines.length&&fs.waterCells>0?'':'none';e.textContent=lines.join('; ')+' · '+VL_OUTPUT_LABELS.foam+(bl?'; '+bl+' · '+vlBoom.label:'')+(pl?'; '+pl+' · '+VL_OUTPUT_LABELS.palette:'');}
    (window as any).__lwVisualLife={...((window as any).__lwVisualLife||{}),caustics:{on:UG.uCausOn.value===1,heavy:UG.uCausHeavy.value===1,sunDeg:+sunDeg.toFixed(1),label:'SIMULATED'},foam:{cover:+fs.cover.toFixed(4),peak:+fs.peak.toFixed(3),wind:+fs.wind.toFixed(3),tick:fs.tick,label:'SIMULATED'},chip:lines};};
   /* Visual Life Pass B6: events from the engine's own channels (boom phase edge, storm tension edge, mean growth step), counted in engine ticks; sound only while the toggle is on */
   let evSt:any=null,evCount=0,evLast:any=null;const playEvent=(ctx:any,e:any)=>{const r=evRecipe(e.kind,e.magnitude);if(!r)return;const t0=ctx.currentTime+.02;
    for(const p of r.parts){const o=ctx.createOscillator(),g=ctx.createGain();o.type=p.wave;o.frequency.setValueAtTime(p.freq,t0+p.at);o.frequency.exponentialRampToValueAtTime(Math.max(20,p.freqEnd),t0+p.at+p.dur);g.gain.setValueAtTime(0,t0+p.at);g.gain.linearRampToValueAtTime(p.gain,t0+p.at+.03);g.gain.exponentialRampToValueAtTime(.0001,t0+p.at+p.dur);o.connect(g);g.connect(ctx.destination);o.start(t0+p.at);o.stop(t0+p.at+p.dur+.05);}
    if(r.noise){const n=Math.max(1,Math.floor(ctx.sampleRate*r.noise.dur));const buf=ctx.createBuffer(1,n,ctx.sampleRate);buf.getChannelData(0).set(noiseSamples(n,(e.tick*31+e.kind.length)|0));const src=ctx.createBufferSource(),lp=ctx.createBiquadFilter(),g=ctx.createGain();src.buffer=buf;lp.type='lowpass';lp.frequency.value=r.noise.lp;g.gain.setValueAtTime(r.noise.gain,t0);g.gain.exponentialRampToValueAtTime(.0001,t0+r.noise.dur);src.connect(lp);lp.connect(g);g.connect(ctx.destination);src.start(t0);}};
   const evStep=()=>{const s=sndRef.current;if(!s.on||!s.ctx||!field){evSt=null;const vl=(window as any).__lwVisualLife;if(vl)vl.sound={on:false,events:evCount,last:evLast,label:'SIMULATED'};return;}
    let gs=0,gn=0;for(let k=0;k<field.N;k+=17){gs+=field.grow[k];gn++;}
    const r=detectEvents(evSt,{tick:field.tick,boomPhase:vlBoom?vlBoom.phase:'none',boomTerm:vlBoom?vlBoom.skyTerm:0,storm:field.storm,grow:gs/gn});evSt=r.state;
    for(const e of r.events){try{playEvent(s.ctx,e);}catch{}evCount++;evLast={kind:e.kind,tick:e.tick,magnitude:+e.magnitude.toFixed(3)};}
    (window as any).__lwVisualLife={...((window as any).__lwVisualLife||{}),sound:{on:true,events:evCount,last:evLast,label:'SIMULATED'}};};
   const fieldStep=(dt:number,sunV:import('three').Vector3,activity:number)=>{if(!field)return;
    const heat=Math.min(1,Math.max(0,((homeStar?.temperature_k||5800)-3000)/6000));
    const ch=stepWorldField(field,dt,{sun:[sunV.x,sunV.y,sunV.z],starHeat:heat,activity,mood:{curiosity:traits.curiosity}});
    if(ch.length&&fieldTex){fieldTex.image.data.set(fieldRGBA(field,(i:number)=>legRGB[i]));fieldTex.needsUpdate=true;
     for(const ps of propSprites){const k=cellOf(field,[ps.n.x,ps.n.y,ps.n.z]);if(!ch.includes(k))continue;const id=LEGEND[field.idx[k]];ps.spr.visible=!!propSheets[id]&&ps.biome===id||!!propSheets[id];if(propSheets[id]&&ps.biome!==id){ps.biome=id;swapProp(ps,id);}}}
    if(foamF){syncFoam(foamF,field);if(foamF.tick!==foamTick){foamTick=foamF.tick;const q=foamTex.image.data;for(let k=0;k<foamF.N;k++){const v=Math.round(Math.min(1,foamF.foam[k])*255);q[k*4]=v;q[k*4+1]=v;q[k*4+2]=v;q[k*4+3]=255;}foamTex.needsUpdate=true;UG.uFoamDrift.value.set(foamF.drift[0],foamF.drift[1]);vlHud();}}
    evStep();
    if(foamF){const sea=seaFrom(field);UG.uSeaDir.value=sea.dir;UG.uSeaAmp.value=sea.amp;UG.uSeaChop.value=sea.chop;}
    storming=Math.max(storming,field.storm);
    fieldAcc+=dt;if(fieldAcc<1)return;const W1=fieldAcc;fieldAcc=0;
    const res=stepCreature(beastLoop,field,[bN.x,bN.y,bN.z],W1,traits,{others:[zerefLoop]});const zN=gpts[1]||gpts[0];stepCreature(zerefLoop,field,zN,W1,null,{others:[beastLoop]});
    if(res.drift)traits={...traits,...res.drift};
    for(const ev of res.events){if(ev.type==='affinity')say(beastNm+' feels a pull toward Zeref (affinity '+ev.affinity.toFixed(2)+').',6);}
    if(res.records.length){expLog=expLog.concat(res.records).slice(-400);try{lwStore.setItem(expKey,JSON.stringify(expLog));}catch{}(window as any).__lwExperiences=expLog;}};
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
    /* Visual Life Pass B5: the hero palette of the home world (engine atmosphere, temperature, water, host-star hue), one function for orbit and first person */
    try{if(homePl){const pal=heroPalette({atmosphere:homePl.atmosphere,temperature_k:homePl.temperature_k,water:homePl.water,hue:homeStar?.hue});const lg2=heroLegend(pal.type,lg.biomes);lg2.forEach((h:string,i:number)=>{const c=parseInt(h.slice(1),16);UG.uHero.value[i].set((c>>16)/255,((c>>8)&255)/255,(c&255)/255);});
     const l2s=(v:number)=>v<=.0031308?12.92*v:1.055*Math.pow(Math.max(0,v),1/2.4)-.055;if(pal.waterRamp){(['shallow','mid','deep'] as const).forEach((k,i)=>UG.uHW.value[i].set(l2s(pal.waterRamp![k][0]),l2s(pal.waterRamp![k][1]),l2s(pal.waterRamp![k][2])));}
     UG.uHeroOn.value=pal.waterRamp?1:0;(window as any).__lwVisualLife={...((window as any).__lwVisualLife||{}),palette:{type:pal.type,heroRole:pal.hero_role,heroShare:+pal.weights[pal.hero_role].toFixed(3),temperature:homePl.temperature_k,label:'SEEDED'}};vlPal={temperature:homePl.temperature_k,type:pal.type};}}catch(e){}
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
   cosmoReady.then(()=>{UG.uShow.value=1;},()=>{UG.uShow.value=1;});
   // atmosphere rim, visible from orbit
   {const lr=limbRim(skyCfg.atmosphere);const rc=VL_ATMOSPHERE.limb_rim[lr.cls==='mid'?'mid':'thick'];
    /* Visual Life Pass B3: the limb rim by atmosphere class (thickness = pack fraction of the radius from the engine atmosphere value; sunward limb brighter and golden at a low sun). Airless worlds have no rim. Old rim stays as the fallback when the pack class is missing. */
    const packRim=lr.enabled;const atm=new THREE.Mesh(new THREE.SphereGeometry(PR*(packRim?1+lr.thicknessFrac:1.07),64,40),new THREE.ShaderMaterial({transparent:true,depthWrite:false,side:THREE.BackSide,blending:THREE.AdditiveBlending,
     uniforms:{uSun:UG.uSun,uRimDay:{value:new THREE.Vector3(...rc.rim_colour.day.linear)},uRimGold:{value:new THREE.Vector3(...rc.golden_hour_rim_colour.linear)},uRimGain:{value:packRim?lr.gain:0},uRimPack:{value:packRim?1:0}},
     vertexShader:`varying vec3 vW;void main(){vW=(modelMatrix*vec4(position,1.0)).xyz;gl_Position=projectionMatrix*viewMatrix*vec4(vW,1.0);}`,
     fragmentShader:`uniform vec3 uSun,uRimDay,uRimGold;uniform float uRimGain,uRimPack;varying vec3 vW;${pairTableGLSL('rimAlpha',rc.alpha_by_sun_limb_cos)}\n${pairTableGLSL('rimGold',rc.golden_hour_mix_by_sun_elev_sin)}\nvoid main(){vec3 n=normalize(vW);vec3 v=normalize(cameraPosition-vW);float f=pow(1.0-abs(dot(n,v)),2.0);if(uRimPack>.5){float cl=dot(n,uSun);vec3 rc=mix(uRimDay,uRimGold,rimGold(cl));float a=rimAlpha(cl)*uRimGain;gl_FragColor=vec4(rc*f*1.1*a,f*a);}else gl_FragColor=vec4(vec3(.35,.6,1.0)*f*1.1,f);}`}));atm.visible=packRim||atmoClass(skyCfg.atmosphere)!=='thin';scene.add(atm);}
   // other bodies: the first planets of the simulated universe, each with its own seeded biome look (water/temperature from its data)
   const COSMO_PLANETS=['crystal_moss','ember_world','glacier','jelly_geyser','paper_sea','sunflower_ring'];
   const bodies=(u.planets||[]).filter((pl:any)=>!VISIT||pl.id!==visitPl.id).slice(0,phone?4:6).map((pl:any,i:number)=>{const bp=biomeParams(pl.id+':'+u.seed,{water:pl.water,temp:pl.temperature_k});
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
   const bladeMat=new THREE.ShaderMaterial({uniforms:{...UG,uAtlas:{value:tex('grass_blade_atlas.png')},uAmp:{value:W.sway_amp_rad},uBladeK:{value:1},uFreq:{value:W.freq_hz},uWave:{value:W.wave_len_world},uGust:{value:W.gust_amp},uGustF:{value:W.gust_freq_hz},uR:{value:PR}},
    side:THREE.DoubleSide,alphaTest:.5,
    vertexShader:`attribute vec3 aN;attribute vec2 aR;uniform vec3 uSun;uniform float uLift;uniform float uBladeK;uniform float uT,uAmp,uFreq,uWave,uGust,uGustF,uR;varying vec2 vUv;varying float vL;${COVER}
uniform vec3 uPlay[8];
     void main(){vec3 n=normalize(aN);float c=cover(n);float near=0.0;for(int i=0;i<8;i++)near=max(near,smoothstep(.22,.0,acos(clamp(dot(n,uPlay[i]),-1.0,1.0))));c*=1.0+near*.8;vec3 t=normalize(cross(abs(n.y)<.99?vec3(0,1,0):vec3(1,0,0),n));vec3 b=cross(n,t);
      float ca=cos(aR.x*6.283),sa=sin(aR.x*6.283);vec3 tx=t*ca+b*sa,tz=-t*sa+b*ca;
      vec3 p=position*(0.55+0.6*fract(aR.x*7.3))*c*uBladeK;float w=pow(uv.y,1.6);vec3 wp=n*(uR+disp(n));
      float ang=uAmp*w*sin(uT*6.2831*uFreq+dot(wp,normalize(vec3(1,.2,.4)))/uWave)+uGust*w*sin(uT*6.2831*uGustF+wp.x*.2);
      p.x+=sin(ang)*p.y;p.y*=cos(ang);
      vec3 world=wp+tx*p.x+n*p.y+tz*p.z;vUv=vec2((aR.y+uv.x)/8.0,uv.y);vL=.3+1.0*max(0.0,dot(n,uSun))+uLift*.5*(1.0-max(0.0,dot(n,uSun)));
      gl_Position=projectionMatrix*viewMatrix*vec4(world,1.0);if(c<.02)gl_Position=vec4(2.0,2.0,2.0,1.0);}`,
    fragmentShader:`uniform sampler2D uAtlas;varying vec2 vUv;varying float vL;void main(){vec4 c=texture2D(uAtlas,vUv);if(c.a<.5)discard;float gy=clamp(vUv.y,0.,1.);vec3 gTip=mix(vec3(.545,.608,.333),vec3(.71,.643,.353),.4*clamp(vL-.6,0.,1.));vec3 g=mix(vec3(.373,.42,.251)*.55,gTip,gy);gl_FragColor=vec4(mix(c.rgb,g,.7)*vL,1.0);} /* pack grass #5F6B40 -> #8B9B55, roots x.55, warm tip #B5A45A only where lit */`});
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
    const n=new THREE.Vector3(...(unitFrom(rr) as [number,number,number]));const f=new THREE.Vector3(...(unitFrom(rr) as [number,number,number]));f.addScaledVector(n,-f.dot(n)).normalize();return {node,n,f,sp,h,spd:.25+rr()*.35,wob:rr()*10,name:r.name};});
   lk2Ground.addLife(residents.map((r:any)=>r.sp.material.map));
   // who can speak: the five residents, plus the active beast when it is Kitten / Zeref / Zeref64 or has a species (never a creature that is not on screen)
   const vcast=voiceCast((residents as any[]).map((r:any)=>r.name),beastName,(()=>{try{return readActiveBeast(localStorage)?.qbeast?.profile?.family||null;}catch{return null;}})());
   residents.slice(0,7).forEach((r,i)=>gpts[i+1].copy(r.n));(window as any).__lwResidents=()=>(residents as any[]).map((r:any)=>({name:r.name,n:[r.n.x,r.n.y,r.n.z]}));// grass starts under the beasts' feet
   // ---- residents in 3D: a delivered slot model (public/creatures3d/custom) first, else the sculpted resident GLB (res_*), else the flat sprite stays.
   {const kinds:string[]=[];(window as any).__lwResident3d=()=>kinds.slice();let q:Promise<any>=Promise.resolve();
    (residents as any[]).forEach((r:any,i:number)=>{const art=(ARTIST_RESIDENTS as any[])[i];const stub=(RES_PAINTS as any[]).find(x=>x.body==='res_'+String(art.id).replace('art-',''));
     const put=(root:any,drive:(dt:number,l:any)=>void,dispose:()=>void,kind:string)=>{if(disposed){dispose();return;}root.traverse((o:any)=>{if(o.isMesh)o.castShadow=true;});r.node.add(root);r.sp.visible=false;r.body={drive,kind};kinds[i]=r.name+':'+kind;cleanup.push(dispose);};
     q=q.catch(()=>{}).then(async()=>{if(disposed)return;
      // Strong devices take the sculpted heavy GLB first. A phone never loads it (size budget): it takes the light rigged model, else the sprite stays.
      const heavy=async()=>{if(!stub||!heavyAllowed({phone,deviceMemory:(navigator as any).deviceMemory,cores:navigator.hardwareConcurrency}))return false;
       const {loadBeastGlb}=await import('./creature-glb-beast');const gb=await loadBeastGlb(THREE,stub as any,{tier:'med',paint:(stub as any).paint});if(!gb)return false;
       const bb=new THREE.Box3().setFromObject(gb.root);const hh=Math.max(.01,bb.max.y-bb.min.y);const k=r.h/hh;const holder=new THREE.Group();gb.root.scale.multiplyScalar(k);gb.root.position.y=-bb.min.y*k;holder.add(gb.root);
       put(holder,(dt,l)=>gb.drive(dt,l,null,null),()=>gb.dispose(),'glb');return true;};
      if(await heavy())return;
      const slot=await loadCreatureModel(THREE,art.id,{low:phone,phone,targetH:r.h});
      if(slot)put(slot.root,(dt,l)=>slot.drive(dt,l),()=>slot.dispose(),'slot');
     }).catch((e:any)=>{(window as any).__lwResident3dErr=String(e);});});}
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
   // ---- Roadster · SEEDED (Cosmo's pack): a VISUAL swap for the spawned-in traveler, loaded only when the button is first pressed. The traveler's own walkOn/stepMover motion drives it (no second physics).
   const SPACE_BG=new THREE.Color(0x02010a);let car:any=null,carLoading=false,carPrev:any=null,carV=0,carSteer=0;const carK=TRAV_H/1.7;
   // roadster flight (SIMULATED): the car lifts off from where it drives, climbs through the air into space seen from the cockpit, and comes back. State lives here; the maths is lib/universe/roadster-flight.mjs
   // look around the cockpit: drag the view; with no drag, in space the view eases down toward the planet below
   let lkY=0,lkP=0,lkD:{x:number;y:number}|null=null,lkAt=-9;
   {const lpd=(e:PointerEvent)=>{if(rf.on)lkD={x:e.clientX,y:e.clientY};},lpm=(e:PointerEvent)=>{if(lkD&&rf.on){lkY-=(e.clientX-lkD.x)*.006;lkP=Math.max(-1.4,Math.min(1.4,lkP-(e.clientY-lkD.y)*.006));lkD={x:e.clientX,y:e.clientY};lkAt=performance.now()/1000;}},lpu=()=>{lkD=null;};
    canvas.addEventListener('pointerdown',lpd);addEventListener('pointermove',lpm);addEventListener('pointerup',lpu);addEventListener('pointercancel',lpu);cleanup.push(()=>{canvas.removeEventListener('pointerdown',lpd);removeEventListener('pointermove',lpm);removeEventListener('pointerup',lpu);removeEventListener('pointercancel',lpu);});}
   (window as any).__lwLook=(y:number,p:number,hold=8)=>{lkY=y;lkP=p;lkAt=performance.now()/1000+hold;};
   const rf:any={on:false,S:null,blend:0,landT:0,hudT:0,plume:null,atmo:null,v:new THREE.Vector3()};
   const rfAtmo=(()=>{const m=new THREE.Mesh(new THREE.SphereGeometry(PR*1.12,48,32),new THREE.ShaderMaterial({transparent:true,depthWrite:false,side:THREE.BackSide,blending:THREE.AdditiveBlending,uniforms:{uK:{value:0}},vertexShader:'varying vec3 vN;varying vec3 vV;void main(){vN=normalize(normalMatrix*normal);vec4 mv=modelViewMatrix*vec4(position,1.);vV=normalize(-mv.xyz);gl_Position=projectionMatrix*mv;}',fragmentShader:'varying vec3 vN;varying vec3 vV;uniform float uK;void main(){float f=pow(clamp(dot(-vN,vV),0.,1.),2.2);gl_FragColor=vec4(vec3(.36,.62,1.)*f*.55*uK,f*uK);}'}));m.visible=false;m.renderOrder=3;scene.add(m);return m;})();cleanup.push(()=>{rfAtmo.geometry.dispose();(rfAtmo.material as any).dispose();});
   const loadCar=()=>{carLoading=true;Promise.all([import('three/examples/jsm/loaders/GLTFLoader.js'),fetch('/universe/livingworld/roadster/roadster_palette.json').then(r=>r.json())]).then(([{GLTFLoader},pal])=>new GLTFLoader().loadAsync('/universe/livingworld/roadster/roadster.glb').then((g:any)=>{
    if(disposed)return;const root=g.scene;const vi=bodyVariantIndex(lwStream(u.seed+':roadster')());const bv=pal.body_variants[vi]||pal.body_variants[0];const parts:any={wheels:[],steer:[],glows:[]};
    root.traverse((o:any)=>{if(o.isMesh){o.castShadow=true;if(o.material?.name==='body_paint'){o.material=o.material.clone();o.material.color.setRGB(...bv.baseColorFactor.slice(0,3));}
     const role=o.userData?.emissive_role||o.parent?.userData?.emissive_role;if(role&&o.material?.emissiveIntensity!==undefined){o.material=o.material.clone();parts.glows.push({m:o.material,role});}}
     if(/^wheel_/.test(o.name))parts.wheels.push(o);if(/^steer_F/.test(o.name))parts.steer.push(o);if(o.name==='body_group')parts.body=o;});
    root.scale.setScalar(carK);root.visible=false;travNode.add(root);car={root,parts,variant:bv.name,pal};
    cleanup.push(()=>{root.traverse((o:any)=>{if(o.isMesh){o.geometry?.dispose();(Array.isArray(o.material)?o.material:[o.material]).forEach((m:any)=>m?.dispose?.());}});});
    (window as any).__lwRoadster={loaded:true,variant:bv.name,glows:parts.glows.map((x:any)=>x.role),wheels:parts.wheels.length};})).catch(()=>{carLoading=false;});};
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
    if(exp==='storm'){storming=1;puff=1;stormSeen=true;say(beastNm+' puffs up at the storm!',4);notice('storm_far');}
    // growth spreads faster where there is light and water (sunlit home, wet biome) — still SIMULATED
    {const hl=Math.max(0,gpts[0].dot(sunDir));const wet=({ocean:1,beach:.9,papersea:1,mushroom:1,plains:.8,heartwood:.9,pine:.7,tundra:.5,glacier:.3,ember:.2,peaks:.3} as any)[biomeOf(gpts[0])]??.6;growLW=Math.min(1.2,growLW+.004*hl*wet);try{lwStore.setItem('lw:growLW:'+bKey,String(growLW));}catch{}}
    traits=driftTraits(traits,u,bKey,exp||'day');glowBoost=1;alive.onTick(prev,u);UG.uSpread.value=Math.min(Math.PI,spreadAngle(u)+growLW);
    if(surface&&gSnap.length)try{surface.setGrowth(growthNow(),u.tick);}catch{}
    try{growthUi();}catch{}
    try{lwStore.setItem('lw:universe',JSON.stringify(u));lwStore.setItem('lw:traits:'+bKey,JSON.stringify(traits));}catch{}};
   // ---- input
   const kd=(e:KeyboardEvent)=>{const k=e.key.toLowerCase();keys.current.add(k);if(k===' '&&spawnRef.current&&roadsterRef.current)e.preventDefault();if(k==='l'&&rfRef.current.on)rfRef.current.assist=rfRef.current.assist==='land'?'':'land';if(k==='f'&&!rfRef.current.on)setFlying(v=>!v);},ku=(e:KeyboardEvent)=>{keys.current.delete(e.key.toLowerCase());};
   addEventListener('keydown',kd);addEventListener('keyup',ku);cleanup.push(()=>{removeEventListener('keydown',kd);removeEventListener('keyup',ku);});
   // orbit drag when not spawned
   let oy=.3,ox=0,drag:{x:number;y:number}|null=null;let userAt=performance.now();const poke=()=>{userAt=performance.now();};let seaF:any=null;let seaQ=0;const SEA_NAMES:Record<string,string>={fish:'fish school',ray:'manta rays',whale:'whale',jelly:'jellyfish',turtle:'turtles',seabird:'seabirds'};const seaHud=(on:boolean,sc?:any)=>{const e=hudSea.current;if(!e)return;e.style.display=on?'':'none';if(on&&sc)e.textContent='Sea life: '+(SEA_NAMES[sc.kind]||sc.kind)+' · SEEDED (recorded IBM counts, not a live feed)';};
   // zoom: wheel on desktop, two-finger pinch on iPhone (pointer events; the canvas is touch-action:none)
   let zT=1,zC=1,zMode='';
   // Zoom-out past the planet's full orbit has no hard stop (when this world is not the door of /universe, which hands off instead): zX is the extra pull-back in ln(distance) units, only a float32 guard at ZX_LIMIT.
   let zX=0,zXc=0;const ZX_LIMIT=12;const pullOut=()=>!spawnRef.current&&!orbitOutRef.current;const ptrs=new Map<number,{x:number;y:number}>();let pinch0=0;
   const pinchD=()=>{const a=[...ptrs.values()];return a.length<2?0:Math.hypot(a[0].x-a[1].x,a[0].y-a[1].y);};
   const wheel=(e:WheelEvent)=>{e.preventDefault();poke();const dy=e.deltaY*(e.deltaMode===1?16:1);if(zT>=.999&&dy>0&&orbitOutRef.current&&!spawnRef.current){orbitOutRef.current();return;}if(pullOut()&&(zT>=.999&&dy>0||zX>0&&dy<0)){zX=Math.max(0,Math.min(ZX_LIMIT,zX+dy*.0016));return;}zT=stepZoom(zT,{wheel:dy});};canvas.addEventListener('wheel',wheel,{passive:false});cleanup.push(()=>canvas.removeEventListener('wheel',wheel));
   const pdz=(e:PointerEvent)=>{poke();ptrs.set(e.pointerId,{x:e.clientX,y:e.clientY});if(ptrs.size===2){pinch0=pinchD();drag=null;}},pmz=(e:PointerEvent)=>{if(!ptrs.has(e.pointerId))return;ptrs.set(e.pointerId,{x:e.clientX,y:e.clientY});if(ptrs.size===2&&pinch0>0){const d=pinchD();{const r=d/pinch0;if(pullOut()&&(zT>=.999&&r<1||zX>0&&r>1))zX=Math.max(0,Math.min(ZX_LIMIT,zX-Math.log(r)));else zT=stepZoom(zT,{pinch:r});}pinch0=d;}},puz=(e:PointerEvent)=>{ptrs.delete(e.pointerId);if(ptrs.size<2)pinch0=0;};
   canvas.addEventListener('pointerdown',pdz);addEventListener('pointermove',pmz);addEventListener('pointerup',puz);addEventListener('pointercancel',puz);cleanup.push(()=>{canvas.removeEventListener('pointerdown',pdz);removeEventListener('pointermove',pmz);removeEventListener('pointerup',puz);removeEventListener('pointercancel',puz);});
   (window as any).__lwSetZoom=(z:number)=>{zT=Math.max(0,Math.min(1,z));};(window as any).__lwSetPullOut=(x:number)=>{zX=Math.max(0,Math.min(ZX_LIMIT,x));};
   const pd=(e:PointerEvent)=>{if((!spawnRef.current||zC>.55)&&ptrs.size<2)drag={x:e.clientX,y:e.clientY};},pm=(e:PointerEvent)=>{if(drag&&ptrs.size<2){ox-=(e.clientX-drag.x)*.006;oy=Math.max(-1.3,Math.min(1.3,oy+(e.clientY-drag.y)*.006));drag={x:e.clientX,y:e.clientY};}},pu=()=>{drag=null;};
   canvas.addEventListener('pointerdown',pd);addEventListener('pointermove',pm);addEventListener('pointerup',pu);cleanup.push(()=>{canvas.removeEventListener('pointerdown',pd);removeEventListener('pointermove',pm);removeEventListener('pointerup',pu);});
   let gRedT=0,gReduced=false;const gBeast=new THREE.Vector3();
   const reducedNow=()=>{try{return document.documentElement.dataset.beastboxReducedMotion==='true'||matchMedia('(prefers-reduced-motion: reduce)').matches||localStorage.getItem(REDUCED_MOTION_KEY)==='true';}catch{return false;}};
   // E2 (Cosmo): a TAP (not a drag) on your beast opens Look Closer. Only the beast mesh counts; drags keep rotating.
   {const tapRay=new THREE.Raycaster(),tapNdc=new THREE.Vector2();let t0:{x:number;y:number;t:number}|null=null;
    const tpd=(e:PointerEvent)=>{t0={x:e.clientX,y:e.clientY,t:performance.now()};};
    const tpu=(e:PointerEvent)=>{const d=t0;t0=null;if(!d||Math.hypot(e.clientX-d.x,e.clientY-d.y)>8||performance.now()-d.t>450)return;
     const rc=canvas.getBoundingClientRect();tapNdc.set((e.clientX-rc.left)/rc.width*2-1,-(e.clientY-rc.top)/rc.height*2+1);tapRay.setFromCamera(tapNdc,camera);
     if(plush&&beastNode.visible&&tapRay.intersectObject(beastNode,true).length){{const bs=vcast.find((c:any)=>c.beast),bl=bs?castLine(bs,'tap',String(u.seed),++voiceN):null;if(bs&&bl){lineRef.current(bs.name+': '+bl);evCool=3;}}window.dispatchEvent(new CustomEvent('beastbox:look-closer',{detail:{id:'beast'}}));return;}
     // a tap on an artist resident: its approved 'tap' voice line (seeded by world seed + tap count); no line, no change
     for(const r of residents as any[]){if(r.node&&tapRay.intersectObject(r.node,true).length){const vk=(RESIDENT_LIFE_KEY as any)[r.name];const vl=vk?creatureVoice(vk,'tap',String(u.seed),++voiceN):null;if(vl){r.hopT=0;lineRef.current(r.name+': '+vl);evCool=3;return;}}}
     // a tap on a landscape: its authored tap line (active beast + place name), view state only
     {const hl=tapRay.ray.intersectSphere(new THREE.Sphere(new THREE.Vector3(),PR+.02),new THREE.Vector3());if(hl&&lwLand){const lsT=lwLand.tapAt([hl.x/hl.length(),hl.y/hl.length(),hl.z/hl.length()]);if(lsT){const g=noticeGate(lmGate,'land:tap',performance.now(),3000,6000);lmGate=g.state;if(g.show){const tx=landscapeTapLine(lsT,{beast:beastName||'Your beast',planet:(homePl as any)?.name||'this world',seed:String(u.seed),n:lmN++});if(tx)lineRef.current(tx);}}}}
     // a tap on a growth node's ground: scale bounce + gold burst (view state only) and one creature-notice line (Emeth's growth_tap_*, active beast name substituted)
     if(surface&&gSnap.length){const hit=tapRay.ray.intersectSphere(new THREE.Sphere(new THREE.Vector3(),PR+.02),new THREE.Vector3());if(hit){const g=surface.tapGrowth([hit.x/hit.length(),hit.y/hit.length(),hit.z/hit.length()],performance.now());if(g?.key)notice(g.key,1500);if(g?.node?.id)gTaps[g.node.id]=(gTaps[g.node.id]||0)+1;}}};
    canvas.addEventListener('pointerdown',tpd);canvas.addEventListener('pointerup',tpu);cleanup.push(()=>{canvas.removeEventListener('pointerdown',tpd);canvas.removeEventListener('pointerup',tpu);});}
   const resize=()=>{if(!host.current)return;const r=host.current.getBoundingClientRect();renderer.setSize(r.width,r.height,false);post?.setSize(r.width,r.height);camera.aspect=r.width/Math.max(1,r.height);camera.updateProjectionMatrix();};
   const ro=new ResizeObserver(resize);ro.observe(host.current!);resize();cleanup.push(()=>ro.disconnect());
   // perf: measure fps for 3s windows and shrink the blade count if the phone can't hold ~50fps
   // test/debug hook: walk the traveler to the first seeded spot of a biome (used for screenshots)
   // test/debug hook: stand the traveler beside growth node i (view-snapped), facing it
   (window as any).__lwGrowthGo=(i=0,back=.07)=>{const n=growthNow()[i];if(!n)return false;const la=n.lat*Math.PI/180,lo=n.lon*Math.PI/180;const c=new THREE.Vector3(Math.cos(la)*Math.cos(lo),Math.sin(la),Math.cos(la)*Math.sin(lo));const t=new THREE.Vector3(0,1,0).cross(c);if(t.lengthSq()<1e-6)t.set(1,0,0);t.normalize();pN.copy(c).addScaledVector(t,-back).normalize();pF.copy(c).sub(pN).addScaledVector(pN,-pN.dot(c.clone().sub(pN))).normalize();return true;};
   (window as any).__lwGoZeref=()=>{const z=(gpts[1]||gpts[0]).clone().normalize();const t=new THREE.Vector3(0,1,0).cross(z).normalize();pN.copy(z).addScaledVector(t,-.06).normalize();pF.copy(z).sub(pN).addScaledVector(pN,-pN.dot(z.clone().sub(pN))).normalize();return true;};(window as any).__lwGoBiome=(b:string)=>{const r=lwS(u.seed+':goto');for(let i=0;i<4000;i++){const v=unitFrom(r) as number[];if(biomeOf(new THREE.Vector3(v[0],v[1],v[2]))===b){pN.set(v[0],v[1],v[2]);pF.set(1,0,0).addScaledVector(pN,-pN.x).normalize();return true;}}return false;};
   // physics + events state: gravity hop on the sphere, wind, storm puff, sunrise, meetings; greeting once per visit
   let exWalk=0,exBack=false,exRun=false;
   let nGate:any=null,nCount=0,stormSeen=false,stormHi=false;const notice=(key:string,gap=6000)=>{const g=noticeGate(nGate,key,performance.now(),gap);nGate=g.state;if(!g.show)return;const tx=noticeLine(key,beastName||'Your beast',String(u.seed),nCount++);if(tx)lineRef.current(tx);};/* Emeth's creature_notices, verbatim */
   {let gKey:string|null=null,gDKey:string|null=null,gGate:any=null,gN=0;growthUi=()=>{const nodes=growthNow();const chip=growthChip(nodes);const el=hudGN.current,hm=hudHome.current,ex=hudGNx.current;
    if(el){el.style.display=chip?'':'none';if(chip){el.textContent=chip.text;el.title=chip.explainer;el.dataset.stage=chip.stage;}}
    if(hm){hm.style.display=chip?.homeText?'':'none';if(chip?.homeText)hm.textContent=chip.homeText;}
    if(ex){ex.style.display=chip?'':'none';if(chip)ex.textContent=chip.explainer;}
    // a line when what the nodes are doing changes (derived from the SIMULATED state; the first reading is silent)
    const k=growthNoteKey(nodes),dk=growthDriveKey(nodes);const tryShow=(key:string|null)=>{if(!key)return;const g=noticeGate(gGate,'growth:'+key,performance.now(),20000,90000);gGate=g.state;if(!g.show)return;const tx=growthNoteLine(key,beastName||'Your beast',String(u.seed),gN++);if(tx)lineRef.current(tx);};
    const dkS=dk||'';if(gKey!==null&&k&&k!==gKey)tryShow(k);else if(gKey!==null&&gDKey!==null&&dk&&dkS!==gDKey)tryShow(dk);if(k)gKey=k;if(gKey!==null)gDKey=dkS;};}
   let voiceN=0,voiceT=14;let seaGate:any=null;const seaCount:Record<string,number>={};const roadsterSeq=createRoadsterVoice();let bY=0,bVY=0,puff=0,storming=0,windS=.3,greeted=false,lastSunH=0,evCool=0;const G_SURF=4.2;const windV=new THREE.Vector3(1,0,.4).normalize();const metCool:Record<string,number>={};
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
     lwStore.setItem(ZKEY,JSON.stringify(zLog));}catch{}(window as any).__lwZerefExperiences=zLog;};
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
       const lb=learnBiome(beastLore,legendAt(field,[bN.x,bN.y,bN.z]));if(lb){traits=driftTraits(traits,u,bKey,lb.trait);traits=driftTraits(traits,u,bKey,'wonder');try{lwStore.setItem('lw:lore:'+bKey,JSON.stringify(beastLore));}catch{}lineRef.current(beastNm+': '+lb.line);evCool=6;}
       for(const r of residents as any[]){const lr=learnBiome(r.lore,legendAt(field,[r.n.x,r.n.y,r.n.z]));if(lr){try{lwStore.setItem('lw:lore:res:'+r.name,JSON.stringify(r.lore));}catch{}say2(r.name,lr.line,4);}}
       const lz=learnBiome(zLore,legendAt(field,[zN0.x,zN0.y,zN0.z]));if(lz){try{lwStore.setItem('lw:lore:zeref',JSON.stringify(zLore));}catch{}zRec({type:'biome_first_entry',lore:lz.lore,lesson:lz.lesson});}
      }
      (window as any).__lwAlive={builds:builds.map(b=>({kind:b.kind,stage:b.stage,progress:b.progress,model:!!b.model,window:!!b.win,emissive:b.win?.material?.emissiveIntensity??null})),moods:(residents as any[]).map(r=>({name:r.name,mood:r.mood,nap:r.nap>0})),rings:rings.length,zerefRecords:zLog.length,window:{...win}};
     }};
   })();
   let fpsT=0,fpsN=0,fps=0,last=performance.now(),t=0,hudT=0;let skyStarA=-1;const camTarget=new THREE.Vector3(),camPos=new THREE.Vector3(0,6,22);const cW=new THREE.Vector3(),cT=new THREE.Vector3(),cN=new THREE.Vector3(0,1,0),camLook=new THREE.Vector3();
   let os1:any=null,lastMoment='';let frameN=0;const compDisc=new THREE.Sprite(new THREE.SpriteMaterial({map:boomTex,color:new THREE.Color(COMPANION_DISC.hex),transparent:true,opacity:.55,depthWrite:false,fog:false,blending:THREE.AdditiveBlending}));compDisc.scale.setScalar(5);scene.add(compDisc);/* second sun: dim disc, NO light (pending Cory) */
   const frame=()=>{os1=null;if(lk2Sky)lk2Sky.dome.visible=false;lk2World.mesh.visible=false;heaven.root.visible=true;raf=requestAnimationFrame(frame);beastNode.visible=insideCreatureVisible(creatureRef.current);const now=performance.now();const rdt=Math.min(.25,(now-last)/1000),dt=Math.min(.05,rdt);last=now;t+=dt;UG.uT.value=t;if(field)UG.uSeaT.value=(field.tick+field.clock.alpha)/4;
    fpsT+=dt;fpsN++;if(fpsT>=3){fps=fpsN/fpsT;fpsT=0;fpsN=0;if(fps<48&&bladeCap>2000){bladeCap=Math.floor(bladeCap*.75);bladeGeo.instanceCount=bladeCap;}(window as any).__lwPerf={fps:+fps.toFixed(1),blades:bladeCap};}
    tickAcc+=dt;if(tickAcc>=TICK_S){tickAcc=0;applyTick();}
    {let a=(((Date.now()/1000+((window as any).__lwDayOffset||0))%DAY_S+DAY_S)%DAY_S)/DAY_S*Math.PI*2;if(HOLD){if(hz.a===null)hz.a=a;a=hz.a;}sunDir.set(Math.cos(a),.35*Math.sin(a*.5+1),Math.sin(a)).normalize();UG.uSun.value.copy(sunDir);{const sSrc=sunSource({field,override:HOLD||(window as any).__lwDayOffset!==undefined});if(sSrc.dir)sunDir.set(sSrc.dir[0],sSrc.dir[1],sSrc.dir[2]).normalize();(window as any).__lwSunSource=sSrc.source;UG.uSun.value.copy(sunDir);}
     const bcOn=beachCamRef.current&&!spawnRef.current&&!!beach;const fN=bcOn?beach.center().clone().normalize():spawnRef.current?pN:bN;if(beachCamRef.current&&!spawnRef.current&&beach&&(window as any).__lwNoon!=='night'){const bn=beach.center().clone().normalize(),bl=beach.landward().clone().normalize();const bt=bl.sub(bn.clone().multiplyScalar(bl.dot(bn)));if(bt.lengthSq()<1e-8)bt.set(1,0,0);bt.normalize();sunDir.copy(bn).addScaledVector(bt,-.55).normalize();} /* noon-ish sun standing seaward of the beach, behind the camera, so the sand, surf and dunes are front-lit */ /* beach view = daytime: the sun stands high over the shore */ else if((window as any).__lwNoon)sunDir.copy(fN).multiplyScalar((window as any).__lwNoon==='night'?-1:1).add(new THREE.Vector3(.5,.6,.2)).normalize(); /* ONE SUN (Cosmo's pack): sun height follows the day clock at the place you stand; same sun for every view */ else if(!HOLD){os1=oneSunAt(Date.now()/1000,[fN.x,fN.y,fN.z],(window as any).__lwDayOffset||0);sunDir.set(os1.dir[0],os1.dir[1],os1.dir[2]);(window as any).__lwSunSource='one-sun';}UG.uSun.value.copy(sunDir);const h=fN.dot(sunDir);const focus=fN.clone().multiplyScalar(PR);sun.position.copy(focus).addScaledVector(sunDir,25);sun.target.position.copy(focus);
     const dayL=Math.max(.1,h*.8+.2);sun.intensity=2.2*dayL;sun.color.copy(starCol).lerp(SKY_DUSK,Math.max(0,1-Math.abs(h)/.2)*.35);hemi.intensity=1.4*Math.max(.12,h*.3+.25);
     sunDisc.position.copy(sunDir).multiplyScalar(160);starMesh.position.copy(sunDisc.position);moon.position.copy(sunDir).multiplyScalar(-70).add(new THREE.Vector3(0,12,0));
     const ground3=zC<.6;const day=ground3?THREE.MathUtils.smoothstep(h,-.12,.35):0;const dusk=ground3?Math.max(0,1-Math.abs(h)/.18)*.7:0;
     let skyNf=1-day*.97;
     if(!ground3){UG.uHazeOn.value=0;vlAir=null;const vl0=(window as any).__lwVisualLife;if(vl0)delete vl0.haze;}
     if(ground3){const bf=(window as any).__lwBoomForce;const bTick=bf?bf.tick:((u as any).tick||0);const bList=bf?[{star:bf.star||homeStar,eventTick:bf.eventTick||0,distance:Math.max(SKY_VIEW.homeBoomMinAu,homePl?.orbit_au||1),dir:boomBearing(String(u.seed||'tiny'),(bf.star||homeStar)?.id||'s')}]:skyBoomList;
      vlBoomList=bList;vlBoomTick=bTick;const upA=[fN.x,fN.y,fN.z],sm=skyMoons(u.seed,homePl,upA,t);
      const sk=skyAt({sunDir:[sunDir.x,sunDir.y,sunDir.z],sunElev:h,up:upA,atmosphere:skyCfg.atmosphere,starTempK:skyCfg.starTempK,skyColor:skyCfg.skyColor||undefined,twilightColor:skyCfg.twilightColor||undefined,star:homeStar,channels:engineChannels(field||{}),tick:bTick,booms:bList,bodies:sm});
      const kz=SKY_VIEW.flatBackgroundMix;(scene.background as any).setRGB(sk.zenith[0]*(1-kz)+sk.horizon[0]*kz,sk.zenith[1]*(1-kz)+sk.horizon[1]*kz,sk.zenith[2]*(1-kz)+sk.horizon[2]*kz);
      vlSunUp=sk.dayWeight;skyNf=Math.max(.03,sk.nightFactor);{const cI=field?cellOf(field,upA):-1;const hz2=hazeFor({atmo:skyCfg.atmosphere,sunElevSin:h,nightFactor:sk.nightFactor,moisture:cI>=0?field.moist[cI]:0,storm:field?field.storm:0});const srgb=(v:number)=>v<=.0031308?12.92*v:1.055*Math.pow(Math.max(0,v),1/2.4)-.055;UG.uHazeOn.value=hz2.enabled?1:0;if(!hz2.enabled)vlAir=null;if(hz2.enabled){const hz3=[0,1,2].map(i=>hz2.colour[i]*(1-.7)+sk.horizon[i]*.7);const sc=hz2.stormColour;UG.uHazeCol.value.set(...([0,1,2].map(i=>(hz3[i]*(1-hz2.stormMix)+sc[i]*hz2.stormMix)) as [number,number,number]));UG.uHazeD.value=hz2.density/(TRAV_H/1.7);UG.uHazeCap.value=hz2.cap;vlAir={atmo:skyCfg.atmosphere,mul:hz2.mul,moisture:cI>=0?field.moist[cI]:0,storm:field?field.storm:0};(window as any).__lwVisualLife={...((window as any).__lwVisualLife||{}),haze:{cls:hz2.cls,mul:+hz2.mul.toFixed(3),density:+hz2.density.toFixed(5),stormMix:+hz2.stormMix.toFixed(3),moisture:cI>=0?+field.moist[cI].toFixed(3):null,label:'SIMULATED'}};}}
      hemi.color.copy(hemiBase).lerp(new THREE.Color().setRGB(sk.zenith[0],sk.zenith[1],sk.zenith[2]),.35);if(!os1)hemi.intensity+=(sk.rig.ambient-.125)*3;
      sk.bodies.forEach((b:any,i:number)=>{let m=skyMoonMeshes[i];if(!m){m=moon.clone();m.material=(moon.material as any).clone();scene.add(m);skyMoonMeshes[i]=m;}const rr=Math.min(6,SKY_VIEW.moonDist*b.radius/b.distance);m.scale.setScalar(rr/2.2);m.position.set(fN.x*PR+b.dir[0]*SKY_VIEW.moonDist,fN.y*PR+b.dir[1]*SKY_VIEW.moonDist,fN.z*PR+b.dir[2]*SKY_VIEW.moonDist);m.visible=b.aboveHorizon;});
      if(sk.bodies.length)moon.userData.engineMoon=true;
      const bg=sk.booms[0];if(bg&&bg.dir&&bg.dir[0]*fN.x+bg.dir[1]*fN.y+bg.dir[2]*fN.z>-.05){boomGlow.visible=true;boomGlow.position.set(fN.x*PR+bg.dir[0]*SKY_VIEW.skyDist,fN.y*PR+bg.dir[1]*SKY_VIEW.skyDist,fN.z*PR+bg.dir[2]*SKY_VIEW.skyDist);boomGlow.material.color.setRGB(bg.color[0],bg.color[1],bg.color[2]);boomGlow.material.opacity=Math.min(1,bg.strength);boomGlow.scale.setScalar(boomSpriteScale(bg.radiusDeg));}else boomGlow.visible=false;
      (window as any).__lwSky={sun:(window as any).__lwSunSource,nf:+sk.nightFactor.toFixed(3),zenith:sk.zenith.map((v:number)=>+v.toFixed(3)),horizon:sk.horizon.map((v:number)=>+v.toFixed(3)),starAlpha:+sk.starAlpha(.6).toFixed(3),booms:sk.booms.map((b:any)=>({phase:b.phase,strength:+b.strength.toFixed(3),label:b.label})),moons:sk.bodies.map((b:any)=>({id:b.id,lit:+b.phase.litFraction.toFixed(3),up:b.aboveHorizon})),atmo:skyCfg.atmosphere,type:skyCfg.type};
      skyStarA=sk.starAlpha(.6);
     }else{(scene.background as any).copy(SKY_NIGHT).lerp(SKY_DAY,day).lerp(SKY_DUSK,dusk*(1-day*.5));boomGlow.visible=false;skyStarA=-1;{const bf2=(window as any).__lwBoomForce;vlBoomList=bf2?[{star:bf2.star||homeStar,eventTick:bf2.eventTick||0,distance:Math.max(SKY_VIEW.homeBoomMinAu,homePl?.orbit_au||1),dir:boomBearing(String(u.seed||'tiny'),(bf2.star||homeStar)?.id||'s')}]:skyBoomList;vlBoomTick=bf2?bf2.tick:((u as any).tick||0);}vlSunUp=0;}
     if(os1&&zC<.85){const sk1=os1.sky,kz=SKY_VIEW.flatBackgroundMix;(scene.background as any).setRGB(sk1.zenith[0]*(1-kz)+sk1.horizon[0]*kz,sk1.zenith[1]*(1-kz)+sk1.horizon[1]*kz,sk1.zenith[2]*(1-kz)+sk1.horizon[2]*kz,THREE.LinearSRGBColorSpace);skyStarA=sk1.starAlpha;skyNf=Math.max(.03,1-os1.day*.97);
      if(os1.day>0){sun.color.set(ONE_SUN.hex);sun.intensity=3.03*os1.day;hemi.intensity=.6*os1.day+.15;hemi.color.setRGB((sk1.zenith[0]+sk1.horizon[0])/2,(sk1.zenith[1]+sk1.horizon[1])/2,(sk1.zenith[2]+sk1.horizon[2])/2);hemi.groundColor.set('#3A4A2A');if(fpOn)beastLamp.intensity=2;}
      if(os1.moment!==lastMoment){if(lastMoment)lineRef.current(SKY_LINES[os1.moment].replace('{beast}',beastNm));lastMoment=os1.moment;}latObj.material.opacity=.28*(1-os1.day*.85);
      if(lk2Sky)lk2Sky.update(true,camera.position,fN,sunDir,sk1.zenith,sk1.horizon,os1.day);heaven.root.visible=!fpOn&&!(zC<.6&&os1.day>=.05);
      if(zC<.6){const vd=localSunDir([fN.x,fN.y,fN.z],LOOK2.volcano.elevationDeg,LOOK2.volcano.azimuthDeg);lk2World.update(true,camera.position,vd,sunDir,sk1.horizon,os1.day);}
      (window as any).__oneSun={label:'SEEDED',fp:fpOn,elev:+os1.elevationDeg.toFixed(1),stop:sk1.stop,moment:os1.moment,starAlpha:+sk1.starAlpha.toFixed(2),companion:'disc, no light'};}
     {const cd=new THREE.Vector3(COMPANION_DISC_DIR[0],COMPANION_DISC_DIR[1],COMPANION_DISC_DIR[2]);compDisc.position.copy(fN).multiplyScalar(PR).addScaledVector(cd.addScaledVector(fN,-.2).normalize(),150);compDisc.material.opacity=.55*(1-(os1?os1.day:day)*.5);}
     /* Visual Life Pass B4: stage the strongest boom (engine boomState phase / shellFrac / 1/d^2 sky term) as ring shell + lit water (first person) or limb bloom (orbit) */
     {const sb=stageBooms(vlBoomList,vlBoomTick,vlSunUp);vlBoom=sb?sb.stage:null;const toS=(v:number)=>Math.max(0,Math.min(1,v<=.0031308?12.92*v:1.055*Math.pow(Math.max(0,v),1/2.4)-.055));
      ringOut.visible=ringIn.visible=ringBody.visible=orbBloom.visible=orbHalo.visible=false;UG.uBoomLit.value=0;
      if(sb){const s=sb.stage;if(sb.dir){UG.uBoomDir.value.set(sb.dir[0],sb.dir[1],sb.dir[2]);UG.uBoomCol.value.set(toS(s.waterLit.colour[0]),toS(s.waterLit.colour[1]),toS(s.waterLit.colour[2]));UG.uBoomLit.value=s.waterLit.mix;UG.uBoomDeep.value=s.waterLit.underMax/.55;}
       if(ground3&&boomGlow.visible&&sb.dir){const pos=boomGlow.position;const half=Math.max(2*SKY_VIEW.skyDist*Math.tan(s.ring.angDeg*Math.PI/180)/.86,boomGlow.scale.x*.3);
        for(const [sp,k,al,c] of [[ringOut,1,1,s.ring.outer],[ringIn,.93,.6,s.ring.inner],[ringBody,.9,.16,s.ring.shadow]] as any[]){sp.visible=s.ring.alpha>.004;sp.position.copy(pos);sp.scale.setScalar(half*k);sp.material.color.setRGB(c[0],c[1],c[2]);sp.material.opacity=Math.min(1,s.ring.alpha*al);}}
       else if(!ground3&&sb.dir){const cd=camera.position.clone().normalize();const lp=limbPoint(sb.dir,[cd.x,cd.y,cd.z]);if(lp&&s.bloom.gain>.002){const R=PR*s.bloom.radiusFrac*3;orbBloom.visible=orbHalo.visible=true;orbBloom.position.set(lp[0]*PR*1.01,lp[1]*PR*1.01,lp[2]*PR*1.01);orbHalo.position.copy(orbBloom.position);orbBloom.scale.setScalar(R);orbHalo.scale.setScalar(R*(1+.06*8));const g=Math.min(1,s.bloom.gain);orbBloom.material.color.setRGB(s.bloom.colour[0],s.bloom.colour[1],s.bloom.colour[2]);orbBloom.material.opacity=g;orbHalo.material.color.setRGB(s.bloom.halo[0],s.bloom.halo[1],s.bloom.halo[2]);orbHalo.material.opacity=Math.min(1,g*.35);}}}
      (window as any).__lwVisualLife={...((window as any).__lwVisualLife||{}),boom:sb?{phase:sb.stage.phase,t:+sb.stage.t.toFixed(3),skyTerm:+sb.stage.skyTerm.toFixed(3),shellFrac:+sb.stage.shellFrac.toFixed(3),ringDeg:+sb.stage.ring.angDeg.toFixed(1),ringAlpha:+sb.stage.ring.alpha.toFixed(3),waterLit:+sb.stage.waterLit.mix.toFixed(3),bloomGain:+sb.stage.bloom.gain.toFixed(3),view:ground3?'first-person':'orbit',label:sb.stage.label}:null};}
     cosmoSky.update(t,os1&&zC<.85?skyNf*(1-os1.day):skyNf,camera.position);nova.update(dt);if(nova.playing)nova.sp.scale.setScalar(30+40*Math.min(1,nova.sp.material.map!.offset.x+1-nova.sp.material.map!.offset.y));island?.update(dt,camera.position);beach?.update(dt);if(starMat)starMat.opacity=skyStarA>=0?skyStarA:1-day*.95;
     // wind: heated by the sun, gusts with storms; drives grass sway and fur
     windS=.25+.35*Math.max(0,h)+storming*.6;windV.applyAxisAngle(fN,dt*.03);try{zDrv?.update(dt);}catch{}zHold.rotateY(dt*.05);fieldStep(dt,sunDir,Math.min(1,joy.current.active?1:0)+(spawnRef.current?.3:0));if(field?.mp){windV.x+=(field.mp.wind.x-windV.x)*dt*.2;windV.z+=(field.mp.wind.z-windV.z)*dt*.2;}storming=Math.max(0,storming-dt*.15);bladeMat.uniforms.uGust.value=W.gust_amp*(.6+windS*1.4);
     // sunrise at the beast: wonder
     const hb=bN.dot(sunDir);if(lastSunH<0&&hb>=0){say(beastNm+' stops to watch the sunrise, eyes wide.',8);hop(1.6);traits=driftTraits(traits,u,bKey,'day');}else if(lastSunH>0&&hb<=0){say('Night falls. '+beastNm+' curls its tail and looks at the stars.',8);traits=driftTraits(traits,u,bKey,'rest');}lastSunH=hb;
     for(const r of residents as any[]){const lit=.45+.55*THREE.MathUtils.smoothstep(r.n.dot(sunDir),-.15,.3);(r.node.children[0] as any).material.color.setScalar(lit);}}
    // gravity on the sphere: hops fall back under surface gravity
    evCool=Math.max(0,evCool-dt);puff=Math.max(0,puff-dt*.6);bVY-=G_SURF*dt;bY=Math.max(0,bY+bVY*dt);if(bY<=0&&bVY<0)bVY=0;
    // creatures learn from each new biome they enter (beast: persisted with its learned things)
    biomeT-=dt;if(biomeT<=0){biomeT=.5;const bb=biomeOf(bN);curBiome=bb;if(!learned['biome:'+bb]){learned['biome:'+bb]=1;const ls=(BIOME_FEEL as any)[bb]?.lesson;if(ls)traits=driftTraits(traits,u,bKey,ls);try{lwStore.setItem('lw:learned:'+bKey,JSON.stringify(learned));}catch{}/* the first-entry line now comes from Emeth's biome lore (alive.frame) */}
     if(hudBiome.current)hudBiome.current.textContent='Biome: '+(cosmoNameOf(spawnRef.current?pN:bN)||(BIOME_NAMES as any)[spawnRef.current?biomeOf(pN):bb]);(window as any).__lwBiome={beast:bb,you:biomeOf(pN),home:biomeOf(gpts[0]),bN:bN.toArray(),g0:gpts[0].toArray()};}
    latPivot.rotation.y+=dt*.02;latObj.rotation.x+=dt*.03;latObj.rotation.z+=dt*.017;
    // residents wander
    const play=UG.uPlay.value;play[0].copy(bN);residents.slice(0,6).forEach((r,i)=>play[i+1].copy(r.n));play[7].copy(spawnRef.current?pN:bN);
    // things wake when the spreading grass reaches them; touched things grow / pulse
    for(const th of things){if(!th.awake){const c=gpts.some(g=>ang(th.n,g)/PR<UG.uSpread.value-.2);if(c){th.awake=true;th.grow=1;}}
     th.cool=Math.max(0,th.cool-dt);th.pulse=Math.max(0,th.pulse-dt*.8);const s0=th.node.scale.x,tg=th.awake?th.size*th.grow*(1+th.pulse*.25):0.001;th.node.scale.setScalar(s0+(tg-s0)*Math.min(1,dt*2));}
    // residents explore things and each other; everything can touch everything
    socialCool=Math.max(0,socialCool-dt);const slReduced=reducedNow(); // sprite life (Cosmo's spritelife numbers): idle breathe, walk bob, hop, sleep curl; transforms only, art untouched
    for(const r of residents as any[]){r.pause=Math.max(0,(r.pause||0)-dt);
     const nt=nearestThing(r.n);if(nt&&nt.d<.35&&r.pause<=0){if(touch(nt.t,r.name)){r.pause=1.5;r.hopT=0;alive.build(r);}}
     else if(nt&&nt.d<4&&Math.sin(t*.2+r.wob)>0)steerTo(r.n,r.f,nt.t.n,dt*1.5);else turn(r.n,r.f,Math.sin(t*.4+r.wob)*dt*.8);
     for(const o of residents as any[])if(o!==r&&ang(r.n,o.n)<.5){steerTo(r.n,r.f,r.n.clone().multiplyScalar(2).sub(o.n),dt*2);if(socialCool<=0&&!spawnRef.current){socialCool=25;lineRef.current(r.name+' and '+o.name+' bumped noses.');}alive.meet(r,o,t);}
     if(ang(r.n,bN)<.6){steerTo(r.n,r.f,r.n.clone().multiplyScalar(2).sub(bN),dt*2);if(!(metCool[r.name]>t)){metCool[r.name]=t+40;r.hopT=0;say(beastNm+' met '+r.name+' and sniffed hello.',5);hop(1.2);traits=driftTraits(traits,u,bKey,'greet');}}
     {const gl=lwLand?.goalFor?.('res:'+r.name,String(u.seed));if(gl){landGoal.set(gl.target[0],gl.target[1],gl.target[2]);if(ang(r.n,landGoal)>gl.arrive*PR){steerTo(r.n,r.f,landGoal,dt*2.2);r.pause=0;}else if(gl.mode!=='gather')r.pause=Math.max(r.pause,.25);}} // landscape routine: gather at the ring and seats, huddle at the shelter in rain and at night (roam-brain SPOTS pattern)
     if(r.pause<=0){const rb=biomeOf(r.n);walkOn(r.n,r.f,r.spd*dt*((BIOME_FEEL as any)[rb]?.speed??1));if(rb==='ocean')steerTo(r.n,r.f,gpts[0],dt*2);}place(r.node,r.n,r.f);if(r.body)r.body.drive(dt,{speed:(r.pause<=0&&!(r.nap>0))?.6:0,mode:'wander',sleep:r.nap>0?1:0,lookCam:0,bob:t*6,heading:0,startle:0,joy:.3});
     {const lk=(RESIDENT_LIFE_KEY as any)[r.name];if(lk&&r.sp){const sl=r.nap>0?1:0;r.sk=(r.sk||0)+(sl-(r.sk||0))*Math.min(1,dt*2.1);r.wk=(r.wk||0)+(((r.pause<=0&&!sl)?1:0)-(r.wk||0))*Math.min(1,dt*4);
      let hu:number|null=null;if(typeof r.hopT==='number'){r.hopT+=dt;if(r.hopT>=hopSeconds(lk))r.hopT=null;else hu=r.hopT/hopSeconds(lk);}
      const tf=lifeTransform(lk,{t,walk:r.wk,sleep:r.sk,hopU:hu,reduced:slReduced});r.sp.scale.set(r.h*tf.sx,r.h*tf.sy,1);r.sp.position.set(tf.dx*r.h,-tf.dy*r.h,0);r.sp.material.rotation=tf.rot;}}}
    alive.frame(dt,t);
    // creature voices (Emeth's approved lines, additive): every 18-40 s one seeded resident says an idle/move/sleep/storm line from its real state; evCool gates it so existing lines win
    voiceT-=dt;if(voiceT<=0){if(evCool>0||!vcast.length)voiceT=2;else{const vt=voiceTurn(String(u.seed),++voiceN,vcast.length);const sp=vcast[vt.who];const vr=sp.beast?null:(residents as any[]).find((q:any)=>q.name===sp.name);voiceT=vt.wait;const vl=castLine(sp,voiceCategory({storming,napping:vr?vr.nap>0:false,moving:vr?vr.pause<=0:false}),String(u.seed),voiceN);if(vl)say(sp.name+': '+vl,6);}}
    // beast: wander by traits; when you're spawned in, run to greet (timing from JSON)
    const sp=spawnRef.current;let restored=false;if(sp&&!wasSpawned){try{const st=JSON.parse(localStorage.getItem(TKEY)||'null');if(st&&st.n&&st.f){pN.fromArray(st.n).normalize();pF.fromArray(st.f);pF.addScaledVector(pN,-pF.dot(pN)).normalize();restored=pF.lengthSq()>.5;}}catch{}}
    if(sp&&!wasSpawned&&!restored){pN.copy(bN).applyAxisAngle(bF,.0).addScaledVector(bF,-3/PR).normalize();pF.copy(bF);pF.addScaledVector(pN,-pF.dot(pN)).normalize();spawnT=0;greetT=-1;travNode.visible=true;}
    if(sp&&!wasSpawned&&restored){travNode.visible=true;spawnT=-1;lineRef.current('Back where you left off.');}
    else if(sp&&!wasSpawned)lineRef.current('A new traveler on the grass.');
    if(sp){travSaveT-=dt;if(travSaveT<=0){travSaveT=1;try{lwStore.setItem(TKEY,JSON.stringify({n:pN.toArray(),f:pF.toArray()}));}catch{}}}
    if(!sp&&wasSpawned){travNode.visible=false;lineRef.current('Grass will keep growing while you’re gone.');}wasSpawned=sp;
    let bSpeed=0;
    if(sp&&spawnT>=0){bSpeed=0;}// your beast spots you and freezes while you arrive
    else if(sp){const side=new THREE.Vector3().crossVectors(pN,pF).normalize();const goal=pN.clone().addScaledVector(pF,.9/PR).addScaledVector(side,.5/PR).normalize();const toP=goal.clone().sub(bN);const dist=Math.acos(Math.min(1,bN.dot(goal)))*PR+1.5*TRAV_H-.05;const dir=toP.addScaledVector(bN,-toP.dot(bN));
     if((!greeted||dist>6)&&dist>1.5*TRAV_H){if(dir.lengthSq()>1e-8){bF.copy(dir.normalize());}const v=1.6*Math.max(.7,bFeel());walkOn(bN,bF,v*dt);bSpeed=1;if(!greeted)greetT=-1;}
     else if(!greeted){greeted=true;greetT=0;lineRef.current('YOU’RE HERE. Rawr! Come see what I built.');traits=driftTraits(traits,u,bKey,'greet');brain.mode='glance';hop(1.4);}
     else if(greetT<0||greetT>2){bSpeed=wander();}
     if(greetT>=0)greetT+=dt;}
    else{bSpeed=wander();}
    function wander(){const nt=nearestThing(bN);if((window as any).__lwHold)return 0;if(nt&&nt.d<.4){if(touch(nt.t,'beast')){const k=nt.t.kind;learned[k]=(learned[k]||0)+1;traits=driftTraits(traits,u,bKey,(THING_LESSON as any)[k]||'day');try{lwStore.setItem('lw:learned:'+bKey,JSON.stringify(learned));}catch{}}}
     // seeded roaming errands: now and then the beast heads for a landscape place (beach / volcano shore / the cage), so it travels the whole pocket
     roamT-=dt;if(roamT<=0&&!roamGoal){roamT=40+roamR()*50;const opts=[beach?.center(),island?.anchor('crater_center'),gpts[0]].filter(Boolean);if(opts.length)roamGoal=(opts[Math.floor(roamR()*opts.length)] as any).clone().normalize();}
     if(roamGoal){steerTo(bN,bF,roamGoal,dt*2.5);if(bN.angleTo(roamGoal)<(beach?beach.radius*.35:.02))roamGoal=null;}
     else if(nt&&nt.d<5*(.3+traits.curiosity))steerTo(bN,bF,nt.t.n,dt*1.2);const v=(roamGoal?.6:.2+.35*traits.curiosity)*bFeel();walkOn(bN,bF,v*dt);if(curBiome==='ocean'&&!roamGoal)steerTo(bN,bF,gpts[0],dt*3);return .35;}
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
     const mag=rf.on?0:Math.min(1,Math.hypot(ix,iy));exBack=iy>.3;
     if(spawnT>=0){spawnT+=dt;const fr=Math.min(F.traveler_spawn.count-1,Math.floor(spawnT*F.traveler_spawn.fps));trav.visible=true;explorer.visible=false;trav.material.map=tSpawn;setFrame(tSpawn,F.traveler_spawn.cols,1,fr,0);if(spawnT>F.traveler_spawn.count/F.traveler_spawn.fps)spawnT=-1;}
     else if(mag>.08){turn(pN,pF,-ix*dt*2.2*(iy>.3?-1:1));const fwd=-iy;exRun=mag>.85;walkOn(pN,pF,(fwd>=0?1:-1)*Math.max(.25,Math.abs(fwd))*(exRun?3.5:1.2)*(TRAV_H/1.7)*Math.min(1,mag/.85)*dt*Math.max(.6,(BIOME_FEEL as any)[biomeOf(pN)]?.speed??1));
      const ang=Math.atan2(ix,-iy);const oct=((Math.round(ang/(Math.PI/4))%8)+8)%8;const ROW8=['N','NE','E','SE','S','SW','W','NW'][oct];const row=ROWS.indexOf(ROW8);
      trav.material.map=tWalk;setFrame(tWalk,F.traveler_walk.cols,8,Math.floor(t*F.traveler_walk.fps)%F.traveler_walk.cols,row<0?4:row);exWalk=mag;}
     else{trav.material.map=tIdle;setFrame(tIdle,F.traveler_idle.cols,1,Math.floor(t*F.traveler_idle.fps)%F.traveler_idle.cols,0);}
     if(spawnT<0){trav.visible=false;explorer.visible=true;exPlay(exWalk>.08?(exRun&&exActs.run?'run':'walk'):(greetT>=0&&greetT<2&&exActs.wave?'wave':(Math.sin(t*.13)>.85&&exActs.look?'look':'idle')));const sw=Math.sin(t*9)*.6*Math.min(1,exWalk);if(legs.length===2){legs[0].rotation.x=sw;legs[1].rotation.x=-sw;}explorer.position.y=Math.abs(Math.sin(t*9))*.02*Math.min(1,exWalk);
      // face the way you walk; backwards input turns the body around
      explorer.rotation.y=(exWalk>.08&&exBack?Math.PI:0)+(exMixer?0:0);}
     exMixer?.update(dt);exWalk=0;
     if(roadsterRef.current&&!car&&!carLoading)loadCar();
     if(car){const cs=mover.w.swim<.4&&mover.w.fly<.4;const wantCar=roadsterRef.current&&spawnT<0&&cs&&!rf.on;car.root.visible=wantCar;
      {/* roadster voices (approved lines, additive; the existing Roadster · SEEDED label is unchanged): board / other_rides / cruise / stop, sequenced by createRoadsterVoice (no clock, no random) */const rv=roadsterSeq.step(dt,{wantCar,carV,storming,night:lastSunH<0,nearResident:(residents as any[]).find((q:any)=>ang(q.n,pN)<.5)?.name||null});if(rv){const rl=roadsterVoice(rv.cat,String(u.seed),++voiceN,{beast:beastNm,other:rv.other||'A friend'});if(rl)say(rl,5);}}
      if(wantCar){explorer.visible=false;const arc=carPrev&&dt>0?Math.acos(Math.min(1,pN.dot(carPrev)))*PR/carK/dt:0;carV+=((exBack?-1:1)*Math.min(14,arc)-carV)*Math.min(1,dt*6);
       const st=driveState(carV),reduced=reducedNow();const P=car.parts;const om=wheelOmega(carV);for(const w of P.wheels)w.rotation.x+=om*dt;
       carSteer+=(steerAngle(ix*(iy>.3?-1:1))-carSteer)*Math.min(1,dt*5);for(const sn of P.steer)sn.rotation.y=carSteer;
       if(P.body)P.body.position.y=bodyBob(carV,t,reduced);
       const night=1-THREE.MathUtils.smoothstep(pN.dot(sunDir),-.12,.35);const hl=headlamp(st,night,t),ug=underglow(st,t);
       for(const gl of P.glows){if(gl.role==='headlamp_warm'){gl.m.emissive.set(hl.hex);gl.m.emissiveIntensity=hl.intensity;}else if(gl.role==='underglow_mood'){gl.m.emissive.set(ug.hex);gl.m.emissiveIntensity=reduced?.5:ug.pulse*1.2;}}
       (window as any).__lwRoadster={...((window as any).__lwRoadster||{}),on:true,state:st,v:+carV.toFixed(2),omega:+om.toFixed(2),steer:+carSteer.toFixed(3)};}
      else if((window as any).__lwRoadster)(window as any).__lwRoadster.on=false;}
     carPrev=(carPrev||new THREE.Vector3()).copy(pN);
     // ---- roadster flight (SIMULATED): lift off from the ground, one continuous climb, no loading cut
     {const RC=rfRef.current,K=keys.current;
      if(!rf.on&&car&&roadsterRef.current&&spawnT<0&&mover.w.swim<.4&&(RC.want||K.has(' ')||RC.assist==='ascent')){
       const g0=PR+hAt(pN);const p0=pN.toArray().map((c:number)=>c*(g0+FLIGHT.hullR)) as number[];
       rf.S=liftOff(p0,pN.toArray(),pF.toArray(),Math.max(0,carV)*carK);rf.on=true;rf.landT=0;RC.on=true;RC.want=false;if(RC.assist!=='ascent')RC.assist='';
       scene.add(car.root);car.root.visible=true;setRfUi(true);lineRef.current('Lift off · SIMULATED · Space = thrust');}
      else if(RC.want&&!rf.on)RC.want=false;
      if(rf.on&&rf.S){const S=rf.S;const gAt=(n:number[])=>PR+hAt(rf.v.set(n[0],n[1],n[2]));
       let inp:any={thrust:(K.has(' ')||RC.thrust)?1:0,brake:(K.has('b')||K.has('shift')||RC.brake)?1:0,pitch:-iy,yaw:ix,roll:(K.has('e')?1:0)-(K.has('q')?1:0),level:1};
       const manual=inp.thrust>0||Math.abs(inp.pitch)>.5||Math.abs(inp.yaw)>.5;
       if(RC.assist&&manual&&RC.assist==='land'){RC.assist='';}
       if(RC.assist==='land'){inp=landingAssist(S,gAt(norm(S.p)));}
       else if(RC.assist==='ascent'){const a=ascentAssist(S,PR+0);if(a.done){RC.assist='';}else inp=a;}
       stepFlight(S,inp,rdt,gAt); /* real elapsed time (cap .25 s; the integrator sub-steps), so a slow frame rate cannot slow the climb */
       // the world follows the car: everything that reads where the traveler is now reads the car
       const nn=norm(S.p);pN.set(nn[0],nn[1],nn[2]);{const f=new THREE.Vector3(S.fwd[0],S.fwd[1],S.fwd[2]);f.addScaledVector(pN,-f.dot(pN));if(f.lengthSq()>1e-4)pF.copy(f.normalize());}
       const U=new THREE.Vector3(S.up[0],S.up[1],S.up[2]),Fw=new THREE.Vector3(S.fwd[0],S.fwd[1],S.fwd[2]),Rt=new THREE.Vector3().crossVectors(U,Fw);
       m4.makeBasis(Rt,U,Fw);car.root.quaternion.setFromRotationMatrix(m4);car.root.position.set(S.p[0],S.p[1],S.p[2]).addScaledVector(U,-FLIGHT.hullR);
       const om=wheelOmega(Math.min(14,Math.hypot(S.v[0],S.v[1],S.v[2])/carK))*(S.landed?1:.2);for(const w of car.parts.wheels)w.rotation.x+=om*dt;
       if(!rf.plume){const pl=new THREE.Mesh(new THREE.ConeGeometry(.42,3.2,18,1,true),new THREE.MeshBasicMaterial({color:0xb48cff,transparent:true,opacity:0,blending:THREE.AdditiveBlending,depthWrite:false,side:THREE.DoubleSide}));pl.rotation.x=-Math.PI/2;pl.position.set(0,.55,-2.6-1.6);car.root.add(pl);rf.plume=pl;cleanup.push(()=>{pl.geometry.dispose();(pl.material as any).dispose();});}
       {const th=S.throttle;rf.plume.material.opacity=.7*th;rf.plume.scale.set(1,1+th*.5,1);for(const gl of car.parts.glows)if(gl.role==='underglow_mood'){gl.m.emissive.set(0x9fe8ff);gl.m.emissiveIntensity=.8+th*3;}}
       const fi=flightInfo(S,gAt(nn));rf.fi=fi;
       // hud: only the text node changes, a few times a second
       {const ph=fi.inSpace?'space':(rf.ph==='space'||rf.ph==='home')?'home':fi.alt>1.5?'leaving':'air';if(ph!==rf.ph){if(ph==='leaving')lineRef.current('Leaving the air behind');else if(ph==='space')lineRef.current('Out past the sky. Same sun.');else if(ph==='home')lineRef.current('Heading home to '+beastNm);rf.ph=ph;}} /* Emeth's roadster lines (one_universe_lines_PROPOSED) */
       rf.hudT-=dt;if(rf.hudT<=0&&hudRef.current){rf.hudT=.12;const el=orbitElements(S);hudRef.current.textContent='Flight · SIMULATED · alt '+Math.max(0,fi.alt).toFixed(1)+' · '+(RC.assist==='land'?'landing':RC.assist==='ascent'?'climbing':fi.inSpace?(el.bound?'in orbit':'leaving'):'in the air');hudRef.current.title='Space = thrust · W/S = nose · A/D = turn · B = brake · L = land';}
       (window as any).__lwFlight={on:true,alt:+fi.alt.toFixed(3),speed:+fi.speed.toFixed(3),climb:+fi.climb.toFixed(3),r:+fi.r.toFixed(3),inSpace:fi.inSpace,escaping:fi.escaping,throttle:+S.throttle.toFixed(2),assist:RC.assist,label:FLIGHT_LABEL,landed:!!S.landed,t:+S.t.toFixed(2)};
       // touch down softly and stop: hand the car back to the ground (same place, same heading)
       if(S.landed&&S.t>1.2&&S.throttle<.05&&inp.thrust<.05&&Math.hypot(S.v[0],S.v[1],S.v[2])<.6){rf.on=false;RC.on=false;RC.assist='';RC.thrust=false;RC.brake=false;travNode.add(car.root);car.root.position.set(0,0,0);car.root.quaternion.identity();car.root.visible=false;rf.plume.material.opacity=0;carV=0;carPrev=null;setRfUi(false);(window as any).__lwFlight={...((window as any).__lwFlight||{}),on:false};}
      }
      else if((window as any).__lwFlight?.on)(window as any).__lwFlight.on=false;}
     place(travNode,pN,pF);if(rf.on)travNode.visible=false;else if(spawnT<0||trav.visible)travNode.visible=true;
     {const inW=WATER_IDS.has(field?legendAt(field,[pN.x,pN.y,pN.z]):(cosmoBiome(pN)||''));mover.fly=flyRef.current;stepMover(mover,{dt,inWater:inW,ground:hAt(pN),mpu:TRAV_H/1.7});
      travNode.position.addScaledVector(pN,mover.y-hAt(pN)*0);(window as any).__lwMove={y:+mover.y.toFixed(3),w:{walk:+mover.w.walk.toFixed(2),swim:+mover.w.swim.toFixed(2),fly:+mover.w.fly.toFixed(2)},inWater:inW};}
     // over-the-shoulder (art target 08_explore_daynight): behind and right of you, looking ahead
     const shS=new THREE.Vector3().crossVectors(pN,pF).normalize();camTarget.copy(pN).multiplyScalar(PR+TRAV_H*.9).addScaledVector(pF,1.6);cW.copy(pN).multiplyScalar(PR+TRAV_H*2.6).addScaledVector(pF,-2.7).addScaledVector(shS,-.55);camTarget.addScaledVector(pN,mover.y);cW.addScaledVector(pN,mover.y*(1-.4*mover.w.swim));cT.copy(camTarget);cN.copy(pN);}
    else{// close framing around your beast (the old watch view); the old orbit is now the far end of the same zoom
     const side=new THREE.Vector3().crossVectors(bN,bF).normalize();const sw=HOLD?0:Math.sin(t*.15);cW.copy(bN).multiplyScalar(PR+1.5).addScaledVector(bF,-2.6*Math.cos(sw)).addScaledVector(side,2.2*sw);
     cT.copy(beastNode.position).addScaledVector(bN,TRAV_H*.6);cN.copy(bN);}
    // ---- one continuous zoom: close over-the-shoulder (z=0) to full planet orbit (z=1); pinch / wheel / buttons all move zT
    // gentle seeded fly-over: in the planet view, after 6 s without input, the camera drifts between the beach, the volcano and the sea, then hands back on touch
    {const mo=sp?'s':watchRef.current?'w':'o';const idle=!HOLD&&performance.now()-userAt>6000;
     if(seaQ&&ocean&&(window as any).__lw?.toOcean(0,seaQ)){seaQ=0;if(seaF)seaF.snap=3;} /* the ocean loads after boot, so a ?sea=X request waits for it */
     if(seaF&&(userAt>seaF.at||beachCamRef.current||mo!=='o'||!ocean)){seaF=null;seaHud(false);}
     if(seaF&&ocean&&mo==='o'){ /* ?sea=X / Sea life button: a camera that stays with the school (seeded positions, species-sized stand-off) until the viewer touches the world */
      const v=ocean.view(seaF.sc,t);const sn=new THREE.Vector3(v.n[0],v.n[1],v.n[2]).normalize();const sh=new THREE.Vector3(v.h[0],v.h[1],v.h[2]);const stand=Math.max(.5,Math.min(6,v.sizeU*(v.kind==='whale'?.7:2.4)+(v.kind==='whale'?0:v.radiusU*.4)));const ht=Math.max(.3,stand*(v.sizeU<.5?.9:.55));
      if(!touring){touring=true;tourN.copy(cN);}{const bn=performance.now();const rd=Math.min(1.5,(seaF.bt?bn-seaF.bt:16)/1000);seaF.bt=bn;if(seaF.snap>0)tourN.copy(sn);else tourN.lerp(sn,Math.min(1,rd*2.2)).normalize();}cN.copy(tourN);
      const stl=sh.clone().sub(tourN.clone().multiplyScalar(sh.dot(tourN)));if(stl.lengthSq()<1e-8)stl.set(1,0,0);stl.normalize();
      cT.copy(tourN).multiplyScalar(PR+.03).addScaledVector(stl,v.sizeU*.4);cW.copy(tourN).multiplyScalar(PR+ht).addScaledVector(stl,-stand);zT=0;
      (window as any).__lwSeaFocus={kind:seaF.sc.kind,species:v.species,standoff:+stand.toFixed(2)};}
     else if(mo==='o'&&beachCamRef.current&&beach){ // dedicated beach angle: camera out on the water side, low, looking up the shore at the sand, dunes and surf, in daylight
      if(!touring){touring=true;tourN.copy(cN);}tourI=0;{const bn=performance.now();const rd=Math.min(1.5,((beach as any).__bcT?bn-(beach as any).__bcT:16)/1000);(beach as any).__bcT=bn;tourN.lerp(beach.center().clone().normalize(),Math.min(1,rd*1.4)).normalize();} /* wall-clock eased, so a slow frame rate still arrives */cN.copy(tourN);
      const lw=beach.landward().clone().normalize();const tl=lw.clone().sub(tourN.clone().multiplyScalar(lw.dot(tourN)));if(tl.lengthSq()<1e-8)tl.set(1,0,0);tl.normalize();const sd=new THREE.Vector3().crossVectors(tourN,tl).normalize();const sw=Math.sin(t*.12);
      /* framed on Cosmo's own anchors: the camera stands out on the water side of the tide_line, above the lifted terrain, looking up the sand to the palms and place slots (not at ground level inside the grass) */
      const tideA=beach.anchor('tide_line'),spawnA=beach.anchor('shore_spawn');const base=PR+Math.max(0,beach.group.position.length());const tn=(tideA||spawnA||beach.center()).clone().normalize();
      cT.copy(tn).multiplyScalar(base+.28).addScaledVector(tl,.9);cW.copy(tn).multiplyScalar(base+.85).addScaledVector(tl,-1.9+sw*.25).addScaledVector(sd,.8*sw);zT=.1;(window as any).__lwBeachFrame={tide:!!tideA,spawn:!!spawnA,base:+base.toFixed(3)};
      (window as any).__lwTour={i:0,place:'beach',beachCam:true,cw:cW.toArray().map((v:number)=>+v.toFixed(2)),ct:cT.toArray().map((v:number)=>+v.toFixed(2)),sun:sunDir.toArray().map((v:number)=>+v.toFixed(2)),beach:beach.center().toArray().map((v:number)=>+v.toFixed(2))};}
     else if(mo==='o'&&idle&&beach){(beach as any).__bcT=0;if(!touring){touring=true;tourN.copy(cN);tourT=0;}tourT-=dt;
      if(tourT<=0){tourT=11+tourR()*5;tourI=(tourI+1)%3;zT=.16+tourR()*.05;}
      const tgt=[beach.center(),island?.anchor('crater_center')||beach.center(),(window as any).__lwOceanN||(window as any).__lwSeaN||gpts[0]][tourI].clone().normalize();tourN.lerp(tgt,Math.min(1,dt*.35)).normalize();cN.copy(tourN);{const tg=new THREE.Vector3().crossVectors(tourN,new THREE.Vector3(0,1,0));if(tg.lengthSq()<1e-6)tg.set(1,0,0);tg.normalize();cT.copy(tourN).multiplyScalar(PR+.2);cW.copy(tourN).multiplyScalar(PR+2.2).addScaledVector(tg,-3.2);}
      (window as any).__lwTour={i:tourI,place:['beach','volcano','ocean'][tourI]};}
     else if(touring){touring=false;if(mo==='o')zT=1;(window as any).__lwTour=null;}}
    const mode=sp?'s':watchRef.current?'w':'o';if(mode!==zMode){zMode=mode;zT=mode==='s'?0:mode==='w'?.12:1;zX=0;}if(HOLD){if(hz.m!==mode){hz.m=mode;hz.z=zT;}zT=hz.z;zX=0;}
    zC+=(zT-zC)*Math.min(1,dt*5);zXc+=(zX-zXc)*Math.min(1,dt*5);const zb=zoomBlend(zC);UG.uLift.value=zb.orbit;{const bk=bladeMat.uniforms.uBladeK;const goal=beachCamRef.current&&!spawnRef.current&&beach?0.28:1;bk.value+=(goal-bk.value)*Math.min(1,dt*3);}(window as any).__lwZoom={z:+zC.toFixed(3),pullOut:+zXc.toFixed(3),target:zT,orbit:+zb.orbit.toFixed(3)};
    {const oW=cN.clone().multiplyScalar(1.2).add(new THREE.Vector3(Math.cos(oy)*Math.sin(ox),Math.sin(oy),Math.cos(oy)*Math.cos(ox))).normalize().multiplyScalar(PR*4.3);
     const dir=cW.clone().normalize().lerp(oW.clone().normalize(),zb.orbit).normalize();const ground0=PR+DISP+TRAV_H*.45;
     const len=clampAboveGround(zoomDistance(zC,cW.length(),oW.length()),0,0);const want=dir.multiplyScalar(Math.max(len,ground0)*Math.exp(zXc*zb.orbit));
     // keep the close view's offset from the focus at low zoom (log-scaled pull-back), so close-up stays over the shoulder
     if(zb.orbit<.5){const off=cW.clone().sub(cN.clone().multiplyScalar(PR));const k=(len-cW.length())/Math.max(.001,oW.length()-cW.length());want.lerp(cN.clone().multiplyScalar(PR).add(off.multiplyScalar(1+k*6)),1-zb.orbit*2);}
     if(seaF&&seaF.snap>0){camPos.copy(want);}else camPos.lerp(want,Math.min(1,dt*(sp?4:2.5)));camPos.setLength(clampAboveGround(camPos.length(),ground0,0));
     const tgt=cT.clone().lerp(cN.clone().multiplyScalar(PR*.15),zb.orbit);if(seaF&&seaF.snap>0){camLook.copy(tgt);seaF.snap--;}else camLook.lerp(tgt,Math.min(1,dt*4));
     camera.position.copy(camPos);camera.up.copy(cN).lerp(new THREE.Vector3(0,1,0),zb.orbit).normalize();camera.lookAt(camLook);{const L=camPos.length(),farW=Math.max(400,L*12);if(lwStars){const tk=Math.min(1,zXc*2);lwStars.position.copy(camera.position).multiplyScalar(tk);lwStars.scale.setScalar(1+(Math.max(1,L/60)-1)*tk);}if(!rf.blend&&Math.abs(camera.far-farW)>1){camera.far=farW;camera.near=zXc>.02?Math.max(.05,L*.004):.05;camera.updateProjectionMatrix();}}}
    // first person eye (Studio note 1): 1.6 m eye (.47 units), level look along your heading, flat 2.5 km local patch + far ridges; the 27 m sphere stays for orbit
    {const vmc=viewModeCamera(viewRef.current);if(vmc.forceOrbit&&sp)zT=1;const want=!!sp&&vmc.eye&&(window as any).__lwEye!==false&&!rf.on&&rf.blend===0&&zC<.25&&mover.w.fly<.4&&mover.w.swim<.4;fpOn=want;
     if(want){travNode.visible=false;const gr=pN.clone().multiplyScalar(PR+hAt(pN));const eye=gr.clone().addScaledVector(pN,.47);camera.position.copy(eye);camera.up.copy(pN);camera.lookAt(eye.clone().addScaledVector(pF,10));
      if(camera.far<1500){camera.far=1500;camera.near=.05;camera.updateProjectionMatrix();}lk2Ground.update(true,gr.clone().addScaledVector(pN,-1.5),pN,os1?os1.day:1,Math.max(0,pN.dot(sunDir)));lk2Ground.step(t);}
     else lk2Ground.update(false,pN,pN,0,0);}
    // roadster flight camera (first person, from the cockpit). blend 0 -> 1 on lift off and back on landing, so the climb is one continuous shot, never a cut.
    {const tB=rf.on?1:0;rf.blend+=(tB-rf.blend)*Math.min(1,dt*(rf.on?2.6:3.2));if(Math.abs(rf.blend-tB)<.003)rf.blend=tB;
     if(rf.blend>0&&rf.S){const S=rf.S,e=THREE.MathUtils.smoothstep(rf.blend,0,1);
      const U=new THREE.Vector3(S.up[0],S.up[1],S.up[2]),Fw=new THREE.Vector3(S.fwd[0],S.fwd[1],S.fwd[2]),Rt=new THREE.Vector3().crossVectors(U,Fw);
      const eye=new THREE.Vector3(S.p[0],S.p[1],S.p[2]).addScaledVector(U,-FLIGHT.hullR+1.12*carK).addScaledVector(Rt,.3*carK).addScaledVector(Fw,.05*carK);
      const gq=camera.quaternion.clone(),gp=camera.position.clone();m4.lookAt(eye,eye.clone().add(Fw),U);const cq=new THREE.Quaternion().setFromRotationMatrix(m4);
      {const fi0=rf.fi;const idle=!lkD&&performance.now()/1000-lkAt>2;if(idle){const toPlanet=Math.acos(Math.max(-1,Math.min(1,-(Fw.x*S.p[0]+Fw.y*S.p[1]+Fw.z*S.p[2])/Math.max(1e-6,Math.hypot(S.p[0],S.p[1],S.p[2])))));const tp=fi0&&fi0.alt>.3?-Math.max(0,Math.min(1,(toPlanet-.35)*.6)):0;lkP+=(tp-lkP)*Math.min(1,dt*1.2);lkY-=lkY*Math.min(1,dt*1.5);}
       cq.multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(lkP,lkY,0,'YXZ')));}
      camera.position.lerpVectors(gp,eye,e);camera.quaternion.copy(gq).slerp(cq,e);camera.up.copy(U);
      const fi=rf.fi||{alt:0,speed:0};const sf=skyFade(fi.alt)*e;const fov=55+e*(10+Math.min(14,(fi.speed||0)*2.2));
      const L=camera.position.length(),farW=Math.max(2400,L*40),nearW=THREE.MathUtils.lerp(.05,.03,e);
      if(Math.abs(camera.fov-fov)>.05||Math.abs(camera.far-farW)>1||Math.abs(camera.near-nearW)>.001){camera.fov=fov;camera.far=farW;camera.near=nearW;camera.updateProjectionMatrix();}
      // leaving the air: the sky goes dark and the stars come out; a blue rim of atmosphere hangs around the planet
      (scene.background as any).lerp(SPACE_BG,1-sf);if(starMat)starMat.opacity=Math.max(starMat.opacity,1-sf);if(lwStars)lwStars.visible=!(os1&&os1.day>.05&&zC<.6) /* no star dots in a ground-level day sky (they read as white blobs) */;
      if(lwStars){lwStars.position.copy(camera.position);lwStars.scale.setScalar(Math.max(1,L/90));}
      rfAtmo.visible=e>.02;(rfAtmo.material as any).uniforms.uK.value=e*(.5+.5*Math.min(1,Math.max(0,fi.alt)/PR));
      (window as any).__lwFlightCam={e:+e.toFixed(3),fov:+fov.toFixed(1),sky:+sf.toFixed(3),eye:eye.toArray().map((v:number)=>+v.toFixed(2))};}
     else if(rfAtmo.visible){rfAtmo.visible=false;if(camera.fov!==55){camera.fov=55;camera.near=.05;camera.updateProjectionMatrix();}}}
    try{(window as any).__lwPlacePin?.();lwLand?.update(t,dt,{sunDir,storm:Math.max(field?.storm||0,storming||0,(window as any).__lwStormForce||0),hasLife:residents.length>0||(u.life||[]).some((l:any)=>l.planet===homePl?.id),cam:camera.position,reduced:reducedNow()});
     {const it0=lwLand?.items?.[0];if(it0){const m=it0.mode;if(m!==lmPrev){const prev=lmPrev;lmPrev=m;if(prev!==null){const g=noticeGate(lmGate,'land:'+m,performance.now(),8000,60000);lmGate=g.state;if(g.show){const tx=landscapeNotice(it0.ls,m,{beast:beastName||'Your beast',planet:(homePl as any)?.name||'this world',seed:String(u.seed),n:lmN++});if(tx)lineRef.current(tx);}}}}}}catch{}
    {const lc=(window as any).__lwLandCam;if(lc&&lwLand)try{lwLand.inspectCam(camera,lc);}catch{}}
    // Alive props: real events only (a breath peak in view, a creature entering a crystal's 3 m, flowers visibly turning) -> one of Emeth's lines, picked by seed.
    {const evs=surface?.update(t,{sunDir,creatures:[bN,...residents.map((r:any)=>r.n)],cam:camera.position})||[];if(surface&&gSnap.length){gRedT-=dt;if(gRedT<=0){gRedT=.5;gReduced=reducedNow();}gBeast.copy(bN).multiplyScalar(PR);surface.growthFrame({t,wind:[field?.mp?.wind?.x||0,field?.mp?.wind?.z||0],turb:field?.mp?.turbulence||0,storm:field?.storm||0,reduced:gReduced,beast:gBeast,px:renderer.domElement.height/(2*Math.tan(camera.fov*Math.PI/360)),nowMs:performance.now()});}for(const k of evs){const f=aliveGate.fire(k,String(u.seed),t);if(f){lineRef.current(f.line);break;}}}heaven.update(t);{const wid=field?legendAt(field,[cN.x,cN.y,cN.z]):(cosmoBiome(cN.clone())||'');heaven.root.visible=zC<.55&&cN.dot(sunDir)>-.08&&!WATER_IDS.has(wid)&&!fpOn&&!(os1&&os1.day>=.05);} /* the heaven shaft is a land feature: over open water it read as a pale triangular wedge */heaven.root.position.copy(cN).multiplyScalar(PR+hAt(cN));heaven.root.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),cN);
    if(GDBG&&surface&&host.current){gDbgT-=dt;if(gDbgT<=0){gDbgT=.4;try{if(!gDbgEl){gDbgEl=document.createElement('div');gDbgEl.setAttribute('data-lw-growthdebug','');gDbgEl.style.cssText='position:absolute;left:8px;top:96px;z-index:5;max-width:70%;padding:4px 7px;border-radius:6px;background:rgba(0,0,0,.72);color:#9fe;font:11px/1.35 monospace;pointer-events:none;white-space:pre';host.current.appendChild(gDbgEl);cleanup.push(()=>{gDbgEl?.remove();});}
     const gi=surface.growthInfo?.();const me=spawnRef.current?pN:bN;let bn:any=null,bd=9;for(const n of gi?.nodes||[]){const la=n.lat*Math.PI/180,lo=n.lon*Math.PI/180;const dd=Math.acos(Math.max(-1,Math.min(1,me.x*Math.cos(la)*Math.cos(lo)+me.y*Math.sin(la)+me.z*Math.cos(la)*Math.sin(lo))));if(dd<bd){bd=dd;bn=n;}}
     const layers=(gi?.lists||[]).filter((l:any)=>l.inTerritory>0).map((l:any)=>l.layer).filter((v:any,i:number,a:any[])=>a.indexOf(v)===i).join(',')||'none';
     gDbgEl.textContent=bn?'growth '+bn.id+'\nkind '+bn.kind+'  stage '+bn.stage+'\nlayers '+layers+'\ntaps '+(gTaps[bn.id]||0)+'  beast arc '+(bd*PR).toFixed(1)+' u':'growth: no nodes';}catch{}}}
    beastLamp.position.copy(beastNode.position).addScaledVector(bN,TRAV_H*1.4);beastLamp.intensity=(1-zb.orbit)*7;
    {const night=1-THREE.MathUtils.smoothstep(cN.dot(sunDir),-.12,.35);const dusk=Math.max(0,1-Math.abs(cN.dot(sunDir))/.18)*.7;
     if(ocean){ocean.update(t,{night,camPos:camera.position});if(((t*2)|0)%4===0)(window as any).__lwOcean=ocean.state();}
     mech?.update(t,dt,{focus:cN.clone().multiplyScalar(PR+hAt(cN)),up:cN,camPos:camera.position,rain:(window as any).__lwWeatherForce?.rain??weather.rain,cloud:(window as any).__lwWeatherForce?.cloud??weather.cloud,wind:weather.wind,night,dusk,ground3:zC<.6,
      torch:sp?travNode.position.clone().addScaledVector(pN,TRAV_H*.7).addScaledVector(new THREE.Vector3().crossVectors(pN,pF).normalize(),-TRAV_H*.25):null,beast:beastNode.position.clone().addScaledVector(bN,TRAV_H*.5)});
     // underwater: Cosmo's ramp tints fog + background by depth when the camera is in the sea
     const sw=sp&&!rf.on?mover.w.swim:0;if(sw>.4){const dM=Math.max(0,-mover.y)/(TRAV_H/1.7);const tD=Math.min(1,dM/60+.15);const uc=underwaterColor(THREE,tD);
      if(!(scene.fog as any)?.isFogExp2)scene.fog=new THREE.FogExp2(uc.getHex(),.1);(scene.fog as any).color.copy(uc);(scene.fog as any).density=THREE.MathUtils.lerp(.035,.09,tD)/(TRAV_H/1.7)*sw*.5;(scene.background as any).lerp(uc,sw);}
     else if((scene.fog as any)?.isFogExp2)scene.fog=null;(window as any).__lwUnder=sw>.4;}
     // Emeth's world lines, fired by the real loop's state edges (sun height, weather, swim/fly, lava, water paths)
     if(beach&&!beachLift&&hData){beachLift=1;const c=beach.center().clone().normalize();const L=Math.max(0,hAt(c)-.004);if(L>0)beach.group.position.copy(c).multiplyScalar(L);(window as any).__lwBeachLift=L;}
    // Emeth's landscape_places lines: fire once when the beast walks into an area (beach / volcano / ocean); seeded pick
     {const here=(spawnRef.current?pN:bN);let area:string|null=null;
      if(beach&&here.angleTo(beach.center())<beach.radius)area='beach';else if(island&&here.angleTo(island.anchor('crater_center'))<.06)area='volcano';else if(field&&WATER_IDS.has(legendAt(field,[here.x,here.y,here.z])))area='ocean';
      if(area!==lwArea){lwArea=area;if(area){placeN++;const others=(residents as any[]).some((q:any)=>beach&&area==='beach'&&q.n.angleTo(beach.center())<beach.radius);const pl=placeLine(others?'beach_games':'reach_'+area,u.seed,placeN);if(pl){lineRef.current(beastNm+': '+pl);evCool=5;}(window as any).__lwPlace={area,n:placeN,line:pl};}}}
     {const ck=stepWorldCues(cues,{sunH:(spawnRef.current?pN:bN).dot(sunDir),rain:weather.rain,under:(window as any).__lwUnder===true,fly:sp?mover.w.fly:0,bursts:island?.state?.().bursts||0,wet:lwWet});if(ck){cueN++;const wl=worldLine(ck,u.seed,cueN);if(wl)say(beastNm+': '+wl,5);(window as any).__lwCue={kind:ck,n:cueN};}}
    if(qTierRef.current&&qTierRef.current!==postTierSeen){postTierSeen=qTierRef.current;postFor(postTierSeen);}
    if(post&&!asciiRef.current){post.render(sunDisc.position,os1?os1.elevationDeg:(Math.asin(Math.max(-1,Math.min(1,sunDir.y)))*180/Math.PI));if((frameN++&31)===0)(window as any).__lwPost=post.state();}else if(asciiRef.current)ascii.render(scene,camera);else renderer.render(scene,camera);
    hudT+=dt;if(hudT>.5){hudT=0;if(ocean){const bn=[bN.x,bN.y,bN.z];const nr=ocean.nearest(bn,t);const seaNear:Record<string,number>={whale:45,ray:25,fish:9,jelly:9,turtle:12,seabird:12};if(nr&&(SEA_VOICE_KEY as any)[nr.kind]&&nr.m<(seaNear[nr.kind]||9)){const sg=noticeGate(seaGate,'sea:'+nr.kind,performance.now(),20000);seaGate=sg.state;if(sg.show){const sc=seaCount[nr.kind]=(seaCount[nr.kind]||0)+1;/* every other sighting of a whale or school of fish keeps the older creature_notices line; every other kind has only the sea_life voice line */const old=(nr.kind==='whale'||nr.kind==='fish')&&sc%2===0;if(old)notice(nr.kind==='whale'?'sea_life_whale':'sea_life_fish',0);else{const sl=seaLifeVoice(nr.kind,String(u.seed),sc);if(sl)lineRef.current(sl);}}}else if(ocean.shoreNear(bn,.05))notice('sea_life_shore',20000);}if(storming>.6&&!stormHi&&field.storm>.6){stormHi=true;stormSeen=true;notice('storm_near');}if(stormSeen&&storming<.15){stormSeen=false;stormHi=false;notice('storm_passes');}const last=u.history?.[u.history.length-1];setHud({tick:u.tick,simE:last?.sim_E??null,life:u.life.length,storms:u.storms.length,cover:Math.min(1,UG.uSpread.value/Math.PI),traits,learned:{...learned},awake:things.filter((x:any)=>x.awake).length,blades:bladeCap,fps:+fps.toFixed(0)});}
   };
   frame();setBooted(true);(window as any).__lw={spawn:()=>setSpawned(true),tourTo:(i:number)=>{userAt=-1e9;tourI=i-1;tourT=0;},beachInfo:()=>{if(!beach)return null;const c=beach.center().clone().normalize();return {hAt:hAt(c),hAtLand:hAt(beach.landward().clone().normalize()),TRAV_H,PR,k:TRAV_H/1.7*.07};},toBeach:(f:number=.12)=>{if(!beach)return false;const sp0=(beach.anchor('shore_spawn')||beach.center()).clone().normalize();const sea=beach.sea().clone().normalize();bN.copy(sp0).addScaledVector(beach.center().clone().normalize().sub(sp0),0).normalize();bN.copy(beach.center().clone().normalize().lerp(beach.landward().clone().normalize(),f)).normalize();bF.copy(sea).addScaledVector(bN,-sea.dot(bN)).normalize();roamGoal=null;roamT=999;return true;},toOcean:(i:number=0,k:number=0)=>{if(!ocean)return false;const L=ocean.data.schools;const sc=(k?L.filter((x:any)=>x.kind===['fish','ray','whale','jelly','turtle','seabird'][k-1]):L)[i];if(!sc)return false;seaF={sc,at:performance.now()};seaHud(true,sc);bN.set(sc.n[0],sc.n[1],sc.n[2]);bF.set(0,1,0).addScaledVector(bN,-bN.y);if(bF.lengthSq()<1e-6)bF.set(1,0,0);bF.normalize();roamGoal=null;roamT=999;return true;},toSea:()=>{if(!island)return false;const v=island.anchor('sea_level').clone().normalize();const r=lwStream(u.seed+':sea-test');for(let i=0;i<400;i++){const d=unitFrom(r) as number[];const w=new THREE.Vector3(d[0],d[1],d[2]);if(w.dot(v)>.8&&WATER_IDS.has(field?legendAt(field,d):(cosmoBiome(w)||''))&&w.dot(v)<.97){pN.copy(w);pF.copy(v).addScaledVector(w,-v.dot(w)).normalize();return true;}}return false;}};
   {/* ?sea=fish|ray|whale jumps the camera to that seeded school (same as the Sea life button) */const sq=new URLSearchParams(window.location.search).get('sea');if(sq){const k=({fish:1,ray:2,whale:3,jelly:4,turtle:5,bird:6,seabird:6} as any)[sq]||0;if(k){seaQ=k;zT=0;}}}
   cleanup.push(()=>{renderer.dispose();plush?.dispose();scene.traverse((o:any)=>{o.geometry?.dispose?.();o.material?.dispose?.();});});
  })().catch(e=>{if(!disposed)setErr(String(e?.message||e));});
  return()=>{disposed=true;cancelAnimationFrame(raf);cleanup.forEach(f=>{try{f();}catch{}});};
 },[gKey,beastKey]);// eslint-disable-line react-hooks/exhaustive-deps
 // touch joystick
 const jd=(e:React.PointerEvent)=>{(e.target as Element).setPointerCapture(e.pointerId);joy.current={x:0,y:0,active:true,id:e.pointerId,cx:e.clientX,cy:e.clientY};setStick({x:0,y:0});};
 const jm=(e:React.PointerEvent)=>{const j=joy.current;if(!j.active||e.pointerId!==j.id)return;const dx=(e.clientX-j.cx)/50,dy=(e.clientY-j.cy)/50;const m=Math.max(1,Math.hypot(dx,dy));j.x=dx/m;j.y=dy/m;setStick({x:j.x,y:j.y});};
 const ju=()=>{joy.current={...joy.current,x:0,y:0,active:false};setStick(null);};
 const T=hud.traits;
  const soundBtn=<button type="button" data-lw-event-sounds aria-pressed={sndOn} onClick={toggleSound} title={VL_TEXT.event_sounds.hint+' '+VL_TEXT.event_sounds.note_long} style={{...pill(sndOn?'#2f855a':'#4a5568'),border:'1px solid rgba(255,255,255,.35)',color:'#fff',cursor:'pointer',font:'inherit',fontSize:11}}>{sndOn?VL_TEXT.event_sounds.state_on:VL_TEXT.event_sounds.state_off}</button>;
  /* Visual Life Pass B7: provenance, read from the view's own snapshot when the person opens it; every row is a label plus the engine channel behind it */
  const provBlock=<details data-lw-vl-provenance style={{width:'100%',fontSize:11,color:'#d9ccff'}} onToggle={(e:any)=>{if(e.currentTarget.open)setProv(vlProvenance((window as any).__lwVisualLife));}}><summary style={{cursor:'pointer'}}>How this look is made</summary>{prov?<div data-lw-vl-provenance-body style={{marginTop:4}}>{prov.rows.map((r:any)=><p key={r.key} data-lw-vl-row={r.key} data-on={r.on?'1':'0'} style={{margin:'2px 0',opacity:r.on?1:.55}}>{r.text} · {r.label} · {r.on?'on':'not in view'} · from {r.driver}</p>)}<p style={{margin:'2px 0'}}>Look pack v{prov.pack.version} · {prov.pack.label} · sha256 {prov.pack.sha256.slice(0,12)}</p><p style={{margin:'2px 0'}}>{prov.seed.text} · {prov.seed.label}</p></div>:null}</details>;
 return <div ref={host} className="lw-root" data-living-world={spawned?'spawned':'orbit'} data-lw-embedded={embedded?'':undefined} style={{pointerEvents:'auto',position:embedded||door?'absolute':'fixed',inset:0,zIndex:embedded||door?1:2147483000,borderRadius:embedded?18:0,overflow:'hidden',background:'#05030f',touchAction:embedded&&!spawned?'pan-y':'none',fontSize:embedded?11:13,color:'#efeaff',font:'13px/1.35 system-ui,sans-serif'}}>
  <canvas ref={canvasRef} style={{position:'absolute',inset:0,width:'100%',height:'100%',display:'block',touchAction:'none'}}/>
  {!booted&&!err?<div role="status" aria-live="polite" data-lw-loading style={{position:'absolute',inset:0,zIndex:4,display:'grid',placeItems:'center',background:'#05030f',color:'#d9ccff',fontWeight:600,pointerEvents:'none'}}>Opening your tiny world…</div>:null}
  {embedded&&infoHost?createPortal(<details data-lw-chips data-lw-info data-lw-in-menu style={{maxWidth:'100%'}}>
   <summary aria-label="About this world: what is recorded, simulated or modelled" style={{listStyle:'none',cursor:'pointer',width:30,height:30,borderRadius:'50%',display:'grid',placeItems:'center',background:'rgba(10,6,30,.78)',border:'1px solid rgba(190,170,255,.6)',color:'#efeaff',font:'700 15px system-ui'}}>ⓘ</summary>
   <div style={{display:'flex',flexWrap:'wrap',gap:6,marginTop:6,padding:8,borderRadius:12,background:'rgba(10,6,30,.86)'}}>
    {visit?<span style={pill('#0f766e')} data-lw-visit title="Terrain is re-generated by the same generators from a seed derived from the RECORDED run, plus this planet's own water and temperature. Nothing from the visit is saved.">Visiting {planetName(visit.id)} · SEEDED (not a measured surface)</span>:null}<span style={pill('#2b6cb0')} data-lw-spark>{LW_LABELS.spark}</span><span style={pill('#9b2c2c')} data-lw-growth>{LW_LABELS.growth}</span><span style={{...pill('#2f855a'),display:'none'}} data-lw-growth-nodes ref={hudGN}/><span style={{...pill('#2c7a7b'),display:'none'}} data-lw-home-growth ref={hudHome}/><span style={pill('#553c9a')} data-lw-model>{LW_LABELS.model}</span><span style={pill('#276749')} data-lw-biome ref={hudBiome}>Biome</span><span style={{...pill('#0e7490'),display:'none'}} data-lw-sea-seeded ref={hudSea}/><span style={{...pill('#0e7490'),display:'none'}} data-lw-visual-life ref={hudVL}/>{soundBtn}{provBlock}
   <p data-lw-growth-explainer ref={hudGNx} style={{display:'none',margin:'4px 2px 0',fontSize:11,lineHeight:1.35,color:'#d9ccff',maxWidth:300}}/></div></details>,infoHost)
  :embedded?<details data-lw-chips data-lw-info style={{position:'absolute',top:'calc(env(safe-area-inset-top) + 8px)',left:8,maxWidth:'calc(100% - 16px)',zIndex:3}}>
   <summary aria-label="About this world: what is recorded, simulated or modelled" style={{listStyle:'none',cursor:'pointer',width:30,height:30,borderRadius:'50%',display:'grid',placeItems:'center',background:'rgba(10,6,30,.78)',border:'1px solid rgba(190,170,255,.6)',color:'#efeaff',font:'700 15px system-ui'}}>ⓘ</summary>
   <div style={{display:'flex',flexWrap:'wrap',gap:6,marginTop:6,padding:8,borderRadius:12,background:'rgba(10,6,30,.86)'}}>
    {visit?<span style={pill('#0f766e')} data-lw-visit title="Terrain is re-generated by the same generators from a seed derived from the RECORDED run, plus this planet's own water and temperature. Nothing from the visit is saved.">Visiting {planetName(visit.id)} · SEEDED (not a measured surface)</span>:null}<span style={pill('#2b6cb0')} data-lw-spark>{LW_LABELS.spark}</span><span style={pill('#9b2c2c')} data-lw-growth>{LW_LABELS.growth}</span><span style={{...pill('#2f855a'),display:'none'}} data-lw-growth-nodes ref={hudGN}/><span style={{...pill('#2c7a7b'),display:'none'}} data-lw-home-growth ref={hudHome}/><span style={pill('#553c9a')} data-lw-model>{LW_LABELS.model}</span><span style={pill('#276749')} data-lw-biome ref={hudBiome}>Biome</span><span style={{...pill('#0e7490'),display:'none'}} data-lw-sea-seeded ref={hudSea}/><span style={{...pill('#0e7490'),display:'none'}} data-lw-visual-life ref={hudVL}/>{soundBtn}{provBlock}
   <p data-lw-growth-explainer ref={hudGNx} style={{display:'none',margin:'4px 2px 0',fontSize:11,lineHeight:1.35,color:'#d9ccff',maxWidth:300}}/></div></details>
  :<details data-lw-chips data-lw-chips-folded={spawned?'1':undefined} key={spawned?'fp':'orbit'} open={!spawned} style={{position:'absolute',top:'calc(env(safe-area-inset-top) + 10px)',left:10,right:10,pointerEvents:'none'}}><summary data-lw-chips-summary style={{pointerEvents:'auto',cursor:'pointer',display:spawned?'inline-block':'none',fontSize:12,padding:'4px 10px',borderRadius:999,background:'rgba(15,23,42,.7)',color:'#fff'}}>How this look is made</summary><div style={{display:'flex',flexWrap:'wrap',gap:6,marginTop:spawned?6:0}}><span style={pill('#4a5568')} data-lw-mood title='No mood source is connected, so the look stays neutral.'>Mood · ABSENT</span>
   {visit?<span style={pill('#0f766e')} data-lw-visit title="Terrain is re-generated by the same generators from a seed derived from the RECORDED run, plus this planet's own water and temperature. Nothing from the visit is saved.">Visiting {planetName(visit.id)} · SEEDED (not a measured surface)</span>:null}<span style={pill('#2b6cb0')} data-lw-spark>{LW_LABELS.spark}</span><span style={pill('#9b2c2c')} data-lw-growth>{LW_LABELS.growth}</span><span style={{...pill('#2f855a'),display:'none'}} data-lw-growth-nodes ref={hudGN}/><span style={{...pill('#2c7a7b'),display:'none'}} data-lw-home-growth ref={hudHome}/><span style={pill('#553c9a')} data-lw-model>{LW_LABELS.model}</span><span style={pill('#276749')} data-lw-biome ref={hudBiome}>Biome</span><span style={{...pill('#0e7490'),display:'none'}} data-lw-sea-seeded ref={hudSea}/><span style={{...pill('#0e7490'),display:'none'}} data-lw-visual-life ref={hudVL}/>{soundBtn}{provBlock}
  </div></details>}
  <div style={{position:'absolute',left:10,right:10,bottom:'calc(env(safe-area-inset-bottom) + 10px)',display:'flex',justifyContent:'space-between',alignItems:'flex-end',gap:8,pointerEvents:'none'}}>
   <div data-lw-card style={{background:'rgba(10,6,30,.72)',borderRadius:12,padding:'8px 10px',maxWidth:'62%',pointerEvents:'auto',display:embedded&&!spawned?'none':undefined}}>
    <b>{beastName||'Your beast'}</b> {genome||(typeof window!=='undefined'&&(window as any).__beastGenome)?'':'(No beast yet. Hatch one and it’ll appear.)'}<br/>
    <details data-lw-details style={{fontSize:12}}><summary style={{cursor:'pointer',opacity:.8}}>Details</summary>
    <span data-lw-build>{'Build '+(process.env.NEXT_PUBLIC_VERCEL_GIT_COMMIT_SHA||'local').slice(0,7)}</span> · Sun: one sun · SEEDED<br/>tick {hud.tick} · sim E {hud.simE??'—'} · life {hud.life} · storms {hud.storms} · grass {Math.round(hud.cover*100)}%<br/>
    {hud.learned?<>things awake {hud.awake??0} · learned {Object.entries(hud.learned).map(([k,v])=>k+' '+v).join(' · ')||'—'}<br/></>:null}
    {T?<>curious {T.curiosity.toFixed(2)} · social {T.sociality.toFixed(2)} · calm {T.calm.toFixed(2)} · joy {T.joy.toFixed(2)} · {T.experiences} experiences</>:null}
    <div><button type="button" data-lw-details-close aria-label="Close details" onClick={e=>{const d=e.currentTarget.closest('details');if(d)(d as HTMLDetailsElement).open=false;}} style={{marginTop:4,padding:'3px 10px',borderRadius:8,border:'1px solid rgba(190,170,255,.5)',background:'rgba(10,6,30,.6)',color:'#efeaff',font:'600 12px system-ui',cursor:'pointer'}}>Close details</button></div>
    </details>
    {err?<div style={{color:'#ffb4b4'}}>Couldn’t load the world: {err}</div>:null}
   </div>
   {(()=>{const toMenu=embedded&&!!menuHost&&!spawned;const actions=<div data-lw-actions data-lw-in-menu={toMenu?'':undefined} style={toMenu?{display:'grid',gridTemplateColumns:'1fr',gap:8}:embedded?{display:'flex',flexDirection:'row',flexWrap:'wrap',justifyContent:'flex-end',gap:5,pointerEvents:'auto',marginLeft:'auto',maxWidth:'100%'}:{display:'flex',flexDirection:'column',gap:6,pointerEvents:'auto'}}>
    {!spawned?<><button type="button" data-lw-beachcam aria-pressed={beachCam} onClick={()=>setBeachCam(v=>!v)} style={btn(beachCam?'#b7791f':'#333')}>{beachCam?'🏖 Beach view: on':'🏖 Beach view'}</button>{!embedded?<button type="button" data-lw-sealife onClick={()=>{const w:any=window;const n=seaJump.current++;const k=1+n%3,i=Math.floor(n/3);if(!w.__lw?.toOcean(i,k)){seaJump.current=0;w.__lw?.toOcean(0,k);}w.__lwSetZoom?.(0);}} style={btn('#1a6b8a')}>🐋 Sea life</button>:null}<button type="button" data-lw-spawn onClick={()=>setSpawned(true)} style={btn('#6b46c1')}>✦ Spawn in</button><button type="button" data-lw-watch onClick={()=>setWatch(w=>!w)} style={btn('#2c5282')}>{watch?'🌍 Orbit view':'👁 Watch your beast'}</button></>:<><button type="button" data-lw-roadster aria-pressed={roadster} onClick={()=>setRoadster(v=>!v)} style={btn(roadster?'#a3111b':'#333')}>{roadster?'🚗 '+ROADSTER_LABEL+': on':'🚗 '+ROADSTER_LABEL}</button><button type="button" data-lw-fly onClick={()=>setFlying(v=>!v)} style={btn(flying?'#2b6cb0':'#333')}>{flying?'🪽 Flying':'🪽 Fly'}</button>{roadster&&!rfUi?<button type="button" data-lw-liftoff onClick={()=>{rfRef.current.want=true;}} style={btn('#5b21b6')}>🚀 Lift off</button>:null}{rfUi?<button type="button" data-lw-land onClick={()=>{rfRef.current.assist=rfRef.current.assist==='land'?'':'land';}} style={btn('#0f766e')}>🛬 Land (assist)</button>:null}<button type="button" data-lw-exit onClick={()=>{if(roadster&&!rfUi){rfRef.current.assist='ascent';}else if(!rfUi)setSpawned(false);else rfRef.current.assist='ascent';}} style={btn('#444')}>{roadster?'🚀 Exit to orbit':'Exit to orbit'}</button></>}{!embedded||spawned?<button type="button" data-lw-ascii onClick={()=>setAscii(v=>!v)} style={btn(ascii?'#2f855a':'#333')}>{ascii?'▦ ASCII on':'▦ ASCII'}</button>:null}
    {embedded&&onExpand?<button type="button" data-lw-expand onClick={onExpand} style={btn('#553c9a')}>⤢ Full screen</button>:null}
    {onClose?<button type="button" data-lw-close onClick={onClose} style={btn('#222')}>Close world</button>:null}
   </div>;return toMenu?createPortal(actions,menuHost!):actions;})()}
  </div>
  <div data-lw-view-chips style={{position:'absolute',top:'calc(env(safe-area-inset-top) + 64px)',right:10,zIndex:3,display:'flex',flexDirection:'column',alignItems:'flex-end',gap:6,pointerEvents:'auto'}}>
   <button type="button" data-lw-view={viewMode} onClick={()=>{const m=nextViewMode(viewMode);writeViewMode(localStorage,m);setViewMode(m);window.dispatchEvent(new Event(VIEW_MODE_EVENT));}} style={{...btn('#2d2363'),fontSize:12,padding:'6px 10px'}}>{viewModeLabel(viewMode,beastName)}</button>
   {qTier?<button type="button" data-lw-quality={qTier} title="Post effects are a SEEDED look (Cosmo's p1post pack): a designed screen effect, not a measurement. Tap to change; remembered on this device." onClick={()=>{const t=nextTier(qTier);writeTierOverride(localStorage,t);setQTier(t);}} style={{...btn('#2d2363'),fontSize:12,padding:'6px 10px'}}>{qualityLabel(qTier)}</button>:null}
  </div>
  {spawned?<div data-lw-hand aria-hidden style={{position:'absolute',left:'calc(env(safe-area-inset-left) + 14px)',bottom:'calc(env(safe-area-inset-bottom) + 250px)',width:70,height:110,pointerEvents:'none',animation:'lwbob 1.1s ease-in-out infinite'}}>
   <style>{'@keyframes lwbob{0%,100%{transform:translateY(0) rotate(-8deg)}50%{transform:translateY(-7px) rotate(-4deg)}}'}</style>
   <img src="/universe/livingworld/asciimode/glow_sprite_torch_256.png" alt="" style={{position:'absolute',left:-25,top:-30,width:120,height:120,mixBlendMode:'screen'}}/>
   <div style={{position:'absolute',left:28,top:26,width:12,height:58,borderRadius:4,background:'linear-gradient(#7a4a24,#4a2a12)'}}/><div style={{position:'absolute',left:22,top:66,width:30,height:30,borderRadius:'40% 40% 46% 46%',background:'#c99a7a',boxShadow:'0 0 18px rgba(255,190,110,.6)'}}/></div>:null}
  {line?<><style>{embedded?'':'@media (max-width:640px){[data-lw-line]{--lw-line-top:calc(env(safe-area-inset-top) + 136px)}}'}</style><div data-lw-line style={{position:'absolute',left:'50%',top:'var(--lw-line-top, calc(env(safe-area-inset-top) + 70px))',transform:'translateX(-50%)',background:'rgba(20,10,50,.82)',borderRadius:12,padding:'8px 14px',fontSize:15,maxWidth:'86%',textAlign:'center',pointerEvents:'none'}}>{line}</div></>:null}
  {spawned&&rfUi?<><details data-lw-flight-help style={{position:'absolute',left:'calc(env(safe-area-inset-left) + 10px)',top:'calc(env(safe-area-inset-top) + 120px)',pointerEvents:'auto',padding:'4px 8px',borderRadius:8,background:'rgba(8,4,24,.72)',color:'#cfe',font:'12px/1.3 system-ui'}}><summary style={{cursor:'pointer'}}>Flight keys</summary>Space = thrust · W/S = nose<br/>A/D = turn · B = brake · L = land</details>
   <div ref={hudRef} data-lw-flight-hud aria-live="off" style={{position:'absolute',left:'50%',transform:'translateX(-50%)',bottom:'calc(env(safe-area-inset-bottom) + 258px)',maxWidth:'92%',padding:'5px 10px',borderRadius:10,background:'rgba(8,4,24,.72)',color:'#cfe',font:'12px/1.3 ui-monospace,monospace',textAlign:'center',pointerEvents:'none'}}>{FLIGHT_LABEL}</div>
   <button type="button" data-lw-thrust onPointerDown={e=>{(e.currentTarget as any).setPointerCapture?.(e.pointerId);rfRef.current.thrust=true;}} onPointerUp={()=>{rfRef.current.thrust=false;}} onPointerCancel={()=>{rfRef.current.thrust=false;}} style={{position:'absolute',right:'calc(env(safe-area-inset-right) + 14px)',bottom:'calc(env(safe-area-inset-bottom) + 130px)',width:88,height:88,borderRadius:'50%',border:'2px solid rgba(180,140,255,.8)',background:'rgba(110,60,220,.55)',color:'#fff',fontWeight:700,fontSize:14,touchAction:'none'}}>🔥 Thrust</button>
   <button type="button" data-lw-brake onPointerDown={e=>{(e.currentTarget as any).setPointerCapture?.(e.pointerId);rfRef.current.brake=true;}} onPointerUp={()=>{rfRef.current.brake=false;}} onPointerCancel={()=>{rfRef.current.brake=false;}} style={{position:'absolute',left:'calc(env(safe-area-inset-left) + 14px)',bottom:'calc(env(safe-area-inset-bottom) + 140px)',width:70,height:70,borderRadius:'50%',border:'2px solid rgba(255,255,255,.35)',background:'rgba(255,255,255,.1)',color:'#fff',fontWeight:700,fontSize:13,touchAction:'none'}}>Brake</button>
  </>:null}
  {spawned?<div data-lw-joystick onPointerDown={jd} onPointerMove={jm} onPointerUp={ju} onPointerCancel={ju}
   style={{position:'absolute',left:'calc(50% - 60px)',bottom:'calc(env(safe-area-inset-bottom) + 120px)',width:120,height:120,borderRadius:'50%',background:'rgba(255,255,255,.08)',border:'2px solid rgba(255,255,255,.25)',touchAction:'none'}}>
   <div style={{position:'absolute',left:60-22+(stick?.x||0)*38,top:60-22+(stick?.y||0)*38,width:44,height:44,borderRadius:'50%',background:'rgba(200,180,255,.55)'}}/>
  </div>:null}
 </div>;
}
const pill=(c:string)=>({background:c,borderRadius:999,padding:'3px 8px',fontSize:11,opacity:.92}) as const;
const btn=(c:string)=>({background:c,color:'#fff',border:0,borderRadius:10,padding:'10px 14px',fontSize:14,fontWeight:600}) as const;
// (embedded worlds shrink the buttons via the [data-lw-embedded] rule in globals.css)
