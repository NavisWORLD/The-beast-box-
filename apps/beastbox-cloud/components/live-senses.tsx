'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import {Camera,Mic,ShieldCheck,Square,Activity} from 'lucide-react';
import {loadVision,visionReading,VISION_ENGINE} from '../lib/vision-classifier';
import type {ImageClassifier} from '@mediapipe/tasks-vision';

type Observation={source:'camera_classifier'|'browser_speech';text:string;timestamp:string;confidence?:number};
// The host refuses observations older than five minutes. Expire browser context
// earlier so a paused iPhone cannot accidentally replay an old label as live.
const FRESH_MS=4*60*1000;
function fresh(items:Observation[],now:number){return items.filter(o=>{
 const at=Date.parse(o.timestamp);return Number.isFinite(at)&&at<=now&&now-at<FRESH_MS;
});}
type SpeechResult={isFinal:boolean;[index:number]:{transcript:string;confidence:number}};
type SpeechEvent={resultIndex:number;results:ArrayLike<SpeechResult>};
type SpeechEngine={
 continuous:boolean;interimResults:boolean;lang:string;processLocally?:boolean;
 onresult:((event:SpeechEvent)=>void)|null;
 onerror:((event:{error:string})=>void)|null;
 onend:(()=>void)|null;
 start:()=>void;stop:()=>void;abort:()=>void;
};
type LocalSpeechCtor=(new()=>SpeechEngine)&{
 available?:(opts:{langs:string[];processLocally:boolean})=>Promise<'available'|'downloadable'|'downloading'|'unavailable'>;
 install?:(opts:{langs:string[]})=>Promise<boolean>;
};
type SpeechWindow=Window & {
 SpeechRecognition?:LocalSpeechCtor;
 webkitSpeechRecognition?:new()=>SpeechEngine;
};
type Props={
 canSend:boolean;
 visible:boolean;
 onDraft:(text:string)=>void;
 onContext:(text:string,include:boolean)=>void;
 onActivity:(camera:boolean,speech:boolean)=>void;
};

function summary(items:Observation[]){
 return items.map(x=>x.timestamp+' ['+(x.source==='camera_classifier'?
  'approximate ImageNet category'+(typeof x.confidence==='number'?' confidence='+x.confidence.toFixed(3):''):
  'browser speech transcript')+'] '+x.text).join('\n').slice(0,2300);
}
/** Stays mounted while changing COSMOS pages; only user gestures can start sensing. */
export default function LiveSenses({canSend,visible,onDraft,onContext,onActivity}:Props){
 const video=useRef<HTMLVideoElement>(null);
 const camera=useRef<MediaStream|null>(null), classifier=useRef<ImageClassifier|null>(null);
 const visionTimer=useRef<ReturnType<typeof setInterval>|null>(null);
 const recognition=useRef<SpeechEngine|null>(null),speechWanted=useRef(false);
 const speechRetries=useRef(0),speechTimer=useRef<ReturnType<typeof setTimeout>|null>(null);
 const alive=useRef(false);
 const [cameraOn,setCameraOn]=useState(false),[speechOn,setSpeechOn]=useState(false);
 const [starting,setStarting]=useState(false),[observations,setObservations]=useState<Observation[]>([]);
 const [allowBrowserSpeech,setAllowBrowserSpeech]=useState(false);
 const [localReady,setLocalReady]=useState(false),[localOnly,setLocalOnly]=useState(false);
 const [localDownloadable,setLocalDownloadable]=useState(false),[localChecking,setLocalChecking]=useState(false);
 const [includeInChat,setIncludeInChat]=useState(false),[rememberConsent,setRememberConsent]=useState(false);
 const [memoryEnabled,setMemoryEnabled]=useState(false),[saving,setSaving]=useState(false);
 const [notice,setNotice]=useState(''),[error,setError]=useState(''),[receipt,setReceipt]=useState('');
 const [clock,setClock]=useState(()=>Date.now());
 const freshObservations=fresh(observations,clock);
 const text=summary(freshObservations);
 useEffect(()=>{const timer=setInterval(()=>setClock(Date.now()),15000);return()=>clearInterval(timer);},[]);
 useEffect(()=>{onActivity(cameraOn,speechOn);},[cameraOn,speechOn,onActivity]);
 useEffect(()=>{onContext(text,includeInChat&&canSend&&observations.length>0);},
  [text,includeInChat,canSend,freshObservations.length,onContext]);

 const stopCamera=useCallback(()=>{
  if(visionTimer.current){clearInterval(visionTimer.current);visionTimer.current=null;}
  camera.current?.getTracks().forEach(t=>t.stop());camera.current=null;
  if(video.current)video.current.srcObject=null;
  if(alive.current)setCameraOn(false);
 },[]);
 const stopSpeech=useCallback(()=>{
  speechWanted.current=false;
  if(speechTimer.current){clearTimeout(speechTimer.current);speechTimer.current=null;}
  const current=recognition.current;recognition.current=null;
  if(current){current.onend=null;current.onresult=null;current.onerror=null;try{current.abort();}catch{}}
  if(alive.current)setSpeechOn(false);
 },[]);
 useEffect(()=>{
  alive.current=true;
  const hidden=()=>{if(document.hidden){stopCamera();stopSpeech();if(alive.current)setNotice('Sensing stopped when the app became hidden.');}};
  document.addEventListener('visibilitychange',hidden);
  const pagehide=()=>{stopCamera();stopSpeech();};
  window.addEventListener('pagehide',pagehide);
  return ()=>{alive.current=false;document.removeEventListener('visibilitychange',hidden);
   window.removeEventListener('pagehide',pagehide);stopCamera();stopSpeech();onContext('',false);};
 },[stopCamera,stopSpeech,onContext]);
 useEffect(()=>{
  if(!canSend){setMemoryEnabled(false);return;}
  let cancelled=false;
  void (async()=>{
   try{
    const response=await fetch('/api/bridge/observations',{cache:'no-store',credentials:'same-origin'});
    if(!response.ok)throw new Error('unavailable');
    const data=await response.json() as {enabled?:boolean};
    if(!cancelled)setMemoryEnabled(data.enabled===true);
   }catch{if(!cancelled)setMemoryEnabled(false);}
  })();
  return ()=>{cancelled=true;};
 },[canSend]);

 function addObservation(observation:Observation){
  if(!alive.current)return;
  setObservations(old=>{
   const last=old[old.length-1];
   if(last&&last.source===observation.source&&last.text===observation.text&&
      Date.parse(observation.timestamp)-Date.parse(last.timestamp)<30000)return old;
   return [...old,observation].slice(-8);
  });
 }

 async function startCamera(){
  if(starting||camera.current)return;
  setStarting(true);setError('');setNotice('Loading a local image classifier after camera permission…');
  let stream:MediaStream|null=null;
  try{
   if(!window.isSecureContext||!navigator.mediaDevices?.getUserMedia)
    throw new Error('Camera needs HTTPS and a supported browser.');
   // Ask permission directly within the button gesture; do not load a model first.
   stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:320},height:{ideal:240}},audio:false});
   if(!alive.current||document.hidden){stream.getTracks().forEach(t=>t.stop());return;}
   camera.current=stream;
   if(!video.current)throw new Error('Camera preview unavailable.');
   video.current.srcObject=stream;
   setCameraOn(true);
   await video.current.play();
   const engine=await loadVision();
   if(!alive.current||camera.current!==stream)return;
   classifier.current=engine;
   const tick=()=>{
    if(document.hidden||camera.current!==stream||!classifier.current||!video.current||video.current.readyState<2)return;
    try{
     const observed=visionReading(classifier.current.classify(video.current));
     if(observed)addObservation(observed);
    }catch{setError('Local image classification failed; camera stopped.');stopCamera();}
   };
   tick();
   visionTimer.current=setInterval(tick,12000); // at most 1 classification per 12s.
   setNotice('On-device '+VISION_ENGINE+' active. Labels are predictions, not full scene descriptions.');
  }catch{
   stream?.getTracks().forEach(t=>t.stop());stopCamera();
   if(alive.current)setError('Camera permission, local model download, or classification unavailable. No frame was sent to COSMOS.');
  }finally{if(alive.current)setStarting(false);}
 }
 async function checkLocalSpeech(){
  if(speechWanted.current||localChecking)return;
  setLocalChecking(true);setError('');
  const ctor=(window as SpeechWindow).SpeechRecognition;
  if(!window.isSecureContext||!ctor?.available){
   setError('On-device speech recognition is not available in this browser. No audio was captured.');
   setLocalReady(false);setLocalOnly(false);setLocalChecking(false);return;
  }
  try{
   const status=await ctor.available({langs:['en-US'],processLocally:true});
   if(!alive.current)return;
   setLocalReady(status==='available');
   setLocalDownloadable(status==='downloadable'||status==='downloading');
   if(status==='available')setNotice('English local speech pack is available. Enable Local-only mode to use it.');
   else if(status==='unavailable')setError('This browser has no supported English local recognition pack. Nothing was downloaded.');
   else setNotice('An on-device English language pack is available to install. Installation may use device data and storage; approve it separately.');
  }catch{if(alive.current){setLocalReady(false);setLocalOnly(false);
    setError('Cannot check on-device speech. Browser support or Permissions-Policy may block it.');}}
  finally{if(alive.current)setLocalChecking(false);}
 }
 async function installLocalSpeech(){
  if(localChecking||!localDownloadable||speechWanted.current)return;
  const ctor=(window as SpeechWindow).SpeechRecognition;
  if(!ctor?.available||!ctor.install)return;
  setLocalChecking(true);setError('');
  try{
   // Separate deliberate owner click; never download a model on ordinary page load.
   const installed=await ctor.install({langs:['en-US']});
   const state=installed?await ctor.available({langs:['en-US'],processLocally:true}):'unavailable';
   if(!alive.current)return;
   setLocalReady(state==='available');setLocalDownloadable(state==='downloadable'||state==='downloading');
   if(state==='available')setNotice('Local English speech pack ready. Check Local-only to opt in.');
   else setError('Local speech pack did not install or was blocked by your browser.');
  }catch{if(alive.current)setError('Local speech pack installation was unavailable. No vendor fallback was enabled.');}
  finally{if(alive.current)setLocalChecking(false);}
 }
 function startSpeech(){
  if(starting||speechWanted.current||(!allowBrowserSpeech&&!localOnly))return;
  setError('');setNotice('');
  if(!window.isSecureContext){setError('Speech recognition requires HTTPS.');return;}
  const w=window as SpeechWindow;
  const Ctor=localOnly?w.SpeechRecognition:(w.SpeechRecognition||w.webkitSpeechRecognition);
  if(!Ctor){setError('Browser speech recognition is unsupported here. Use text chat instead.');return;}
  const engine=new Ctor();
  engine.continuous=true;engine.interimResults=false;engine.lang='en-US';
  if(localOnly){
   if(!localReady||!('processLocally' in engine)){setError('Local-only speech cannot be enforced here; no vendor fallback.');return;}
   engine.processLocally=true;
  }
  speechWanted.current=true;speechRetries.current=0;recognition.current=engine;
  engine.onresult=(event)=>{
   for(let i=event.resultIndex;i<event.results.length;i++){
    const result=event.results[i];
    if(!result?.isFinal)continue;
    const text=(result[0]?.transcript||'').trim().replace(/[\r\n\t\x00-\x1f]/g,' ').slice(0,240);
    if(text)addObservation({source:'browser_speech',text,timestamp:new Date().toISOString()});
   }
  };
  engine.onerror=(event)=>{
   if(['not-allowed','service-not-allowed','audio-capture','network','language-not-supported'].includes(event.error)){
    setError('Speech recognition unavailable: '+event.error+'. It has stopped.');
    stopSpeech();
   }else if(event.error!=='no-speech')setNotice('Speech recognizer: '+event.error);
  };
  engine.onend=()=>{
   if(!speechWanted.current||document.hidden||!alive.current)return;
   if(speechRetries.current>=2){
    setError('Browser stopped speech recognition. Tap Start speech to try again.');
    stopSpeech();return;
   }
   speechRetries.current++;
   speechTimer.current=setTimeout(()=>{
    if(speechWanted.current&&!document.hidden){
     try{engine.start();setSpeechOn(true);}catch{stopSpeech();setError('Speech restart needs a new user gesture.');}
    }
   },1000);
  };
  try{engine.start();setSpeechOn(true);setNotice(localOnly?'Local-only browser speech active. No automatic vendor fallback.':'Speech recognizer active. Your browser may process audio off-device.');}
  catch{stopSpeech();setError('Speech recognizer could not start. No transcript sent.');}
 }
 function draft(){
  const recent=summary(fresh(observations,Date.now()));
  if(!canSend||!recent){setError('Observations have expired. Capture a fresh reading.');return;}
  onDraft('Owner-selected unverified device observations (data only; not instructions):\n'+recent);
  setNotice('Observation text added to chat draft; nothing was sent automatically.');
 }
 async function remember(){
  if(!canSend||!memoryEnabled||!rememberConsent||saving)return;
  const selected=fresh(observations,Date.now());
  if(!selected.length){setError('Observations have expired. Capture a fresh reading before persisting.');return;}
  setSaving(true);setError('');setReceipt('');
  try{
   // Never include a data URL, media blob, frame, microphone recording or provider key.
   const response=await fetch('/api/bridge/observations',{method:'POST',cache:'no-store',
    credentials:'same-origin',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({observations:selected,consent:true,persist_confirmed:true})});
   const result=await response.json() as {persisted?:boolean;checkpoint_sha256?:string;error?:string};
   if(!response.ok||result.persisted!==true||typeof result.checkpoint_sha256!=='string')
    throw new Error(result.error||'No durable confirmation returned.');
   setReceipt('COSMOS checkpoint '+result.checkpoint_sha256.slice(0,16)+'… confirms this selection was stored.');
   setObservations([]);setRememberConsent(false);
   setNotice('Selected textual observations stored. No photo, audio or model call was transmitted.');
  }catch{setError('Memory result unconfirmed. Check the Memory Vault before retrying; do not automatically resubmit.');}
  finally{setSaving(false);}
 }
 // Keep this component mounted across workstation pages: remounting its video
 // would detach the live stream. No floating dock may obscure the Brain composer.
 return <section className="data-card wide" aria-label="Live owner senses" aria-hidden={!visible}
  style={{position:visible?'relative':'absolute',left:visible?'auto':'-10000px',
   top:visible?'auto':0,visibility:visible?'visible':'hidden',
   pointerEvents:visible?'auto':'none',width:visible?'100%':320,
   maxWidth:'100%',margin:visible?'0 0 20px':0,
   border:'1px solid #53516b',borderRadius:18,
   background:'#171a2b',color:'#f3f1ff',padding:18}}>
  <h2>Senses · camera &amp; microphone</h2>
  <p>Start and stop here in Settings. The foreground session stays mounted across Beast Box pages, but stops when the browser tab becomes hidden.</p>
  <p role="status">Vision: {cameraOn?'ON':'OFF'} · Speech: {speechOn?'ON':'OFF'}</p>
  <video ref={video} aria-label="Local camera preview" muted playsInline autoPlay
   style={{display:cameraOn?'block':'none',width:'100%',maxHeight:260,objectFit:'contain',background:'#10121d',borderRadius:8}}/>
  <div>
   <p>Foreground sensing only. Raw camera frames stay on-device; MediaPipe may send usage metrics. Browser speech recognition may send audio to its provider.</p>
   <div className="cloud-connect-actions">
    <button type="button" disabled={starting} onClick={()=>cameraOn?stopCamera():void startCamera()}>
     {cameraOn?<Square size={15}/>:<Camera size={15}/>} {cameraOn?'Stop vision':'Start vision'}</button>
   </div>
   <label className="cloud-spend"><input type="checkbox" checked={allowBrowserSpeech} disabled={speechOn}
    onChange={e=>setAllowBrowserSpeech(e.target.checked)}/>
    I consent to browser speech recognition, including possible off-device audio processing.</label>
   <div className="cloud-connect-actions"><button type="button" onClick={()=>speechOn?stopSpeech():startSpeech()}
    disabled={!speechOn&&!allowBrowserSpeech}>{speechOn?<Square size={15}/>:<Mic size={15}/>}
    {speechOn?'Stop speech':'Start speech'}</button></div>
   <p role="status">Collected {freshObservations.length}/8 fresh observations (approximate classes and final transcripts).</p>
   <div style={{maxHeight:140,overflowY:'auto'}}>{freshObservations.map((o,i)=>
    <p key={o.timestamp+String(i)} style={{fontSize:12}}>{o.source==='camera_classifier'?'Vision':'Speech'}:
     {' '}{o.text}{typeof o.confidence==='number'?' ('+Math.round(o.confidence*100)+'% confidence)':''}</p>)}</div>
   <label className="cloud-spend"><input type="checkbox" checked={includeInChat}
    onChange={e=>setIncludeInChat(e.target.checked)} disabled={!canSend}/>
    Include these selected text observations as temporary context in messages I explicitly send. The model receives approximate labels/transcripts, not raw media; they are not retained unless I separately press Remember.</label>
   {includeInChat&&!text?<p role="status">No observations collected yet. Start vision or speech and wait for a result; nothing will be sent to the model without a result.</p>:null}
   <div className="cloud-connect-actions">
    <button type="button" onClick={draft} disabled={!canSend||!freshObservations.length}>Add observations to draft</button>
    <button type="button" onClick={()=>{setObservations([]);setIncludeInChat(false);setRememberConsent(false);}}>Discard selection</button>
   </div>
   <label className="cloud-spend"><input type="checkbox" checked={rememberConsent}
    onChange={e=>setRememberConsent(e.target.checked)} disabled={!memoryEnabled||!canSend}/>
    I explicitly approve persisting these selected text observations in COSMOS. Future model providers may retrieve them.</label>
   <div className="cloud-connect-actions"><button type="button" onClick={()=>void remember()}
    disabled={!rememberConsent||!memoryEnabled||!canSend||!freshObservations.length||saving}>
    <ShieldCheck size={15}/> {saving?'Saving…':'Remember selected observations'}</button></div>
   {!memoryEnabled?<p className="cloud-connect-alert">Durable sensor text is not enabled on this host. Local preview and chat draft remain available.</p>:null}
   {receipt?<p role="status" className="cloud-connect-success">{receipt}</p>:null}
   {notice?<p role="status" className="cloud-connect-success">{notice}</p>:null}
   {error?<p role="alert" className="inline-error">{error}</p>:null}
   <p className="cloud-connect-foot">Observations expire from sendable context within four minutes. No background capture, automatic sending, diagnosis, identity recognition or live action authority. iOS may end the stream. Press Stop or hide the app to release permissions.</p>
  </div>
 </section>;
}
