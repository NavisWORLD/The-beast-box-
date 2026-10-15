'use client';
import {useEffect,useRef,useState} from 'react';
import Creature3DCanvas from './creature-3d-canvas';
import Link from 'next/link';
import {useCompanion} from './companion-provider';
import {useBeastSession} from './beast-session';
import {shownName} from '../lib/companion/session.mjs';
import {deriveEmotions,emotionLine} from '../lib/companion/emotion.mjs';
import {createActor,motionPersona,stepActor,triggerCue} from '../lib/companion/film-motion.mjs';
import {createVisionState,sampleVideoFrame,visionReaction} from '../lib/companion/device-vision.mjs';

/**
 * Camera field: the device camera feed IS a pocket dimension portal opening into reality,
 * and the selected creature (3D model, film-style motion, seed-derived emotions) wanders
 * across the detected surface plane. Honest label: NOT AR.
 * Frames stay on the device; nothing is recorded or uploaded. Tracks stop on exit.
 */
type Phase='idle'|'asking'|'live'|'denied'|'unsupported'|'error';
const W=2.2; // world half-width the actor wanders in
export default function CameraField({fullscreen=false,autoStart=false,floorPx=0,onLive}:{fullscreen?:boolean;autoStart?:boolean;floorPx?:number;onLive?:(live:boolean)=>void}){
 const {profile}=useCompanion();const {session}=useBeastSession();
 // The user's own selected creature: the same saved QBEAST the /spark picker, Surprise Me and the Cage write.
 const beast:any=session?.beast?.genome?.seed?session.beast:null;
 const name=beast?shownName(beast):'your creature';
 const em:any=deriveEmotions(beast);void Link;
 const video=useRef<HTMLVideoElement>(null),stream=useRef<MediaStream|null>(null);
 const visionCanvas=useRef<HTMLCanvasElement|null>(null),visionState=useRef<any>(null);
 const stage=useRef<HTMLDivElement>(null),body=useRef<HTMLDivElement>(null),shadowRef=useRef<HTMLSpanElement>(null),portalRef=useRef<HTMLDivElement>(null);
 const surfaceRef=useRef<{detected:boolean;floorPct:number;tilt:number;kind:string}>({detected:true,floorPct:10,tilt:0,kind:'pocket-plane'});
 const [phase,setPhase]=useState<Phase>('idle'),[msg,setMsg]=useState(''),[react,setReact]=useState('');
 const [visionSummary,setVisionSummary]=useState('pocket dimension ready · not AR');
 const [surfaceLabel,setSurfaceLabel]=useState('pocket rift anchored');
 const actor=useRef<any>(null),actorPose=useRef<any>(null),look=useRef<{x:number;z:number}|null>(null);
 function stop(){stream.current?.getTracks().forEach(t=>t.stop());stream.current=null;if(video.current)video.current.srcObject=null;setPhase(p=>p==='live'||p==='asking'?'idle':p);onLive?.(false);}
 async function start(){
  setMsg('');
  if(typeof navigator==='undefined'||!navigator.mediaDevices?.getUserMedia){setPhase('unsupported');setMsg('This browser has no camera access here (it needs HTTPS and a camera). The creature still wanders on the starfield.');return;}
  setPhase('asking');
  try{const s=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}},audio:false});stream.current=s;const v=video.current;if(v){v.setAttribute('playsinline','');v.muted=true;v.srcObject=s;await v.play().catch(()=>{});}setPhase('live');onLive?.(true);}
  catch(e:any){stream.current?.getTracks().forEach(t=>t.stop());stream.current=null;const denied=e?.name==='NotAllowedError'||e?.name==='SecurityError';setPhase(denied?'denied':'error');setMsg(denied?'Camera permission was not granted. Nothing was recorded. The creature keeps exploring the starfield instead; you can allow the camera in Safari settings (aA → Website Settings → Camera) and tap Start camera again.':`Camera could not start (${e?.name||'error'}). The creature keeps exploring the starfield.`);}
 }
 useEffect(()=>{const hide=()=>{if(document.hidden)stop();};document.addEventListener('visibilitychange',hide);window.addEventListener('pagehide',stop);return()=>{document.removeEventListener('visibilitychange',hide);window.removeEventListener('pagehide',stop);stream.current?.getTracks().forEach(t=>t.stop());stream.current=null;};},[]);
 useEffect(()=>{if(autoStart)void start();},[autoStart]);// eslint-disable-line react-hooks/exhaustive-deps
 // On-device browser vision loop (~8Hz while camera is live): notices motion, faces, light, and horizontal surfaces locally.
 useEffect(()=>{
  if(phase!=='live')return;
  if(!visionCanvas.current&&typeof document!=='undefined')visionCanvas.current=document.createElement('canvas');
  if(!visionState.current)visionState.current=createVisionState();
  const id=window.setInterval(()=>{
   const v=video.current,c=visionCanvas.current,st=visionState.current;
   if(!v||!c||!st)return;
   const obs=sampleVideoFrame(v,c,st);
   if(obs.surface){
    surfaceRef.current=obs.surface;
    setSurfaceLabel(obs.surface.detected?`surface: ${obs.surface.kind} (${Math.round(obs.surface.confidence*100)}%)`:'pocket rift plane');
   }
   const rx=visionReaction(obs,em,{worldWidth:W,name});
   setVisionSummary(rx.summary);
   if(rx.lookAt)look.current=rx.lookAt;
   const a=actor.current;
   if(a&&rx.cue&&(rx.action==='approach'||rx.action==='flee')){
    triggerCue(a,rx.cue,rx.target||rx.lookAt);
    if(rx.noticeLine)setReact(rx.noticeLine);
   }
  },140);
  return()=>window.clearInterval(id);
 },[phase,em,name]);
 // Film-style wander loop. Seeded by the creature's own seed so each creature moves its own way.
 useEffect(()=>{
  const seed=String(beast?.genome?.seed||beast?.seed||profile?.seed||name);
  const p=motionPersona({id:seed,seed});
  // Emotions bias the persona: joy/mischief hop more, fear stays small and close, curiosity roams.
  const persona={...p,hop:Math.min(1,p.hop+(em.joy+em.mischief-80)/400),walk:Math.min(1,p.walk+(em.curiosity-50)/300)};
  actor.current=createActor(persona,{x:0,z:0,radius:em.dominant==='fear'?1:W,seed});
  const reduced=typeof matchMedia!=='undefined'&&matchMedia('(prefers-reduced-motion: reduce)').matches;
  let raf=0,last=performance.now();
  const tick=(t:number)=>{const dt=(t-last)/1000;last=t;const a=actor.current;const el=body.current;
   if(a&&el){const ps=stepActor(a,dt,{lookAt:look.current,emotion:em,reduced});actorPose.current=ps;
    const surf=surfaceRef.current;
    const baseFloor=surf?.floorPct??8;
    const z=Math.max(-1,Math.min(1,ps.z/W));const depth=.78+.24*(z+1)/2; // z>0 nearer the viewer → lower and bigger
    const left=50+Math.max(-1,Math.min(1,ps.x/W))*36;const bottom=Math.max(4,baseFloor-4)+(1-(z+1)/2)*15;
    el.style.left=`${left}%`;el.style.bottom=`calc(${floorPx}px + ${bottom}%)`;
    el.style.transform=`translateX(-50%) translateY(${-ps.lift*90}px) scale(${depth*(ps.sx||1)},${depth*(ps.sy||1)}) rotateY(${Math.sin(ps.heading)<0?180:0}deg) rotateX(8deg) rotateZ(${(surf?.tilt||0)*0.35}deg)`;
    el.dataset.state=ps.state;
    if(shadowRef.current){shadowRef.current.style.transform=`scale(${ps.shadowScale??1})`;shadowRef.current.style.opacity=String(ps.shadowOpacity??0.65);}
    if(portalRef.current){
     portalRef.current.style.bottom=`calc(${floorPx}px + ${Math.max(3,baseFloor-2)}%)`;
     portalRef.current.style.transform=`translateX(-50%) perspective(520px) rotateX(68deg) rotateZ(${surf?.tilt||0}deg)`;
    }}
   raf=requestAnimationFrame(tick);};
  raf=requestAnimationFrame(tick);return()=>cancelAnimationFrame(raf);
 },[beast?.seed,profile?.seed,name,em.dominant,floorPx]);// eslint-disable-line react-hooks/exhaustive-deps
 function onTap(e:React.PointerEvent){
  const r=stage.current?.getBoundingClientRect();if(!r||!actor.current)return;
  const fx=(e.clientX-r.left)/r.width,fy=(e.clientY-r.top)/r.height;
  const x=((fx-.5)/.38)*W,z=Math.max(-1,Math.min(1,((fy-.6)/.4)*2-1))*W;
  const onBeast=(e.target as HTMLElement).closest('[data-field-creature]');
  if(onBeast){setReact(`${name} looks up at you through the pocket rift. ${emotionLine(name,em)}`);look.current=null;actor.current.state='anticipate';actor.current.t=0;actor.current.dur=.2;actor.current.target={x:actor.current.x,z:actor.current.z};}
  else{const scared=em.dominant==='fear';const tx=scared?actor.current.x-(x-actor.current.x)*.5:x,tz=scared?actor.current.z:z;
   const target={x:Math.max(-W,Math.min(W,tx)),z:Math.max(-W,Math.min(W,tz))};
   actor.current.target=target;actor.current.home={...target};
   triggerCue(actor.current,scared?'scared':em.dominant==='curiosity'?'curious':em.dominant==='mischief'?'zoomies':'walk',target);
   setReact(scared?`${name} is shy and scoots away from the tap.`:em.dominant==='curiosity'?`${name} goes to sniff the surface you tapped.`:em.dominant==='mischief'?`${name} zooms across the pocket rift to the spot!`:`${name} heads over to look.`);}
  window.setTimeout(()=>setReact(''),3200);
 }
 const live=phase==='live';
 return <section aria-label="Open Field camera" data-open-field data-camera-field={phase} style={{position:fullscreen?'fixed':'relative',inset:fullscreen?0:undefined,zIndex:fullscreen?0:undefined,margin:fullscreen?0:'12px auto',maxWidth:fullscreen?undefined:560,color:'#e8f4ff'}}>
  <div ref={stage} onPointerDown={onTap} data-field-stage style={{position:'relative',width:'100%',height:fullscreen?'100dvh':'min(70dvh,620px)',borderRadius:fullscreen?0:18,overflow:'hidden',touchAction:'manipulation',background:'radial-gradient(circle at 50% 35%,#361f6e 0%,#120a2e 48%,#040711 92%)',boxShadow:'inset 0 0 48px rgba(142,92,255,0.28)'}}>
   <video ref={video} playsInline muted autoPlay aria-label="Live camera preview (not recorded)" style={{position:'absolute',inset:0,width:'100%',height:'100%',objectFit:'cover',opacity:live?1:0}}/>
   {/* Vivid Pocket Dimension Portal Vignette & Surface Rift Ring */}
   <div aria-hidden style={{position:'absolute',inset:0,pointerEvents:'none',background:'radial-gradient(circle at 50% 55%,transparent 48%,rgba(18,8,44,0.52) 82%,rgba(8,4,22,0.84) 100%)',boxShadow:'inset 0 0 36px rgba(120,235,255,0.24)'}}/>
   <div ref={portalRef} data-pocket-portal aria-hidden style={{position:'absolute',left:'50%',bottom:`calc(${floorPx}px + 8%)`,width:'min(86vw,440px)',height:'min(46vw,230px)',transform:'translateX(-50%) perspective(520px) rotateX(68deg)',borderRadius:'50%',pointerEvents:'none',background:'radial-gradient(ellipse at center,rgba(125,249,255,0.24) 0%,rgba(176,102,255,0.22) 45%,rgba(18,8,42,0.08) 68%,transparent 75%)',border:'2px solid rgba(138,245,255,0.52)',boxShadow:'0 0 32px rgba(138,245,255,0.42), inset 0 0 28px rgba(186,112,255,0.45)',transition:'bottom 140ms ease-out'}}/>
   <div aria-hidden style={{position:'absolute',left:0,right:0,bottom:0,height:'26%',background:'linear-gradient(transparent,#0006)',pointerEvents:'none'}}/>
   <div ref={body} data-field-creature style={{display:beast?'block':'none',perspective:600,position:'absolute',left:'50%',bottom:'8%',width:'min(48vw,240px)',height:'min(48vw,240px)',transformOrigin:'50% 100%',willChange:'transform,left,bottom'}}>
    {beast?<div data-field-sprite={beast?.qbeast?.profile?.id||beast.genome.seed} style={{width:'100%',height:'100%',transformStyle:'preserve-3d',filter:'drop-shadow(0 12px 16px rgba(6,2,20,0.75)) drop-shadow(0 0 14px rgba(130,235,255,0.28))'}}><Creature3DCanvas genome={beast.genome} stage={beast.nativeStage||beast.stage||1} emotion={em} actorPoseRef={actorPose} lookAtRef={look} label={`${name} · 3D living companion from recorded-seed sprite`}/></div>:null}
    <span ref={shadowRef} data-contact-shadow aria-hidden style={{position:'absolute',left:'20%',right:'20%',bottom:2,height:12,borderRadius:'50%',background:'radial-gradient(ellipse at center,rgba(4,2,14,0.82) 0%,rgba(98,225,255,0.25) 65%,transparent 100%)',filter:'blur(3px)',zIndex:-1,transition:'transform 60ms linear'}}/>
   </div>
   <div style={{position:'absolute',top:fullscreen?'max(100px,calc(env(safe-area-inset-top) + 92px))':10,left:10,right:10,display:'flex',flexWrap:'wrap',gap:6,alignItems:'center',pointerEvents:'none'}}>
    <span style={{padding:'3px 9px',borderRadius:999,background:'#080d22cc',border:'1px solid #7dd9ea44',fontSize:11,fontWeight:700}}>{live?'● POCKET DIMENSION LIVE · NOT RECORDED':'✦ POCKET DIMENSION PORTAL'} · not AR</span>
    <span data-field-emotion={em.dominant} style={{padding:'3px 9px',borderRadius:999,background:'#080d22cc',border:'1px solid #b57bff44',fontSize:11}}>{name} feels {em.dominant} · {em.choice.motion}</span>
    <span data-field-vision style={{padding:'3px 9px',borderRadius:999,background:'#080d22cc',border:'1px solid #7dd9ea44',fontSize:11}}>{live?`👁 ${visionSummary}`:`👁 on-device vision + ${surfaceLabel} · not AR`}</span>
   </div>
   {react?<p role="status" style={{position:'absolute',left:12,right:12,bottom:fullscreen?`calc(${floorPx}px + 34%)`:'28%',margin:0,padding:'6px 10px',borderRadius:12,background:'#0c1228d9',border:'1px solid #7dd9ea55',fontSize:13,textAlign:'center',pointerEvents:'none'}}>{react}</p>:null}
   {!beast?<div data-field-no-creature style={{position:'absolute',left:'50%',bottom:`calc(${floorPx}px + 8%)`,transform:'translateX(-50%)',width:'min(300px,84%)',padding:12,borderRadius:16,background:'#0c1228ee',border:'1px solid #7dd9ea66',textAlign:'center',fontSize:13}} onPointerDown={e=>e.stopPropagation()}>No creature picked yet. <a href="/spark/index.html#catalog-picker" style={{color:'#9aefff',fontWeight:700}}>Pick one in the Spark Lab catalogue</a> and it will explore here.</div>:null}
   {!live?<div data-camera-prompt style={{position:'absolute',left:'50%',top:'40%',transform:'translate(-50%,-50%)',width:'min(320px,86%)',padding:14,borderRadius:18,background:'#0c1228ee',border:'1px solid #7dd9ea66',textAlign:'center',boxShadow:'0 12px 36px #0008'}} onPointerDown={e=>e.stopPropagation()}>
    <strong style={{display:'block',fontSize:15}}>🌀 Open Pocket Dimension for {name}</strong>
    <p style={{fontSize:12,color:'#c6d2ee',margin:'6px 0 10px'}}>Opens a dimensional rift into your camera view with on-device surface, motion, face, and light sensing. Nothing is ever recorded or uploaded.</p>
    <button type="button" data-start-camera onClick={()=>void start()} disabled={phase==='asking'} style={{minHeight:44,width:'100%',borderRadius:12,border:'1px solid #78ddea88',background:'linear-gradient(135deg,#1b415a,#2d1f5e)',color:'#d7faff',fontWeight:800}}>{phase==='asking'?'Opening rift…':phase==='denied'||phase==='error'?'Try camera again':'Start camera'}</button>
    {msg?<p role="alert" style={{fontSize:12,color:'#ffd2d2',margin:'8px 0 0'}}>{msg}</p>:null}
   </div>:<button type="button" onPointerDown={e=>e.stopPropagation()} onClick={stop} style={{position:'absolute',right:10,top:fullscreen?'max(100px,calc(env(safe-area-inset-top) + 92px))':10,minHeight:36,padding:'4px 12px',borderRadius:999,border:'1px solid #78ddea88',background:'#0c1228e0',color:'#d7faff',fontWeight:700,fontSize:12}}>Stop camera</button>}
  </div>
  {!fullscreen?<p style={{fontSize:11,color:'#9fc6d8',margin:'6px 4px'}}>Tap anywhere on the dimensional surface and {name} reacts. On-device vision senses surfaces, motion, faces and room light locally (never uploaded or recorded). Camera preview + 3D pocket rift overlay, not AR.</p>:null}
 </section>;
}
