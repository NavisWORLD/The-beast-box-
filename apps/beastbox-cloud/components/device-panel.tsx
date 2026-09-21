'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import {Camera,Mic,ShieldCheck,Square} from 'lucide-react';

type Props={canSend:boolean;onDraft:(text:string)=>void};
type Reading={camera?:string;microphone?:string};

/**
 * Browser-only, explicit-permission sensing. Never captures a photo, records
 * speech, sends media, or grants COSMOS host camera/microphone authority.
 * The current tiny language model accepts TEXT, not image or audio tensors.
 */
export default function DevicePanel({canSend,onDraft}:Props){
 const video=useRef<HTMLVideoElement>(null);
 const camera=useRef<MediaStream|null>(null),microphone=useRef<MediaStream|null>(null);
 const audio=useRef<AudioContext|null>(null),analyser=useRef<AnalyserNode|null>(null);
 const meter=useRef<ReturnType<typeof setInterval>|null>(null);
 const alive=useRef(true);
 const [cameraOn,setCameraOn]=useState(false),[micOn,setMicOn]=useState(false);
 const [level,setLevel]=useState(0),[sample,setSample]=useState<Reading>({});
 const [consent,setConsent]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [working,setWorking]=useState(false);
 const stopCamera=useCallback(()=>{
  camera.current?.getTracks().forEach(track=>track.stop());camera.current=null;
  if(video.current)video.current.srcObject=null;
  if(alive.current)setCameraOn(false);
 },[]);
 const stopMic=useCallback(()=>{
  if(meter.current!==null){clearInterval(meter.current);meter.current=null;}
  analyser.current=null;
  microphone.current?.getTracks().forEach(track=>track.stop());microphone.current=null;
  if(audio.current){void audio.current.close().catch(()=>{});audio.current=null;}
  if(alive.current){setMicOn(false);setLevel(0);}
 },[]);
 useEffect(()=>{
  alive.current=true;
  const handleVisibility=()=>{if(document.hidden){stopCamera();stopMic();}};
  document.addEventListener('visibilitychange',handleVisibility);
  return ()=>{alive.current=false;document.removeEventListener('visibilitychange',handleVisibility);
   stopCamera();stopMic();};
 },[stopCamera,stopMic]);

 async function startCamera(){
  if(working||camera.current)return;
  setError('');setNotice('');setWorking(true);
  let stream:MediaStream|null=null;
  try{
   if(!window.isSecureContext||!navigator.mediaDevices?.getUserMedia)
    throw new Error('Camera requires browser support and a secure HTTPS page.');
   stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}},audio:false});
   if(!alive.current){stream.getTracks().forEach(track=>track.stop());return;}
   camera.current=stream;
   if(!video.current)throw new Error('Camera preview is unavailable.');
   video.current.srcObject=stream;
   // iOS Safari may reject play() while the element is display:none.
   setCameraOn(true);
   await video.current.play();
  }catch{
   stream?.getTracks().forEach(track=>track.stop());stopCamera();
   if(alive.current)setError('Camera unavailable or permission denied. No image was sent.');
  }finally{if(alive.current)setWorking(false);}
 }
 async function startMic(){
  if(working||microphone.current)return;
  setError('');setNotice('');setWorking(true);
  let stream:MediaStream|null=null;
  try{
   if(!window.isSecureContext||!navigator.mediaDevices?.getUserMedia)
    throw new Error('Microphone requires browser support and a secure HTTPS page.');
   stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true},video:false});
   if(!alive.current){stream.getTracks().forEach(track=>track.stop());return;}
   microphone.current=stream;
   const ctx=new AudioContext();
   audio.current=ctx;
   const source=ctx.createMediaStreamSource(stream);
   const node=ctx.createAnalyser();
   node.fftSize=1024;
   source.connect(node); // Deliberately NOT connected to speakers or any recorder.
   analyser.current=node;
   await ctx.resume();
   meter.current=setInterval(()=>{
    if(!alive.current||!analyser.current)return;
    const data=new Float32Array(analyser.current.fftSize);
    analyser.current.getFloatTimeDomainData(data);
    const rms=Math.sqrt(data.reduce((sum,x)=>sum+x*x,0)/data.length);
    setLevel(Math.min(1,rms));
   },250);
   if(alive.current)setMicOn(true);
  }catch{
   stream?.getTracks().forEach(track=>track.stop());stopMic();
   if(alive.current)setError('Microphone unavailable or permission denied. No sound was sent.');
  }finally{if(alive.current)setWorking(false);}
 }

 function sampleCamera(){
  if(!camera.current||!video.current||video.current.readyState<2){setError('Camera frame is not ready yet.');return;}
  const canvas=document.createElement('canvas');
  canvas.width=32;canvas.height=24;
  const ctx=canvas.getContext('2d',{willReadFrequently:true});
  if(!ctx){setError('Canvas sampling is unavailable.');return;}
  ctx.drawImage(video.current,0,0,32,24);
  const rgba=ctx.getImageData(0,0,32,24).data;
  let sum=0;
  for(let i=0;i<rgba.length;i+=4)sum+=0.2126*rgba[i]+0.7152*rgba[i+1]+0.0722*rgba[i+2];
  const light=Math.round(sum/(32*24*255)*100);
  setSample(previous=>({...previous,camera:'Camera light-level sample: '+light+'% average brightness (32×24 local pixel summary; no object recognition).'}));
  setNotice('Camera sampled locally. Raw pixels have not left your device.');
 }
 function sampleMic(){
  if(!micOn||!analyser.current){setError('Turn on the microphone first.');return;}
  const data=new Float32Array(analyser.current.fftSize);
  analyser.current.getFloatTimeDomainData(data);
  const rms=Math.sqrt(data.reduce((sum,x)=>sum+x*x,0)/data.length);
  setSample(previous=>({...previous,microphone:'Microphone level sample: '+Math.round(Math.min(1,rms)*1000)/1000+' relative RMS (not speech transcription).'}));
  setNotice('Audio amplitude sampled locally. No recording or waveform was sent.');
 }
 function draft(){
  if(!consent||!canSend||(!sample.camera&&!sample.microphone))return;
  onDraft(['User-authorized browser sensor summary; approximate numeric readings, not vision or speech understanding.',
    sample.camera,sample.microphone].filter(Boolean).join('\n'));
  setConsent(false);setSample({});stopCamera();stopMic();
 }
 return <section className="data-card wide cloud-connect" aria-label="Browser camera and microphone">
  <div className="cloud-connect-heading"><Camera size={20}/><div><h2>Device senses · camera & microphone</h2><p>Permissioned browser preview; nothing starts automatically.</p></div></div>
  <p>Use your device camera and mic to generate small numerical summaries locally. The current text-only SmolLM2 cannot identify objects in images or transcribe speech. No video, photos or raw sound go to COSMOS.</p>
  <div className="cloud-connect-actions">
   <button type="button" disabled={working} onClick={()=>cameraOn?stopCamera():void startCamera()}>{cameraOn?<Square size={15}/>:<Camera size={15}/>} {cameraOn?'Stop camera':'Start camera'}</button>
   <button type="button" disabled={working} onClick={()=>micOn?stopMic():void startMic()}>{micOn?<Square size={15}/>:<Mic size={15}/>} {micOn?'Stop microphone':'Start microphone'}</button>
  </div>
  <video ref={video} muted playsInline autoPlay aria-label="Local camera preview" style={{display:cameraOn?'block':'none',width:'100%',maxHeight:260,objectFit:'contain',borderRadius:12,background:'#0d1220'}}/>
  {micOn?<p role="status">Microphone level: {Math.round(level*1000)/10}% relative amplitude (no recording)</p>:null}
  <div className="cloud-connect-actions">
   <button type="button" onClick={sampleCamera} disabled={!cameraOn}>Sample camera brightness</button>
   <button type="button" onClick={sampleMic} disabled={!micOn}>Sample microphone level</button>
  </div>
  {sample.camera?<p className="cloud-connect-success" role="status">{sample.camera}</p>:null}
  {sample.microphone?<p className="cloud-connect-success" role="status">{sample.microphone}</p>:null}
  <label className="cloud-spend"><input type="checkbox" checked={consent} onChange={event=>setConsent(event.target.checked)}/>
    I choose to draft these numeric summaries for COSMOS chat. Sending that chat will save its text in durable memory.</label>
  <div className="cloud-connect-actions">
   <button type="button" onClick={draft} disabled={!consent||!canSend||(!sample.camera&&!sample.microphone)}><ShieldCheck size={15}/> Add to chat draft (do not send yet)</button>
  </div>
  {!canSend?<p className="cloud-connect-alert">Connect a genuine model before transferring a summary into chat. Device preview stays local.</p>:null}
  {notice?<p className="cloud-connect-success" role="status">{notice}</p>:null}
  {error?<p className="inline-error" role="alert">{error}</p>:null}
  <p className="cloud-connect-foot">Camera/mic tracks stop on Stop, navigation or hidden tab. No background listening, cloud STT, image upload, medical or emotion interpretation, or physical actuation. A separate vision or speech model would be required for semantic seeing/hearing.</p>
 </section>;
}
