'use client';
// Zoomable, rotatable 3D Tiny Universe (Cosmo's visual audit, Oct 23 2026). Renders ONLY tiny-universe/v1 engine data:
// stars, planets, storms, life and black-hole remnants come from the grown universe; nothing is invented: storms the growth has not produced yet are added as SEEDED (lib/universe/seeded-storms.mjs), labelled as such.
// Log zoom: surface -> planet -> neighbours -> universe. Drag rotates, wheel/pinch zooms, tap a world to fly to it.
// Art: Cosmo's deepspace sheets (accretion disk + photon ring on real black-hole remnants, storm clouds on real storms).
// Seeded only (string hash LCG from the universe seed); no Math.random.
import {isPanGesture,panStep,decayPan,centroid,keyPanPixels,worldPerPixel} from '@/lib/universe/view-gestures.mjs';
import {allStorms} from '@/lib/universe/seeded-storms.mjs';
import {seededBlackHoles,seededInfall,BH_LABEL} from '@/lib/universe/seeded-black-holes.mjs';
import {useEffect,useRef,useState} from 'react';
import * as THREE from 'three';
import {isSoftwareGL} from '@/lib/three/soft-gl';
import {homeOf,biomeOf} from '@/lib/universe/tiny-universe-view.mjs';
import {doorProgress,doorPreload,doorZoomStep,DOOR_NEAR} from '@/lib/universe/door.mjs';
import {blackBodyToRGB,sunIntensity,initSystem,advanceTo,orbitR as gOrbitR} from '@/lib/universe/genesis-sun.mjs';
import {starTexture,glowTexture,coronaMesh,atmosphereMesh,nightGlowOnly} from '@/lib/universe/genesis-sun-three';
import {createPlanetKit} from '@/lib/universe/planet-body-three';
import {pickType,variantFor,sunExposure,glowSet} from '@/lib/universe/planet-types.mjs';
import PLANET_VARIANTS from '@/lib/universe/planet-variants.json';
import {seedMoons,moonOffset,pickOccluder} from '@/lib/universe/moons.mjs';
import {SPRITE_TINT} from '@/lib/universe/planet-types.mjs';
import {threadFade,threadBrightness,creatureHome,threadBend} from '@/lib/universe/alive-props.mjs';
// One Mind, Refracted (Cosmo's concept 09): faint threads from one origin to every creature (brightness = how recently its
// own loop really ticked, /api/cosmos/activity) and dimmer ones to stars, planets and storms. Only at full zoom-out; hideable.
const THREADS_KEY='beastbox.oneMindThreads.v1';const SEG=24;
/* eslint-disable @typescript-eslint/no-explicit-any */
// E5a (Cosmo): planets wear their biome's own colour + glow maps (public/universe/livingworld/biomes); the flat colour stays as the tint/fallback.
const BIOME_MAP:Record<string,string>={ember:'ember_world',paper:'paper_sea',jelly:'jelly_geyser',sunflower:'sunflower_ring',moss:'crystal_moss',glacier:'glacier'};
const BIOME_HEX:Record<string,number>={ember:0xff7a2a,paper:0xe9d9b0,jelly:0x8fa8ff,sunflower:0xffd24a,moss:0x8fd06a,glacier:0xdff2ff};
function rand(seed:string){let h=0;for(const c of seed)h=(h*31+c.charCodeAt(0))>>>0;return()=>{h=(h*1664525+1013904223)>>>0;return h/2**32;};}
import {zoomLineKind,doorLineKind,zoomLine,noticeLine,noticeGate} from '@/lib/universe/zoom-lines.mjs';
import {growthNodesAt,growthHomeWorld} from '@/lib/universe/seeded-growth-nodes.mjs';
import {growthZoomLine,planetWords} from '@/lib/universe/growth-copy.mjs';
import {seededLandscapes,landscapeMode,landscapeZoom} from '@/lib/universe/seeded-landscapes.mjs';
/** Emeth zoom_growth line for the home world, derived from the SEEDED nodes' SIMULATED state (null when there are none). */
// Landscape zoom line: "{place} · {kind}" plus the mode line from landscapeMode. This view has no live insolation, so it never reads night; but a storm on the landscape's own planet is a real (seeded) signal here, so a stormy planet shows the shelter line. hasLife comes from the engine's life[]; the living world shows the full live mode. `n` rotates the seeded pick per zoom-in.
const landscapeLineFor=(u:any,n=0):string|null=>{try{const ls=seededLandscapes(u).find((l:any)=>l.home_exception)||seededLandscapes(u)[0];if(!ls)return null;const m=landscapeMode(ls,{ins:1,storm:allStorms(u).some((q:any)=>q.planet===ls.planet)?1:0,hasLife:(u.life||[]).some((l:any)=>l.planet===ls.planet)});const z=landscapeZoom(ls,m,{beast:'Your beast',seed:String(u.seed||'tiny'),n});return z.line?z.title+'. '+z.line:z.title;}catch{return null;}};
const growthLineFor=(u:any):string|null=>{try{if(!u?.planets?.length)return null;const home=growthHomeWorld(u);const nodes=growthNodesAt(u,u.tick).filter((n:any)=>n.planet===home);return nodes.length?growthZoomLine(nodes,planetWords(home,home),String(u.seed||'tiny'),Math.floor((u.tick||0)/20)):null;}catch{return null;}};
export const ZOOM_MIN=1.2,ZOOM_MAX=1400;
/* Zoom-out has no hard stop any more: ZOOM_MAX is the old comfortable range, ZOOM_LIMIT is only a float32-precision guard (10,000x beyond it).
   Past ZOOM_MAX the far plane and the background star shell grow with the camera distance, so nothing is cut or clipped. */
export const ZOOM_LIMIT=1e7;
export function zoomStage(d:number){return d<6?'Surface':d<16?'Planet':d<40?'Orbit':d<120?'System':d<500?'Neighbours':'Universe';}
const SPAN=420;
export function starPos(st:any){const r=rand(st.id);return new THREE.Vector3((st.x-0.5)*SPAN,(r()-0.5)*SPAN*0.18,(st.y-0.5)*SPAN);}
export default function Universe3D({u,beast,onSelect,onAlive,doorOn=false,onDoor}:{u:any;beast?:string|null;onSelect?:(id:string|null)=>void;onAlive?:(kind:'zoom_planet'|'zoom_star'|'threads_visible')=>void;doorOn?:boolean;onDoor?:(v:number,preload:boolean)=>void}){
 const doorOnRef=useRef(doorOn);doorOnRef.current=doorOn;const onDoorRef=useRef(onDoor);onDoorRef.current=onDoor;
 const aliveRef=useRef(onAlive);aliveRef.current=onAlive;
 const [threadsOn,setThreadsOn]=useState(true);const threadsRef=useRef(true);threadsRef.current=threadsOn;const [threadsShown,setThreadsShown]=useState(false);const [activityNote,setActivityNote]=useState('');
 useEffect(()=>{try{if(localStorage.getItem(THREADS_KEY)==='0')setThreadsOn(false);}catch{}},[]);
 const toggleThreads=()=>setThreadsOn(v=>{const n=!v;try{localStorage.setItem(THREADS_KEY,n?'1':'0');}catch{}return n;});
 const activity=useRef<any[]>([]);
 useEffect(()=>{let dead=false;const load=()=>fetch('/api/cosmos/activity',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(j=>{if(dead||!j?.creatures)return;activity.current=j.creatures;const n=j.creatures.length;setActivityNote(n?`${n} creature${n===1?'':'s'} · brightness = how recently its own loop ticked`:'no creature loop activity reported');}).catch(()=>{if(!dead)setActivityNote('loop activity unavailable · threads drawn at the faint floor');});load();const iv=setInterval(load,300000);return()=>{dead=true;clearInterval(iv);};},[]);
 const host=useRef<HTMLDivElement>(null);const uRef=useRef(u);uRef.current=u;const sel=useRef(onSelect);sel.current=onSelect;
 const [zline,setZline]=useState<{text:string;key:string;n:number}|null>(null);const zlineN=useRef(0);const zlineT=useRef(0);
 const showZLine=(kind:'zoom_out'|'zoom_in',key:string|null,override?:string|null)=>{if(!key)return;const text=override||zoomLine(kind,key,String(uRef.current?.seed||'tiny'),zlineN.current);if(!text)return;zlineN.current++;setZline({text,key,n:zlineN.current});window.clearTimeout(zlineT.current);zlineT.current=window.setTimeout(()=>setZline(null),5200);};
 const beastRef=useRef(beast);beastRef.current=beast;const nGate=useRef<any>(null),nN=useRef(0),nT=useRef(0);const [notice,setNotice]=useState<{text:string;key:string;n:number}|null>(null);
 /* Emeth's creature_notices, text verbatim; {beast} = the active beast's name. One at a time, with a quiet gap (noticeGate). */
 const showNotice=(key:string,gapMs?:number)=>{const g=noticeGate(nGate.current,key,performance.now(),gapMs);nGate.current=g.state;if(!g.show)return;const text=noticeLine(key,beastRef.current||'Your beast',String(uRef.current?.seed||'tiny'),nN.current);if(!text)return;nN.current++;setNotice({text,key,n:nN.current});window.clearTimeout(nT.current);nT.current=window.setTimeout(()=>setNotice(null),6000);};
 const [stage,setStage]=useState('Planet');const api=useRef<{zoom:(f:number)=>void;home:()=>void}|null>(null);
 useEffect(()=>{const el=host.current;if(!el)return;
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false});renderer.setPixelRatio(Math.min(2,devicePixelRatio||1));el.appendChild(renderer.domElement);
  renderer.domElement.style.cssText='display:block;width:100%;height:100%;touch-action:none;cursor:grab';
  const scene=new THREE.Scene();scene.background=new THREE.Color(0x05030f);
  const cam=new THREE.PerspectiveCamera(55,1,0.05,6000);
  scene.add(new THREE.AmbientLight(0x8877bb,0.22)); // dim fill: the star is the light now, so night sides really go dark
  // E5b (Cosmo): screen-space gravitational lensing around a real black-hole remnant. Port of deepspace/lensing.glsl (art approximation,
  // not GR). WebGL1-safe; skipped on CPU-rendered WebGL, and any shader error turns it off for good so the plain render stays.
  let lensOn=!isSoftwareGL()||/[?&]lens=1/.test(location.search);const prevErr=renderer.debug.onShaderError;renderer.debug.onShaderError=(...a:any[])=>{lensOn=false;(prevErr as any)?.(...a);};
  const rt=new THREE.WebGLRenderTarget(2,2);const lensCam=new THREE.OrthographicCamera(-1,1,1,-1,0,1);const lensScene=new THREE.Scene();
  const lensMat=new THREE.ShaderMaterial({uniforms:{tScene:{value:rt.texture},bhScreen:{value:new THREE.Vector2(.5,.5)},rs:{value:0},aspect:{value:1},strength:{value:1}},depthTest:false,depthWrite:false,
   vertexShader:'varying vec2 vUv;void main(){vUv=uv;gl_Position=vec4(position.xy,0.,1.);}',
   fragmentShader:`uniform sampler2D tScene;uniform vec2 bhScreen;uniform float rs,aspect,strength;varying vec2 vUv;
void main(){vec2 d=vUv-bhScreen;d.x*=aspect;float r=length(d);float bend=strength*rs*rs/max(r,rs*0.5);vec2 dir=d/max(r,1e-5);vec2 s=d-dir*bend;s.x/=aspect;
vec3 c=texture2D(tScene,bhScreen+s).rgb;float ring=exp(-pow((r-1.5*rs)/(0.08*rs+1e-5),2.0));c+=ring*vec3(1.0,0.85,1.0)*0.6*strength;c*=mix(1.0,smoothstep(rs*0.98,rs*1.02,r),step(1e-4,rs));gl_FragColor=vec4(c,1.0);
#include <colorspace_fragment>
}`});
  lensScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2,2),lensMat));const bhV=new THREE.Vector3(),bhC=new THREE.Vector3();
  let seededBH:THREE.Group|null=null;let bhNear=false,bhFar=false;const renderLensed=()=>{let best:THREE.Object3D|null=null,bd=1e9;for(const g of [...starObj.values(),...(seededBH?[seededBH]:[])]){if(!g.userData.bh)continue;g.getWorldPosition(bhV);const dd=bhV.distanceTo(cam.position);if(dd<bd){bd=dd;best=g;}}
   if(!lensOn||!best){renderer.render(scene,cam);return;}
   best.getWorldPosition(bhC);const p=bhC.clone().project(cam);const on=p.z<1&&Math.abs(p.x)<1.3&&Math.abs(p.y)<1.3;if(!on){renderer.render(scene,cam);return;}
   const sz=renderer.getDrawingBufferSize(new THREE.Vector2());if(rt.width!==sz.x||rt.height!==sz.y)rt.setSize(sz.x,sz.y);
   const rsS=((best!.userData.bhR||2.2)/Math.max(.01,bd))/Math.tan(cam.fov*Math.PI/360)*0.5;lensMat.uniforms.bhScreen.value.set((p.x+1)/2,(p.y+1)/2);lensMat.uniforms.rs.value=Math.min(.25,rsS);
   lensMat.uniforms.aspect.value=cam.aspect;lensMat.uniforms.strength.value=Math.min(1,Math.max(0,(1.3-Math.max(Math.abs(p.x),Math.abs(p.y)))/0.3));
   renderer.setRenderTarget(rt);renderer.render(scene,cam);renderer.setRenderTarget(null);renderer.render(lensScene,lensCam);};

  const tl=new THREE.TextureLoader();const tex=(n:string)=>{const t=tl.load('/universe/deepspace/'+n);t.colorSpace=THREE.SRGBColorSpace;return t;};
  /* storm art has a square edge: multiply it by a radial fade (canvas, destination-in) so only the swirl shows */
  const roundTex=(n:string)=>{const t=new THREE.Texture();t.colorSpace=THREE.SRGBColorSpace;const img=new Image();img.onload=()=>{const c=document.createElement('canvas');c.width=c.height=512;const g=c.getContext('2d')!;g.drawImage(img,0,0,512,512);g.globalCompositeOperation='destination-in';const gr=g.createRadialGradient(256,256,0,256,256,256);gr.addColorStop(0,'rgba(0,0,0,1)');gr.addColorStop(.55,'rgba(0,0,0,.85)');gr.addColorStop(.92,'rgba(0,0,0,0)');g.fillStyle=gr;g.fillRect(0,0,512,512);t.image=c;t.needsUpdate=true;};img.src='/universe/deepspace/'+n;return t;};
  // seeded background stars (the shell follows the camera and scales with its distance, so zoom-out never leaves it behind)
  let bgStars:THREE.Points|null=null;
  {const r=rand(String(uRef.current?.seed||'tiny'));const n=1800,p=new Float32Array(n*3);for(let i=0;i<n;i++){const th=r()*Math.PI*2,ph=Math.acos(2*r()-1),R=2500+r()*800;p[i*3]=R*Math.sin(ph)*Math.cos(th);p[i*3+1]=R*Math.cos(ph);p[i*3+2]=R*Math.sin(ph)*Math.sin(th);}
   const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(p,3));bgStars=new THREE.Points(g,new THREE.PointsMaterial({color:0xffffff,size:2.2,sizeAttenuation:false,transparent:true,opacity:.75}));scene.add(bgStars);}
  const world=new THREE.Group();scene.add(world);
  const MAXT=160;const tPos=new Float32Array(MAXT*SEG*2*3),tCol=new Float32Array(MAXT*SEG*2*3);const tGeo=new THREE.BufferGeometry();
  tGeo.setAttribute('position',new THREE.BufferAttribute(tPos,3));tGeo.setAttribute('color',new THREE.BufferAttribute(tCol,3));tGeo.setDrawRange(0,0);
  const tMat=new THREE.LineBasicMaterial({vertexColors:true,transparent:true,opacity:0,blending:THREE.AdditiveBlending,depthWrite:false});
  const threads=new THREE.LineSegments(tGeo,tMat);threads.frustumCulled=false;threads.visible=false;scene.add(threads);
  const origin=new THREE.Sprite(new THREE.SpriteMaterial({map:glowTexture(),color:0xd8c8ff,blending:THREE.AdditiveBlending,depthWrite:false,transparent:true,opacity:0}));origin.scale.setScalar(26);origin.visible=false;scene.add(origin);
  const hc=new THREE.Color(),ctl=new THREE.Vector3(),pa=new THREE.Vector3(),pb=new THREE.Vector3(),O=new THREE.Vector3(0,0,0);
  let wasShown=false;
  function drawThreads(fade:number){const U=uRef.current;if(!U)return 0;const seed=String(U.seed||'tiny');let k=0;const now=Date.now();
   const add=(id:string,to:THREE.Vector3,b:number,dim:boolean)=>{if(k>=MAXT)return;const bend=threadBend(seed,id);const L=to.length();ctl.copy(to).multiplyScalar(.5).add(new THREE.Vector3(bend[0]*L,bend[1]*L,bend[2]*L));
    const hue0=(bend[0]+.5)*.6;
    for(let i=0;i<SEG;i++){const t0=i/SEG,t1=(i+1)/SEG;for(const [t,dst] of [[t0,pa],[t1,pb]] as [number,THREE.Vector3][]){const a=(1-t)*(1-t),bq=2*(1-t)*t,c=t*t;dst.set(a*O.x+bq*ctl.x+c*to.x,a*O.y+bq*ctl.y+c*to.y,a*O.z+bq*ctl.z+c*to.z);}
     const o=(k*SEG+i)*6;tPos[o]=pa.x;tPos[o+1]=pa.y;tPos[o+2]=pa.z;tPos[o+3]=pb.x;tPos[o+4]=pb.y;tPos[o+5]=pb.z;
     // refracted: white at the origin, splitting into colour along the thread
     const lum=(dim?.22:.9)*b;for(const [j,t] of [[0,t0],[3,t1]] as [number,number][]){hc.setHSL((hue0+t*.75)%1,Math.min(1,t*1.6),.5+.4*(1-t));tCol[o+j]=hc.r*lum;tCol[o+j+1]=hc.g*lum;tCol[o+j+2]=hc.b*lum;}}
    k++;};
   const home=homeOf(U);
   for(const c of activity.current){const pid=c.id==='zeref'?home:creatureHome(seed,c.id,U.planets);const m=pid?planetMesh.get(pid):null;if(m)add('c:'+c.id,m.position,threadBrightness(c,now).b,false);}
   for(const [id,g] of starObj)add('s:'+id,g.position,1,true);
   for(const [id,m] of planetMesh)add('p:'+id,m.position,1,true);
   for(const [id,sp] of stormObj)add('w:'+id,sp.position,1,true);
   tGeo.setDrawRange(0,k*SEG*2);tGeo.attributes.position.needsUpdate=true;tGeo.attributes.color.needsUpdate=true;tMat.opacity=.55*fade;origin.material.opacity=.5*fade;return k;}
  const legacyPlanets=typeof location!=='undefined'&&/[?&]planets=biome/.test(location.search);const planetKit=createPlanetKit();
  const moonsOf=new Map<string,{m:any;mesh:any;body:any}[]>();let moonsBuilt=false;const mv=new THREE.Vector3(),mc=new THREE.Vector3();
  const planetMesh=new Map<string,THREE.Mesh>();const starObj=new Map<string,THREE.Object3D>();const stormObj=new Map<string,THREE.Sprite>();
  const _sv=new THREE.Vector3();const sphere=new THREE.SphereGeometry(1,32,20);
  const diskTex=tex('accretion_disk_1024.png'),ringTex=tex('photon_ring_512.png'),stormTex=[roundTex('storm_cloud_violet_1024.png'),roundTex('storm_cloud_teal_1024.png')];
  // E5c (Cosmo deepspace art): a wormhole ring and an asteroid belt are ART placed from the real star layout (seeded, no Math.random);
  // storms get seeded lightning flashes. GLBs load lazily after the first frame so the universe opens fast.
  let decoDone=false;const boltTex=tex('lightning_4x2_256.png');boltTex.repeat.set(1/4,1/2);const bolts=new Map<string,THREE.Sprite>();let mixer:THREE.AnimationMixer|null=null;const belt:THREE.Object3D[]=[];
  function addDeco(){const U=uRef.current;if(decoDone||!U||!U.stars?.length)return;decoDone=true;const seed=String(U.seed||'tiny');const r=rand(seed+':deepspace');
   const hp=U.planets.find((p:any)=>p.id===homeOf(U));const hs=hp?starObj.get(hp.star):[...starObj.values()][0];if(!hs)return;
   let far:THREE.Object3D|null=null,fd=-1;for(const g of starObj.values()){const d=g.position.distanceTo(hs.position)+(g.userData.bh?1e6:0);if(g!==hs&&d>fd){fd=d;far=g;}}
   const outer=Math.max(8,...U.planets.filter((p:any)=>p.star===hp?.star).map((p:any)=>orbitR(p)))+6;
   import('three/examples/jsm/loaders/GLTFLoader.js').then(({GLTFLoader})=>{const L=new GLTFLoader();
    L.load('/universe/deepspace/models/wormhole_ring.glb',gl=>{const o=gl.scene;o.scale.setScalar(0.2);o.rotation.x=Math.PI/2;o.userData.art='wormhole';
     if(far)o.position.copy(hs.position).lerp(far.position,0.5);else o.position.copy(hs.position).add(new THREE.Vector3(outer*2,0,0));o.position.y+=6;world.add(o);
     if(gl.animations[0]){mixer=new THREE.AnimationMixer(o);mixer.clipAction(gl.animations[0]).play();}});
    for(const k of ['a','b','c'])L.load(`/universe/deepspace/models/asteroid_${k}_far.glb`,gl=>{let mesh:any=null;gl.scene.traverse((c:any)=>{if(!mesh&&c.isMesh)mesh=c;});if(!mesh)return;
     const n=40,im=new THREE.InstancedMesh(mesh.geometry,mesh.material,n),M=new THREE.Matrix4(),q=new THREE.Quaternion(),e=new THREE.Euler();
     for(let i=0;i<n;i++){const a=r()*Math.PI*2,R=outer+(r()-0.5)*4,sc=0.012+r()*0.035;e.set(r()*6.28,r()*6.28,r()*6.28);q.setFromEuler(e);
      M.compose(new THREE.Vector3(Math.cos(a)*R,(r()-0.5)*1.2,Math.sin(a)*R),q,new THREE.Vector3(sc,sc,sc));im.setMatrixAt(i,M);}
     const g=new THREE.Group();g.position.copy(hs.position);g.add(im);g.userData.spin=0.01+r()*0.02;world.add(g);belt.push(g);});
   }).catch(()=>{});}
  let lastT=0;function lightning(t:number){const U=uRef.current;const live=new Set<string>();
   for(const sm of (U?allStorms(U):[])){const sp=stormObj.get(sm.planet);if(!sp)continue;live.add(sm.planet);let b=bolts.get(sm.planet);
    if(!b){const tx=boltTex.clone();tx.needsUpdate=true;b=new THREE.Sprite(new THREE.SpriteMaterial({map:tx,blending:THREE.AdditiveBlending,depthWrite:false,transparent:true}));world.add(b);bolts.set(sm.planet,b);}
    const bucket=Math.floor(t/1.6),ph=t/1.6-bucket,rr=rand(sm.planet+':bolt:'+bucket);const fire=rr()<0.35+0.4*Math.min(1,sm.intensity/0.5);const f=Math.floor(ph*1.6*24);
    b.visible=fire&&f<8;if(b.visible){const m=b.material.map!;m.offset.set((f%4)/4,1-(Math.floor(f/4)+1)/2);b.position.copy(sp.position).add(new THREE.Vector3((rr()-0.5)*sp.scale.x*.6,(rr()-0.3)*sp.scale.x*.4,(rr()-0.5)*sp.scale.x*.6));b.scale.setScalar(sp.scale.x*.7);}}
   for(const[k,b]of bolts)if(!live.has(k)){world.remove(b);bolts.delete(k);}
   const dt=Math.max(0,Math.min(.1,t-lastT));lastT=t;mixer?.update(dt);for(const g of belt)g.rotation.y=t*g.userData.spin;}
  const bioCache=new Map<string,THREE.Texture>();const bioLoader=new THREE.TextureLoader();let csT:THREE.Texture|null=null,ccT:THREE.Texture|null=null;const cleanSunTex=()=>{if(!csT){csT=bioLoader.load('/universe/planets/handoff/sun_clean/sun_clean_sprite_add_1024.png');csT.colorSpace=THREE.SRGBColorSpace;csT.anisotropy=4;}return csT!;};const cleanCoronaTex=()=>{if(!ccT){ccT=bioLoader.load('/universe/planets/handoff/sun_clean/sun_clean_corona_add_4x4_256.png');ccT.colorSpace=THREE.SRGBColorSpace;}return ccT!;};let coronaT:THREE.Texture|null=null;const coronaTex=()=>{if(!coronaT){coronaT=bioLoader.load('/universe/livingworld/landforms/sky/sun_corona_512.png');coronaT.colorSpace=THREE.SRGBColorSpace;}return coronaT;};
  const biomeTex=(k:string,kind:'color'|'glow')=>{const key=k+'_'+kind;let t=bioCache.get(key);if(!t){t=bioLoader.load('/universe/livingworld/biomes/'+key+'.webp');if(kind==='color')t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=4;bioCache.set(key,t);}return t;};
  /* SEEDED black hole (Cory's a.html physics; the recording has none): black sphere, his orange->violet noise accretion disk (RingGeometry 1.2R..3R),
     photon ring, orbiting infall on Kepler orbits (w = sqrt(GM/r^3)), and the same screen-space lensing as real remnants. */
  const buildSeededBH=(sb:any,U:any)=>{const R=sb.radius,g=new THREE.Group();g.position.set(sb.x,sb.y,sb.z);g.userData.bh=true;g.userData.bhR=R;g.userData.seeded=true;g.name='seeded-black-hole';
   g.add(new THREE.Mesh(new THREE.SphereGeometry(R,48,24),new THREE.MeshBasicMaterial({color:0x000000})));
   const pivot=new THREE.Group();pivot.rotation.x=sb.tilt;pivot.name='bh-pivot';g.add(pivot);
   const dm=new THREE.ShaderMaterial({uniforms:{time:{value:0}},vertexShader:'varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
    fragmentShader:'uniform float time;varying vec2 vUv;float noise(vec2 p){return fract(sin(dot(p,vec2(12.9898,78.233)))*43758.5453);}void main(){float radius=length(vUv-0.5);float n=noise(floor(vUv*60.0)/60.0*5.0+time*0.2);vec3 color=mix(vec3(1.0,0.5,0.1),vec3(0.8,0.1,1.0),radius*2.0);gl_FragColor=vec4(color*(0.35+0.65*n),1.0)*clamp(1.0-radius*1.8,0.0,1.0);}',side:THREE.DoubleSide,transparent:true,blending:THREE.AdditiveBlending,depthWrite:false});
   const disk=new THREE.Mesh(new THREE.RingGeometry(R*sb.diskInner,R*sb.diskOuter,128),dm);disk.rotation.x=-Math.PI/2;disk.name='bh-disk';pivot.add(disk);
   const ring=new THREE.Sprite(new THREE.SpriteMaterial({map:ringTex,blending:THREE.AdditiveBlending,depthWrite:false,transparent:true}));ring.scale.setScalar(R*3.3);g.add(ring);
   const inf=seededInfall(sb,String(U.seed||'tiny'),160);const pos=new Float32Array(inf.length*3),col=new Float32Array(inf.length*3);inf.forEach((q,i)=>{const c=new THREE.Color().setRGB(1,0.5-0.4*q.hot,0.1+0.8*q.hot);col.set([c.r,c.g,c.b],i*3);});
   const pg=new THREE.BufferGeometry();pg.setAttribute('position',new THREE.BufferAttribute(pos,3));pg.setAttribute('color',new THREE.BufferAttribute(col,3));
   const pts=new THREE.Points(pg,new THREE.PointsMaterial({size:R*0.12,vertexColors:true,transparent:true,opacity:.9,blending:THREE.AdditiveBlending,depthWrite:false,sizeAttenuation:true}));pts.name='bh-infall';pts.userData.inf=inf;pivot.add(pts);
   return g;};
  const updateSeededBH=(t:number)=>{if(!seededBH)return;const pv=seededBH.getObjectByName('bh-pivot') as THREE.Group;const dm=(pv.getObjectByName('bh-disk') as THREE.Mesh).material as THREE.ShaderMaterial;dm.uniforms.time.value=t;
   const pts=pv.getObjectByName('bh-infall') as THREE.Points;const inf=pts.userData.inf as any[];const a=(pts.geometry.attributes.position as THREE.BufferAttribute);inf.forEach((q,i)=>{const th=q.a0+q.w*t;a.setXYZ(i,Math.cos(th)*q.r,q.h,Math.sin(th)*q.r);});a.needsUpdate=true;};
  function build(){const U=uRef.current;if(!U)return;
   if(!seededBH){const sb=seededBlackHoles(U)[0];if(sb){seededBH=buildSeededBH(sb,U);seededBH.userData.id=sb.id;world.add(seededBH);starObj.set(sb.id,seededBH);(window as any).__u3dFocus=(id:string)=>{if(starObj.has(id)){targetId=id;goal=Math.log(id.startsWith('seeded-bh-')?45:14);pinned=false;}};(el as any).dataset.seededBh=BH_LABEL;const lb=document.createElement('div');lb.setAttribute('data-bh-label','');lb.textContent='Black hole · '+BH_LABEL+' (the recording has none; Cory’s a.html physics)';lb.style.cssText='font-size:11px;color:#ffd9b0;background:rgba(12,8,32,.62);border:1px solid #ff9a4d66;border-radius:10px;padding:3px 8px;max-width:100%;pointer-events:none';(el!.querySelector('[data-u3d-stack]')||el!).appendChild(lb);}}
   for(const st of U.stars){if(starObj.has(st.id))continue;const g=new THREE.Group();g.position.copy(starPos(st));
    if(st.remnant==='black_hole'){g.userData.bh=true;g.add(new THREE.Mesh(new THREE.SphereGeometry(2.2,32,16),new THREE.MeshBasicMaterial({color:0x000000})));
     const disk=new THREE.Mesh(new THREE.PlaneGeometry(16,16),new THREE.MeshBasicMaterial({map:diskTex,transparent:true,blending:THREE.AdditiveBlending,depthWrite:false,side:THREE.DoubleSide}));disk.rotation.x=-Math.PI/2+0.25;disk.name='disk';g.add(disk);
     const ring=new THREE.Sprite(new THREE.SpriteMaterial({map:ringTex,blending:THREE.AdditiveBlending,depthWrite:false,transparent:true}));ring.scale.setScalar(7.2);g.add(ring);}
    else{const rr=1.2+0.9*Math.log10(1+st.mass_solar*3);const sc=new THREE.Color(...blackBodyToRGB(st.temperature_k));g.userData.sunColor=sc;g.userData.star=st;/* no black occluder sphere: it poked in front of the sprite plane off-axis and drew a hard black blob on the disc. The clean sprite is depth-tested, so nearer planets still cover it *//* the old hash-noise corona shell read as a grainy grey ring: Cosmo's corona billboard + soft glow (below) replace it */
     {const sp=new THREE.Sprite(new THREE.SpriteMaterial({map:cleanSunTex(),color:new THREE.Color(sc.r/1.0,sc.g/0.86,sc.b/0.58).multiplyScalar(0.9),blending:THREE.AdditiveBlending,depthWrite:false,transparent:true}));sp.scale.setScalar(rr*2*4);sp.name='sun-clean-sprite';g.add(sp);
      const ct=bioLoader.load('/universe/planets/handoff/sun_clean/sun_clean_corona_add_4x4_256.png');ct.colorSpace=THREE.SRGBColorSpace;ct.repeat.set(.25,.25);const cs=new THREE.Sprite(new THREE.SpriteMaterial({map:ct,color:sp.material.color,blending:THREE.AdditiveBlending,depthWrite:false,transparent:true}));cs.scale.setScalar(rr*2*4);cs.name='sun-corona-sprite';cs.userData.frames=ct;g.add(cs);} // Cosmo's sun_clean (additive twin, premultiplied-alpha fix): disc + halo, then a 16-frame looping corona
     const L=new THREE.PointLight(sc,sunIntensity(st.luminosity),0,2);g.add(L);}/* inverse-square, like the pens' PointLight(color,2,20000,2) */
    g.userData.id=st.id;world.add(g);starObj.set(st.id,g);}
   for(const pl of U.planets){if(planetMesh.has(pl.id))continue;
    if(!legacyPlanets){ // the pocket globe's material on every planet (Cosmo's pack): displaced terrain, ocean depth/foam, clouds, atmosphere
     const type=pickType(pl),pv:any=(PLANET_VARIANTS as any)[pl.id],vr=pv?{lonDeg:pv[0],tiltDeg:pv[1],spinDegPerS:pv[2],cloudLonDeg:pv[3]}:variantFor(pl.id,rand);
     const body=planetKit.create(type,vr);const m=body.mesh as any;m.scale.setScalar(0.35+0.18*Math.sqrt(pl.radius_earth));m.userData.id=pl.id;m.userData.body=body;(body as any).setTempK?.(pl.temperature_k);m.userData.ptype=type;world.add(m);planetMesh.set(pl.id,m);continue;}
    const bk=biomeOf(pl),bm=BIOME_MAP[bk];const mat=new THREE.MeshStandardMaterial({color:bm?0xffffff:(BIOME_HEX[bk]||0x9988ff),roughness:.85,metalness:0,emissive:bm?0xffffff:0x110822,emissiveIntensity:bm?.35:1});if(bm){mat.map=biomeTex(bm,'color');mat.emissiveMap=biomeTex(bm,'glow');}const sunV=nightGlowOnly(mat);const m=new THREE.Mesh(sphere,mat);
    m.scale.setScalar(0.35+0.18*Math.sqrt(pl.radius_earth));m.userData.id=pl.id;m.userData.sunV=sunV;if((pl.atmosphere||0)>0.08){const at=atmosphereMesh(Math.min(1,0.35+pl.atmosphere));m.add(at);m.userData.atm=at;}world.add(m);planetMesh.set(pl.id,m);}
   if(!legacyPlanets&&!moonsBuilt&&planetMesh.size>=U.planets.length){moonsBuilt=true; // SEEDED moons (the recorded genesis has none): labeled in the HUD, derived only from the universe seed
    for(const mo of seedMoons(String(U.seed||'tiny'),U.planets)){const body=planetKit.create('moon',{lonDeg:mo.lonDeg,tiltDeg:0,spinDegPerS:0,cloudLonDeg:0});const mesh=body.mesh as any;mesh.userData.moonId=mo.id;mesh.userData.seeded=true;world.add(mesh);const L=moonsOf.get(mo.planet)||[];L.push({m:mo,mesh,body});moonsOf.set(mo.planet,L);}}
  }
  const orbitR=(pl:any)=>gOrbitR(pl.orbit_au);
  // Cory's N-body (Definitive Core updateInterSystemPhysics): each star holds its planets under G*m/r^2, fixed dt, seeded phase start
  const systems=new Map<string,{sys:any,state:{t:number},key:string}>();const sv=new THREE.Vector3();
  function place(t:number){const U=uRef.current;if(!U)return;build();
   for(const st of U.stars){const g=starObj.get(st.id);if(!g||g.userData.bh)continue;const pls=U.planets.filter((p:any)=>p.star===st.id);if(!pls.length)continue;const key=pls.map((p:any)=>p.id).join('|');
    let S=systems.get(st.id);if(!S||S.key!==key){S={sys:initSystem(st,pls),state:{t:t},key};systems.set(st.id,S);}
    advanceTo(S.sys,S.state,t);
    {const fr=Math.floor(performance.now()/125)%16;for(const g of starObj.values()){const c:any=g.children.find((x:any)=>x.name==='sun-corona-sprite');const ft=c?.userData.frames;if(ft)ft.offset.set((fr%4)*.25,1-(Math.floor(fr/4)+1)*.25);}}
    for(const sp of S.sys.planets){const m=planetMesh.get(sp.id);if(!m)continue;m.position.set(g.position.x+sp.p[0],g.position.y+sp.p[1],g.position.z+sp.p[2]);
     // the star is the light: direction from this world to its star (view space) drives day/night, phases and the scatter shell
     sv.copy(g.position).sub(m.position).normalize();
     if(m.userData.body){const dd=g.position.distanceTo(m.position),ex=sunExposure(sunIntensity(g.userData.star.luminosity),dd),R=m.scale.x,vh=(el as HTMLElement).clientHeight,col=g.userData.sunColor,glow=glowSet(g.userData.star.temperature_k);
      const ml=moonsOf.get(sp.id)||[],cands:any[]=[];
      for(const q of ml){const o=moonOffset(q.m,t);q.mesh.position.set(m.position.x+o.x*R,m.position.y+o.y*R,m.position.z+o.z*R);q.mesh.scale.setScalar(R*q.m.radiusFrac);q.mesh.userData.th=o.theta;cands.push({x:q.mesh.position.x,y:q.mesh.position.y,z:q.mesh.position.z,r:q.mesh.scale.x,q});}
      const occ=cands.length?pickOccluder(m.position,sv,cands):null;
      m.userData.body.update({t,cam,sunPos:g.position,sunColor:col,exposure:ex,viewH:vh,glow,occ:occ?{c:mv.set(occ.x,occ.y,occ.z).clone(),r:occ.r}:null});
      const near=cam.position.distanceTo(m.position)<45,tint=SPRITE_TINT[m.userData.ptype]||[0.5,0.6,1];
      for(const q of ml){q.mesh.visible=near;if(near)q.body.update({t,cam,sunPos:g.position,sunColor:col,exposure:ex,viewH:vh,glow,spinRad:q.mesh.userData.th,occ:{c:m.position,r:R},parent:{c:m.position,tint}});}}
     if(m.userData.sunV)m.userData.sunV.value.copy(sv).transformDirection(cam.matrixWorldInverse);
     const at=m.userData.atm;if(at){const u=at.material.uniforms;u.cameraPos.value.copy(cam.position);u.lightDir.value.copy(sv);u.time.value=t;const c=g.userData.sunColor as THREE.Color;const hsl=c.getHSL({h:0,s:0,l:0});u.intensityBoost.value=0.8+Math.min(1.5,hsl.s*1.2+hsl.l);}}
    const cor=g.children.find((c:any)=>c.userData.isStarCorona) as any;if(cor)cor.material.uniforms.time.value=t;}
   const live=new Set<string>();for(const sm of allStorms(U)){const p=planetMesh.get(sm.planet);if(!p)continue;live.add(sm.planet);let sp=stormObj.get(sm.planet);
    if(!sp){sp=new THREE.Sprite(new THREE.SpriteMaterial({map:stormTex[sm.planet.length%2],transparent:true,depthWrite:false,opacity:.75,blending:THREE.AdditiveBlending}));world.add(sp);stormObj.set(sm.planet,sp);}
    sp.position.copy(p.position);sp.scale.setScalar(p.scale.x*(3+2*Math.min(1,sm.intensity/0.5)));}
   for(const[k,sp]of stormObj)if(!live.has(k)){world.remove(sp);stormObj.delete(k);showNotice('storm_passes',6000);}
   for(const g of starObj.values()){const d=g.getObjectByName('disk');if(d)d.rotation.z=t*0.05;}updateSeededBH(simT);
   addDeco();lightning(t);}
  // camera rig: spherical around a target, log distance
  let simT=0,simRate=1,pinned=false,yaw=0.6,pitch=0.5,logD=Math.log(30),goal=Math.log(30),doorV=0,doorPre=false,lastMs=0,lastDt=0,targetId:string|null=homeOf(uRef.current||{planets:[],life:[]});const tgt=new THREE.Vector3(),want=new THREE.Vector3();
  const doorLive=()=>doorOnRef.current&&!!targetId&&targetId===homeOf(uRef.current)&&!!planetMesh.get(targetId);
  const minLogD=()=>{const m:any=targetId?planetMesh.get(targetId):null;if(m&&doorLive())return Math.log(m.scale.x*(DOOR_NEAR-0.02));return Math.log(m?Math.max(0.02,m.scale.x*1.1):ZOOM_MIN);}; /* with the door on, the universe camera stops at the pocket orbit framing and the pocket world takes over */ // planets can be approached to ~10% of their radius above the surface (the maps are ~2048 px around, so closer needs the flat-ground layer, not built yet)
  const setZoom=(f:number)=>{ // door open: zoom input drives the pocket world, and leaves it from full orbit
   if(doorV>=0.999){const w:any=window;const z=w.__lwZoom?.target??1;const r=doorZoomStep(z,Math.sign(f),Math.max(.01,Math.min(.2,Math.abs(f)*1.2)));if(r.leave){const m:any=planetMesh.get(targetId||'');goal=Math.log((m?m.scale.x:1)*5.6);}else w.__lwSetZoom?.(r.z);return;}
   goal=Math.min(Math.log(ZOOM_LIMIT),Math.max(minLogD(),goal+f));};
  const leave=()=>{if(doorV>0){const m:any=planetMesh.get(targetId||'');goal=Math.log((m?m.scale.x:1)*5.6);}};window.addEventListener('u3d-door-leave',leave);
  api.current={zoom:setZoom,home:()=>{targetId=homeOf(uRef.current);goal=Math.log(10);pinned=false;pan={x:0,y:0,z:0};}};
  const ptrs=new Map<number,{x:number,y:number}>();let pinch=0,moved=0;const panPtrs=new Set<number>();const panBasis={rx:1,ry:0,rz:0,ux:0,uy:1,uz:0,k:.01};const panTmp=new THREE.Vector3();let panTarget=targetId;
  /* shared pan (two-finger drag, right drag, Shift+drag, Shift+arrows): an offset on the look-at point; it eases back when you pick another world or arrive at the door */
  let pan={x:0,y:0,z:0};const panBy=(dx:number,dy:number)=>{pan=panStep(pan,panBasis,dx,dy,Math.exp(logD)*2);};(window as any).__u3dPan=()=>({...pan});
  const cv=renderer.domElement;
  const down=(e:PointerEvent)=>{if(isPanGesture({button:e.pointerType==='mouse'?e.button:0,shiftKey:e.pointerType==='mouse'&&e.shiftKey}))panPtrs.add(e.pointerId);cv.setPointerCapture(e.pointerId);ptrs.set(e.pointerId,{x:e.clientX,y:e.clientY});moved=0;if(ptrs.size===2){const [a,b]=[...ptrs.values()];pinch=Math.hypot(a.x-b.x,a.y-b.y);}cv.style.cursor='grabbing';};
  const move=(e:PointerEvent)=>{const p=ptrs.get(e.pointerId);if(!p)return;const dx=e.clientX-p.x,dy=e.clientY-p.y;const c0=ptrs.size===2?centroid(...([...ptrs.values()] as [any,any])):null;p.x=e.clientX;p.y=e.clientY;moved+=Math.abs(dx)+Math.abs(dy);
   if(ptrs.size===2){const [a,b]=[...ptrs.values()];const d=Math.hypot(a.x-b.x,a.y-b.y);if(pinch)setZoom(-Math.log(d/pinch));pinch=d;if(c0){const c1=centroid(a,b);panBy(c1.x-c0.x,c1.y-c0.y);}return;}
   if(panPtrs.has(e.pointerId)){panBy(dx,dy);return;}
   yaw-=dx*0.006;pitch=Math.max(-1.45,Math.min(1.45,pitch+dy*0.006));};
  const up=(e:PointerEvent)=>{ptrs.delete(e.pointerId);panPtrs.delete(e.pointerId);pinch=0;cv.style.cursor='grab';if(moved<6&&ptrs.size===0)tap(e);};
  const wheel=(e:WheelEvent)=>{e.preventDefault();setZoom(e.deltaY*0.0028);};
  const ray=new THREE.Raycaster();
  function tap(e:PointerEvent){const b=cv.getBoundingClientRect();ray.setFromCamera(new THREE.Vector2((e.clientX-b.left)/b.width*2-1,-(e.clientY-b.top)/b.height*2+1),cam);
   let hit:any=ray.intersectObjects([...planetMesh.values()],false)[0];if(!hit){/* small worlds are hard to hit: take the nearest one within 30 px of the tap */let best=30;for(const m of planetMesh.values()){const q=(m as any).position.clone().project(cam);if(q.z>1)continue;const dx=(q.x*.5+.5)*b.width-(e.clientX-b.left),dy=(-q.y*.5+.5)*b.height-(e.clientY-b.top);const dd=Math.hypot(dx,dy);if(dd<best){best=dd;hit={object:m};}}}if(hit){targetId=hit.object.userData.id;goal=Math.log(6);pinned=true;sel.current?.(targetId);return;}
   const sh=ray.intersectObjects([...starObj.values()],true)[0];if(sh){let o:any=sh.object;while(o&&!o.userData?.id)o=o.parent;if(o){targetId=o.userData.id;goal=Math.log(String(targetId).startsWith('seeded-bh-')?45:14);pinned=false;sel.current?.(targetId);return;}}pinned=false;sel.current?.(null);}
  cv.addEventListener('pointerdown',down);cv.addEventListener('pointermove',move);cv.addEventListener('pointerup',up);cv.addEventListener('pointercancel',up);cv.addEventListener('wheel',wheel,{passive:false});const noMenu=(e:Event)=>{e.preventDefault();};cv.addEventListener('contextmenu',noMenu);const keyPan=(e:KeyboardEvent)=>{if(!e.shiftKey||!el.contains(document.activeElement))return;const kp=keyPanPixels(e.key);if(kp){e.preventDefault();panBy(kp[0],kp[1]);}};addEventListener('keydown',keyPan);
  const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;let raf=0,last='';const t0=performance.now();
  const frame=(ms:number)=>{const W=el.clientWidth,H=el.clientHeight;if(cv.width!==Math.floor(W*renderer.getPixelRatio())){renderer.setSize(W,H,false);cam.aspect=W/Math.max(1,H);cam.updateProjectionMatrix();}
   const t=reduce?0:(ms-t0)/1000;{const dts0=lastMs?Math.min(.1,(ms-lastMs)/1000):.016;simRate+=((pinned?.1:1)-simRate)*Math.min(1,dts0*4);simT+=reduce?0:dts0*simRate;}place(simT);{const dts=lastMs?Math.min(.1,(ms-lastMs)/1000):.016;lastMs=ms;lastDt=dts;goal=Math.max(goal,minLogD());logD=reduce?goal:logD+(goal-logD)*Math.min(1,dts*7);} /* eased so a zoom click or tap glides instead of jumping */ const d=Math.exp(logD);
   {let v=0,pre=false;if(doorLive()){const rr=d/(planetMesh.get(targetId!) as any).scale.x;v=doorProgress(rr);pre=doorPreload(rr);}if(Math.abs(v-doorV)>0.002||pre!==doorPre||(v===0&&doorV!==0)||(v===1&&doorV!==1)){{const dk=doorLineKind(doorV,v);if(dk)showZLine(dk.kind,dk.key);}doorV=v;doorPre=pre;onDoorRef.current?.(v,pre);}}
   // past the neighbourhood the camera eases its focus from the chosen world back to the universe centre
   const m:any=targetId?(planetMesh.get(targetId)||starObj.get(targetId)):null;const k=Math.min(1,Math.max(0,(d-260)/700));want.set(0,0,0);if(m)want.copy(m.position).multiplyScalar(1-k);tgt.lerp(want,1-Math.exp(-(lastDt||.016)*7.5)); /* frame-rate independent (0.125 at 60 fps): on a slow renderer the focus still keeps up with an orbiting planet */
   if(targetId!==panTarget){panTarget=targetId;pan={x:0,y:0,z:0};}else if(doorV>0.01)pan=decayPan(pan,lastDt||.016,4);panTmp.set(tgt.x+pan.x,tgt.y+pan.y,tgt.z+pan.z);cam.position.set(panTmp.x+d*Math.cos(pitch)*Math.sin(yaw),panTmp.y+d*Math.sin(pitch),panTmp.z+d*Math.cos(pitch)*Math.cos(yaw));cam.near=Math.max(0.02,d*0.01);cam.far=Math.max(6000,d*5);if(bgStars){const k=Math.max(1,d/1000);bgStars.position.copy(cam.position);bgStars.scale.setScalar(k);}cam.updateProjectionMatrix();cam.lookAt(panTmp);{const e=cam.matrixWorld.elements;panBasis.rx=e[0];panBasis.ry=e[1];panBasis.rz=e[2];panBasis.ux=e[4];panBasis.uy=e[5];panBasis.uz=e[6];panBasis.k=worldPerPixel(cam.fov,d,Math.max(1,el.clientHeight||600));}
   if(targetId&&planetMesh.has(targetId)){const pm:any=planetMesh.get(targetId);const sg=starObj.get((uRef.current?.planets||[]).find((p:any)=>p.id===targetId)?.star);if(sg){const a1=pm.position.clone().project(cam),b1=sg.position.clone().project(cam);(window as any).__u3dSunDir={planet:targetId,screen:[+(b1.x-a1.x).toFixed(3),+(b1.y-a1.y).toFixed(3)],note:'NDC offset from the planet to its star; the lit limb must face this way'};}}
   if(seededBH){const wp=new THREE.Vector3();seededBH.getWorldPosition(wp);const dB=cam.position.distanceTo(wp),R=seededBH.userData.bhR||4;const q=wp.clone().project(cam);const seen=q.z<1&&Math.abs(q.x)<1&&Math.abs(q.y)<1;
    if(dB<R*14){if(!bhNear){bhNear=true;bhFar=true;showNotice('black_hole_near');}}
    else if(bhNear&&dB>R*30){bhNear=false;showNotice('black_hole_away');}
    else if(!bhNear&&!bhFar&&seen&&dB>R*30){bhFar=true;showNotice('black_hole_far');}
    el.dataset.bhDist=String(Math.round(dB/R));{const lb=el.querySelector('[data-bh-label]') as HTMLElement|null;if(lb){const z2=zoomStage(d);lb.style.display=(doorV<.05&&(z2!=='Surface'||targetId==='seeded-bh-0')&&(dB<R*40||z2==='System'||z2==='Neighbours'||z2==='Universe'))?'':'none';}}}
   {const zs=zoomStage(d);if(targetId&&stormObj.has(targetId)&&(zs==='Planet'||zs==='Surface'))showNotice('storm_near');else if(stormObj.size&&(zs==='Orbit'||zs==='System'))showNotice('storm_far');}
   const s=zoomStage(d);if(s!==last){const wider=last==='Orbit'||last==='System'||last==='Neighbours'||last==='Universe';{const zk=zoomLineKind(last,s,{blackHole:!!seededBH||(uRef.current?.stars||[]).some((q:any)=>q.remnant==='black_hole')});if(zk){const gl=zk.kind==='zoom_in'&&(s==='Orbit'||s==='Planet')?(s==='Orbit'?(landscapeLineFor(uRef.current,zlineN.current)||growthLineFor(uRef.current)):(growthLineFor(uRef.current)||landscapeLineFor(uRef.current,zlineN.current))):null;showZLine(zk.kind,zk.key,gl);}}last=s;setStage(s);el.dataset.zoomStage=s;
    // a real zoom-in reached a world: Emeth's line for a planet or a star
    if(s==='Planet'&&wider&&targetId)aliveRef.current?.(starObj.has(targetId)?'zoom_star':'zoom_planet');}
   {const f=threadsRef.current?threadFade(d):0;const on=f>.02;threads.visible=on;origin.visible=on;if(on)drawThreads(f);
    if(on!==wasShown){wasShown=on;setThreadsShown(on);el.dataset.threads=on?'shown':'hidden';if(on&&f>0)aliveRef.current?.('threads_visible');}}
   renderLensed();raf=requestAnimationFrame(frame);};
  raf=requestAnimationFrame(frame);
  return()=>{cancelAnimationFrame(raf);cv.removeEventListener('wheel',wheel);cv.removeEventListener('contextmenu',noMenu);removeEventListener('keydown',keyPan);window.removeEventListener('u3d-door-leave',leave);rt.dispose();lensMat.dispose();renderer.dispose();el.removeChild(cv);};
 },[]);
 return <div ref={host} data-universe-3d style={{position:'absolute',inset:0}}>
  <div data-u3d-stack style={{position:'absolute',left:52,top:196,zIndex:3,display:'flex',flexDirection:'column',alignItems:'flex-start',gap:6,maxWidth:'min(70vw,300px)',pointerEvents:'none'}}>{(()=>{const hp=u?homeOf(u):null,pre=hp?String(hp).replace(/-p\d+$/,'-p'):'~';const st=(u?allStorms(u):[]).slice().sort((a:any,b:any)=>(b.planet.startsWith(pre)?1:0)-(a.planet.startsWith(pre)?1:0));if(!u)return <div data-storm-list-loading style={{fontSize:12,color:'#e9ddff',background:'rgba(12,8,32,.62)',border:'1px solid #8f6bff55',borderRadius:10,padding:'4px 8px',opacity:.8}}>Storms · loading…</div>;return st.length?<details data-storm-list style={{pointerEvents:'auto',maxWidth:'100%',fontSize:12,color:'#e9ddff',background:'rgba(12,8,32,.62)',border:'1px solid #8f6bff55',borderRadius:10,padding:'4px 8px'}}><summary style={{cursor:'pointer'}}>Storms · {st.length}</summary>{st.slice(0,6).map((x:any)=><div key={x.id} data-storm={x.id} style={{padding:'1px 0'}}>{x.planet} · {x.kind||'storm'} · {x.night?'night side · ':''}{x.label==='SEEDED'?'SEEDED':'SIMULATED growth'}</div>)}{st.length>6?<details data-storm-more><summary style={{cursor:'pointer',opacity:.85}}>Show all {st.length}</summary>{st.slice(6).map((x:any)=><div key={x.id} data-storm={x.id} style={{padding:'1px 0'}}>{x.planet} · {x.kind||'storm'} · {x.night?'night side · ':''}{x.label==='SEEDED'?'SEEDED':'SIMULATED growth'}</div>)}</details>:null}<div style={{opacity:.7,paddingTop:2}}>The recorded genesis has no storms; these are seeded from its counts.</div></details>:null;})()}</div>
  {zline?<div key={zline.n} data-zoom-line={zline.key} aria-live="polite" style={{position:'absolute',left:'50%',top:(typeof window!=='undefined'&&window.innerWidth<560)?'34%':'18%',transform:'translateX(-50%)',maxWidth:'min(86vw,520px)',textAlign:'center',zIndex:3,pointerEvents:'none',fontSize:15,lineHeight:1.35,color:'#f1e8ff',background:'rgba(12,8,32,.62)',border:'1px solid #8f6bff55',borderRadius:14,padding:'8px 14px',textShadow:'0 1px 6px #000'}}>{zline.text}</div>:null}
  {notice?<div key={notice.n} data-creature-notice={notice.key} aria-live="polite" style={{position:'absolute',left:'50%',top:(typeof window!=='undefined'&&window.innerWidth<560)?'44%':'26%',transform:'translateX(-50%)',maxWidth:'min(86vw,520px)',textAlign:'center',zIndex:3,pointerEvents:'none',fontSize:15,lineHeight:1.35,color:'#f1e8ff',background:'rgba(12,8,32,.62)',border:'1px solid #8f6bff55',borderRadius:14,padding:'8px 14px',textShadow:'0 1px 6px #000'}}>{notice.text}</div>:null}
  <div data-u3d-zoom style={{position:'absolute',right:56,top:'calc(50% - 200px)',display:'flex',flexDirection:'column',gap:6,zIndex:2}}>
   <button type="button" aria-label="Zoom in" onClick={()=>api.current?.zoom(-0.5)} style={zbtn}>＋</button>
   <span data-zoom-stage style={{fontSize:11,color:'#d8c8ff',textAlign:'center',background:'rgba(10,6,30,.7)',borderRadius:8,padding:'3px 4px'}}>{stage}</span>
   <button type="button" aria-label="Zoom out" onClick={()=>api.current?.zoom(0.5)} style={zbtn}>－</button>
   <button type="button" aria-label="Fly home" onClick={()=>api.current?.home()} style={zbtn}>⌂</button>
   <button type="button" aria-label={threadsOn?'Hide the One Mind threads':'Show the One Mind threads'} aria-pressed={threadsOn} data-threads-toggle onClick={toggleThreads} style={{...zbtn,fontSize:14,opacity:threadsOn?1:.55}}>✦</button>
  </div>
  {threadsOn&&threadsShown?<div data-threads-label style={{position:'absolute',left:'50%',top:'calc(50% - 230px)',transform:'translateX(-50%)',zIndex:2,fontSize:11,color:'#d8c8ff',background:'rgba(10,6,30,.7)',borderRadius:10,padding:'4px 10px',textAlign:'center',maxWidth:'80%',pointerEvents:'none'}}>One Mind, Refracted · {activityNote||'reading loop activity…'}</div>:null}
 </div>;
}
const zbtn:React.CSSProperties={width:40,height:40,borderRadius:20,border:'1px solid #7a5cff',background:'rgba(20,10,50,.8)',color:'#fff',fontSize:18};
