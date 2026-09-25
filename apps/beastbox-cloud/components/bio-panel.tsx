'use client';
import {useCallback,useEffect,useState} from 'react';
import {Activity,ShieldCheck} from 'lucide-react';

type QuantumArchive={schema:string;records:Array<{index:number;job_id:string;backend:string;timestamp:string;entropy:number;top_state:string;total_shots:number}>;live_hardware:boolean;raw_results_present:boolean;new_paid_job_required:boolean};
type BioConfig={enabled:boolean;persist_enabled:boolean;remote_enabled:boolean;cst_preview_enabled?:boolean;cns_model_probe_enabled?:boolean;signal_model_probe_enabled?:boolean;quantum_archive?:QuantumArchive|null};
type BioResult={persisted?:boolean;event?:{features?:number[]};checkpoint_sha256?:string;error?:string};
const METRICS=[
 {key:'heart_rate_bpm',label:'Heart rate (bpm)',min:30,max:220,step:1},
 {key:'hrv_rmssd_ms',label:'HRV RMSSD (ms)',min:0,max:500,step:0.1},
 {key:'respiration_rate_bpm',label:'Respiration (breaths/min)',min:4,max:60,step:0.1},
 {key:'skin_temperature_c',label:'Skin temperature (°C)',min:20,max:45,step:0.1},
 {key:'spo2_pct',label:'SpO₂ (%)',min:70,max:100,step:0.1},
 {key:'eda_microsiemens',label:'Electrodermal activity (µS)',min:0,max:100,step:0.1},
] as const;

export default function BioPanel({backendReachable}:{backendReachable:boolean}){
 const [config,setConfig]=useState<BioConfig|null>(null);
 const [consent,setConsent]=useState(false),[persistConsent,setPersistConsent]=useState(false),[remoteConsent,setRemoteConsent]=useState(false);
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [compareConsent,setCompareConsent]=useState(false),[comparison,setComparison]=useState<{delta_l2:Record<string,number>;controls:Record<string,{dyn12:number[]}>;event_sha256:string}|null>(null);
 const [values,setValues]=useState<Record<string,string>>({});
 const [probeApproved,setProbeApproved]=useState(false),[probePrompt,setProbePrompt]=useState('Hello, Beast.');
 const [probeResult,setProbeResult]=useState<{logit_l2:Record<string,number>;reference_response:string;conditioned_response:string;
   checkpoint_sha256:string;event_sha256:string;cns7_roles:string[];same_response:boolean}|null>(null);
 const [signalMode,setSignalMode]=useState<'pure_sensory'|'pure_quantum'|'fused'>('fused');
 const [archiveIndex,setArchiveIndex]=useState(0),[signalApproved,setSignalApproved]=useState(false);
 const [signalResult,setSignalResult]=useState<{
  checkpoint_sha256:string;mode:string;cns_dyn12:number[];
  fusion:{fusion_sha256:string;vector:number[];equation:string};
  sources:Array<{family:string;execution_mode:string;kind:string}>;
  time_shift_control?:{shifted_index:number;classification:string}|null;
  native_probe:{logit_l2_vs_reference:Record<string,number>;response_reference:string;response_conditioned:string;
   conditioned_cache_parity:boolean;arms:Record<string,{telemetry_by_layer:Array<{gate:number;sigma:number;state_norm:number;omega_mean:number}>}>};
  live_quantum_hardware_used:boolean;paid_provider_job_started:boolean;weights_updated:boolean;persistent_memory_updated:boolean;
 }|null>(null);
 const refresh=useCallback(async()=>{
  if(!backendReachable){setConfig(null);return;}
  const resp=await fetch('/api/bridge/bio',{credentials:'same-origin',cache:'no-store'});
  if(!resp.ok)throw new Error('Could not check bio integration status.');
  setConfig(await resp.json() as BioConfig);
 },[backendReachable]);
 useEffect(()=>{void refresh().catch(()=>{setConfig(null);setError('Bio service unreachable; no data was sent.');});},[refresh]);
 async function compare(){
  if(!backendReachable||!config?.cst_preview_enabled||busy||!consent||!compareConsent)return;
  const readings:Record<string,number>={};
  for(const field of METRICS){
   const raw=values[field.key]?.trim();
   if(!raw)continue;
   const value=Number(raw);
   if(!Number.isFinite(value)||value<field.min||value>field.max){setError('Check the declared unit ranges.');return;}
   readings[field.key]=value;
  }
  if(!Object.keys(readings).length){setError('Enter a numerical measurement to compare.');return;}
  setBusy(true);setError('');setNotice('');setComparison(null);
  try{
   const response=await fetch('/api/bridge/bio',{method:'POST',credentials:'same-origin',cache:'no-store',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'cst_preview',source:'manual',
     consent:true,compare_confirmed:true,readings})});
   const result=await response.json() as {schema?:string;persisted?:boolean;model_invoked?:boolean;
    delta_l2?:Record<string,number>;controls?:Record<string,{dyn12:number[]}>;event_sha256?:string;error?:string};
   if(!response.ok)throw new Error(result.error||'Isolated software state preview rejected.');
   if(result.schema!=='cst-software-sensor-preview-v1'||result.persisted!==false||
      result.model_invoked!==false||!result.delta_l2||!result.controls||
      !Object.values(result.delta_l2).every(v=>typeof v==='number'&&Number.isFinite(v)&&v>=0)||
      !Object.values(result.controls).every(arm=>Array.isArray(arm.dyn12)&&arm.dyn12.length===12&&
       arm.dyn12.every(v=>typeof v==='number'&&Number.isFinite(v)&&Math.abs(v)<=1))||
      typeof result.event_sha256!=='string'||! /^[a-f0-9]{64}$/.test(result.event_sha256))
    throw new Error('Host returned no valid, nonpersistent software comparison.');
   setComparison({delta_l2:result.delta_l2,controls:result.controls,event_sha256:result.event_sha256});
   setNotice('Matched reference-state controls completed without a model call or durable write.');
  }catch(e){setError(e instanceof Error?e.message:'Software-state comparison unavailable.');}
  finally{setBusy(false);setCompareConsent(false);}
 }
 async function runModelProbe(){
  if(!backendReachable||!config?.cns_model_probe_enabled||!consent||!probeApproved||busy||!probePrompt.trim())return;
  const readings:Record<string,number>={};
  for(const f of METRICS){
   const raw=values[f.key]?.trim();if(!raw)continue;
   const n=Number(raw);
   if(!Number.isFinite(n)||n<f.min||n>f.max){setError('Check numerical sensor ranges.');return;}
   readings[f.key]=n;
  }
  if(!Object.keys(readings).length){setError('Enter one numeric sensor value first.');return;}
  setBusy(true);setError('');setNotice('');setProbeResult(null);setProbeApproved(false);
  try{
   const response=await fetch('/api/bridge/cns-model-probe',{method:'POST',credentials:'same-origin',cache:'no-store',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({source:'manual',consent:true,model_probe_confirmed:true,readings,text:probePrompt.trim()})});
   const v=await response.json() as {schema?:string;model_invoked?:boolean;weights_updated?:boolean;
    persistent_memory_updated?:boolean;owner_tools_used?:boolean;quantum_hardware_used?:boolean;
    intelligence_gain_proven?:boolean;logit_l2?:Record<string,number>;reference_response?:string;
    conditioned_response?:string;checkpoint_sha256?:string;event_sha256?:string;
    cns7_roles?:string[];same_response?:boolean;error?:string};
   if(!response.ok)throw new Error(v.error||'Native CNS-model comparison unavailable.');
   if(v.schema!=='cosmos-cns7-model-probe-v1'||v.model_invoked!==true||
      v.weights_updated!==false||v.persistent_memory_updated!==false||
      v.owner_tools_used!==false||v.quantum_hardware_used!==false||
      v.intelligence_gain_proven!==false||!v.logit_l2||
      Object.values(v.logit_l2).some(n=>typeof n!=='number'||!Number.isFinite(n)||n<0)||
      typeof v.reference_response!=='string'||typeof v.conditioned_response!=='string'||
      typeof v.same_response!=='boolean'||!Array.isArray(v.cns7_roles)||v.cns7_roles.length!==7||
      !/^[a-f0-9]{64}$/.test(v.checkpoint_sha256||'')||!/^[a-f0-9]{64}$/.test(v.event_sha256||''))
      throw new Error('Host returned no verifiable real-model CNS comparison.');
   setProbeResult(v as NonNullable<typeof probeResult>);
   setNotice('Pinned RAWRPHØS ran a real, fixed-weight sensor-conditioned comparison. No durable write.');
  }catch(e){setError(e instanceof Error?e.message:'Native probe unavailable.');}
  finally{setBusy(false);}
 }
 async function runSignalProbe(){
  if(!backendReachable||!config?.signal_model_probe_enabled||busy||!signalApproved||!probePrompt.trim())return;
  const needsSensory=signalMode!=='pure_quantum';
  const needsQuantum=signalMode!=='pure_sensory';
  const readings:Record<string,number>={};
  if(needsSensory){
   if(!consent){setError('Approve this one numerical measurement submission first.');return;}
   for(const f of METRICS){
    const raw=values[f.key]?.trim();if(!raw)continue;
    const n=Number(raw);
    if(!Number.isFinite(n)||n<f.min||n>f.max){setError('Check numerical sensor ranges.');return;}
    readings[f.key]=n;
   }
   if(!Object.keys(readings).length){setError('Enter one numeric sensor value for sensory or fused conditioning.');return;}
  }
  const records=config.quantum_archive?.records||[];
  if(needsQuantum&&!records.some(r=>r.index===archiveIndex)){setError('Choose a listed archive replay record.');return;}
  setBusy(true);setError('');setNotice('');setSignalResult(null);setSignalApproved(false);
  try{
   const sensory=needsSensory?{type:'bio',source:'manual',consent:true,readings}:null;
   const quantum=needsQuantum?{type:'ibm_fez_published_summary',index:archiveIndex,archive_replay_confirmed:true}:null;
   const response=await fetch('/api/bridge/signal-model-probe',{method:'POST',credentials:'same-origin',cache:'no-store',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text:probePrompt.trim(),mode:signalMode,conditioning_confirmed:true,sensory,quantum})});
   const v=await response.json() as {schema?:string;checkpoint_sha256?:string;mode?:string;cns_dyn12?:number[];
    fusion?:{fusion_sha256?:string;vector?:number[];equation?:string};sources?:Array<{family?:string;execution_mode?:string;kind?:string}>;
    time_shift_control?:{shifted_index?:number;classification?:string}|null;
    native_probe?:{logit_l2_vs_reference?:Record<string,number>;response_reference?:string;response_conditioned?:string;
     conditioned_cache_parity?:boolean;arms?:Record<string,{telemetry_by_layer?:Array<{gate?:number;sigma?:number;state_norm?:number;omega_mean?:number}>}>};
    live_quantum_hardware_used?:boolean;paid_provider_job_started?:boolean;weights_updated?:boolean;persistent_memory_updated?:boolean;error?:string};
   if(!response.ok)throw new Error(v.error||'Typed sensory/quantum native probe unavailable.');
   const logits=v.native_probe?.logit_l2_vs_reference;
   if(v.schema!=='cosmos-sensory-quantum-native-probe-v1'||v.mode!==signalMode||
      !/^[a-f0-9]{64}$/.test(v.checkpoint_sha256||'')||
      !Array.isArray(v.cns_dyn12)||v.cns_dyn12.length!==12||v.cns_dyn12.some(n=>typeof n!=='number'||!Number.isFinite(n)||Math.abs(n)>1)||
      !v.fusion||!/^[a-f0-9]{64}$/.test(v.fusion.fusion_sha256||'')||
      !Array.isArray(v.fusion.vector)||v.fusion.vector.length!==12||
      !Array.isArray(v.sources)||!v.sources.length||!logits||Object.values(logits).some(n=>typeof n!=='number'||!Number.isFinite(n)||n<0)||
      v.native_probe?.conditioned_cache_parity!==true||
      typeof v.native_probe?.response_reference!=='string'||typeof v.native_probe?.response_conditioned!=='string'||
      v.live_quantum_hardware_used!==false||v.paid_provider_job_started!==false||
      v.weights_updated!==false||v.persistent_memory_updated!==false)
     throw new Error('Host returned no verifiable typed fixed-weight comparison.');
   setSignalResult(v as NonNullable<typeof signalResult>);
   setNotice('Typed signal experiment completed against pinned RAWRPHØS. Archive replay is classical replay; no QPU job, durable memory write, or weight update occurred.');
  }catch(e){setError(e instanceof Error?e.message:'Typed signal probe unavailable.');}
  finally{setBusy(false);}
 }
 async function send(action:'preview'|'persist'){
  if(!backendReachable||!config?.enabled||busy||!consent)return;
  setError('');setNotice('');
  const readings:Record<string,number>={};
  for(const field of METRICS){
   const raw=values[field.key]?.trim();
   if(!raw)continue;
   const value=Number(raw);
   if(!Number.isFinite(value)||value<field.min||value>field.max){setError('Check the declared unit ranges.');return;}
   readings[field.key]=value;
  }
  if(!Object.keys(readings).length){setError('Enter at least one measurement.');return;}
  if(action==='persist'&&!persistConsent){setError('Confirm durable retention separately.');return;}
  setBusy(true);
  try{
   const payload={action,source:'manual',consent:true,readings,
    ...(action==='persist'?{persist_confirmed:true,...(remoteConsent?{remote_share_confirmed:true}:{})}:{})};
   const resp=await fetch('/api/bridge/bio',{method:'POST',credentials:'same-origin',cache:'no-store',
    headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
   const result=await resp.json() as BioResult;
   if(!resp.ok)throw new Error(result.error||'Bio request rejected.');
   setNotice(action==='preview'?'Preview complete: normalized numbers only. No new memory or model request.':
    'Confirmed measurement committed to the existing COSMOS substrate. This is not a clinical or emotion assessment.');
   setPersistConsent(false);setRemoteConsent(false);
  }catch(e){setError((e as Error).message);}finally{setBusy(false);}
 }
 return <section className="cloud-connect data-card wide" aria-label="Bio sensor integration">
  <div className="cloud-connect-heading"><Activity size={20}/><div><h2>Bio / sensor inputs</h2><p>Owner-permissioned physiological summaries, not a diagnosis.</p></div></div>
  <p>Supply numbers manually to preview the 12-channel CST adapter. Missing readings stay marked missing. No wearable, Health app, EEG hardware, or camera permissions are automatically requested.</p>
  {!backendReachable||!config?.enabled?<p className="cloud-connect-alert" role="status">Bio ingestion is disabled on the host. Set BEASTBOX_BIO_INGEST_ENABLED=yes on the persistent service to allow owner previews. No measurements will be transmitted.</p>:null}
  <form onSubmit={e=>{e.preventDefault();void send('preview');}} autoComplete="off">
   {METRICS.map(f=><label key={f.key}>{f.label}<input type="number" min={f.min} max={f.max} step={f.step} inputMode="decimal" value={values[f.key]||''}
    onChange={e=>{setValues(old=>({...old,[f.key]:e.target.value}));setComparison(null);setCompareConsent(false);}} disabled={!backendReachable||!config?.enabled||busy}/></label>)}
   <label><span>Explicit bio-data consent</span><span><input type="checkbox" checked={consent} disabled={!backendReachable||!config?.enabled||busy} onChange={e=>setConsent(e.target.checked)}/> I authorize this one measurement submission.</span></label>
   <button type="submit" disabled={!backendReachable||!config?.enabled||!consent||busy}><ShieldCheck size={16}/> {busy?'Processing…':'Preview without saving'}</button>
  </form>
  {config?.cst_preview_enabled?<div className="cloud-connect-actions">
   <label className="cloud-spend"><input type="checkbox" checked={compareConsent} disabled={!backendReachable||!consent||busy}
    onChange={event=>setCompareConsent(event.target.checked)}/> I separately approve running one isolated software CST/dyn12 comparison using these entered numbers. This computes matched baseline, zero-gate, shuffled and frozen controls. It does not invoke a model or persist data.</label>
   <button type="button" disabled={!compareConsent||!consent||busy||!backendReachable} onClick={()=>void compare()}>
    <Activity size={16}/> Compare software states (no save)</button>
  </div>:<p className="cloud-connect-foot">Isolated CST controls are disabled on this host. The ordinary bio preview does not run hosted dyn12.</p>}
  {comparison?<div className="cloud-connect-success" role="status">
    <strong>Isolated reference-state control comparison · one step</strong>
    <p>Baseline vs zero-gate L2: {comparison.delta_l2.vs_zero_gate}; vs shuffled: {comparison.delta_l2.vs_shuffled}; vs frozen: {comparison.delta_l2.vs_frozen}.</p>
    <p>Input event SHA-256: {comparison.event_sha256.slice(0,16)}… Baseline dyn12: {comparison.controls.baseline?.dyn12.join(', ')}.</p>
    <p>Numerical state differences are not evidence of improved model accuracy, living physiology or quantum effects. No durable memory changed.</p>
  </div>:null}
  {config?.cns_model_probe_enabled?<div className="cloud-connect-actions">
   <h3>🪰 CNS7 → RAWRPHØS · Real inference probe</h3>
   <p>Runs the existing seven-role software controller on your entered numbers, then compares pinned stable 14K model logits and two fixed-seed responses. Separate from normal owner chat. No sensor hardware or QPU is attested; no weights, history or memory are changed.</p>
   <label htmlFor="cns-probe-prompt">Short prompt (1–220 characters)</label>
   <input id="cns-probe-prompt" value={probePrompt} maxLength={220} disabled={busy}
    onChange={e=>{setProbePrompt(e.target.value);setProbeResult(null);}}/>
   <label className="cloud-spend"><input type="checkbox" checked={probeApproved} disabled={busy||!consent}
    onChange={e=>setProbeApproved(e.target.checked)}/> I separately approve sending these unverified numerical readings through CNS7 to the private, pinned RAWRPHØS 14K model for this one experiment. No quantum hardware, cloud billing, memory retention or tool use.</label>
   <button type="button" disabled={busy||!backendReachable||!consent||!probeApproved||!probePrompt.trim()} onClick={()=>void runModelProbe()}>
    <Activity size={16}/> {busy?'Running paired native inference…':'Compare native CNS7 vs reference'}
   </button>
   {probeResult?<div className="cloud-connect-success" role="status">
    <strong>Real native model · paired fixed-weight probe</strong>
    <p>Model SHA: {probeResult.checkpoint_sha256.slice(0,16)}… · Sensor event SHA: {probeResult.event_sha256.slice(0,16)}…</p>
    <p>Controller roles: {probeResult.cns7_roles.join(', ')}.</p>
    <p>Conditioned vs reference next-token logit L2: {probeResult.logit_l2.conditioned_vs_reference}; vs rotated input: {probeResult.logit_l2.conditioned_vs_rotated}; zero vs reference: {probeResult.logit_l2.zero_vs_reference}.</p>
    <p><strong>Reference:</strong> {probeResult.reference_response||'(empty)'}</p>
    <p><strong>Conditioned:</strong> {probeResult.conditioned_response||'(empty)'}</p>
    <p>{probeResult.same_response?'Both responses are identical.':'Responses differ under the fixed-seed control.'} A changed logit or sentence does NOT prove improved intelligence or a quantum effect.</p>
   </div>:null}
  </div>:<p className="cloud-connect-foot">Real native CNS7-to-model comparison is off on this host until BEASTBOX_CNS_MODEL_PROBE_ENABLED=yes. Standard chat is unaffected.</p>}
  {config?.signal_model_probe_enabled?<div className="cloud-connect-actions">
   <h3>🌌 Sensory + quantum-derived → CNS7 → RAWRPHØS</h3>
   <p>This owner-only experiment keeps three contracts separate: current numerical sensory data, a published IBM Fez archive-summary replay, and the model&apos;s generic C1–C12 control input. Archive replay is classical replay, not a fresh QPU run.</p>
   <label htmlFor="signal-mode">Conditioning source
    <select id="signal-mode" value={signalMode} disabled={busy} onChange={e=>{setSignalMode(e.target.value as typeof signalMode);setSignalResult(null);setSignalApproved(false);}}>
     <option value="pure_sensory">Sensory only</option><option value="pure_quantum">Quantum-derived archive replay only</option><option value="fused">Fused sensory + quantum-derived replay</option>
    </select>
   </label>
   {signalMode!=='pure_sensory'?<label htmlFor="archive-record">IBM Fez published summary replay
    <select id="archive-record" value={archiveIndex} disabled={busy} onChange={e=>{setArchiveIndex(Number(e.target.value));setSignalResult(null);setSignalApproved(false);}}>
     {(config.quantum_archive?.records||[]).map(r=><option key={r.index} value={r.index}>#{r.index+1} · {r.backend} · {r.timestamp} · H={r.entropy}</option>)}
    </select>
   </label>:null}
   <p className="cloud-connect-foot">The archived records expose source-reported job ID, timestamp, entropy, top state and shot count only. Full raw histograms are not reconstructed. No paid provider execution is started by this control.</p>
   <label className="cloud-spend"><input type="checkbox" checked={signalApproved} disabled={busy||(signalMode!=='pure_quantum'&&!consent)}
    onChange={e=>setSignalApproved(e.target.checked)}/> I approve one fixed-weight native comparison using the selected typed sources. This does not persist the readings, train the model, grant tools, or launch IBM/Azure quantum hardware.</label>
   <button type="button" disabled={busy||!backendReachable||!signalApproved||!probePrompt.trim()||(signalMode!=='pure_quantum'&&!consent)}
    onClick={()=>void runSignalProbe()}><Activity size={16}/> {busy?'Running matched signal arms…':'Run typed signal → native model experiment'}</button>
   {signalResult?<div className="cloud-connect-success" role="status">
    <strong>Typed fixed-weight integration receipt</strong>
    <p>Mode: {signalResult.mode} · Model SHA: {signalResult.checkpoint_sha256.slice(0,16)}… · Fusion SHA: {signalResult.fusion.fusion_sha256.slice(0,16)}…</p>
    <p>Sources: {signalResult.sources.map(s=>s.family+' / '+s.kind+' / '+s.execution_mode).join(' · ')}.</p>
    <p>Conditioned vs reference logit L2: {signalResult.native_probe.logit_l2_vs_reference.conditioned}; classical matched: {signalResult.native_probe.logit_l2_vs_reference.classical_matched}; zero: {signalResult.native_probe.logit_l2_vs_reference.zero}.</p>
    {signalResult.time_shift_control?<p>Time-shift control used archive record #{signalResult.time_shift_control.shifted_index+1}: {signalResult.time_shift_control.classification}.</p>:null}
    <p><strong>Reference:</strong> {signalResult.native_probe.response_reference||'(empty)'}</p>
    <p><strong>Conditioned:</strong> {signalResult.native_probe.response_conditioned||'(empty)'}</p>
    <p>Cache parity: {signalResult.native_probe.conditioned_cache_parity?'verified':'failed'}. A changed logit/output demonstrates computational sensitivity only; it does not establish quantum advantage, biological life, or improved intelligence.</p>
   </div>:null}
  </div>:<p className="cloud-connect-foot">Typed sensory/quantum native probe is off until BEASTBOX_SIGNAL_MODEL_PROBE_ENABLED=yes. No live QPU job is needed for archive replay.</p>}
  {config?.persist_enabled?<div className="cloud-connect-actions">
   <label className="cloud-spend"><input type="checkbox" checked={persistConsent} disabled={busy} onChange={e=>setPersistConsent(e.target.checked)}/> I explicitly consent to durable memory and model processing of these measurements.</label>
   {config.remote_enabled?<label className="cloud-spend"><input type="checkbox" checked={remoteConsent} disabled={busy} onChange={e=>setRemoteConsent(e.target.checked)}/> If a remote model is active, I also approve sharing the normalized measurements with that provider.</label>:null}
   <button type="button" disabled={!consent||!persistConsent||busy||!backendReachable} onClick={()=>void send('persist')}>Commit to COSMOS memory</button>
  </div>:<p className="cloud-connect-foot">Durable bio ingestion remains disabled. Host must separately set BEASTBOX_BIO_PERSIST_ENABLED=yes. Preview changes no checkpoint.</p>}
  {notice?<p className="cloud-connect-success" role="status">{notice}</p>:null}
  {error?<p className="inline-error" role="alert">{error}</p>:null}
  <p className="cloud-connect-foot">For research and personal experimentation only. Source labels are user-supplied, not hardware-attested. No automatic diagnosis, emotion inference, cloud billing, or device control.</p>
 </section>;
}
