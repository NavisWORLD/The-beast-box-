'use client';
import {useEffect,useRef,useState} from 'react';
import CosmicCompanion3D from './cosmic-companion-3d';
import ZerefSprite3D from './zeref-sprite-3d';
import {useCompanion} from './companion-provider';
import {useBeastSession} from './beast-session';
import {shownName} from '../lib/companion/session.mjs';
import {talkPersona} from '../lib/companion/beast-talk.mjs';
import {ZEREF_PROFILE} from '../lib/zeref/zeref-mind.mjs';
import {speakWith,voiceStatus} from '../lib/companion/voice-provider.mjs';

type Caps={camera:boolean;mic:boolean;motion:boolean;bluetooth:boolean;webgl:boolean};
function detect():Caps{
 const n:any=typeof navigator!=='undefined'?navigator:{};
 let webgl=false;try{const c=document.createElement('canvas');webgl=!!(c.getContext('webgl2')||c.getContext('webgl'));}catch{}
 return {camera:!!n.mediaDevices?.getUserMedia,mic:!!n.mediaDevices?.getUserMedia,motion:typeof window!=='undefined'&&'DeviceOrientationEvent' in window,bluetooth:'bluetooth' in n,webgl};
}
/**
 * Open Field: the live camera preview with the selected creature's 3D model drawn on top.
 * Honest label: this is NOT AR. There is no tracking, depth or surface detection;
 * the creature floats over the preview. Camera frames are never stored or uploaded.
 */
export default function OpenFieldCamera(){
 const {profile}=useCompanion();const {session}=useBeastSession();
 const beast=session?.beast?.qbeast?.profile?.id?session.beast:null;
 const name=beast?shownName(beast):talkPersona({beast:null,cage:profile}).name;
 const video=useRef<HTMLVideoElement>(null),stream=useRef<MediaStream|null>(null);
 const [on,setOn]=useState(false),[msg,setMsg]=useState(''),[caps,setCaps]=useState<Caps|null>(null),[grok,setGrok]=useState('checking…');
 useEffect(()=>{setCaps(detect());void voiceStatus().then(v=>setGrok(v.grok.configured?'configured (backend key)':'not set up'));},[]);
 function stop(){stream.current?.getTracks().forEach(t=>t.stop());stream.current=null;if(video.current)video.current.srcObject=null;setOn(false);}
 useEffect(()=>{const hide=()=>{if(document.hidden)stop();};document.addEventListener('visibilitychange',hide);window.addEventListener('pagehide',stop);return()=>{document.removeEventListener('visibilitychange',hide);window.removeEventListener('pagehide',stop);stop();};},[]);
 async function start(){
  setMsg('');
  if(!navigator.mediaDevices?.getUserMedia){setMsg('This browser has no camera access here. The field still works without it.');return;}
  try{const s=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}},audio:false});stream.current=s;if(video.current){video.current.srcObject=s;await video.current.play().catch(()=>{});}setOn(true);}
  catch(e:any){stop();setMsg(e?.name==='NotAllowedError'||e?.name==='SecurityError'?'Camera permission was not granted. Nothing was recorded; you can still play in the field below.':`Camera could not start (${e?.name||'error'}).`);}
 }
 const label=(k:keyof Caps,t:string)=>caps?<li key={k} data-cap={k} data-available={caps[k]}>{t}: {caps[k]?'available':'not in this browser'}</li>:null;
 return <section aria-label="Open Field camera" data-open-field style={{position:'relative',margin:'12px auto',maxWidth:560,padding:12,border:'1px solid #7dd9ea55',borderRadius:20,background:'#0c1329',color:'#e8f4ff'}}>
  <header style={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:8}}><div><strong>✦ OPEN FIELD · {name}</strong><small style={{display:'block',color:'#9fc6d8'}}>Camera preview + 3D overlay · not AR (no tracking or surface detection)</small></div>
   <button type="button" onClick={()=>on?stop():void start()} style={{minHeight:44,padding:'8px 14px',borderRadius:12,border:'1px solid #78ddea88',background:'#17364a',color:'#d7faff',fontWeight:800}}>{on?'Close camera':'Open camera field'}</button></header>
  <div style={{position:'relative',marginTop:10,aspectRatio:'3 / 4',maxHeight:'60dvh',borderRadius:16,overflow:'hidden',background:'radial-gradient(circle at 50% 40%,#2a1d55,#050914 70%)'}}>
   <video ref={video} playsInline muted aria-label="Live camera preview (not recorded)" style={{position:'absolute',inset:0,width:'100%',height:'100%',objectFit:'cover',display:on?'block':'none'}}/>
   <div style={{position:'absolute',inset:'15% 10% 0 10%'}}>{!beast&&!profile?<ZerefSprite3D greet={0} autoRotate turntable={false} turntableAngle={null}/>:<CosmicCompanion3D quality="low" profile={beast||!profile?null:profile} dimensionalId={!beast&&!profile?ZEREF_PROFILE.id:null} preferSprite={Boolean(beast?.genome?.seed)} spriteGenome={beast?.genome||null} spriteStage={beast?.nativeStage||beast?.stage||1} spriteName={name} spriteId={beast?.qbeast?.profile?.id||''} state={on?'observing':'idle'} label={!beast&&!profile?`Artistic 3D Moonwraith ${ZEREF_PROFILE.id} · not saved Zeref · over the camera preview`:`${name} over the camera preview`}/>}</div>
   {!on?<p style={{position:'absolute',left:12,right:12,bottom:10,margin:0,fontSize:12,color:'#c6d2ee'}}>Camera is off. Tap Open camera field to see {name} over your camera view.</p>:<span style={{position:'absolute',top:8,left:8,padding:'3px 8px',borderRadius:999,background:'#000a',fontSize:11}}>● LIVE PREVIEW · NOT RECORDED</span>}
  </div>
  {msg?<p role="alert" style={{fontSize:13,color:'#ffd2d2'}}>{msg}</p>:null}
  <details style={{marginTop:8,fontSize:12}}><summary>What this device can sense</summary><ul>
   {label('camera','Camera')}{label('mic','Microphone')}{label('motion','Motion sensors')}{label('bluetooth','Web Bluetooth (Muse)')}{label('webgl','3D graphics')}
   <li>Voice: browser speech available{caps?'':'…'} · Grok voice: {grok}</li>
  </ul><button type="button" onClick={()=>{const r=speakWith('browser',`Hi, I'm ${name}!`,{name});setMsg(r.ok?'':r.error||'');}} style={{minHeight:44,borderRadius:12}}>Hear {name} (browser voice)</button></details>
 </section>;
}
