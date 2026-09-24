'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import {Activity,ShieldCheck,Square} from 'lucide-react';

type MotionPoint={magnitude:number;rotation:number|null;at:number};
type OrientationPoint={beta:number;gamma:number;at:number};
type DraftSample={text:string;at:number};
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
 const [active,setActive]=useState(false),[waiting,setWaiting]=useState(false);
 const [seen,setSeen]=useState(false),[sample,setSample]=useState<DraftSample|null>(null);
 const [consent,setConsent]=useState(false),[clock,setClock]=useState(()=>Date.now());
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
  motion.current={magnitude,rotation,at:Date.now()};
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
  if(alive.current){setActive(false);setWaiting(false);setSeen(false);setSample(null);setConsent(false);}
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
  const timer=setInterval(()=>setClock(Date.now()),5000);
  return ()=>clearInterval(timer);
 },[sample]);
 async function start(){
  if(enabled.current||waiting)return;
  setError('');setNotice('');setWaiting(true);setSample(null);setConsent(false);
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
  setSample({text:lines.join('\n'),at:now});setClock(now);setConsent(false);setError('');
  setNotice('Numeric snapshot ready locally. No sensor stream was sent or stored.');
 }
 const fresh=sample!==null&&clock-sample.at<SAMPLE_AGE_MS;
 function draft(){
  if(!canSend||!consent||!sample)return;
  if(Date.now()-sample.at>=SAMPLE_AGE_MS){setSample(null);setConsent(false);setError('Sample expired. Collect another reading.');return;}
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
   <button type="button" onClick={()=>{setSample(null);setConsent(false);}} disabled={!sample}>Discard sample</button></div>
  {!canSend?<p className="cloud-connect-alert">Connect a genuine model to draft a sample. Local sensing remains optional.</p>:null}
  {notice?<p className="cloud-connect-success" role="status">{notice}</p>:null}
  {error?<p className="inline-error" role="alert">{error}</p>:null}
  <p className="cloud-connect-foot">Stop, tab hide, page exit and navigation release listeners and discard readings. No background capture, medical diagnosis, person tracking, automatic transmission or persistent physiological measurements.</p>
 </section>;
}
