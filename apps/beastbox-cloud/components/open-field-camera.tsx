'use client';
import {useEffect,useState} from 'react';
import CameraField from './camera-field';
import {useChshHistory} from './use-chsh-game';
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
 * Open Field: the selected creature's real 3D model standing on your floor over the live camera.
 * Honest labels: WebXR AR (hit-test) where supported; on iPhone Safari a motion-anchored overlay (rotation only, assumed floor,
 * not full AR) plus Quick Look for true ARKit AR. Camera frames are never stored or uploaded.
 */
export default function OpenFieldCamera(){
 const {profile}=useCompanion();const {session}=useBeastSession();
 const beast=session?.beast?.qbeast?.profile?.id?session.beast:null;
 const name=beast?shownName(beast):talkPersona({beast:null,cage:profile}).name;
 const hist=useChshHistory();
 const [msg,setMsg]=useState(''),[caps,setCaps]=useState<Caps|null>(null),[grok,setGrok]=useState('checking…');
 useEffect(()=>{setCaps(detect());void voiceStatus().then(v=>setGrok(v.grok.configured?'configured (backend key)':'not set up'));},[]);
 const label=(k:keyof Caps,t:string)=>caps?<li key={k} data-cap={k} data-available={caps[k]}>{t}: {caps[k]?'available':'not in this browser'}</li>:null;
 return <section aria-label="Lost COSMOS Field camera" data-open-field style={{position:'relative',margin:'12px auto',maxWidth:560,padding:12,border:'1px solid #7dd9ea55',borderRadius:20,background:'#0c1329cc',color:'#e8f4ff'}}>
  <header style={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:8}}><div><strong>✦ LOST COSMOS FIELD</strong><small style={{display:'block',color:'#9fc6d8'}}>Your companion + Zeref walking in your room · true AR tracking (WebXR, Android) · camera overlay on iPhone (+ Quick Look AR)</small></div>
</header>
  <CameraField />
  {msg?<p role="alert" style={{fontSize:13,color:'#ffd2d2'}}>{msg}</p>:null}
  {hist&&hist.length?<details data-chsh-history style={{marginTop:8,fontSize:12}}><summary>CHSH game (Bell nonlocality) · daily history</summary>
   <table style={{width:'100%',borderCollapse:'collapse'}}><thead><tr><th align='left'>Date (UTC)</th><th align='left'>IBM job</th><th align='right'>Win rate</th></tr></thead><tbody>{hist.map(r=><tr key={r.job} data-chsh-row={r.job}><td>{r.date}</td><td style={{fontFamily:'monospace',fontSize:11}}>{r.job}</td><td align='right'>{(r.winRate*100).toFixed(1)}% ± {(r.se*100).toFixed(1)}</td></tr>)}</tbody></table>
   <small style={{color:'#9fc6d8'}}>Real IBM hardware, settings hash-committed before each run. Classical bound 75%, ideal quantum 85.4%. Not loophole-free: no space-like separation (one chip, one controller).</small></details>:null}
  <details style={{marginTop:8,fontSize:12}}><summary>What this device can sense</summary><ul>
   {label('camera','Camera')}{label('mic','Microphone')}{label('motion','Motion sensors')}{label('bluetooth','Web Bluetooth (Muse)')}{label('webgl','3D graphics')}
   <li>Voice: browser speech available{caps?'':'…'} · Grok voice: {grok}</li>
  </ul><button type="button" onClick={()=>{const r=speakWith('browser',`Hi, I'm ${name}!`,{name});setMsg(r.ok?'':r.error||'');}} style={{minHeight:44,borderRadius:12}}>Hear {name} (browser voice)</button></details>
 </section>;
}
