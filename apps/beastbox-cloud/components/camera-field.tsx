'use client';
import {useEffect,useRef,useState} from 'react';
import {useCompanion} from './companion-provider';
import {useBeastSession} from './beast-session';
import {shownName} from '../lib/companion/session.mjs';
import {deriveEmotions,emotionLine} from '../lib/companion/emotion.mjs';
import type {ArMode} from './ar-creature-stage';

/**
 * Camera field (Oct 16 2026 AR rewrite): the device camera feed is the open field and the selected creature is its real
 * 3D model (sculpted GLB, fur, CST-driven life + grounded hops) standing on the floor with a contact shadow.
 * Modes, labelled honestly on screen: WebXR AR (surface hit-test) where the browser has it; on iPhone Safari a camera
 * overlay anchored with the motion sensors (rotation only, floor assumed below the phone, tap to place); otherwise a fixed view.
 * iPhone also gets Quick Look (true ARKit AR) via a USDZ export of the model. Frames stay on the device; tracks stop on exit.
 */
type Phase='idle'|'asking'|'live'|'denied'|'unsupported'|'error';
type Stage=Awaited<ReturnType<typeof import('./ar-creature-stage').createArStage>>;
const MODE_LABEL:Record<ArMode,string>={xr:'WebXR AR · real surface tracking',anchored:'Motion-anchored overlay · rotation tracked, floor assumed ~1.35 m below (not full AR)',preview:'Fixed view · no motion tracking'};
export default function CameraField({fullscreen=false,autoStart=false,floorPx=0,onLive}:{fullscreen?:boolean;autoStart?:boolean;floorPx?:number;onLive?:(live:boolean)=>void}){
 const {profile}=useCompanion();const {session}=useBeastSession();void profile;
 // The user's own selected creature: the same saved QBEAST the /spark picker, Surprise Me and the Cage write.
 const beast:any=session?.beast?.genome?.seed?session.beast:null;
 const name=beast?shownName(beast):'your creature';
 const em:any=deriveEmotions(beast);
 const video=useRef<HTMLVideoElement>(null),stream=useRef<MediaStream|null>(null);
 const stage=useRef<HTMLDivElement>(null),host=useRef<HTMLDivElement>(null),ar=useRef<Stage|null>(null);
 const [phase,setPhase]=useState<Phase>('idle'),[msg,setMsg]=useState(''),[react,setReact]=useState('');
 const [mode,setMode]=useState<ArMode>('preview'),[xrOk,setXrOk]=useState(false),[qlOk,setQlOk]=useState(false),[placed,setPlaced]=useState(false),[usdz,setUsdz]=useState<string|null>(null),[busy,setBusy]=useState(false);
function stop(){stream.current?.getTracks().forEach(t=>t.stop());stream.current=null;if(video.current)video.current.srcObject=null;setPhase(p=>p==='live'||p==='asking'?'idle':p);onLive?.(false);}
 async function start(){
  setMsg('');const oriP=ar.current?.enableOrientation();
  if(typeof navigator==='undefined'||!navigator.mediaDevices?.getUserMedia){setPhase('unsupported');setMsg('This browser has no camera access here (it needs HTTPS and a camera). The creature still wanders on the starfield.');return;}
  setPhase('asking');
  try{const s=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}},audio:false});stream.current=s;const v=video.current;if(v){v.setAttribute('playsinline','');v.muted=true;v.srcObject=s;await v.play().catch(()=>{});}setPhase('live');onLive?.(true);void oriP?.then(ok=>{if(ok===false)setMsg('Motion sensors were not allowed, so the view stays fixed. Tap the floor to place your creature.');});}
  catch(e:any){stream.current?.getTracks().forEach(t=>t.stop());stream.current=null;const denied=e?.name==='NotAllowedError'||e?.name==='SecurityError';setPhase(denied?'denied':'error');setMsg(denied?'Camera permission was not granted. Nothing was recorded. The creature keeps exploring the starfield instead; you can allow the camera in Safari settings (aA → Website Settings → Camera) and tap Start camera again.':`Camera could not start (${e?.name||'error'}). The creature keeps exploring the starfield.`);}
 }
 useEffect(()=>{const hide=()=>{if(document.hidden)stop();};document.addEventListener('visibilitychange',hide);window.addEventListener('pagehide',stop);return()=>{document.removeEventListener('visibilitychange',hide);window.removeEventListener('pagehide',stop);stream.current?.getTracks().forEach(t=>t.stop());stream.current=null;};},[]);
 useEffect(()=>{if(autoStart)void start();},[autoStart]);// eslint-disable-line react-hooks/exhaustive-deps
 // The 3D AR stage: real GLB creature living on the floor (see ar-creature-stage.ts).
 useEffect(()=>{const el=host.current;if(!el||!beast?.genome)return;let gone=false,st:Stage|null=null;
  void import('./ar-creature-stage').then(async({createArStage})=>{if(gone)return;
   st=await createArStage(el,beast.genome,{onMode:setMode,onPlaced:()=>setPlaced(true)});if(gone){st.dispose();return;}ar.current=st;
   setXrOk(await st.xrSupported());const a=document.createElement('a');setQlOk(!!a.relList?.supports?.('ar'));
  }).catch(()=>setMsg('3D could not start on this device.'));
  return()=>{gone=true;st?.dispose();ar.current=null;};
 },[beast?.genome?.seed]);// eslint-disable-line react-hooks/exhaustive-deps
 async function startXR(){const st=ar.current;if(!st)return;const ok=await st.startXR(stage.current||undefined);if(!ok)setMsg('WebXR AR could not start here; using the camera overlay instead.');}
 async function quickLook(){const st=ar.current;if(!st)return;setBusy(true);try{const url=usdz||await st.exportUsdz();setUsdz(url);
  const a=document.createElement('a');a.rel='ar';a.href=url;a.download=`${name}.usdz`;const img=document.createElement('img');a.appendChild(img);document.body.appendChild(a);a.click();a.remove();}catch{setMsg('Quick Look export failed on this device.');}finally{setBusy(false);}}
 function say(t:string){setReact(t);window.setTimeout(()=>setReact(''),3200);}
 function onTap(e:React.PointerEvent){
  if((e.target as HTMLElement).closest('button,a,[data-camera-prompt]'))return;
  const st=ar.current;if(!st||mode==='xr')return;
  if(st.place(e.clientX,e.clientY)){const scared=em.dominant==='fear';say(scared?`${name} is shy and edges over to the new spot.`:em.dominant==='mischief'?`${name} zooms over to the spot!`:`${name} trots over to explore. ${emotionLine(name,em)}`);}
  else say('Tap the floor (below the horizon) to place '+name+'.');
 }
 const live=phase==='live';
 return <section aria-label="Open Field camera" data-open-field data-camera-field={phase} style={{position:fullscreen?'fixed':'relative',inset:fullscreen?0:undefined,zIndex:fullscreen?0:undefined,margin:fullscreen?0:'12px auto',maxWidth:fullscreen?undefined:560,color:'#e8f4ff'}}>
  <div ref={stage} onPointerDown={onTap} data-field-stage style={{position:'relative',width:'100%',height:fullscreen?'100dvh':'min(70dvh,620px)',borderRadius:fullscreen?0:18,overflow:'hidden',touchAction:'manipulation',background:'radial-gradient(circle at 50% 30%,#2a1d55,#050914 70%)'}}>
   <video ref={video} playsInline muted autoPlay aria-label="Live camera preview (not recorded)" style={{position:'absolute',inset:0,width:'100%',height:'100%',objectFit:'cover',opacity:live?1:0}}/>
   <div aria-hidden style={{position:'absolute',left:0,right:0,bottom:0,height:'26%',background:'linear-gradient(transparent,#0006)',pointerEvents:'none'}}/>
   <div ref={host} data-field-creature data-ar-host data-live={live?'1':'0'} role="img" aria-label={`${name} in 3D on your floor`} style={{display:beast?'block':'none',position:'absolute',inset:0,bottom:floorPx}}/>
   <div data-field-chips style={{position:'absolute',top:fullscreen?'max(100px,calc(env(safe-area-inset-top) + 92px))':10,left:10,right:live?124:10,display:'flex',flexWrap:'wrap',gap:6,alignItems:'center',pointerEvents:'none'}}>
    <span data-ar-mode={mode} style={{padding:'3px 9px',borderRadius:999,background:'#000a',fontSize:11,fontWeight:700}}>{live?'● LIVE CAMERA · NOT RECORDED':'✦ STARFIELD'} · {MODE_LABEL[mode]}</span>
    <span data-field-emotion={em.dominant} style={{padding:'3px 9px',borderRadius:999,background:'#000a',fontSize:11}}>{name} feels {em.dominant}</span>
   </div>
   {react?<p role="status" style={{position:'absolute',left:12,right:12,bottom:`calc(${floorPx}px + 12px)`,margin:0,padding:'6px 10px',borderRadius:12,background:'#0c1228d9',fontSize:13,textAlign:'center',pointerEvents:'none'}}>{react}</p>:null}
   {!beast?<div data-field-no-creature style={{position:'absolute',left:'50%',bottom:`calc(${floorPx}px + 8%)`,transform:'translateX(-50%)',width:'min(300px,84%)',padding:12,borderRadius:16,background:'#0c1228ee',border:'1px solid #7dd9ea66',textAlign:'center',fontSize:13}} onPointerDown={e=>e.stopPropagation()}>No creature picked yet. <a href="/spark/index.html#catalog-picker" style={{color:'#9aefff',fontWeight:700}}>Pick one in the Spark Lab catalogue</a> and it will explore here.</div>:null}
   {!live?<div data-camera-prompt style={{position:'absolute',left:'50%',top:'40%',transform:'translate(-50%,-50%)',width:'min(320px,86%)',padding:14,borderRadius:18,background:'#0c1228ee',border:'1px solid #7dd9ea66',textAlign:'center',boxShadow:'0 12px 36px #0008'}} onPointerDown={e=>e.stopPropagation()}>
    <strong style={{display:'block',fontSize:15}}>📷 Let {name} explore your world</strong>
    <p style={{fontSize:12,color:'#c6d2ee',margin:'6px 0 10px'}}>Your camera becomes the open field. The picture stays on this phone: nothing is recorded or uploaded, and the camera turns off when you leave.</p>
    <button type="button" data-start-camera onClick={()=>void start()} disabled={phase==='asking'} style={{minHeight:44,width:'100%',borderRadius:12,border:'1px solid #78ddea88',background:'#17364a',color:'#d7faff',fontWeight:800}}>{phase==='asking'?'Waiting for permission…':phase==='denied'||phase==='error'?'Try camera again':'Start camera'}</button>
    {msg?<p role="alert" style={{fontSize:12,color:'#ffd2d2',margin:'8px 0 0'}}>{msg}</p>:null}
   </div>:<><div data-ar-actions style={{position:'absolute',left:10,right:10,bottom:`calc(${floorPx}px + 56px)`,display:'flex',gap:8,justifyContent:'center',flexWrap:'wrap'}} onPointerDown={e=>e.stopPropagation()}>
     {xrOk&&mode!=='xr'?<button type="button" data-start-xr onClick={()=>void startXR()} style={{minHeight:44,padding:'0 14px',borderRadius:999,border:'1px solid #78ddea88',background:'#17364aee',color:'#d7faff',fontWeight:800}}>Start AR (surface tracking)</button>:null}
     {qlOk&&beast?<button type="button" data-quick-look onClick={()=>void quickLook()} disabled={busy} style={{minHeight:44,padding:'0 14px',borderRadius:999,border:'1px solid #b9a2ff88',background:'#2a1d55ee',color:'#efe6ff',fontWeight:800}}>{busy?'Preparing…':'View in your room (Quick Look AR)'}</button>:null}
     {!placed&&mode!=='xr'?<span style={{padding:'6px 10px',borderRadius:999,background:'#000a',fontSize:12}}>Point at the floor and tap to place {name}</span>:null}
    </div><button type="button" onPointerDown={e=>e.stopPropagation()} onClick={stop} style={{position:'absolute',right:10,top:fullscreen?'max(100px,calc(env(safe-area-inset-top) + 92px))':10,minHeight:36,padding:'4px 12px',borderRadius:999,border:'1px solid #78ddea88',background:'#0c1228e0',color:'#d7faff',fontWeight:700,fontSize:12}}>Stop camera</button></>}
  </div>
  {!fullscreen?<p style={{fontSize:11,color:'#9fc6d8',margin:'6px 4px'}}>Tap anywhere and {name} reacts. Emotions come from its seed and real care events only (see the Spark Lab for the why). On iPhone the creature is anchored with the motion sensors (rotation only, floor assumed): not full AR. Quick Look and WebXR give real surface-tracked AR.</p>:null}
 </section>;
}
