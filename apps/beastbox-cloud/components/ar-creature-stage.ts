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
type Three=typeof import('three');
export type ArMode='xr'|'anchored'|'preview';
export const EYE_HEIGHT=1.35; // assumed phone height above the floor in anchored mode (metres)
const ROAM=.55,HEIGHT=.3; // roam radius around the placed spot, creature height (metres)
export async function createArStage(host:HTMLElement,gen:PlushGenome,{onMode,onPlaced,onState}:{onMode?:(m:ArMode)=>void;onPlaced?:(p:{x:number;y:number;z:number})=>void;onState?:(s:string)=>void}={}){
 const THREE:Three=await import('three');
 const [{loadBeastGlb,beastStudio,GLB_PLANS},{buildPlush},cst,{createLife,stepLife,POCKET_RADIUS},{createHop,stepHop}]=await Promise.all([
  import('./creature-glb-beast'),import('./creature-plush-3d'),import('../lib/physics/cst-integrator.mjs'),import('../lib/creatures3d/life-brain.mjs'),import('../lib/physics/ground-hop.mjs')]);
 const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
 const r=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'default'});r.setPixelRatio(Math.min(devicePixelRatio||1,2));r.outputColorSpace=THREE.SRGBColorSpace;
 r.setClearColor(0x000000,0);r.shadowMap.enabled=true;r.shadowMap.type=THREE.PCFSoftShadowMap;
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
 // creature
 const body=new THREE.Group();anchor.add(body);let drive:(dt:number,l:any,mp:any,look:any)=>void=()=>{};let dispose=()=>{};let foot=0,glbRef:any=null;
 const fit=(o:any)=>{o.updateMatrixWorld(true);const bb=new THREE.Box3().setFromObject(o);const h=Math.max(.01,bb.max.y-bb.min.y);o.scale.multiplyScalar(HEIGHT/h);o.updateMatrixWorld(true);bb.setFromObject(o);foot=-bb.min.y+o.position.y;o.position.y=foot;};
 const plush=buildPlush(THREE,gen as any,{low:true});body.add(plush.root);fit(plush.root);drive=(dt,l,mp,lk)=>plush.drive(dt,l,mp,lk);dispose=()=>plush.dispose();
 let kind='plush';
 const ready=GLB_PLANS.includes(gen.body)?loadBeastGlb(THREE,gen,{tier:'high'}).then(gb=>{if(!gb||disposed){gb?.dispose();return;}plush.root.visible=false;body.add(gb.root);fit(gb.root);glbRef=gb;kind='glb';
   drive=(dt,l,mp,lk)=>gb.drive(dt,l,mp,lk);const pd=dispose;dispose=()=>{gb.dispose();pd();};}).catch(()=>{}):Promise.resolve();
 const S=cst.createCSTState(gen.seed);const life:any=createLife(gen.seed,{x:.4,z:.3});const hop=createHop(gen.seed);const k=ROAM/POCKET_RADIUS;
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
  anchor.position.copy(hit);life.x=0;life.z=0;life.mode='approach';life.timer=2;onPlaced?.({x:hit.x,y:hit.y,z:hit.z});return true;}
 // ---- WebXR immersive-ar with hit-test
 let xrSession:any=null,hitSource:any=null;
 async function xrSupported(){try{return !!(navigator as any).xr&&await (navigator as any).xr.isSessionSupported('immersive-ar');}catch{return false;}}
 async function startXR(overlay?:HTMLElement){const xr=(navigator as any).xr;if(!xr)return false;
  try{xrSession=await xr.requestSession('immersive-ar',{requiredFeatures:['hit-test'],optionalFeatures:['dom-overlay','local-floor'],...(overlay?{domOverlay:{root:overlay}}:{})});}catch{return false;}
  r.xr.enabled=true;r.xr.setReferenceSpaceType('local');await r.xr.setSession(xrSession);
  const viewer=await xrSession.requestReferenceSpace('viewer');hitSource=await xrSession.requestHitTestSource({space:viewer});
  xrSession.addEventListener('select',()=>{if(ring.visible){anchor.position.setFromMatrixPosition(ring.matrix);floor.constant=-anchor.position.y;life.x=0;life.z=0;onPlaced?.({...anchor.position});}});
  xrSession.addEventListener('end',()=>{hitSource=null;xrSession=null;r.xr.enabled=false;ring.visible=false;setMode(ori?'anchored':'preview');});
  setMode('xr');return true;}
 // ---- Quick Look (iOS AR): USDZ of the visible model meshes (static bind pose, flat paint colours)
 async function exportUsdz(){await ready;const {USDZExporter}=await import('three/examples/jsm/exporters/USDZExporter.js');
  const grp=new THREE.Group();const src=glbRef?.root||plush.root;src.updateMatrixWorld(true);const C=glbRef?.colors;
  src.traverse((o:any)=>{if(!o.isMesh||o.userData.shell||!o.visible)return;let vis=true;for(let p=o.parent;p;p=p.parent)if(!p.visible)vis=false;if(!vis)return;
   const m0:any=Array.isArray(o.material)?o.material[0]:o.material;const col=m0?.vertexColors&&C?C.base:(m0?.color||new THREE.Color(0xcccccc));
   const m=new THREE.Mesh(o.geometry,new THREE.MeshStandardMaterial({color:col,roughness:m0?.roughness??.7,metalness:m0?.metalness??0,emissive:m0?.emissive||new THREE.Color(0),emissiveIntensity:m0?.emissiveIntensity??0}));
   o.matrixWorld.decompose(m.position,m.quaternion,m.scale);grp.add(m);});
  const bb=new THREE.Box3().setFromObject(grp);const sc=HEIGHT/Math.max(.01,bb.max.y-bb.min.y);grp.scale.setScalar(sc);grp.position.y=-bb.min.y*sc;const wrap=new THREE.Group();wrap.add(grp);
  const data=await new USDZExporter().parseAsync(wrap);return URL.createObjectURL(new Blob([data],{type:'model/vnd.usdz+zip'}));}
 // ---- loop
 const size=()=>{const w=host.clientWidth||300,h=host.clientHeight||300;r.setSize(w,h,false);cam.aspect=w/h;
  // the rear camera in portrait shows ~70° vertically; object-fit:cover on a tall screen keeps that, on wide boxes it crops vertically
  cam.fov=w/h<3/4?66:THREE.MathUtils.radToDeg(2*Math.atan(Math.tan(THREE.MathUtils.degToRad(33))*(3/4)/(w/h)));cam.updateProjectionMatrix();};
 size();const ro=new ResizeObserver(size);ro.observe(host);
 let disposed=false,last=performance.now(),manual=-1;const lookV={x:0,y:0,z:0},lp=new THREE.Vector3(),wp=new THREE.Vector3();
 const frameFn=(now:number,frame?:any)=>{if(disposed)return;const dt=manual>=0?manual:Math.min(.05,(now-last)/1000);last=now;if(manual>=0)manual=-1;
  if(frame&&hitSource){const res=frame.getHitTestResults(hitSource);if(res.length){const p=res[0].getPose(r.xr.getReferenceSpace());if(p){ring.matrix.fromArray(p.transform.matrix);ring.visible=true;}}else ring.visible=false;}
  else poseCam();
  const d=reduced?0:dt;cst.stepCSTState(S,d);const mp=cst.motionParams(S);
  cam.getWorldPosition(wp);anchor.worldToLocal(lp.copy(wp));
  stepLife(life,d,{mood:mp.mood,cam:{x:lp.x/k,z:lp.z/k},rain:0});
  const hp=stepHop(hop,d,{mode:life.mode,speed:life.speed,startle:life.startle||0,mp,g:9.8,scale:HEIGHT,groundY:0});
  body.position.set(life.x*k,hp.y,life.z*k);body.rotation.y=Math.PI/2-life.heading;const sq=hp.squash;body.scale.set(1-sq*.5,1+sq,1-sq*.5);
  blob.position.set(body.position.x,.002,body.position.z);const lift=Math.min(1,hp.y/.25);blob.scale.setScalar(HEIGHT*1.25*(1-lift*.4));(blob.material as any).opacity=1-lift*.6;
  catcher.position.set(body.position.x,0,body.position.z);
  lookV.x=wp.x;lookV.y=wp.y;lookV.z=wp.z;
  const ll=(()=>{const gr=glbRef?.root;if(!gr||life.lookCam<.3)return null;const v=gr.worldToLocal(new THREE.Vector3(wp.x,wp.y,wp.z));return {yaw:Math.atan2(v.x,v.z),pitch:Math.atan2(v.y-.6,Math.hypot(v.x,v.z))};})();
  drive(d,{...life,speed:Math.min(1,life.speed*2)},mp,glbRef?ll:(life.lookCam>.3?lookV:null));
  r.render(scene,cam);
  host.dataset.arLife=life.mode;host.dataset.arAir=String(hp.air);host.dataset.arKind=kind;onState?.(life.mode);
 };
 r.setAnimationLoop(frameFn);
 (window as any).__arStage={step:(dt:number)=>{manual=dt;},mode:()=>mode,kind:()=>kind,life:()=>({mode:life.mode,x:life.x*k,z:life.z*k,y:body.position.y}),place};
 return {place,enableOrientation,startXR,xrSupported,exportUsdz,ready,get mode(){return mode;},
  dispose(){disposed=true;r.setAnimationLoop(null);ro.disconnect();window.removeEventListener('deviceorientation',onOri);try{xrSession?.end();}catch{}dispose();r.dispose();cv.remove();}};
}
