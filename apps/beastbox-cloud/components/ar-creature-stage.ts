/**
 * Open Field AR stage (Oct 16 2026). The selected creature as its real 3D model, standing on the floor.
 * Three honest modes:
 *  - 'xr'       WebXR immersive-ar + hit-test (Android Chrome & other WebXR browsers): real surface detection and 6-DoF tracking.
 *  - 'anchored' iOS Safari / no WebXR: live camera behind a 3D scene whose camera follows the phone's DeviceOrientation
 *               (rotation only, no position tracking); the floor is ASSUMED 1.35 m below the phone. Tap the floor to place.
 *  - 'preview'  no motion sensors (desktop) or before permission: the same scene from a fixed camera angle.
 * Quick Look (iOS true AR) is offered separately through a USDZ export of the model (static pose).
 * The creature lives on its own: life-brain modes + CST state (lib/physics/cst-integrator) + grounded hops (ground-hop).
 */
import type {PlushGenome} from './creature-plush-3d';
import {seededStream} from '../lib/seeded-stream.mjs';const __rs=seededStream('components/ar-creature-stage.ts');
type Three=typeof import('three');
export type ArMode='xr'|'anchored'|'preview';
export const EYE_HEIGHT=1.35; // assumed phone height above the floor in anchored mode (metres)
const ROAM=1.1,HEIGHT=.3; // roam radius around the placed spot, creature height (metres)
export async function createArStage(host:HTMLElement,gen:PlushGenome,opts:{onMode?:(m:ArMode)=>void;onPlaced?:(p:{x:number;y:number;z:number})=>void;onState?:(s:string)=>void;name?:string;friend?:{genome:PlushGenome;name:string};onEvent?:(t:string)=>void}={}){
 const {onMode,onPlaced,onState}=opts;
 const THREE:Three=await import('three');
 const [{loadBeastGlb,beastStudio,GLB_PLANS},{buildPlush},cst,{createLife,stepLife,pokeLife,POCKET_RADIUS},{createHop,stepHop}]=await Promise.all([
  import('./creature-glb-beast'),import('./creature-plush-3d'),import('../lib/physics/cst-integrator.mjs'),import('../lib/creatures3d/life-brain.mjs'),import('../lib/physics/ground-hop.mjs')]);
 const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
 // Software GL (CI SwiftShader, GPU-less devices): no MSAA, 1x pixels, no shadow map, light fur. Probed BEFORE the renderer
 // exists because antialias can't be turned off later; a CPU rasteriser at 2x + MSAA starves rAF (game input polling, taps).
 const soft=(await import('../lib/three/soft-gl')).isSoftwareGL();
 const r=new THREE.WebGLRenderer({antialias:!soft,alpha:true,powerPreference:soft?'low-power':'default'});r.setPixelRatio(soft?1:Math.min(devicePixelRatio||1,2));r.outputColorSpace=THREE.SRGBColorSpace;
 r.setClearColor(0x000000,0);r.shadowMap.enabled=!soft;r.shadowMap.type=THREE.PCFSoftShadowMap;
 const cv=r.domElement;cv.dataset.arCanvas='';Object.assign(cv.style,{position:'absolute',inset:'0',width:'100%',height:'100%',touchAction:'manipulation'});host.appendChild(cv);
 const scene=new THREE.Scene();const studio=beastStudio(THREE,r,scene);r.toneMappingExposure=1.05;scene.environmentIntensity=.55;
 studio.key.position.set(-1.2,3,1.4);studio.key.shadow.camera.left=studio.key.shadow.camera.bottom=-1;studio.key.shadow.camera.right=studio.key.shadow.camera.top=1;studio.key.shadow.camera.near=.1;studio.key.shadow.camera.far=8;studio.key.shadow.radius=6;
 const cam=new THREE.PerspectiveCamera(65,1,.02,40);cam.position.set(0,EYE_HEIGHT,0);
 // anchor: the placed spot on the floor. Shadow catcher + soft contact blob live there.
 const anchor=new THREE.Group();anchor.position.set(0,0,-1.4);scene.add(anchor);studio.key.target=anchor;
 const catcher=new THREE.Mesh(new THREE.PlaneGeometry(3,3),new THREE.ShadowMaterial({opacity:.38}));catcher.rotation.x=-Math.PI/2;catcher.receiveShadow=true;anchor.add(catcher);
 const bc=document.createElement('canvas');bc.width=bc.height=64;const g=bc.getContext('2d')!;const gr=g.createRadialGradient(32,32,0,32,32,32);gr.addColorStop(0,'rgba(0,0,0,.75)');gr.addColorStop(.55,'rgba(0,0,0,.3)');gr.addColorStop(1,'rgba(0,0,0,0)');g.fillStyle=gr;g.fillRect(0,0,64,64);
 const blob=new THREE.Mesh(new THREE.PlaneGeometry(1,1),new THREE.MeshBasicMaterial({map:new THREE.CanvasTexture(bc),transparent:true,depthWrite:false}));blob.rotation.x=-Math.PI/2;blob.position.y=.002;blob.renderOrder=2;anchor.add(blob);
 // placement ring (shows where a tap will put the creature; the XR reticle in 'xr')
 const ring=new THREE.Mesh(new THREE.RingGeometry(.09,.115,40).rotateX(-Math.PI/2),new THREE.MeshBasicMaterial({color:0x9aefff,transparent:true,opacity:.85,depthWrite:false}));ring.matrixAutoUpdate=false;ring.visible=false;scene.add(ring);
 // creatures: the user's own companion plus (optionally) Zeref, each with its own life brain, hop, CST state and contact shadow.
 const k=ROAM/POCKET_RADIUS;let kind='plush';
 type Pet={name:string;body:any;blob:any;life:any;hop:any;S:any;drive:(dt:number,l:any,mp:any,look:any)=>void;glb:any;plush:any;dispose:()=>void;happy:number};
 const pets:Pet[]=[];
 const mkBlob=()=>{const m=new THREE.Mesh(new THREE.PlaneGeometry(1,1),new THREE.MeshBasicMaterial({map:blob.material.map,transparent:true,depthWrite:false}));m.rotation.x=-Math.PI/2;m.position.y=.002;m.renderOrder=2;anchor.add(m);return m;};
 function addPet(g:PlushGenome,name:string,start:{x:number;z:number}){
  const body=new THREE.Group();anchor.add(body);const fit=(o:any)=>{o.updateMatrixWorld(true);const bb=new THREE.Box3().setFromObject(o);const h=Math.max(.01,bb.max.y-bb.min.y);o.scale.multiplyScalar(HEIGHT/h);o.updateMatrixWorld(true);bb.setFromObject(o);o.position.y=-bb.min.y+o.position.y;};
  const plush=buildPlush(THREE,g as any,{low:true});body.add(plush.root);fit(plush.root);
  const P:Pet={name,body,blob:pets.length?mkBlob():blob,life:createLife(g.seed,start),hop:createHop(g.seed),S:cst.createCSTState(g.seed),drive:(dt,l,mp,lk)=>plush.drive(dt,l,mp,lk),glb:null,plush,dispose:()=>plush.dispose(),happy:0};
  pets.push(P);
  const rd=GLB_PLANS.includes(g.body)?loadBeastGlb(THREE,g,{tier:soft?'low':'high'}).then(gb=>{if(!gb||disposed){gb?.dispose();return;}plush.root.visible=false;body.add(gb.root);fit(gb.root);P.glb=gb;if(pets[0]===P)kind='glb';
   P.drive=(dt,l,mp,lk)=>gb.drive(dt,l,mp,lk);const pd=P.dispose;P.dispose=()=>{gb.dispose();pd();};}).catch(()=>{}):Promise.resolve();
  return rd;}
 const ready=addPet(gen,opts.name||'companion',{x:.4,z:.3});
 if(opts.friend)void addPet(opts.friend.genome,opts.friend.name,{x:-1.1,z:-.6});
 // play props (floor-local metres): a treat and a toy ball
 const treatM=new THREE.Mesh(new THREE.SphereGeometry(.03,12,10),new THREE.MeshStandardMaterial({color:0xffb84d,emissive:0x552200,roughness:.5}));treatM.visible=false;anchor.add(treatM);
 const ballM=new THREE.Mesh(new THREE.SphereGeometry(.045,16,12),new THREE.MeshStandardMaterial({color:0x5fd4ff,emissive:0x0a3550,roughness:.35}));ballM.visible=false;ballM.castShadow=true;anchor.add(ballM);
 let treat:{x:number;z:number}|null=null;const ball={on:false,x:0,y:0,z:0,vx:0,vy:0,vz:0,kicks:0};
 // ---- camera pose
 let mode:ArMode='preview';const setMode=(m:ArMode)=>{mode=m;host.dataset.arMode=m;onMode?.(m);};setMode('preview');
 let ori:{a:number;b:number;g:number}|null=null;const screenAngle=()=>((screen.orientation?.angle??(window as any).orientation??0) as number)*Math.PI/180;
 const onOri=(e:DeviceOrientationEvent)=>{if(e.alpha==null||e.beta==null||e.gamma==null)return;ori={a:e.alpha*Math.PI/180,b:e.beta*Math.PI/180,g:e.gamma*Math.PI/180};if(mode==='preview')setMode('anchored');};
 const E=new THREE.Euler(),q0=new THREE.Quaternion(),q1=new THREE.Quaternion(-Math.sqrt(.5),0,0,Math.sqrt(.5)),Z=new THREE.Vector3(0,0,1);let yaw0:number|null=null;
 const poseCam=()=>{if(mode==='anchored'&&ori){cam.position.set(0,EYE_HEIGHT,0);E.set(ori.b,ori.a,-ori.g,'YXZ');cam.quaternion.setFromEuler(E).multiply(q1).multiply(q0.setFromAxisAngle(Z,-screenAngle()));
   // re-centre compass yaw so "forward" is where the phone pointed when sensors started
   if(yaw0===null){const f=new THREE.Vector3(0,0,-1).applyQuaternion(cam.quaternion);yaw0=Math.atan2(-f.x,-f.z);}cam.quaternion.premultiply(q0.setFromAxisAngle(new THREE.Vector3(0,1,0),-yaw0));}
  else if(mode==='preview'){cam.position.set(0,EYE_HEIGHT*.75,0);cam.rotation.set(-.62,0,0);}};
 async function enableOrientation(){const D:any=(window as any).DeviceOrientationEvent;if(!D)return false;
  try{if(typeof D.requestPermission==='function'){const p=await D.requestPermission();if(p!=='granted')return false;}}catch{return false;}
  window.addEventListener('deviceorientation',onOri);return true;}
 // ---- tap to place: ray from the camera to the (detected or assumed) floor plane
 const ray=new THREE.Raycaster(),ndc=new THREE.Vector2(),floor=new THREE.Plane(new THREE.Vector3(0,1,0),0),hit=new THREE.Vector3();
 function place(cx:number,cy:number){const rc=cv.getBoundingClientRect();ndc.set((cx-rc.left)/rc.width*2-1,-((cy-rc.top)/rc.height)*2+1);ray.setFromCamera(ndc,cam);
  if(!ray.ray.intersectPlane(floor,hit))return false;const d=hit.distanceTo(cam.position);if(d>7)return false;
  anchor.position.copy(hit);pets.forEach((p,i)=>{p.life.x=i?-.5:0;p.life.z=i?-.3:0;p.life.mode='approach';p.life.timer=2;});onPlaced?.({x:hit.x,y:hit.y,z:hit.z});return true;}
 // ---- WebXR immersive-ar with hit-test
 let xrSession:any=null,hitSource:any=null;
 async function xrSupported(){try{return !!(navigator as any).xr&&await (navigator as any).xr.isSessionSupported('immersive-ar');}catch{return false;}}
 async function startXR(overlay?:HTMLElement){const xr=(navigator as any).xr;if(!xr)return false;
  try{xrSession=await xr.requestSession('immersive-ar',{requiredFeatures:['hit-test'],optionalFeatures:['dom-overlay','local-floor'],...(overlay?{domOverlay:{root:overlay}}:{})});}catch{return false;}
  r.xr.enabled=true;r.xr.setReferenceSpaceType('local');await r.xr.setSession(xrSession);
  const viewer=await xrSession.requestReferenceSpace('viewer');hitSource=await xrSession.requestHitTestSource({space:viewer});
  xrSession.addEventListener('select',()=>{if(ring.visible){anchor.position.setFromMatrixPosition(ring.matrix);floor.constant=-anchor.position.y;pets.forEach((p,i)=>{p.life.x=i?-.5:0;p.life.z=i?-.3:0;});onPlaced?.({...anchor.position});}});
  xrSession.addEventListener('end',()=>{hitSource=null;xrSession=null;r.xr.enabled=false;ring.visible=false;setMode(ori?'anchored':'preview');});
  setMode('xr');return true;}
 // ---- Quick Look (iOS AR): USDZ of the visible model meshes (static bind pose, flat paint colours)
 async function exportUsdz(){await ready;const {USDZExporter}=await import('three/examples/jsm/exporters/USDZExporter.js');
  const grp=new THREE.Group();const p0=pets[0];const src=p0.glb?.root||p0.plush.root;src.updateMatrixWorld(true);const C=p0.glb?.colors;
  src.traverse((o:any)=>{if(!o.isMesh||o.userData.shell||!o.visible)return;let vis=true;for(let p=o.parent;p;p=p.parent)if(!p.visible)vis=false;if(!vis)return;
   const m0:any=Array.isArray(o.material)?o.material[0]:o.material;const col=m0?.vertexColors&&C?C.base:(m0?.color||new THREE.Color(0xcccccc));
   const m=new THREE.Mesh(o.geometry,new THREE.MeshStandardMaterial({color:col,roughness:m0?.roughness??.7,metalness:m0?.metalness??0,emissive:m0?.emissive||new THREE.Color(0),emissiveIntensity:m0?.emissiveIntensity??0}));
   o.matrixWorld.decompose(m.position,m.quaternion,m.scale);grp.add(m);});
  const bb=new THREE.Box3().setFromObject(grp);const sc=HEIGHT/Math.max(.01,bb.max.y-bb.min.y);grp.scale.setScalar(sc);grp.position.y=-bb.min.y*sc;const wrap=new THREE.Group();wrap.add(grp);
  const data=await new USDZExporter().parseAsync(wrap);return URL.createObjectURL(new Blob([data],{type:'model/vnd.usdz+zip'}));}
 // ---- play: call, pet (tap a creature), feed (treat in front of you), throw a toy
 const camFloor=(dist:number)=>{cam.getWorldPosition(wp);const f=new THREE.Vector3(0,0,-1).applyQuaternion(cam.quaternion);f.y=0;if(f.lengthSq()<1e-4)f.set(0,0,-1);f.normalize();const p=wp.clone().addScaledVector(f,dist);anchor.worldToLocal(p);const r0=Math.hypot(p.x,p.z),R=ROAM*.9;if(r0>R){p.x*=R/r0;p.z*=R/r0;}return {p,f};};
 function call(){pets.forEach(P=>pokeLife(P.life,{fear:0,joy:1}));return pets.map(p=>p.name);}
 function feed(){const {p}=camFloor(.8);treat={x:p.x,z:p.z};treatM.position.set(p.x,.03,p.z);treatM.visible=true;return true;}
 function toss(){const {p,f}=camFloor(.35);Object.assign(ball,{on:true,kicks:0,x:p.x,y:.5,z:p.z,vx:f.x*1.8,vy:1.2,vz:f.z*1.8});ballM.visible=true;return true;}
 function pet(cx:number,cy:number){const rc=cv.getBoundingClientRect();ndc.set((cx-rc.left)/rc.width*2-1,-((cy-rc.top)/rc.height)*2+1);ray.setFromCamera(ndc,cam);
  for(const P of pets){const hitP=ray.intersectObject(P.body,true);const c=P.body.getWorldPosition(new THREE.Vector3());c.y+=HEIGHT/2;if(hitP.length||ray.ray.distanceToPoint(c)<HEIGHT*.6){P.happy=1.8;P.life.mode='glance';P.life.timer=2.5;P.life.sleep=0;return P.name;}}return null;}
 // ---- loop
 const size=()=>{const w=host.clientWidth||300,h=host.clientHeight||300;r.setSize(w,h,false);cam.aspect=w/h;
  // the rear camera in portrait shows ~70° vertically; object-fit:cover on a tall screen keeps that, on wide boxes it crops vertically
  cam.fov=w/h<3/4?66:THREE.MathUtils.radToDeg(2*Math.atan(Math.tan(THREE.MathUtils.degToRad(33))*(3/4)/(w/h)));cam.updateProjectionMatrix();};
 size();const ro=new ResizeObserver(size);ro.observe(host);
 let disposed=false,last=performance.now(),manual=-1,lastPaint=0;const lookV={x:0,y:0,z:0},lp=new THREE.Vector3(),wp=new THREE.Vector3();
 const frameFn=(now:number,frame?:any)=>{if(disposed)return;
  // Background use (no live camera, e.g. behind the /go field game) or software GL: cap at ~15 fps so the page's own loops keep their frames.
  if(manual<0&&!frame&&(soft||host.dataset.live!=='1')&&now-lastPaint<66)return;lastPaint=now;const dt=manual>=0?manual:Math.min(.05,(now-last)/1000);last=now;if(manual>=0)manual=-1;
  if(frame&&hitSource){const res=frame.getHitTestResults(hitSource);if(res.length){const p=res[0].getPose(r.xr.getReferenceSpace());if(p){ring.matrix.fromArray(p.transform.matrix);ring.visible=true;}}else ring.visible=false;}
  else poseCam();
  const d=reduced?0:dt;cam.getWorldPosition(wp);anchor.worldToLocal(lp.copy(wp));lookV.x=wp.x;lookV.y=wp.y;lookV.z=wp.z;
  // toy ball physics (floor-local metres, simple bounce + friction)
  if(ball.on){ball.vy-=9.8*d;ball.x+=ball.vx*d;ball.y+=ball.vy*d;ball.z+=ball.vz*d;if(ball.y<.045){ball.y=.045;ball.vy=Math.abs(ball.vy)>.6?-ball.vy*.45:0;ball.vx*=.9;ball.vz*=.9;}
   const r0=Math.hypot(ball.x,ball.z),R=ROAM*.95;if(r0>R){ball.x*=R/r0;ball.z*=R/r0;ball.vx*=-.5;ball.vz*=-.5;}ballM.position.set(ball.x,ball.y,ball.z);ballM.rotation.x+=ball.vz*d*8;ballM.rotation.z-=ball.vx*d*8;}
  const props:any[]=[];if(treat)props.push({x:treat.x/k,z:treat.z/k,id:'treat'});if(ball.on&&ball.y<.2)props.push({x:ball.x/k,z:ball.z/k,id:'toy'});
  pets.forEach((P,i)=>{const {life,hop}=P;cst.stepCSTState(P.S,d);const mp=cst.motionParams(P.S);
   const others=pets.filter(o=>o!==P).map(o=>({x:o.life.x,z:o.life.z,id:o.name}));
   stepLife(life,d,{mood:mp.mood,cam:{x:lp.x/k,z:lp.z/k},rain:0,treats:props,residents:others,onEat:(id:string)=>{
    if(id==='treat'){treat=null;treatM.visible=false;P.happy=2;opts.onEvent?.(`${P.name} munches the treat!`);}
    else if(id==='toy'&&ball.on){P.happy=1.5;ball.kicks++;if(ball.kicks>3){ball.on=false;ballM.visible=false;opts.onEvent?.(`${P.name} caught the toy and drops it at your feet.`);}else{const a=life.heading+(__rs()-.5)*1.4;ball.vx=Math.cos(a)*1.4;ball.vz=Math.sin(a)*1.4;ball.vy=1.6;ball.y=.1;opts.onEvent?.(`${P.name} bats the toy!`);}}}});
   P.happy=Math.max(0,P.happy-d);
   const hp=stepHop(hop,d,{mode:life.mode,speed:life.speed,startle:Math.max(life.startle||0,P.happy>0?.6:0),mp,g:9.8,scale:HEIGHT,groundY:0});
   P.body.position.set(life.x*k,hp.y,life.z*k);P.body.rotation.y=Math.PI/2-life.heading;const sq=hp.squash;P.body.scale.set(1-sq*.5,1+sq,1-sq*.5);
   P.blob.position.set(P.body.position.x,.002,P.body.position.z);const lift=Math.min(1,hp.y/.25);P.blob.scale.setScalar(HEIGHT*1.25*(1-lift*.4));P.blob.material.opacity=1-lift*.6;
   if(i===0){catcher.position.set(P.body.position.x,0,P.body.position.z);host.dataset.arAir=String(hp.air);}
   const gr=P.glb?.root;const ll=gr&&life.lookCam>=.3?(()=>{const v=gr.worldToLocal(new THREE.Vector3(wp.x,wp.y,wp.z));return {yaw:Math.atan2(v.x,v.z),pitch:Math.atan2(v.y-.6,Math.hypot(v.x,v.z))};})():null;
   P.drive(d,{...life,speed:Math.min(1,life.speed*2)},mp,P.glb?ll:(life.lookCam>.3?lookV:null));});
  const life=pets[0].life;
  r.render(scene,cam);
  host.dataset.arLife=life.mode;host.dataset.arKind=kind;host.dataset.arPets=String(pets.length);onState?.(life.mode);
 };
 // ?manual=1 (QA captures): no free-running loop; __arStage.step(dt) advances the life + renders one frame deterministically.
 const qManual=new URLSearchParams(location.search).get('manual')==='1';if(!qManual)r.setAnimationLoop(frameFn);
 (window as any).__arStage={step:(dt:number)=>{manual=dt;frameFn(performance.now());},mode:()=>mode,kind:()=>kind,life:()=>({mode:pets[0].life.mode,x:pets[0].life.x*k,z:pets[0].life.z*k,y:pets[0].body.position.y}),pets:()=>pets.map(p=>({name:p.name,mode:p.life.mode,x:p.life.x*k,z:p.life.z*k})),place,call,feed,toss,pet};
 return {place,call,feed,toss,pet,enableOrientation,startXR,xrSupported,exportUsdz,ready,get mode(){return mode;},
  dispose(){disposed=true;r.setAnimationLoop(null);ro.disconnect();window.removeEventListener('deviceorientation',onOri);try{xrSession?.end();}catch{}pets.forEach(p=>p.dispose());r.dispose();cv.remove();}};
}
