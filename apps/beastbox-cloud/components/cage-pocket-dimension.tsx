'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import {Compass,Expand,Minus,Plus,RotateCcw,Settings2} from 'lucide-react';
import type {BaseLook,CreatureProfile} from '../lib/creature-profile';
import {renderBeast} from '../public/spark/draw.mjs';
import {createCreatureRig} from '../lib/creature-model';
import styles from './cage-pocket-dimension.module.css';

type View={theta:number;phi:number;zoom:number};
type Pointer={x:number;y:number};
type Props={
 genome:any|null; qbeastId:string|null; profile:CreatureProfile|null;
 fallbackLook:BaseLook; stage:number; state:string; reduced:boolean;
 behaviorPosition:{x:number;y:number}|null; onActiveChange:(active:boolean)=>void;
};
const STORAGE='beastbox-cage-pocket-settings-v1';
const INITIAL:View={theta:.65,phi:1.08,zoom:10};
const clamp=(v:number,low:number,high:number)=>Math.max(low,Math.min(high,v));
const seedValue=(key:string)=>{let h=2166136261;for(const ch of key){h=Math.imul(h^ch.charCodeAt(0),16777619);}return h>>>0;};
/**
 * Actual WebGL 3D environment inside the EXISTING Beast Cage circle.
 * The QBEAST is the existing native 64x64 sprite, displayed as a 3D-world
 * billboard. Orbit/zoom are camera-only; no genome, game or saved authority
 * is manufactured by exploring this local presentation.
 */
export default function CagePocketDimension({genome,qbeastId,profile,fallbackLook,stage,state,reduced,behaviorPosition,onActiveChange}:Props){
 const canvasRef=useRef<HTMLCanvasElement>(null);
 const view=useRef<View>({...INITIAL}),pointers=useRef<Map<number,Pointer>>(new Map());
 const position=useRef(behaviorPosition),motionState=useRef(state),autoRef=useRef(true);
 const [enabled,setEnabled]=useState(true),[ready,setReady]=useState(false),[failed,setFailed]=useState(false);
 const [autoOrbit,setAutoOrbit]=useState(false),[quality,setQuality]=useState<'low'|'auto'>('auto'),[zoom,setZoom]=useState(10),[settingsLoaded,setSettingsLoaded]=useState(false);
 const [message,setMessage]=useState('Drag to orbit · pinch or scroll to zoom');
 const stageSafe=clamp(Math.floor(Number(stage)||1),1,3);
 const id=qbeastId||profile?.id||'visual-preview';
 useEffect(()=>{position.current=behaviorPosition;},[behaviorPosition?.x,behaviorPosition?.y]);
 useEffect(()=>{motionState.current=state;},[state]);
 useEffect(()=>{autoRef.current=autoOrbit;},[autoOrbit]);
 useEffect(()=>{
  try{
   const parsed=JSON.parse(localStorage.getItem(STORAGE)||'null');
   if(parsed&&typeof parsed==='object'){
    if(typeof parsed.enabled==='boolean')setEnabled(parsed.enabled);
    if(parsed.quality==='low'||parsed.quality==='auto')setQuality(parsed.quality);
    if(typeof parsed.autoOrbit==='boolean')setAutoOrbit(parsed.autoOrbit);
   }
  }catch{/* Privacy mode: defaults are entirely local */ }
  finally{setSettingsLoaded(true);}
 },[]);
 useEffect(()=>{
  if(!settingsLoaded)return; // Never overwrite restored preferences with hydration defaults.
  try{localStorage.setItem(STORAGE,JSON.stringify({enabled,quality,autoOrbit}));}catch{/* view works without storage */ }
 },[settingsLoaded,enabled,quality,autoOrbit]);
 useEffect(()=>{onActiveChange(enabled&&ready&&!failed);return()=>onActiveChange(false);},[enabled,ready,failed,onActiveChange]);
 const changeZoom=useCallback((next:number)=>{
  const z=clamp(next,5.7,14.4);view.current.zoom=z;setZoom(z);
 },[]);
 const reset=()=>{view.current={...INITIAL};setZoom(INITIAL.zoom);setMessage('Pocket view reset · same Beast');};
 const onPointerDown=(e:React.PointerEvent<HTMLCanvasElement>)=>{
  if(e.pointerType==='mouse'&&e.button!==0)return;
  e.currentTarget.setPointerCapture(e.pointerId);
  pointers.current.set(e.pointerId,{x:e.clientX,y:e.clientY});
 };
 const onPointerMove=(e:React.PointerEvent<HTMLCanvasElement>)=>{
  const last=pointers.current.get(e.pointerId);if(!last)return;
  if(pointers.current.size===1){
   const v=view.current;
   v.theta-=(e.clientX-last.x)*.009;
   v.phi=clamp(v.phi+(e.clientY-last.y)*.008,.37,1.47);
  }else if(pointers.current.size===2){
   const other=[...pointers.current.entries()].find(([id])=>id!==e.pointerId)?.[1];
   if(other){
    const before=Math.hypot(last.x-other.x,last.y-other.y);
    const after=Math.hypot(e.clientX-other.x,e.clientY-other.y);
    if(before>15&&after>15)changeZoom(view.current.zoom*(before/after));
   }
  }
  pointers.current.set(e.pointerId,{x:e.clientX,y:e.clientY});
 };
 const releasePointer=(e:React.PointerEvent<HTMLCanvasElement>)=>{
  pointers.current.delete(e.pointerId);
  if(e.currentTarget.hasPointerCapture(e.pointerId))e.currentTarget.releasePointerCapture(e.pointerId);
 };
 const onKeyboard=(e:React.KeyboardEvent<HTMLCanvasElement>)=>{
  if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();view.current.theta+=(e.key==='ArrowLeft'?.18:-.18);}
  if(e.key==='ArrowUp'||e.key==='ArrowDown'){e.preventDefault();view.current.phi=clamp(view.current.phi+(e.key==='ArrowUp'?-.14:.14),.37,1.47);}
  if(e.key==='+'||e.key==='='){e.preventDefault();changeZoom(view.current.zoom-.7);}
  if(e.key==='-'){e.preventDefault();changeZoom(view.current.zoom+.7);}
 };
 useEffect(()=>{
  const canvas=canvasRef.current;
  if(!enabled||failed||!canvas)return;
  let disposed=false,raf=0,cleanup=()=>{};
  setReady(false);
  void (async()=>{
   try{
    if(!window.WebGLRenderingContext)throw Error('WebGL is not available');
    const THREE=await import('three');
    if(disposed)return;
    const renderer=new THREE.WebGLRenderer({canvas,alpha:false,antialias:quality==='auto',powerPreference:'low-power'});
    renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,quality==='low'?1:1.5));
    renderer.outputColorSpace=THREE.SRGBColorSpace;
    renderer.setClearColor(0x070d21,1);
    const scene=new THREE.Scene();
    scene.background=new THREE.Color(0x070d21);
    scene.fog=new THREE.FogExp2(0x141333,.038);
    const camera=new THREE.PerspectiveCamera(44,1,.1,80);
    scene.add(new THREE.HemisphereLight(0xaeddfc,0x1c1036,2.1));
    const glow=new THREE.PointLight(0x8befff,25,10);
    glow.position.set(0,4,1);scene.add(glow);
    const rim=new THREE.PointLight(0xffa0eb,18,12);
    rim.position.set(-3,2,-3);scene.add(rim);
    const ground=new THREE.Mesh(new THREE.BoxGeometry(9.1,.32,9.1),new THREE.MeshStandardMaterial({color:0x122644,metalness:.2,roughness:.76}));
    ground.position.y=-.21;scene.add(ground);
    const grid=new THREE.GridHelper(9,12,0x6ad4ff,0x2e5274);
    grid.position.y=-.035;scene.add(grid);
    // A real 3D cube chamber: the circle is only the viewport/mask.
    const chamber=new THREE.Mesh(new THREE.BoxGeometry(9.4,5.3,9.4),new THREE.MeshBasicMaterial({color:0x7757cd,transparent:true,opacity:.048,depthWrite:false,side:THREE.BackSide}));
    chamber.position.y=2.37;scene.add(chamber);
    const chamberEdge=new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(9.4,5.3,9.4)),new THREE.LineBasicMaterial({color:0x6ab5f3,transparent:true,opacity:.27}));
    chamberEdge.position.y=2.37;scene.add(chamberEdge);
    const altar=new THREE.Mesh(new THREE.CylinderGeometry(1.12,1.26,.16,32),new THREE.MeshStandardMaterial({color:0x302b66,metalness:.58,roughness:.4,emissive:0x241152,emissiveIntensity:.3}));
    altar.position.y=.08;scene.add(altar);
    const ring=new THREE.Mesh(new THREE.TorusGeometry(1.32,.032,7,54),new THREE.MeshBasicMaterial({color:0x9bf2ff,transparent:true,opacity:.77}));
    ring.rotation.x=Math.PI/2;ring.position.y=.17;scene.add(ring);
    const seed=seedValue(String(genome?.seed||profile?.id||'beastbox-pocket'));
    let randomState=seed||1;
    const rand=()=>{randomState^=randomState<<13;randomState^=randomState>>>17;randomState^=randomState<<5;return(randomState>>>0)/4294967296;};
    const cubeMat=new THREE.MeshStandardMaterial({color:0x253b69,roughness:.78,metalness:.15});
    const crystalMat=new THREE.MeshStandardMaterial({color:0x73e6ef,emissive:0x1a5a88,emissiveIntensity:.55,roughness:.24,metalness:.38});
    const violetMat=new THREE.MeshStandardMaterial({color:0xc39af1,emissive:0x45288e,emissiveIntensity:.5,roughness:.29,metalness:.25});
    // World geometry is stable for this QBEAST; it is not new quantum data.
    for(let i=0;i<(quality==='low'?22:36);i++){
     const x=(rand()-.5)*8.15,z=(rand()-.5)*8.15;
     if(Math.hypot(x,z)<1.75)continue;
     const h=.15+rand()*.8;
     const mesh=i%3===0
      ?new THREE.Mesh(new THREE.OctahedronGeometry(.18+rand()*.27,0),i%2?crystalMat:violetMat)
      :new THREE.Mesh(new THREE.BoxGeometry(.35+rand()*.45,h,.35+rand()*.45),cubeMat);
     mesh.position.set(x,i%3===0?.28:-.02+h/2,z);
     mesh.rotation.y=rand()*Math.PI;
     scene.add(mesh);
    }
    const starGeo=new THREE.BufferGeometry(),stars:number[]=[];
    for(let i=0;i<(quality==='low'?60:130);i++)stars.push((rand()-.5)*8.7,.7+rand()*4.25,(rand()-.5)*8.7);
    starGeo.setAttribute('position',new THREE.Float32BufferAttribute(stars,3));
    const points=new THREE.Points(starGeo,new THREE.PointsMaterial({color:0xaccfff,size:.042,transparent:true,opacity:.78}));
    scene.add(points);
    let creature:THREE.Object3D;
    let spriteTexture:import('three').CanvasTexture|null=null;
    let rig:ReturnType<typeof createCreatureRig>|null=null;
    if(qbeastId){
     if(!genome?.seed)throw Error('Canonical QBEAST has not restored its genome');
     const rgba=renderBeast(genome,stageSafe,'open');
     if(rgba.length!==64*64*4)throw Error('Canonical sprite did not render at 64x64');
     const art=document.createElement('canvas');art.width=art.height=64;
     const ctx=art.getContext('2d');if(!ctx)throw Error('Native sprite canvas unavailable');
     ctx.putImageData(new ImageData(new Uint8ClampedArray(rgba),64,64),0,0);
     spriteTexture=new THREE.CanvasTexture(art);spriteTexture.colorSpace=THREE.SRGBColorSpace;
     spriteTexture.magFilter=THREE.NearestFilter;spriteTexture.minFilter=THREE.NearestFilter;
     const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:spriteTexture,transparent:true,alphaTest:.015,depthTest:true}));
     sprite.scale.set(2.05,2.05,1);creature=sprite;
    }else{
     rig=createCreatureRig(profile,fallbackLook,quality);
     creature=rig.group;creature.scale.setScalar(.57);
    }
    creature.position.set(0,1.17,0);scene.add(creature);
    const shadow=new THREE.Mesh(new THREE.CircleGeometry(.62,28),new THREE.MeshBasicMaterial({color:0x020a18,transparent:true,opacity:.4,depthWrite:false}));
    shadow.rotation.x=-Math.PI/2;shadow.position.y=.16;scene.add(shadow);
    const onLost=(e:Event)=>{e.preventDefault();setFailed(true);setReady(false);};
    canvas.addEventListener('webglcontextlost',onLost);
    const resize=()=>{
     if(disposed)return;
     const bounds=canvas.getBoundingClientRect();
     if(bounds.width<2||bounds.height<2)return;
     renderer.setSize(Math.floor(bounds.width),Math.floor(bounds.height),false);
     camera.aspect=bounds.width/bounds.height;camera.updateProjectionMatrix();
    };
    const observer=typeof ResizeObserver!=='undefined'?new ResizeObserver(resize):null;
    observer?.observe(canvas);window.addEventListener('resize',resize);resize();
    let previous=performance.now(),lastPaint=0,t=0,rendered=false,visible=true;
    const intersect=typeof IntersectionObserver!=='undefined'?new IntersectionObserver(entries=>{visible=entries.some(e=>e.isIntersecting);},{threshold:.02}):null;
    intersect?.observe(canvas);
    const move=new THREE.Vector3(0,0,0),focus=new THREE.Vector3(0,.9,0);
    const animate=(now:number)=>{
     if(disposed)return;
     raf=requestAnimationFrame(animate);
     const dt=Math.min(.06,Math.max(0,(now-previous)/1000));previous=now;
     if(document.hidden||!visible||now-lastPaint<(quality==='low'?55:33))return;
     lastPaint=now;
     if(!reduced)t+=dt;
     const p=position.current;
     const hasPosition=p&&Number.isFinite(p.x)&&Number.isFinite(p.y);
     const x=hasPosition?(clamp(p.x,0,1)-.5)*5.8:(reduced?0:Math.sin(t*.28+seed%9)*1.2);
     const z=hasPosition?(clamp(p.y,0,1)-.5)*5.8:(reduced?0:Math.cos(t*.23+seed%7)*1.05);
     move.lerp(new THREE.Vector3(x,0,z),Math.min(1,dt*2.5));
     creature.position.set(move.x,1.22+(!reduced?Math.sin(t*1.55)*.09:0),move.z);
     shadow.position.set(move.x,.17,move.z);
     if(rig){rig.halo.rotation.y=t*.5;rig.group.rotation.y=reduced?0:Math.sin(t*.4)*.24;}
     const v=view.current;
     if(autoRef.current&&!reduced&&pointers.current.size===0)v.theta+=dt*.12;
     focus.lerp(new THREE.Vector3(move.x*.25,.7,move.z*.25),Math.min(1,dt*2.4));
     camera.position.set(focus.x+v.zoom*Math.sin(v.phi)*Math.sin(v.theta),
      focus.y+v.zoom*Math.cos(v.phi),
      focus.z+v.zoom*Math.sin(v.phi)*Math.cos(v.theta));
     camera.lookAt(focus);
     ring.rotation.z=reduced?0:t*.07;
     try{renderer.render(scene,camera);}catch{setReady(false);setFailed(true);return;}
     if(!rendered){rendered=true;setReady(true);}
    };
    raf=requestAnimationFrame(animate);
    cleanup=()=>{
     cancelAnimationFrame(raf);window.removeEventListener('resize',resize);
     observer?.disconnect();intersect?.disconnect();canvas.removeEventListener('webglcontextlost',onLost);
     rig?.dispose();
     if(rig)scene.remove(rig.group);
     const geometries=new Set<import('three').BufferGeometry>(),materials=new Set<import('three').Material>();
     scene.traverse(obj=>{
      if(obj instanceof THREE.Mesh||obj instanceof THREE.Points||obj instanceof THREE.LineSegments||obj instanceof THREE.Sprite){
       if(obj instanceof THREE.Mesh||obj instanceof THREE.Points||obj instanceof THREE.LineSegments)geometries.add(obj.geometry);
       const material=obj.material;
       (Array.isArray(material)?material:[material]).forEach(m=>materials.add(m));
      }
     });
     geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());
     spriteTexture?.dispose();renderer.dispose();
    };
   }catch{
    if(!disposed){setReady(false);setFailed(true);setMessage('3D unavailable · original Beast habitat preserved');}
   }
  })();
  return()=>{disposed=true;cancelAnimationFrame(raf);cleanup();setReady(false);};
 },[enabled,failed,quality,id,genome?.seed,profile?.id,stageSafe,fallbackLook,reduced]);
 return <div className={styles.root} data-pocket-dimension="true" data-pocket-state={!enabled?'classic':failed?'fallback':ready?'ready':'loading'} data-creature-id={id}>
  {enabled&&!failed?<canvas ref={canvasRef} className={styles.canvas} data-pocket-webgl="true"
   role="img" aria-label={"Interactive 3D cube-world camera around "+(qbeastId||'the preview creature')+". Drag, pinch or use arrow keys to orbit. This is visual exploration, not native game progression."}
   tabIndex={0} onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={releasePointer} onPointerCancel={releasePointer}
   onKeyDown={onKeyboard} onWheel={e=>{e.preventDefault();changeZoom(view.current.zoom+e.deltaY*.012);}}
  />:null}
  <details className={styles.settings} data-pocket-settings="true">
   <summary><Settings2 size={16} aria-hidden="true"/> World settings</summary>
   <div className={styles.panel}>
    <strong>DIMENSIONAL POCKET</strong>
    <p>Camera-only exploration. This Beast keeps its original QBEAST ID, care, model, memories and native game save.</p>
    <label className={styles.switch}><input type="checkbox" checked={enabled} onChange={e=>{setFailed(false);setEnabled(e.target.checked);}}/>3D pocket enabled</label>
    <label className={styles.switch}><input type="checkbox" checked={autoOrbit} onChange={e=>setAutoOrbit(e.target.checked)}/>Slow camera orbit</label>
    <label>Zoom distance <input type="range" min="5.7" max="14.4" step=".1" value={zoom} disabled={!enabled} onChange={e=>changeZoom(Number(e.target.value))}/></label>
    <label>Render quality <select value={quality} onChange={e=>setQuality(e.target.value==='low'?'low':'auto')}><option value="auto">Balanced</option><option value="low">Battery saver</option></select></label>
    <div className={styles.actions}>
     <button type="button" onClick={()=>changeZoom(view.current.zoom-.9)} disabled={!enabled} aria-label="Zoom into pocket world"><Plus size={16}/> Near</button>
     <button type="button" onClick={()=>changeZoom(view.current.zoom+.9)} disabled={!enabled} aria-label="Zoom out of pocket world"><Minus size={16}/> Far</button>
     <button type="button" onClick={reset}><RotateCcw size={16}/> Reset</button>
    </div>
    <p className={styles.notice}>{failed?'WebGL unavailable: original habitat is active. Try Classic mode.':ready?'3D pocket active · recorded QBEAST preserved':enabled?'Building dimensional space…':'Original circular habitat active'}</p>
   </div>
  </details>
  {ready&&enabled?<div className={styles.hint} aria-hidden="true"><Compass size={13}/> Orbit · pinch to zoom</div>:null}
  {!ready&&enabled&&!failed?<span className={styles.loading} role="status">Opening pocket dimension…</span>:null}
  <span className={styles.sr} role="status">{message}</span>
 </div>;
}
