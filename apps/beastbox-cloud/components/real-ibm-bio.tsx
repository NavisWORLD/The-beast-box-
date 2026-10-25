'use client';
// Real IBM Bio Connection: ONE button. Measure a fingertip heartbeat on this device (rear camera + torch, optional mic),
// reduce it to numbers, inject the numbers into the existing bio path, dispatch the repo's real-IBM workflow, show the result.
// Raw video/audio never leave the device. Heartbeat MEASURED only if the PPG quality gate passes. IBM RECORDED only after the run. Rigetti SIMULATED.
import {useCallback,useEffect,useRef,useState} from 'react';
import {Activity,HeartPulse,Square,ExternalLink} from 'lucide-react';
import {measureFingertip,sha256Hex,MEASURE_SECONDS,type Progress} from '../lib/bio/capture';
import {buildBioPacket,existingBioInjection,type BioPacket} from '../lib/bio/bio-packet.mjs';
import {PPG_REASONS} from '../lib/bio/ppg.mjs';
import {IBM_STATES,QVM_STATES} from '../lib/bio/bio-states.mjs';

type Phase='idle'|'measuring'|'invalid'|'injecting'|'dispatching'|'dispatched'|'done'|'error';
type Status={found?:boolean;status?:string;conclusion?:string|null;run_url?:string;ibm?:string|null;rigetti?:string|null};
const POLL_MS=20000,POLL_MAX=135;
async function post(path:string,body:unknown){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),cache:'no-store'});const j=await r.json().catch(()=>({}));return {status:r.status,body:j as Record<string,unknown>};}

export default function RealIbmBio({owner}:{owner:boolean}){
 const [phase,setPhase]=useState<Phase>('idle'),[withMic,setWithMic]=useState(false);
 const [prog,setProg]=useState<Progress|null>(null),[msg,setMsg]=useState('');
 const [packet,setPacket]=useState<BioPacket|null>(null),[torch,setTorch]=useState<string>('');
 const [inject,setInject]=useState(''),[runUrl,setRunUrl]=useState(''),[status,setStatus]=useState<Status|null>(null);
 const abort=useRef<AbortController|null>(null),poll=useRef(0);
 useEffect(()=>()=>{abort.current?.abort();window.clearTimeout(poll.current);},[]);

 const pollStatus=useCallback((sha12:string,n=0)=>{
  poll.current=window.setTimeout(async()=>{
   try{const r=await fetch('/api/bio-connection?sha='+sha12,{cache:'no-store'});const j=await r.json() as Status&{ok?:boolean};
    if(r.ok&&j.found){setStatus(j);if(j.run_url)setRunUrl(j.run_url);if(j.status==='completed'){setPhase('done');return;}}
   }catch{}
   if(n<POLL_MAX)pollStatus(sha12,n+1);
  },n===0?4000:POLL_MS);
 },[]);

 const stop=()=>{abort.current?.abort();};
 const start=async()=>{
  setMsg('');setPacket(null);setInject('');setRunUrl('');setStatus(null);setProg(null);setTorch('');
  const ac=new AbortController();abort.current=ac;setPhase('measuring');
  try{
   const m=await measureFingertip({withMic,onProgress:setProg,signal:ac.signal});setTorch(m.torch);
   if(!m.ppg.valid){setPhase('invalid');setMsg(PPG_REASONS[m.ppg.reason||'no_pulse']||'No valid pulse.');return;}
   const pk=await buildBioPacket({ppg:m.ppg,light:m.light,audio:m.audio},sha256Hex);setPacket(pk);
   // 3) inject the numbers into the existing bio path (same schema BioPanel uses). Preview only; nothing is persisted by this button.
   setPhase('injecting');
   try{const i=await post('/api/bridge/bio',existingBioInjection(pk));
    setInject(i.status===200?'Injected into the bio loop (preview, not persisted).':i.status===503?'Bio loop host is offline or bio ingestion is off, so the host preview did not run. The numbers still seed the IBM run.':i.status===401?'Owner session needed for the bio loop.':'Bio loop did not accept the preview ('+i.status+'). The numbers still seed the IBM run.');
   }catch{setInject('Bio loop unreachable. The numbers still seed the IBM run.');}
   // 4) dispatch the real IBM workflow (server holds the GitHub token; the workflow holds the IBM secret)
   setPhase('dispatching');
   const d=await post('/api/bio-connection',{packet:pk});
   if(d.status!==200||d.body.ok!==true){setPhase('error');setMsg(d.status===401?'Owner login required. Sign in as the owner, then try again.':d.status===503?'Dispatch is not configured yet: the server needs BEASTBOX_GITHUB_DISPATCH_TOKEN. Your heartbeat was measured and the numbers are ready, but no IBM job was started.':String(d.body.error||'Dispatch failed ('+d.status+').'));return;}
   setRunUrl(String(d.body.run_url||''));setPhase('dispatched');pollStatus(pk.packet_sha256.slice(0,12));
  }catch(e){
   const aborted=e instanceof DOMException&&e.name==='AbortError';
   setPhase(aborted?'idle':'error');setMsg(aborted?'Measurement cancelled. Camera and light released.':e instanceof Error?e.message:'Measurement failed.');
  }
 };

 const busy=phase==='measuring'||phase==='injecting'||phase==='dispatching';
 const pct=prog?Math.round(prog.elapsed_s/prog.total_s*100):0;
 const ibm=status?.ibm?(IBM_STATES[status.ibm]||status.ibm):null,qvm=status?.rigetti?(QVM_STATES[status.rigetti]||status.rigetti):null;
 return <section className="cloud-connect data-card wide real-ibm-bio" aria-label="Real IBM Bio Connection">
  <div className="cloud-connect-heading"><HeartPulse size={20}/><div><h2>REAL IBM BIO CONNECTION</h2><p>Your fingertip heartbeat becomes numbers, seeds the signal loop, and starts one real IBM spark that continues into the Rigetti simulator.</p></div></div>
  {!owner?<p className="cloud-connect-alert" role="status">Owner login required. This button can start real IBM time, so only the owner session can use it.</p>:null}
  <ol className="rib-steps" style={{listStyle:'none',padding:0,margin:'10px 0',display:'grid',gap:6,fontSize:13}}>
   <li>1 · Heartbeat: {packet?<b>MEASURED · {packet.pulse.bpm.toFixed(0)} bpm{packet.pulse.hrv_rmssd_ms!==null?' · HRV '+packet.pulse.hrv_rmssd_ms.toFixed(0)+' ms':''} · quality {packet.pulse.sqi.toFixed(2)}</b>:phase==='measuring'?<b>measuring… {pct}%</b>:phase==='invalid'?<b>no valid pulse</b>:<span>not measured yet</span>}</li>
   <li>2 · Numbers only: {packet?<b>packet {packet.packet_sha256.slice(0,12)} · raw video/audio stay on this phone</b>:<span>waiting</span>}</li>
   <li>3 · Injected into the bio loop: {inject?<b>{inject}</b>:<span>waiting</span>}</li>
   <li>4 · Real IBM spark: {phase==='dispatching'?<b>dispatching…</b>:runUrl?<b>dispatched · <a href={runUrl} target="_blank" rel="noreferrer">Actions run <ExternalLink size={12}/></a></b>:<span>waiting</span>}</li>
   <li>5 · Result: {ibm||qvm?<b>{ibm||'IBM result pending'} · {qvm||'Rigetti pending'}</b>:phase==='dispatched'?<b>running… ({status?.status||'queued'})</b>:<span>waiting</span>}</li>
  </ol>
  {phase==='measuring'?<div role="status" aria-live="polite" style={{margin:'8px 0'}}>
   <div style={{height:8,borderRadius:4,background:'rgba(255,255,255,.12)',overflow:'hidden'}}><div style={{width:pct+'%',height:'100%',background:'#ff4d6d'}}/></div>
   <p className="cloud-connect-foot">{prog?.finger?'Finger detected. Hold still.':'Cover the rear camera AND the light with your fingertip, gently.'} Red {prog?.red??0} · Torch {prog?.torch==='requested'?'requested (unconfirmed)':prog?.torch==='unavailable'?'unavailable, use a bright lamp behind your finger':'…'}{prog?.provisional_bpm?' · provisional '+prog.provisional_bpm+' bpm (not final)':''}</p>
  </div>:null}
  {phase==='invalid'?<p className="cloud-connect-alert" role="alert"><b>No valid pulse.</b> {msg} Nothing was sent and no IBM time was used.</p>:null}
  {phase==='error'?<p className="cloud-connect-alert" role="alert">{msg}</p>:null}
  {phase==='idle'&&msg?<p className="cloud-connect-foot" role="status">{msg}</p>:null}
  {phase==='dispatched'||phase==='done'?<p className="cloud-connect-success" role="status">{phase==='done'?(status?.conclusion==='success'?'Run finished.':'Run finished with conclusion: '+(status?.conclusion||'unknown')+'.'):'Dispatched. IBM and the Rigetti simulator run inside GitHub Actions; this page checks every 20 seconds.'} {ibm?.startsWith('Skipped')?'No IBM job was submitted, so nothing is RECORDED.':''}</p>:null}
  <label className="cloud-spend"><input type="checkbox" checked={withMic} disabled={busy} onChange={e=>setWithMic(e.target.checked)}/> Also use the microphone for light audio numbers (levels only, no recording)</label>
  <div className="cloud-connect-actions">
   <button className="primary-action" type="button" disabled={!owner||busy} onClick={()=>void start()} aria-label="Start Real IBM Bio Connection"><Activity size={16}/> {phase==='measuring'?'MEASURING '+MEASURE_SECONDS+' S…':phase==='injecting'?'INJECTING…':phase==='dispatching'?'DISPATCHING…':'START REAL IBM BIO CONNECTION'}</button>
   {phase==='measuring'?<button className="outline-action" type="button" onClick={stop}><Square size={14}/> Cancel</button>:null}
  </div>
  <p className="cloud-connect-foot">Tap once, then hold your fingertip over the rear camera and light for {MEASURE_SECONDS} seconds. This sends numbers only (bpm, HRV, quality, light and audio levels, a sha256) and starts one real IBM run of at most 20 QPU seconds; it is skipped if the plan has under 60 seconds left. Heartbeat is MEASURED only when the pulse quality passes; IBM is RECORDED only after the run; Rigetti is SIMULATED. Not a medical device. {torch?'Torch: '+(torch==='requested'?'requested, unconfirmed':'unavailable')+'.':''}</p>
 </section>;
}
