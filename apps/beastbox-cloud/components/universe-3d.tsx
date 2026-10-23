'use client';
// Zoomable, rotatable 3D Tiny Universe (Cosmo's visual audit, Oct 23 2026). Renders ONLY tiny-universe/v1 engine data:
// stars, planets, storms, life and black-hole remnants come from the grown universe; nothing is invented.
// Log zoom: surface -> planet -> neighbours -> universe. Drag rotates, wheel/pinch zooms, tap a world to fly to it.
// Art: Cosmo's deepspace sheets (accretion disk + photon ring on real black-hole remnants, storm clouds on real storms).
// Seeded only (string hash LCG from the universe seed); no Math.random.
import {useEffect,useRef,useState} from 'react';
import * as THREE from 'three';
import {homeOf,biomeOf} from '@/lib/universe/tiny-universe-view.mjs';
import {threadFade,threadBrightness,creatureHome,threadBend} from '@/lib/universe/alive-props.mjs';
// One Mind, Refracted (Cosmo's concept 09): faint threads from one origin to every creature (brightness = how recently its
// own loop really ticked, /api/cosmos/activity) and dimmer ones to stars, planets and storms. Only at full zoom-out; hideable.
const THREADS_KEY='beastbox.oneMindThreads.v1';const SEG=24;
/* eslint-disable @typescript-eslint/no-explicit-any */
const BIOME_HEX:Record<string,number>={ember:0xff7a2a,paper:0xe9d9b0,jelly:0x8fa8ff,sunflower:0xffd24a,moss:0x8fd06a,glacier:0xdff2ff};
function rand(seed:string){let h=0;for(const c of seed)h=(h*31+c.charCodeAt(0))>>>0;return()=>{h=(h*1664525+1013904223)>>>0;return h/2**32;};}
function starHex(t:number){return t>15000?0xbcd4ff:t>9000?0xe2ebff:t>6500?0xfff6e0:t>4500?0xffd59a:0xff9a6a;}
export const ZOOM_MIN=1.2,ZOOM_MAX=1400;
export function zoomStage(d:number){return d<6?'Surface':d<40?'Planet':d<260?'Neighbours':'Universe';}
const SPAN=420;
export function starPos(st:any){const r=rand(st.id);return new THREE.Vector3((st.x-0.5)*SPAN,(r()-0.5)*SPAN*0.18,(st.y-0.5)*SPAN);}
export default function Universe3D({u,onSelect,onAlive}:{u:any;onSelect?:(id:string|null)=>void;onAlive?:(kind:'zoom_planet'|'zoom_star'|'threads_visible')=>void}){
 const aliveRef=useRef(onAlive);aliveRef.current=onAlive;
 const [threadsOn,setThreadsOn]=useState(true);const threadsRef=useRef(true);threadsRef.current=threadsOn;const [threadsShown,setThreadsShown]=useState(false);const [activityNote,setActivityNote]=useState('');
 useEffect(()=>{try{if(localStorage.getItem(THREADS_KEY)==='0')setThreadsOn(false);}catch{}},[]);
 const toggleThreads=()=>setThreadsOn(v=>{const n=!v;try{localStorage.setItem(THREADS_KEY,n?'1':'0');}catch{}return n;});
 const activity=useRef<any[]>([]);
 useEffect(()=>{let dead=false;const load=()=>fetch('/api/cosmos/activity',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(j=>{if(dead||!j?.creatures)return;activity.current=j.creatures;const n=j.creatures.length;setActivityNote(n?`${n} creature${n===1?'':'s'} · brightness = how recently its own loop ticked`:'no creature loop activity reported');}).catch(()=>{if(!dead)setActivityNote('loop activity unavailable · threads drawn at the faint floor');});load();const iv=setInterval(load,300000);return()=>{dead=true;clearInterval(iv);};},[]);
 const host=useRef<HTMLDivElement>(null);const uRef=useRef(u);uRef.current=u;const sel=useRef(onSelect);sel.current=onSelect;
 const [stage,setStage]=useState('Planet');const api=useRef<{zoom:(f:number)=>void;home:()=>void}|null>(null);
 useEffect(()=>{const el=host.current;if(!el)return;
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false});renderer.setPixelRatio(Math.min(2,devicePixelRatio||1));el.appendChild(renderer.domElement);
  renderer.domElement.style.cssText='display:block;width:100%;height:100%;touch-action:none;cursor:grab';
  const scene=new THREE.Scene();scene.background=new THREE.Color(0x05030f);
  const cam=new THREE.PerspectiveCamera(55,1,0.05,6000);
  scene.add(new THREE.AmbientLight(0x8877bb,0.55));
  const tl=new THREE.TextureLoader();const tex=(n:string)=>{const t=tl.load('/universe/deepspace/'+n);t.colorSpace=THREE.SRGBColorSpace;return t;};
  // seeded background stars
  {const r=rand(String(uRef.current?.seed||'tiny'));const n=1800,p=new Float32Array(n*3);for(let i=0;i<n;i++){const th=r()*Math.PI*2,ph=Math.acos(2*r()-1),R=2500+r()*800;p[i*3]=R*Math.sin(ph)*Math.cos(th);p[i*3+1]=R*Math.cos(ph);p[i*3+2]=R*Math.sin(ph)*Math.sin(th);}
   const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(p,3));scene.add(new THREE.Points(g,new THREE.PointsMaterial({color:0xffffff,size:2.2,sizeAttenuation:false,transparent:true,opacity:.75})));}
  const world=new THREE.Group();scene.add(world);
  const MAXT=160;const tPos=new Float32Array(MAXT*SEG*2*3),tCol=new Float32Array(MAXT*SEG*2*3);const tGeo=new THREE.BufferGeometry();
  tGeo.setAttribute('position',new THREE.BufferAttribute(tPos,3));tGeo.setAttribute('color',new THREE.BufferAttribute(tCol,3));tGeo.setDrawRange(0,0);
  const tMat=new THREE.LineBasicMaterial({vertexColors:true,transparent:true,opacity:0,blending:THREE.AdditiveBlending,depthWrite:false});
  const threads=new THREE.LineSegments(tGeo,tMat);threads.frustumCulled=false;threads.visible=false;scene.add(threads);
  const origin=new THREE.Sprite(new THREE.SpriteMaterial({color:0xd8c8ff,blending:THREE.AdditiveBlending,depthWrite:false,transparent:true,opacity:0}));origin.scale.setScalar(26);origin.visible=false;scene.add(origin);
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
  const planetMesh=new Map<string,THREE.Mesh>();const starObj=new Map<string,THREE.Object3D>();const stormObj=new Map<string,THREE.Sprite>();
  const sphere=new THREE.SphereGeometry(1,32,20);
  const diskTex=tex('accretion_disk_1024.png'),ringTex=tex('photon_ring_512.png'),stormTex=[tex('storm_cloud_violet_1024.png'),tex('storm_cloud_teal_1024.png')];
  function build(){const U=uRef.current;if(!U)return;
   for(const st of U.stars){if(starObj.has(st.id))continue;const g=new THREE.Group();g.position.copy(starPos(st));
    if(st.remnant==='black_hole'){g.add(new THREE.Mesh(new THREE.SphereGeometry(2.2,32,16),new THREE.MeshBasicMaterial({color:0x000000})));
     const disk=new THREE.Mesh(new THREE.PlaneGeometry(16,16),new THREE.MeshBasicMaterial({map:diskTex,transparent:true,blending:THREE.AdditiveBlending,depthWrite:false,side:THREE.DoubleSide}));disk.rotation.x=-Math.PI/2+0.25;disk.name='disk';g.add(disk);
     const ring=new THREE.Sprite(new THREE.SpriteMaterial({map:ringTex,blending:THREE.AdditiveBlending,depthWrite:false,transparent:true}));ring.scale.setScalar(7.2);g.add(ring);}
    else{const rr=1.2+0.9*Math.log10(1+st.mass_solar*3);const m=new THREE.Mesh(sphere,new THREE.MeshBasicMaterial({color:starHex(st.temperature_k)}));m.scale.setScalar(rr);g.add(m);
     const glow=new THREE.Sprite(new THREE.SpriteMaterial({map:ringTex,color:starHex(st.temperature_k),blending:THREE.AdditiveBlending,depthWrite:false,transparent:true,opacity:.35}));glow.scale.setScalar(rr*7);g.add(glow);
     const L=new THREE.PointLight(starHex(st.temperature_k),2.2,0,0);g.add(L);}
    g.userData.id=st.id;world.add(g);starObj.set(st.id,g);}
   for(const pl of U.planets){if(planetMesh.has(pl.id))continue;const m=new THREE.Mesh(sphere,new THREE.MeshStandardMaterial({color:BIOME_HEX[biomeOf(pl)]||0x9988ff,roughness:.85,metalness:0,emissive:0x110822}));
    m.scale.setScalar(0.35+0.18*Math.sqrt(pl.radius_earth));m.userData.id=pl.id;world.add(m);planetMesh.set(pl.id,m);}
  }
  const orbitR=(pl:any)=>4+5*Math.sqrt(pl.orbit_au);
  function place(t:number){const U=uRef.current;if(!U)return;build();
   for(const pl of U.planets){const m=planetMesh.get(pl.id),s=starObj.get(pl.star);if(!m||!s)continue;const a=pl.phase*Math.PI*2+t*0.05/Math.pow(pl.orbit_au,1.5);const R=orbitR(pl);m.position.set(s.position.x+Math.cos(a)*R,s.position.y,s.position.z+Math.sin(a)*R);}
   const live=new Set<string>();for(const sm of U.storms||[]){const p=planetMesh.get(sm.planet);if(!p)continue;live.add(sm.planet);let sp=stormObj.get(sm.planet);
    if(!sp){sp=new THREE.Sprite(new THREE.SpriteMaterial({map:stormTex[sm.planet.length%2],transparent:true,depthWrite:false,opacity:.75}));world.add(sp);stormObj.set(sm.planet,sp);}
    sp.position.copy(p.position);sp.scale.setScalar(p.scale.x*(3+2*Math.min(1,sm.intensity/0.5)));}
   for(const[k,sp]of stormObj)if(!live.has(k)){world.remove(sp);stormObj.delete(k);}
   for(const g of starObj.values()){const d=g.getObjectByName('disk');if(d)d.rotation.z=t*0.05;}}
  // camera rig: spherical around a target, log distance
  let yaw=0.6,pitch=0.5,logD=Math.log(30),targetId:string|null=homeOf(uRef.current||{planets:[],life:[]});const tgt=new THREE.Vector3(),want=new THREE.Vector3();
  const setZoom=(f:number)=>{logD=Math.min(Math.log(ZOOM_MAX),Math.max(Math.log(ZOOM_MIN),logD+f));};
  api.current={zoom:setZoom,home:()=>{targetId=homeOf(uRef.current);logD=Math.log(10);}};
  const ptrs=new Map<number,{x:number,y:number}>();let pinch=0,moved=0;
  const cv=renderer.domElement;
  const down=(e:PointerEvent)=>{cv.setPointerCapture(e.pointerId);ptrs.set(e.pointerId,{x:e.clientX,y:e.clientY});moved=0;if(ptrs.size===2){const [a,b]=[...ptrs.values()];pinch=Math.hypot(a.x-b.x,a.y-b.y);}cv.style.cursor='grabbing';};
  const move=(e:PointerEvent)=>{const p=ptrs.get(e.pointerId);if(!p)return;const dx=e.clientX-p.x,dy=e.clientY-p.y;p.x=e.clientX;p.y=e.clientY;moved+=Math.abs(dx)+Math.abs(dy);
   if(ptrs.size===2){const [a,b]=[...ptrs.values()];const d=Math.hypot(a.x-b.x,a.y-b.y);if(pinch)setZoom(-Math.log(d/pinch));pinch=d;return;}
   yaw-=dx*0.006;pitch=Math.max(-1.45,Math.min(1.45,pitch+dy*0.006));};
  const up=(e:PointerEvent)=>{ptrs.delete(e.pointerId);pinch=0;cv.style.cursor='grab';if(moved<6&&ptrs.size===0)tap(e);};
  const wheel=(e:WheelEvent)=>{e.preventDefault();setZoom(e.deltaY*0.0015);};
  const ray=new THREE.Raycaster();
  function tap(e:PointerEvent){const b=cv.getBoundingClientRect();ray.setFromCamera(new THREE.Vector2((e.clientX-b.left)/b.width*2-1,-(e.clientY-b.top)/b.height*2+1),cam);
   const hit=ray.intersectObjects([...planetMesh.values()],false)[0];if(hit){targetId=hit.object.userData.id;logD=Math.log(6);sel.current?.(targetId);return;}
   const sh=ray.intersectObjects([...starObj.values()],true)[0];if(sh){let o:any=sh.object;while(o&&!o.userData?.id)o=o.parent;if(o){targetId=o.userData.id;logD=Math.log(14);sel.current?.(targetId);return;}}sel.current?.(null);}
  cv.addEventListener('pointerdown',down);cv.addEventListener('pointermove',move);cv.addEventListener('pointerup',up);cv.addEventListener('pointercancel',up);cv.addEventListener('wheel',wheel,{passive:false});
  const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;let raf=0,last='';const t0=performance.now();
  const frame=(ms:number)=>{const W=el.clientWidth,H=el.clientHeight;if(cv.width!==Math.floor(W*renderer.getPixelRatio())){renderer.setSize(W,H,false);cam.aspect=W/Math.max(1,H);cam.updateProjectionMatrix();}
   const t=reduce?0:(ms-t0)/1000;place(t);const d=Math.exp(logD);
   // past the neighbourhood the camera eases its focus from the chosen world back to the universe centre
   const m:any=targetId?(planetMesh.get(targetId)||starObj.get(targetId)):null;const k=Math.min(1,Math.max(0,(d-260)/700));want.set(0,0,0);if(m)want.copy(m.position).multiplyScalar(1-k);tgt.lerp(want,0.12);
   cam.position.set(tgt.x+d*Math.cos(pitch)*Math.sin(yaw),tgt.y+d*Math.sin(pitch),tgt.z+d*Math.cos(pitch)*Math.cos(yaw));cam.near=Math.max(0.02,d*0.01);cam.updateProjectionMatrix();cam.lookAt(tgt);
   const s=zoomStage(d);if(s!==last){const wider=last==='Neighbours'||last==='Universe';last=s;setStage(s);el.dataset.zoomStage=s;
    // a real zoom-in reached a world: Emeth's line for a planet or a star
    if(s==='Planet'&&wider&&targetId)aliveRef.current?.(starObj.has(targetId)?'zoom_star':'zoom_planet');}
   {const f=threadsRef.current?threadFade(d):0;const on=f>.02;threads.visible=on;origin.visible=on;if(on)drawThreads(f);
    if(on!==wasShown){wasShown=on;setThreadsShown(on);el.dataset.threads=on?'shown':'hidden';if(on&&f>0)aliveRef.current?.('threads_visible');}}
   renderer.render(scene,cam);raf=requestAnimationFrame(frame);};
  raf=requestAnimationFrame(frame);
  return()=>{cancelAnimationFrame(raf);cv.removeEventListener('wheel',wheel);renderer.dispose();el.removeChild(cv);};
 },[]);
 return <div ref={host} data-universe-3d style={{position:'absolute',inset:0}}>
  <div style={{position:'absolute',right:56,top:'calc(50% - 200px)',display:'flex',flexDirection:'column',gap:6,zIndex:2}}>
   <button type="button" aria-label="Zoom in" onClick={()=>api.current?.zoom(-0.5)} style={zbtn}>＋</button>
   <span data-zoom-stage style={{fontSize:11,color:'#d8c8ff',textAlign:'center',background:'rgba(10,6,30,.7)',borderRadius:8,padding:'3px 4px'}}>{stage}</span>
   <button type="button" aria-label="Zoom out" onClick={()=>api.current?.zoom(0.5)} style={zbtn}>－</button>
   <button type="button" aria-label="Fly home" onClick={()=>api.current?.home()} style={zbtn}>⌂</button>
   <button type="button" aria-label={threadsOn?'Hide the One Mind threads':'Show the One Mind threads'} aria-pressed={threadsOn} data-threads-toggle onClick={toggleThreads} style={{...zbtn,fontSize:14,opacity:threadsOn?1:.55}}>⟡</button>
  </div>
  {threadsOn&&threadsShown?<div data-threads-label style={{position:'absolute',left:'50%',top:'calc(50% - 230px)',transform:'translateX(-50%)',zIndex:2,fontSize:11,color:'#d8c8ff',background:'rgba(10,6,30,.7)',borderRadius:10,padding:'4px 10px',textAlign:'center',maxWidth:'80%',pointerEvents:'none'}}>One Mind, Refracted · {activityNote||'reading loop activity…'}</div>:null}
 </div>;
}
const zbtn:React.CSSProperties={width:40,height:40,borderRadius:20,border:'1px solid #7a5cff',background:'rgba(20,10,50,.8)',color:'#fff',fontSize:18};
