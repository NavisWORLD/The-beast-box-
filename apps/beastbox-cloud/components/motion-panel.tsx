'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import {Activity,ShieldCheck,Square} from 'lucide-react';

type MotionPoint={magnitude:number;rotation:number|null;at:number};
type OrientationPoint={beta:number;gamma:number;at:number};
type DraftSample={text:string;at:number;rmsG:number|null};
type PermissionConstructor={requestPermission?:()=>Promise<'granted'|'denied'>};
type Props={canSend:boolean;onDraft:(text:string)=>void};
const SAMPLE_AGE_MS=60_000;
const LIVE_AGE_MS=3_000;
const number=(n:number|null|undefined):n is number=>typeof n==='number'&&Number.isFinite(n);
const rounded=(n:number)=>Math.round(n*100)/100;

/** Explicitly started, foreground-only browser numeric motion summary.
 * This is NOT a medical, location, identity or physical-actuation sensor.
 * It never transmits the stream; only a separately approved text draft can be sent.
 */
export default function MotionPanel({canSend,onDraft}:Props){
 const alive=useRef(false),enabled=useRef(false);
 const motion=useRef<MotionPoint|null>(null),orientation=useRef<OrientationPoint|null>(null);
 const aggregate=useRef({sumSq:0,count:0,start:0,at:0});
 const [active,setActive]=useState(false),[waiting,setWaiting]=useState(false);
 const [seen,setSeen]=useState(false),[sample,setSample]=useState<DraftSample|null>(null);
 const [consent,setConsent]=useState(false),[previewConsent,setPreviewConsent]=useState(false);
 const [previewing,setPreviewing]=useState(false),[previewVector,setPreviewVector]=useState<number[]|null>(null);
 const [clock,setClock]=useState(()=>Date.now());
 const [error,setError]=useState(''),[notice,setNotice]=useState('');
 const onMotion=useCallback((event:DeviceMotionEvent)=>{
  if(!enabled.current||document.hidden)return;
  const a=event.accelerationIncludingGravity;
  if(!number(a?.x)||!number(a?.y)||!number(a?.z))return;
  const r=event.rotationRate;
  // Clamp input to a finite, physically plausible display range. No high-rate state updates.
  const magnitude=Math.min(200,Math.hypot(a.x,a.y,a.z));
  const rotation=number(r?.alpha)&&number(r?.beta)&&number(r?.gamma)
    ?Math.min(2000,Math.hypot(r.alpha,r.beta,r.gamma)):null;
  const now=Date.now();
  motion.current={magnitude,rotation,at:now};
  // No gravity-free samples are retained: only a bounded 2s RMS accumulator.
  const raw=event.acceleration;
  if(number(raw?.x)&&number(raw?.y)&&number(raw?.z)){
   const value=Math.hypot(raw.x,raw.y,raw.z);
   if(value<=100){
    const bucket=aggregate.current;
    if(!bucket.start||now-bucket.start>2000){bucket.sumSq=0;bucket.count=0;bucket.start=now;}
    if(bucket.count<100){bucket.sumSq+=value*value;bucket.count++;bucket.at=now;}
   }
  }
  setSeen(true);
 },[]);
 const onOrientation=useCallback((event:DeviceOrientationEvent)=>{
  if(!enabled.current||document.hidden||!number(event.beta)||!number(event.gamma))return;
  orientation.current={beta:Math.max(-180,Math.min(180,event.beta)),
   gamma:Math.max(-90,Math.min(90,event.gamma)),at:Date.now()};
  setSeen(true);
 },[]);
 const stop=useCallback(()=>{
  enabled.current=false;
  window.removeEventListener('devicemotion',onMotion);
  window.removeEventListener('deviceorientation',onOrientation);
  motion.current=null;orientation.current=null;
  aggregate.current={sumSq:0,count:0,start:0,at:0};
  if(alive.current){setActive(false);setWaiting(false);setSeen(false);setSample(null);setConsent(false);setPreviewConsent(false);setPreviewVector(null);}
 },[onMotion,onOrientation]);
 useEffect(()=>{
  alive.current=true;
  const hidden=()=>{if(document.hidden)stop();};
  const pagehide=()=>stop();
  document.addEventListener('visibilitychange',hidden);
  window.addEventListener('pagehide',pagehide);
  return ()=>{alive.current=false;document.removeEventListener('visibilitychange',hidden);
   window.removeEventListener('pagehide',pagehide);stop();};
 },[stop]);
 useEffect(()=>{
  if(!sample)return;
  const timer=setInterval(()=>{
   const now=Date.now();setClock(now);
   if(now-sample.at>=SAMPLE_AGE_MS){setSample(null);setConsent(false);setPreviewConsent(false);setPreviewVector(null);}
  },5000);
  return ()=>clearInterval(timer);
 },[sample]);
 async function start(){
  if(enabled.current||waiting)return;
  setError('');setNotice('');setWaiting(true);setSample(null);setConsent(false);setPreviewConsent(false);setPreviewVector(null);
  try{
   if(!window.isSecureContext)throw new Error('Motion sensing requires an HTTPS page.');
   const m=typeof DeviceMotionEvent==='undefined'?null:
    DeviceMotionEvent as typeof DeviceMotionEvent & PermissionConstructor;
   const o=typeof DeviceOrientationEvent==='undefined'?null:
    DeviceOrientationEvent as typeof DeviceOrientationEvent & PermissionConstructor;
   if(!m&&!o)throw new Error('Motion/orientation events are unsupported by this browser.');
   // Invoke iOS permission requests directly from the Start-button gesture,
   // before yielding to an await or other asynchronous work.
   const requests:Promise<'granted'|'denied'>[]=[];
   if(m?.requestPermission)requests.push(m.requestPermission());
   if(o?.requestPermission)requests.push(o.requestPermission());
   if(requests.length&&(await Promise.all(requests)).some(result=>result!=='granted'))
    throw new Error('Motion permission was denied; no readings collected.');
   if(!alive.current||document.hidden)return;
   enabled.current=true;
   if(m)window.addEventListener('devicemotion',onMotion);
   if(o)window.addEventListener('deviceorientation',onOrientation);
   setActive(true);
   setNotice('Listening locally. Tap Sample now for one bounded numeric snapshot.');
  }catch(e){stop();if(alive.current)setError(e instanceof Error?e.message:'Motion sensing unavailable.');}
  finally{if(alive.current)setWaiting(false);}
 }
 function takeSample(){
  if(!enabled.current)return;
  const now=Date.now();
  const m=motion.current&&now-motion.current.at<LIVE_AGE_MS?motion.current:null;
  const o=orientation.current&&now-orientation.current.at<LIVE_AGE_MS?orientation.current:null;
  if(!m&&!o){setError('No fresh browser motion reading. Move your phone slightly or check permissions.');return;}
  const lines=['Owner-selected UNVERIFIED browser device motion sample (not location, medical data, or a command).',
   'Sample time: '+new Date(now).toISOString()];
  if(m){lines.push('Acceleration INCLUDING gravity magnitude: '+rounded(m.magnitude)+' m/s² (approximate).');
   if(m.rotation!==null)lines.push('Rotation rate magnitude: '+rounded(m.rotation)+' degrees/s (approximate).');}
  if(o)lines.push('Orientation tilt: beta '+rounded(o.beta)+'°, gamma '+rounded(o.gamma)+'° (device axes; approximate).');
  const bucket=aggregate.current;
  const rmsG=bucket.count>=3&&now-bucket.at<LIVE_AGE_MS
   ?Math.sqrt(bucket.sumSq/bucket.count)/9.80665:null;
  aggregate.current={sumSq:0,count:0,start:0,at:0};
  if(rmsG!==null&&rmsG<=20)lines.push('Gravity-free acceleration RMS: '+rounded(rmsG)+' g (approximate; '+bucket.count+' browser events).');
  setSample({text:lines.join('\n'),at:now,rmsG:rmsG!==null&&rmsG<=20?rounded(rmsG):null});
  setClock(now);setConsent(false);setPreviewConsent(false);setPreviewVector(null);setError('');
  setNotice('Numeric snapshot ready locally. No sensor stream was sent or stored.');
 }
 const fresh=sample!==null&&clock-sample.at<SAMPLE_AGE_MS;
 async function previewBio(){
  if(previewing||!previewConsent||!sample||sample.rmsG===null)return;
  if(Date.now()-sample.at>=SAMPLE_AGE_MS){setSample(null);setPreviewConsent(false);setError('Motion sample expired; collect a new one.');return;}
  setPreviewing(true);setError('');setPreviewVector(null);
  try{
   // Only feature flag metadata is fetched first; a disabled host receives NO measurement.
   const status=await fetch('/api/bridge/bio',{credentials:'same-origin',cache:'no-store'});
   const config=await status.json() as {enabled?:boolean};
   if(!status.ok||config.enabled!==true)throw new Error('Host bio normalization preview is disabled. No measurement was transmitted.');
   if(!alive.current||!enabled.current||document.hidden||Date.now()-sample.at>=SAMPLE_AGE_MS)
    throw new Error('Sensor stopped or numeric sample expired before submission.');
   const response=await fetch('/api/bridge/bio',{method:'POST',credentials:'same-origin',cache:'no-store',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({
     action:'preview',source:'browser_sensor',consent:true,
     readings:{accelerometer_rms_g:sample.rmsG}})});
   const result=await response.json() as {persisted?:boolean;model_invoked?:boolean;event?:{features?:number[]};error?:string};
   if(!response.ok)throw new Error(result.error||'Host rejected numeric preview.');
   const vector=result.event?.features;
   if(result.persisted!==false||result.model_invoked!==false||!Array.isArray(vector)||
      vector.length!==12||vector.some(v=>typeof v!=='number'||!Number.isFinite(v)||Math.abs(v)>1))
    throw new Error('Host preview returned an invalid or unconfirmed normalized event.');
   if(alive.current&&enabled.current&&!document.hidden){
    setPreviewVector(vector);
    setNotice('Host normalized one unverified motion number; no model or durable state was changed.');
   }
   setPreviewConsent(false);
  }catch(e){if(alive.current)setError(e instanceof Error?e.message:'Host preview unavailable.');}
  finally{if(alive.current)setPreviewing(false);}
 }
 function draft(){
  if(!canSend||!consent||!sample)return;
  if(Date.now()-sample.at>=SAMPLE_AGE_MS){setSample(null);setConsent(false);setPreviewConsent(false);setPreviewVector(null);setError('Sample expired. Collect another reading.');return;}
  onDraft(sample.text);stop();
 }
 return <section className="data-card wide cloud-connect" aria-label="Browser motion sensor">
  <div className="cloud-connect-heading"><Activity size={20}/><div><h2>Device motion · optional</h2>
   <p>iPhone/Android acceleration and tilt, when supported. Explicit foreground permission only.</p></div></div>
  <p>One approximate numerical snapshot, not a motion recording or a location. No stream, identifiers, sensor access, or tool authority reaches the model. Browser support varies.</p>
  <div className="cloud-connect-actions">
   <button type="button" disabled={waiting} onClick={()=>active?stop():void start()}>
    {active?<Square size={15}/>:<Activity size={15}/>} {waiting?'Requesting permission…':active?'Stop motion':'Start motion'}</button>
   <button type="button" disabled={!active||!seen} onClick={takeSample}>Sample now</button>
  </div>
  <p role="status">Motion: {active?(seen?'Receiving numeric events':'Waiting for device events'):'OFF'}.</p>
  {fresh&&sample?<p className="cloud-connect-success" role="status" style={{whiteSpace:'pre-wrap'}}>{sample.text}</p>:null}
  {sample&&!fresh?<p role="status">The snapshot expired after 60 seconds. Sample again.</p>:null}
  <label className="cloud-spend"><input type="checkbox" checked={consent}
   onChange={event=>setConsent(event.target.checked)} disabled={!fresh||!canSend}/>
   I approve adding this numeric sample to my chat draft. Only if I subsequently send that chat may its text enter COSMOS conversation memory.</label>
  <div className="cloud-connect-actions"><button type="button" onClick={draft}
   disabled={!canSend||!consent||!fresh}><ShieldCheck size={15}/> Add sample to draft (do not send)</button>
   <button type="button" onClick={()=>{setSample(null);setConsent(false);setPreviewConsent(false);setPreviewVector(null);}} disabled={!sample}>Discard sample</button></div>
  <label className="cloud-spend"><input type="checkbox" checked={previewConsent}
   onChange={event=>setPreviewConsent(event.target.checked)} disabled={!fresh||sample?.rmsG===null||previewing}/>
   I approve transmitting ONLY this one approximate gravity-free acceleration RMS number to the authenticated COSMOS host for a non-persistent, CST-compatible 12-channel normalization preview. No model, hardware authority or durable memory operation.</label>
  <div className="cloud-connect-actions"><button type="button" disabled={!fresh||!previewConsent||sample?.rmsG===null||previewing}
   onClick={()=>void previewBio()}><Activity size={15}/> {previewing?'Normalizing…':'Preview 12-channel numeric event (do not save)'}</button></div>
  {fresh&&sample?.rmsG===null?<p role="status">Gravity-free motion data was unavailable; no RMS estimate can be sent to the host.</p>:null}
  {previewVector?<p className="cloud-connect-success" role="status">Normalized 12-channel vector: {previewVector.join(', ')}. Only index 6 corresponds to acceleration; other channels are missing, not measured. No CST runtime state or checkpoint changed.</p>:null}
  {!canSend?<p className="cloud-connect-alert">Connect a genuine model to draft a sample. Local sensing remains optional.</p>:null}
  {notice?<p className="cloud-connect-success" role="status">{notice}</p>:null}
  {error?<p className="inline-error" role="alert">{error}</p>:null}
  <p className="cloud-connect-foot">Stop, tab hide, page exit and navigation release listeners and discard readings. No background capture, medical diagnosis, person tracking, automatic transmission or persistent physiological measurements. A one-off host preview is not continuous CST runtime integration.</p>
 </section>;
}
