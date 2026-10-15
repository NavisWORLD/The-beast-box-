'use client';
import {useEffect,useState} from 'react';
import CameraField from './camera-field';
import {useCompanion} from './companion-provider';
import {useBeastSession} from './beast-session';
import {shownName} from '../lib/companion/session.mjs';
import {talkPersona} from '../lib/companion/beast-talk.mjs';
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
 const [msg,setMsg]=useState(''),[caps,setCaps]=useState<Caps|null>(null),[grok,setGrok]=useState('checking…');
 useEffect(()=>{setCaps(detect());void voiceStatus().then(v=>setGrok(v.grok.configured?'configured (backend key)':'not set up'));},[]);
 const label=(k:keyof Caps,t:string)=>caps?<li key={k} data-cap={k} data-available={caps[k]}>{t}: {caps[k]?'available':'not in this browser'}</li>:null;
 return <section aria-label="Open Field camera" data-open-field style={{position:'relative',margin:'12px auto',maxWidth:560,padding:12,border:'1px solid #7dd9ea55',borderRadius:20,background:'#0c1329',color:'#e8f4ff'}}>
  <header style={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:8}}><div><strong>✦ OPEN FIELD</strong><small style={{display:'block',color:'#9fc6d8'}}>Camera preview + 3D overlay · not AR (no tracking or surface detection)</small></div>
</header>
  <CameraField />
  {msg?<p role="alert" style={{fontSize:13,color:'#ffd2d2'}}>{msg}</p>:null}
  <details style={{marginTop:8,fontSize:12}}><summary>What this device can sense</summary><ul>
   {label('camera','Camera')}{label('mic','Microphone')}{label('motion','Motion sensors')}{label('bluetooth','Web Bluetooth (Muse)')}{label('webgl','3D graphics')}
   <li>Voice: browser speech available{caps?'':'…'} · Grok voice: {grok}</li>
  </ul><button type="button" onClick={()=>{const r=speakWith('browser',`Hi, I'm ${name}!`,{name});setMsg(r.ok?'':r.error||'');}} style={{minHeight:44,borderRadius:12}}>Hear {name} (browser voice)</button></details>
 </section>;
}
