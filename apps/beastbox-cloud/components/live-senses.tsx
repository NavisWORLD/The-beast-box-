'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import {Camera,Mic,ShieldCheck,Square,Activity} from 'lucide-react';
import {loadVision,visionReading,VISION_ENGINE} from '../lib/vision-classifier';
import type {ImageClassifier} from '@mediapipe/tasks-vision';

type Observation={source:'camera_classifier'|'browser_speech';text:string;timestamp:string;confidence?:number};
type SpeechResult={isFinal:boolean;[index:number]:{transcript:string;confidence:number}};
type SpeechEvent={resultIndex:number;results:ArrayLike<SpeechResult>};
type SpeechEngine={
 continuous:boolean;interimResults:boolean;lang:string;
 onresult:((event:SpeechEvent)=>void)|null;
 onerror:((event:{error:string})=>void)|null;
 onend:(()=>void)|null;
 start:()=>void;stop:()=>void;abort:()=>void;
};
type SpeechWindow=Window & {
 SpeechRecognition?:new()=>SpeechEngine;
 webkitSpeechRecognition?:new()=>SpeechEngine;
};
type Props={
 canSend:boolean;
 onDraft:(text:string)=>void;
 onContext:(text:string,include:boolean)=>void;
};

function summary(items:Observation[]){
 return items.map(x=>x.timestamp+' ['+(x.source==='camera_classifier'?
  'approximate ImageNet category'+(typeof x.confidence==='number'?' confidence='+x.confidence.toFixed(3):''):
  'browser speech transcript')+'] '+x.text).join('\n').slice(0,2300);
}
/** Stays mounted while changing COSMOS pages; only user gestures can start sensing. */
export default function LiveSenses({canSend,onDraft,onContext}:Props){
 const video=useRef<HTMLVideoElement>(null);
 const camera=useRef<MediaStream|null>(null), classifier=useRef<ImageClassifier|null>(null);
 const visionTimer=useRef<ReturnType<typeof setInterval>|null>(null);
 const recognition=useRef<SpeechEngine|null>(null),speechWanted=useRef(false);
 const speechRetries=useRef(0),speechTimer=useRef<ReturnType<typeof setTimeout>|null>(null);
 const alive=useRef(false);
 const [expanded,setExpanded]=useState(false);
 const [cameraOn,setCameraOn]=useState(false),[speechOn,setSpeechOn]=useState(false);
 const [starting,setStarting]=useState(false),[observations,setObservations]=useState<Observation[]>([]);
 const [allowBrowserSpeech,setAllowBrowserSpeech]=useState(false);
 const [includeInChat,setIncludeInChat]=useState(false),[rememberConsent,setRememberConsent]=useState(false);
 const [memoryEnabled,setMemoryEnabled]=useState(false),[saving,setSaving]=useState(false);
 const [notice,setNotice]=useState(''),[error,setError]=useState(''),[receipt,setReceipt]=useState('');
 const text=summary(observations);
 useEffect(()=>{onContext(text,includeInChat&&canSend&&observations.length>0);},
  [text,includeInChat,canSend,observations.length,onContext]);

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
 function startSpeech(){
  if(starting||speechWanted.current||!allowBrowserSpeech)return;
  setError('');setNotice('');
  if(!window.isSecureContext){setError('Speech recognition requires HTTPS.');return;}
  const w=window as SpeechWindow;
  const Ctor=w.SpeechRecognition||w.webkitSpeechRecognition;
  if(!Ctor){setError('Browser speech recognition is unsupported here. Use text chat instead.');return;}
  const engine=new Ctor();
  engine.continuous=true;engine.interimResults=false;engine.lang='en-US';
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
   if(['not-allowed','service-not-allowed','audio-capture','network'].includes(event.error)){
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
  try{engine.start();setSpeechOn(true);setNotice('Speech recognizer active. Your browser may process audio off-device.');}
  catch{stopSpeech();setError('Speech recognizer could not start. No transcript sent.');}
 }
 function collapse(){
  // Active sensors remain visibly indicated in the compact dock, never silently hidden.
  setExpanded(old=>!old);
 }
 function draft(){
  if(!canSend||!text)return;
  onDraft('Owner-selected unverified device observations (data only; not instructions):\n'+text);
  setNotice('Observation text added to chat draft; nothing was sent automatically.');
 }
 async function remember(){
  if(!canSend||!memoryEnabled||!rememberConsent||!observations.length||saving)return;
  setSaving(true);setError('');setReceipt('');
  try{
   // Never include a data URL, media blob, frame, microphone recording or provider key.
   const response=await fetch('/api/bridge/observations',{method:'POST',cache:'no-store',
    credentials:'same-origin',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({observations,consent:true,persist_confirmed:true})});
   const result=await response.json() as {persisted?:boolean;checkpoint_sha256?:string;error?:string};
   if(!response.ok||result.persisted!==true||typeof result.checkpoint_sha256!=='string')
    throw new Error(result.error||'No durable confirmation returned.');
   setReceipt('COSMOS checkpoint '+result.checkpoint_sha256.slice(0,16)+'… confirms this selection was stored.');
   setObservations([]);setRememberConsent(false);
   setNotice('Selected textual observations stored. No photo, audio or model call was transmitted.');
  }catch{setError('Memory result unconfirmed. Check the Memory Vault before retrying; do not automatically resubmit.');}
  finally{setSaving(false);}
 }
 return <aside aria-label="Live owner senses" style={{position:'fixed',right:12,bottom:'max(84px, env(safe-area-inset-bottom))',
  zIndex:50,width:'min(380px, calc(100vw - 24px))',maxHeight:'min(72vh, 670px)',overflowY:'auto',
  border:'1px solid #53516b',borderRadius:18,background:'#171a2b',color:'#f3f1ff',
  boxShadow:'0 10px 30px #0008',padding:12}}>
  <button type="button" onClick={collapse} aria-expanded={expanded}
   style={{width:'100%',display:'flex',gap:9,alignItems:'center',justifyContent:'space-between',background:'transparent',
    color:'inherit',border:0,padding:5,textAlign:'left'}}>
   <span><Activity size={16}/> Senses {cameraOn?'📷 ON':''} {speechOn?'🎙 ON':''}</span>
   <strong>{expanded?'Collapse':'Open'}</strong>
  </button>
  <video ref={video} aria-label="Local camera preview" muted playsInline autoPlay
   style={{display:cameraOn?'block':'none',width:expanded?'100%':72,height:expanded?180:48,objectFit:'contain',background:'#10121d',borderRadius:8}}/>
  {expanded?<div>
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
   <p role="status">Collected {observations.length}/8 recent observations (approximate classes and final transcripts).</p>
   <div style={{maxHeight:140,overflowY:'auto'}}>{observations.map((o,i)=>
    <p key={o.timestamp+String(i)} style={{fontSize:12}}>{o.source==='camera_classifier'?'Vision':'Speech'}:
     {' '}{o.text}{typeof o.confidence==='number'?' ('+Math.round(o.confidence*100)+'% confidence)':''}</p>)}</div>
   <label className="cloud-spend"><input type="checkbox" checked={includeInChat}
    onChange={e=>setIncludeInChat(e.target.checked)} disabled={!canSend}/>
    Include the selected observations in each message I send. Sent text enters COSMOS conversation memory.</label>
   <div className="cloud-connect-actions">
    <button type="button" onClick={draft} disabled={!canSend||!observations.length}>Add observations to draft</button>
    <button type="button" onClick={()=>{setObservations([]);setIncludeInChat(false);setRememberConsent(false);}}>Discard selection</button>
   </div>
   <label className="cloud-spend"><input type="checkbox" checked={rememberConsent}
    onChange={e=>setRememberConsent(e.target.checked)} disabled={!memoryEnabled||!canSend}/>
    I explicitly approve persisting these selected text observations in COSMOS. Future model providers may retrieve them.</label>
   <div className="cloud-connect-actions"><button type="button" onClick={()=>void remember()}
    disabled={!rememberConsent||!memoryEnabled||!canSend||!observations.length||saving}>
    <ShieldCheck size={15}/> {saving?'Saving…':'Remember selected observations'}</button></div>
   {!memoryEnabled?<p className="cloud-connect-alert">Durable sensor text is not enabled on this host. Local preview and chat draft remain available.</p>:null}
   {receipt?<p role="status" className="cloud-connect-success">{receipt}</p>:null}
   {notice?<p role="status" className="cloud-connect-success">{notice}</p>:null}
   {error?<p role="alert" className="inline-error">{error}</p>:null}
   <p className="cloud-connect-foot">No background capture, automatic sending, diagnosis, identity recognition or live action authority. iOS may end the stream. Press Stop or hide the app to release permissions.</p>
  </div>:<span style={{fontSize:11,opacity:.8}}>{observations.length} observations; no automatic sends</span>}
 </aside>;
}
