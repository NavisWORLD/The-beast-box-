'use client';
import {useEffect,useRef,useState} from 'react';
import PixelBeast from './pixel-beast';
import Link from 'next/link';
import {useCompanion} from './companion-provider';
import {useBeastSession} from './beast-session';
import {shownName} from '../lib/companion/session.mjs';
import {deriveEmotions,emotionLine} from '../lib/companion/emotion.mjs';
import {createActor,motionPersona,stepActor} from '../lib/companion/film-motion.mjs';

/**
 * Camera field: the device camera feed IS the open field, and the selected creature
 * (3D model, film-style motion, seed-derived emotions) wanders over it, grounded near
 * the bottom of the view. Honest label: NOT AR. No tracking, depth or surface detection.
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
 const stage=useRef<HTMLDivElement>(null),body=useRef<HTMLDivElement>(null);
 const [phase,setPhase]=useState<Phase>('idle'),[msg,setMsg]=useState(''),[react,setReact]=useState('');
 const actor=useRef<any>(null),look=useRef<{x:number;z:number}|null>(null);
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
   if(a&&el){const ps=stepActor(a,dt,{lookAt:look.current,reduced});
    const z=Math.max(-1,Math.min(1,ps.z/W));const depth=.75+.25*(z+1)/2; // z>0 nearer the viewer → lower and bigger
    const left=50+Math.max(-1,Math.min(1,ps.x/W))*38;const bottom=4+(1-(z+1)/2)*16;
    el.style.left=`${left}%`;el.style.bottom=`calc(${floorPx}px + ${bottom}%)`;
    el.style.transform=`translateX(-50%) translateY(${-ps.lift*90}px) scale(${depth*(ps.sx||1)},${depth*(ps.sy||1)}) rotateY(${Math.sin(ps.heading)<0?180:0}deg) rotateX(8deg)`;
    el.dataset.state=ps.state;}
   raf=requestAnimationFrame(tick);};
  raf=requestAnimationFrame(tick);return()=>cancelAnimationFrame(raf);
 },[beast?.seed,profile?.seed,name,em.dominant,floorPx]);// eslint-disable-line react-hooks/exhaustive-deps
 function onTap(e:React.PointerEvent){
  const r=stage.current?.getBoundingClientRect();if(!r||!actor.current)return;
  const fx=(e.clientX-r.left)/r.width,fy=(e.clientY-r.top)/r.height;
  const x=((fx-.5)/.38)*W,z=Math.max(-1,Math.min(1,((fy-.6)/.4)*2-1))*W;
  const onBeast=(e.target as HTMLElement).closest('[data-field-creature]');
  if(onBeast){setReact(`${name} looks up at you. ${emotionLine(name,em)}`);look.current=null;actor.current.state='anticipate';actor.current.t=0;actor.current.dur=.2;actor.current.target={x:actor.current.x,z:actor.current.z};}
  else{const scared=em.dominant==='fear';const tx=scared?actor.current.x-(x-actor.current.x)*.5:x,tz=scared?actor.current.z:z;
   actor.current.target={x:Math.max(-W,Math.min(W,tx)),z:Math.max(-W,Math.min(W,tz))};actor.current.home={...actor.current.target};actor.current.state='walk';actor.current.t=0;actor.current.dur=1.6;
   setReact(scared?`${name} is shy and scoots away from the tap.`:em.dominant==='curiosity'?`${name} goes to sniff what you tapped.`:em.dominant==='mischief'?`${name} zooms over to the spot!`:`${name} heads over to look.`);}
  window.setTimeout(()=>setReact(''),3200);
 }
 const live=phase==='live';
 return <section aria-label="Open Field camera" data-open-field data-camera-field={phase} style={{position:fullscreen?'fixed':'relative',inset:fullscreen?0:undefined,zIndex:fullscreen?0:undefined,margin:fullscreen?0:'12px auto',maxWidth:fullscreen?undefined:560,color:'#e8f4ff'}}>
  <div ref={stage} onPointerDown={onTap} data-field-stage style={{position:'relative',width:'100%',height:fullscreen?'100dvh':'min(70dvh,620px)',borderRadius:fullscreen?0:18,overflow:'hidden',touchAction:'manipulation',background:'radial-gradient(circle at 50% 30%,#2a1d55,#050914 70%)'}}>
   <video ref={video} playsInline muted autoPlay aria-label="Live camera preview (not recorded)" style={{position:'absolute',inset:0,width:'100%',height:'100%',objectFit:'cover',opacity:live?1:0}}/>
   <div aria-hidden style={{position:'absolute',left:0,right:0,bottom:0,height:'26%',background:'linear-gradient(transparent,#0006)',pointerEvents:'none'}}/>
   <div ref={body} data-field-creature style={{display:beast?'block':'none',perspective:600,position:'absolute',left:'50%',bottom:'8%',width:'min(46vw,230px)',height:'min(46vw,230px)',transformOrigin:'50% 100%',willChange:'transform,left,bottom'}}>
    {beast?<div data-field-sprite={beast?.qbeast?.profile?.id||beast.genome.seed} style={{width:'100%',height:'100%',transformStyle:'preserve-3d',filter:'drop-shadow(0 10px 12px #0009)'}}><PixelBeast genome={beast.genome} stage={beast.nativeStage||beast.stage||1} publicSpark pose={em.dominant==='fear'?'emote':em.dominant==='joy'||em.dominant==='mischief'?'react':'idle'} emote={em.dominant==='fear'?'sleep':em.dominant==='joy'?'spark':'watch'} label={`${name} · same recorded-seed sprite as the catalogue`}/></div>:null}
    <span aria-hidden style={{position:'absolute',left:'22%',right:'22%',bottom:2,height:10,borderRadius:'50%',background:'#0008',filter:'blur(4px)',zIndex:-1}}/>
   </div>
   <div style={{position:'absolute',top:fullscreen?'max(100px,calc(env(safe-area-inset-top) + 92px))':10,left:10,right:10,display:'flex',flexWrap:'wrap',gap:6,alignItems:'center',pointerEvents:'none'}}>
    <span style={{padding:'3px 9px',borderRadius:999,background:'#000a',fontSize:11,fontWeight:700}}>{live?'● LIVE CAMERA · NOT RECORDED':'✦ STARFIELD'} · not AR</span>
    <span data-field-emotion={em.dominant} style={{padding:'3px 9px',borderRadius:999,background:'#000a',fontSize:11}}>{name} feels {em.dominant} · {em.choice.motion}</span>
   </div>
   {react?<p role="status" style={{position:'absolute',left:12,right:12,bottom:fullscreen?`calc(${floorPx}px + 34%)`:'28%',margin:0,padding:'6px 10px',borderRadius:12,background:'#0c1228d9',fontSize:13,textAlign:'center',pointerEvents:'none'}}>{react}</p>:null}
   {!beast?<div data-field-no-creature style={{position:'absolute',left:'50%',bottom:`calc(${floorPx}px + 8%)`,transform:'translateX(-50%)',width:'min(300px,84%)',padding:12,borderRadius:16,background:'#0c1228ee',border:'1px solid #7dd9ea66',textAlign:'center',fontSize:13}} onPointerDown={e=>e.stopPropagation()}>No creature picked yet. <a href="/spark/index.html#catalog-picker" style={{color:'#9aefff',fontWeight:700}}>Pick one in the Spark Lab catalogue</a> and it will explore here.</div>:null}
   {!live?<div data-camera-prompt style={{position:'absolute',left:'50%',top:'40%',transform:'translate(-50%,-50%)',width:'min(320px,86%)',padding:14,borderRadius:18,background:'#0c1228ee',border:'1px solid #7dd9ea66',textAlign:'center',boxShadow:'0 12px 36px #0008'}} onPointerDown={e=>e.stopPropagation()}>
    <strong style={{display:'block',fontSize:15}}>📷 Let {name} explore your world</strong>
    <p style={{fontSize:12,color:'#c6d2ee',margin:'6px 0 10px'}}>Your camera becomes the open field. The picture stays on this phone: nothing is recorded or uploaded, and the camera turns off when you leave.</p>
    <button type="button" data-start-camera onClick={()=>void start()} disabled={phase==='asking'} style={{minHeight:44,width:'100%',borderRadius:12,border:'1px solid #78ddea88',background:'#17364a',color:'#d7faff',fontWeight:800}}>{phase==='asking'?'Waiting for permission…':phase==='denied'||phase==='error'?'Try camera again':'Start camera'}</button>
    {msg?<p role="alert" style={{fontSize:12,color:'#ffd2d2',margin:'8px 0 0'}}>{msg}</p>:null}
   </div>:<button type="button" onPointerDown={e=>e.stopPropagation()} onClick={stop} style={{position:'absolute',right:10,top:fullscreen?'max(100px,calc(env(safe-area-inset-top) + 92px))':10,minHeight:36,padding:'4px 12px',borderRadius:999,border:'1px solid #78ddea88',background:'#0c1228e0',color:'#d7faff',fontWeight:700,fontSize:12}}>Stop camera</button>}
  </div>
  {!fullscreen?<p style={{fontSize:11,color:'#9fc6d8',margin:'6px 4px'}}>Tap anywhere and {name} reacts. Emotions come from its seed and real care events only (see the Spark Lab for the why). Camera preview + 3D overlay, not AR: there is no tracking or surface detection.</p>:null}
 </section>;
}
