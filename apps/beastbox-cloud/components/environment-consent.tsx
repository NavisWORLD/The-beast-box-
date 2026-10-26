'use client';
// One opt-in consent control: "let my surroundings give the pocket universe life". Off by default, per user, revocable.
// Numbers only (a light level, a sound level, a motion level, heartbeat bpm/quality). Never audio, video or a waveform.
import {useCallback,useEffect,useRef,useState} from 'react';
import {CHANNELS,ENV_NOTE,describeChannel,validateEnvironment,type EnvChannel} from '../lib/environment/environment-link.mjs';
import {getEnvironment,grantEnvironment,revokeEnvironmentLocal,setEnvironmentNumbers,subscribeEnvironment,getHeartNumbers} from '../lib/environment/environment-store.mjs';
import {startSensors,type Want} from '../lib/environment/sensor-runtime';
const none:Want={light:false,sound:false,motion:false};
const WANT_KEY='beastbox:environment-channels:v1';
export default function EnvironmentConsent({onClose}:{onClose:()=>void}){
 const [env,setEnv]=useState(getEnvironment());
 const [want,setWant]=useState<Want>(none);
 const [server,setServer]=useState('');const [err,setErr]=useState('');
 const stopRef=useRef<null|(()=>void)>(null),last=useRef(0),signedOut=useRef(false);
 useEffect(()=>subscribeEnvironment(setEnv),[]);
 // What the server holds for this account (never auto-starts sensors: each visit needs the person's own tap and the browser's permission).
 useEffect(()=>{let live=true;fetch('/api/environment',{cache:'no-store'}).then(async r=>{const j=await r.json().catch(()=>({}));if(!live)return;
  if(r.status===401){signedOut.current=true;setServer('Not signed in: your numbers are used on this device only and nothing is stored.');}
  else if(r.status===503)setServer('Private storage is not set up on this site: nothing is stored.');
  else if(j.consent)setServer('Your account has a saved consent record. Tick below to resume; your device asks permission again.');
  else setServer('Nothing is stored for you.');}).catch(()=>{if(live)setServer('Could not reach the site to check your saved record.');});return()=>{live=false;};},[]);
 const sample=useCallback((s:{light:EnvChannel;sound:EnvChannel;motion:EnvChannel})=>{
  const h=getHeartNumbers(Date.now());
  const raw={light:s.light,sound:s.sound,motion:s.motion,heart:h?{state:'MEASURED',bpm:h.bpm,sqi:h.sqi}:{state:'unavailable'}};
  const v=validateEnvironment(raw);
  if(!v.ok||!v.numbers){setErr('Not used: '+v.errors.slice(0,2).join('; '));return;}
  setErr('');setEnvironmentNumbers(v.numbers,Date.now());
  const now=Date.now();
  if(!signedOut.current&&now-last.current>=5000){last.current=now;
   fetch('/api/environment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(CHANNELS.map(c=>[c,(v.numbers as any)[c]])))})
    .then(r=>{if(r.status===401){signedOut.current=true;setServer('Not signed in: your numbers are used on this device only and nothing is stored.');}else if(r.status===200)setServer('Stored privately for your account (numbers only, replaced every few seconds).');else if(r.status===503)setServer('Private storage is not set up on this site: nothing is stored.');}).catch(()=>{});}
 },[]);
 // sensors run only while consent is on, and only the ticked channels
 useEffect(()=>{stopRef.current?.();stopRef.current=null;if(!env.consent||!(want.light||want.sound||want.motion))return;let dead=false;
  startSensors(want,sample).then(r=>{if(dead)r.stop();else stopRef.current=r.stop;}).catch(()=>{});
  return()=>{dead=true;stopRef.current?.();stopRef.current=null;};},[env.consent,want,sample]);
 useEffect(()=>()=>{stopRef.current?.();},[]);
 const revoke=async()=>{stopRef.current?.();stopRef.current=null;setWant(none);revokeEnvironmentLocal();setErr('');
  try{const r=await fetch('/api/environment',{method:'DELETE'});setServer(r.status===200?'Consent revoked and your stored record erased.':r.status===401?'Consent revoked on this device. Nothing was stored.':'Consent revoked on this device; the stored record could not be erased right now.');}catch{setServer('Consent revoked on this device; could not reach the site to erase the stored record.');}};
 const nums=env.numbers as any;
 const row=(k:keyof Want,label:string)=><label style={{display:'flex',gap:8,alignItems:'center',minHeight:40}}><input type="checkbox" checked={want[k]} disabled={!env.consent} onChange={e=>setWant({...want,[k]:e.target.checked})}/>{label}</label>;
 return <div role="dialog" aria-label="My surroundings and the pocket universe" data-environment-consent style={{position:'fixed',left:0,right:0,bottom:0,zIndex:9000,maxHeight:'80vh',overflowY:'auto',boxSizing:'border-box',padding:'14px 14px calc(14px + env(safe-area-inset-bottom))',background:'rgba(12,10,28,.96)',color:'#f2ecff',borderTop:'1px solid rgba(180,160,255,.4)',borderRadius:'16px 16px 0 0',fontSize:14,lineHeight:1.4,pointerEvents:'auto'}}>
  <div style={{display:'flex',justifyContent:'space-between',gap:8,alignItems:'center'}}><strong>Give the pocket universe life from my surroundings</strong><button type="button" onClick={onClose} aria-label="Close" style={{minWidth:44,minHeight:44}}>✕</button></div>
  <label style={{display:'flex',gap:8,alignItems:'center',minHeight:44,fontWeight:600}}><input type="checkbox" data-environment-consent-toggle checked={env.consent} onChange={e=>e.target.checked?grantEnvironment():void revoke()}/>I consent (off by default; you can revoke any time)</label>
  <div style={{opacity:env.consent?1:.55}}>{row('light','Light (ambient light sensor, else a camera brightness number)')}{row('sound','Sound level (one loudness number, no recording)')}{row('motion','Motion (device movement level)')}
   <div style={{minHeight:32}}>Heartbeat: {getHeartNumbers(Date.now())?'your last valid IBM BIO pulse, bpm and quality only':'no valid pulse, not used (take one in IBM BIO)'}</div></div>
  {env.consent?<ul style={{margin:'6px 0',paddingLeft:18}}>{CHANNELS.map(c=><li key={c}>{describeChannel(c,nums?.[c])}</li>)}</ul>:null}
  {err?<p role="alert" style={{color:'#ffb3b3',margin:'4px 0'}}>{err}</p>:null}
  <p style={{margin:'6px 0',opacity:.9}}>{ENV_NOTE}</p>
  <p style={{margin:'6px 0'}}>{server}</p>
  <p style={{margin:'6px 0',opacity:.8}}>Your numbers tilt the same four sand wells the Rigetti-simulated receipt already weights. The world is a simulation; your surroundings are not simulated, and nothing is invented when a sensor says no.</p>
  <button type="button" data-environment-revoke onClick={()=>void revoke()} style={{minHeight:44,width:'100%'}}>Revoke and erase my stored numbers</button>
 </div>;
}
