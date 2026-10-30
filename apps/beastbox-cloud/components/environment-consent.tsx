'use client';
// One opt-in consent control: "let my surroundings give the pocket universe life". Off by default, per user, revocable.
// FIVE switches (time of day, device motion, light level, sound level, fingertip pulse), all OFF until the person turns them on, plus ONE camera switch
// that covers light and pulse. The camera does one job at a time: while the pulse flow says pulse_read_started, light waits (until pulse_read_ended).
// Numbers only (a level, bpm/quality). Never audio, video or a waveform. The long explanations live on /privacy ("Privacy and info").
import {useCallback,useEffect,useRef,useState} from 'react';
import {CHANNELS,validateEnvironment,type EnvChannel} from '../lib/environment/environment-link.mjs';
import {getEnvironment,grantEnvironment,revokeEnvironmentLocal,setEnvironmentNumbers,subscribeEnvironment,getHeartNumbers} from '../lib/environment/environment-store.mjs';
import {startSensors,type Want} from '../lib/environment/sensor-runtime';
type Sw={time:boolean;motion:boolean;light:boolean;sound:boolean;pulse:boolean;camera:boolean};
const allOff:Sw={time:false,motion:false,light:false,sound:false,pulse:false,camera:false};
// Status lines are 44 characters or fewer (wording from consent_status_fixes_PROPOSED.json); the right-hand status slot of a switch row holds 22.
const SIGNED_OUT='Used on this device only. Nothing is stored.';
const PULSE_NOT_READY_HINT='Not available here yet.';// 23: fits the 35-char hint slot under the switch
const PULSE_NOT_READY_LONG='Pulse reading is not available here yet.';// 40: full-width notice line only, never a row hint
const PULSE_NOT_READY_ROW='Not available yet';
const ROWS:{k:keyof Sw;label:string;hint:string}[]=[
 {k:'time',label:'Time of day',hint:'Uses your clock'},
 {k:'motion',label:'Device motion',hint:'How your phone moves'},
 {k:'light',label:'Light level',hint:'Room brightness. Uses the camera.'},
 {k:'sound',label:'Sound level',hint:'Uses the microphone. Loudness only.'},
 {k:'pulse',label:'Fingertip pulse',hint:'Uses the camera. Beats per minute.'},
];
/** 0..1 phase of the local day from the device clock (a number, nothing else). */
const dayPhase=(d:Date)=>(d.getHours()*3600+d.getMinutes()*60+d.getSeconds())/86400;
export default function EnvironmentConsent({onClose,beastName}:{onClose:()=>void;beastName?:string|null}){
 const beast=(beastName||'your beast').split(/\s+·\s+/)[0];
 const [env,setEnv]=useState(getEnvironment());
 const [sw,setSw]=useState<Sw>(allOff);const swRef=useRef<Sw>(allOff);swRef.current=sw;
 const [confirm,setConfirm]=useState(false);const [notice,setNotice]=useState('');
 const [server,setServer]=useState('');const [err,setErr]=useState('');const [ticks,setTicks]=useState(0);
 // Only the signed-in owner can take a fingertip reading (the Studio IBM BIO page is owner-only). Visitors are treated as not-owner until the session says otherwise.
 const [isOwnerView,setIsOwnerView]=useState(false);
 useEffect(()=>{let live=true;fetch('/api/session',{cache:'no-store'}).then(r=>r.json()).then(j=>{if(live)setIsOwnerView(j?.owner===true);}).catch(()=>{});return()=>{live=false;};},[]);
 const isOwnerRef=useRef(false);isOwnerRef.current=isOwnerView;
 const stopRef=useRef<null|(()=>void)>(null),last=useRef(0),signedOut=useRef(false);
 useEffect(()=>subscribeEnvironment(setEnv),[]);
 // What the server holds for this account (never auto-starts sensors: each visit needs the person's own tap and the browser's permission).
 useEffect(()=>{let live=true;fetch('/api/environment',{cache:'no-store'}).then(async r=>{const j=await r.json().catch(()=>({}));if(!live)return;
  if(r.status===401){signedOut.current=true;setServer(SIGNED_OUT);}
  else if(r.status===503)setServer('Private storage is off. Nothing is stored.');
  else if(j.consent)setServer('Saved record found. Switch on to resume.');
  else setServer('Nothing is stored for you.');}).catch(()=>{if(live)setServer('Couldn\'t check your saved record.');});return()=>{live=false;};},[]);
 const sample=useCallback((s:{light:EnvChannel;sound:EnvChannel;motion:EnvChannel})=>{
  const w=swRef.current,now=Date.now();
  const h=w.pulse&&w.camera&&isOwnerRef.current?getHeartNumbers(now):null;
  const raw={light:w.light&&w.camera?s.light:{state:'off'},sound:s.sound,motion:s.motion,
   heart:w.pulse&&w.camera&&isOwnerRef.current?(h?{state:'MEASURED',bpm:h.bpm,sqi:h.sqi}:{state:'unavailable'}):{state:'off'},
   time:w.time?{state:'MEASURED',level:Math.round(dayPhase(new Date(now))*1000)/1000}:{state:'off'}};
  const v=validateEnvironment(raw);
  if(!v.ok||!v.numbers){setErr('Not used: '+v.errors.slice(0,2).join('; '));return;}
  setErr('');setTicks(t=>t+1);setEnvironmentNumbers(v.numbers,now);
  if(!signedOut.current&&now-last.current>=5000){last.current=now;
   fetch('/api/environment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(CHANNELS.map(c=>[c,(v.numbers as any)[c]])))})
    .then(r=>{if(r.status===401){signedOut.current=true;setServer(SIGNED_OUT);}else if(r.status===200)setServer('Saved privately for you. Numbers only.');else if(r.status===503)setServer('Private storage is off. Nothing is stored.');}).catch(()=>{});}
 },[]);
 // Sensors run only while sharing is on, and only for switches that are on. Light needs the camera switch AND no pulse being read (one camera job at a time).
 const want:Want={sound:sw.sound,motion:sw.motion,light:sw.light&&sw.camera&&!env.pulseReading};
 const wantKey=[want.sound,want.motion,want.light,sw.time,sw.pulse,sw.camera].join();
 useEffect(()=>{stopRef.current?.();stopRef.current=null;if(!env.consent)return;let dead=false;setTicks(0);
  startSensors(want,sample).then(r=>{if(dead)r.stop();else stopRef.current=r.stop;}).catch(()=>{});
  return()=>{dead=true;stopRef.current?.();stopRef.current=null;};
  // eslint-disable-next-line react-hooks/exhaustive-deps
 },[env.consent,wantKey,sample]);
 useEffect(()=>()=>{stopRef.current?.();},[]);
 const stop=async()=>{stopRef.current?.();stopRef.current=null;setSw(allOff);revokeEnvironmentLocal();setErr('');setConfirm(false);
  setNotice(beast+' is back to its own sky.');
  try{const r=await fetch('/api/environment',{method:'DELETE'});setServer(r.status===200?'Stopped. Saved numbers deleted.':r.status===401?'Stopped. Nothing was stored.':'Stopped here. Couldn\'t erase saved numbers.');}catch{setServer('Stopped here. Site unreachable; not erased.');}};
 const nums=env.numbers as any;
 const status=(k:keyof Sw):string=>{
  if(k==='pulse'&&!isOwnerView)return PULSE_NOT_READY_ROW;
  if(!env.consent||!sw[k])return 'Off';
  if(k==='camera')return 'On';
  if(k==='time')return 'On';
  if((k==='light'||k==='pulse')&&!sw.camera)return 'Needs camera switch';
  if(k==='light'&&env.pulseReading)return 'Paused: reading pulse';
  if(k==='pulse'){const c=nums?.heart;return c?.state==='MEASURED'?Math.round(c.bpm)+' bpm':'No valid pulse';}
  const c=nums?.[k];
  if(c?.state==='MEASURED')return Math.round(c.level*100)+'%';
  if(c?.state==='denied')return 'Permission declined';
  if(c?.state==='unavailable'&&ticks>=3)return 'Unavailable here';
  return 'Waiting for permission';
 };
 const row=(k:keyof Sw,label:string,hint:string)=>{const id='env-sw-'+k;const locked=k==='pulse'&&!isOwnerView;
  if(locked)hint=PULSE_NOT_READY_HINT;
  return <div key={k} data-env-row={k} style={{display:'flex',gap:10,alignItems:'center',minHeight:48,padding:'4px 0'}}>
   <input id={id} type="checkbox" role="switch" aria-checked={sw[k]} checked={sw[k]&&!locked} disabled={!env.consent||locked} data-env-switch={k} onChange={e=>setSw({...sw,[k]:e.target.checked})} style={{width:28,height:28,flex:'0 0 auto'}}/>
   <label htmlFor={id} style={{flex:'1 1 auto',minWidth:0}}><strong style={{display:'block'}}>{label}</strong><small style={{display:'block',opacity:.75}}>{hint}</small></label>
   <span data-env-status={k} style={{flex:'0 0 auto',fontSize:12,opacity:.9,textAlign:'right',maxWidth:'38%'}}>{status(k)}</span>
  </div>;};
 return <div role="dialog" aria-label="World signals" data-environment-consent style={{position:'fixed',left:0,right:0,bottom:0,zIndex:9000,maxHeight:'85vh',overflowY:'auto',boxSizing:'border-box',padding:'14px 14px calc(14px + env(safe-area-inset-bottom))',background:'rgba(12,10,28,.96)',color:'#f2ecff',borderTop:'1px solid rgba(180,160,255,.4)',borderRadius:'16px 16px 0 0',fontSize:14,lineHeight:1.4,pointerEvents:'auto'}}>
  <div style={{display:'flex',justifyContent:'space-between',gap:8,alignItems:'center'}}><strong>Give your universe more life</strong><button type="button" onClick={onClose} aria-label="Close" style={{minWidth:48,minHeight:48}}>✕</button></div>
  <p style={{margin:'2px 0 8px',opacity:.85}}>Off until you turn it on. Stop any time.</p>
  {env.consent
   ?<div style={{fontWeight:600,minHeight:24}} data-env-state>Sharing my world&apos;s signals</div>
   :<button type="button" data-environment-consent-toggle onClick={()=>setConfirm(true)} style={{minHeight:48,width:'100%',fontWeight:600}}>Share my world&apos;s signals</button>}
  <div style={{opacity:env.consent?1:.55}}>{ROWS.map(r=>row(r.k,r.label,r.hint))}{row('camera','Camera','One switch for light and pulse')}</div>
  {err?<p role="alert" style={{color:'#ffb3b3',margin:'4px 0'}}>{err}</p>:null}
  <p style={{margin:'6px 0'}} data-env-server>{server}</p>
  {notice?<p role="status" data-env-notice style={{margin:'6px 0'}}>{notice}</p>:env.consent&&!isOwnerView?<p role="status" data-env-notice="pulse" style={{margin:'6px 0'}}>{PULSE_NOT_READY_LONG}</p>:null}
  <button type="button" data-environment-revoke onClick={()=>void stop()} style={{minHeight:48,width:'100%'}}>Stop sharing</button>
  <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',gap:8,marginTop:6}}><span style={{opacity:.8}}>Stop sharing deletes your saved numbers.</span><a href="/privacy#labels-and-signals" data-env-learn-more style={{flex:'0 0 auto',display:'inline-flex',alignItems:'center',justifyContent:'center',width:120,height:44,color:'#9beffd',textDecoration:'underline'}}>Learn more</a></div>
  {confirm?<div role="alertdialog" aria-modal="true" aria-label="Turn on world signals?" data-env-confirm style={{position:'fixed',inset:0,zIndex:9100,display:'grid',placeItems:'center',background:'rgba(4,3,12,.7)'}}>
   <div style={{background:'#171233',border:'1px solid rgba(180,160,255,.5)',borderRadius:16,padding:18,margin:16,maxWidth:360}}>
    <strong style={{display:'block',marginBottom:6}}>Turn on world signals?</strong>
    <p style={{margin:'0 0 12px'}}>{beast}&apos;s universe will start reacting to the signals you switch on.</p>
    <div style={{display:'flex',gap:8}}>
     <button type="button" data-env-confirm-yes style={{flex:1,minHeight:48,fontWeight:600}} onClick={()=>{setConfirm(false);setNotice('');grantEnvironment();}}>Yes, give it life</button>
     <button type="button" data-env-confirm-no style={{flex:1,minHeight:48}} onClick={()=>setConfirm(false)}>Not now</button>
    </div>
   </div>
  </div>:null}
 </div>;
}
