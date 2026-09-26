'use client';
import {useState} from 'react';
import {Activity} from 'lucide-react';

type Report={
 schema:string;engine_version:string;verified:boolean;observed_checkpoints:number;
 earliest_observed_sequence:number;latest_sequence:number;latest_checkpoint_sha256:string;
 memory_records:number;observed_memory_digest_changed:boolean;observed_state_family_changed:boolean;
 model_weight_growth_proven:boolean;improved_intelligence_proven:boolean;side_effects:string;
 history_window_limited:boolean;
};
export default function EngineGrowth(){
 const [report,setReport]=useState<Report|null>(null);
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 async function inspect(){
  if(busy)return;
  setBusy(true);setError('');setReport(null);
  try{
   const res=await fetch('/api/bridge/engine-growth',{cache:'no-store',credentials:'same-origin'});
   const data=await res.json() as Report&{error?:string};
   if(!res.ok)throw new Error(data.error||'Verified engine report unavailable');
   if(data.schema!=='cosmos-engine-growth-report-v1'||data.verified!==true||
     data.model_weight_growth_proven!==false||data.improved_intelligence_proven!==false||
     data.side_effects!=='NONE_READ_ONLY'||!Number.isSafeInteger(data.latest_sequence))
     throw new Error('Invalid or unverified engine report');
   setReport(data);
  }catch(e){setError(e instanceof Error?e.message:'Engine report unavailable');}
  finally{setBusy(false);}
 }
 return <article className="data-card wide" aria-label="Verified COSMOS engine growth">
  <span>ENGINE CONTINUITY · READ ONLY</span>
  <p>Evidence from verified durable checkpoints. Changing state and accumulating memories do not prove a smarter model or automatic code upgrades.</p>
  <button type="button" className="outline-action" disabled={busy} onClick={()=>void inspect()}>
   <Activity size={15}/>{busy?'Inspecting…':'Inspect verified engine changes'}</button>
  {error?<p role="alert" className="inline-error">{error}</p>:null}
  {report?<div role="status">
   <div className="insight-line"><span>Engine version</span><b>{report.engine_version}</b></div>
   <div className="insight-line"><span>Observed checkpoints</span><b>{report.observed_checkpoints} · sequence {report.earliest_observed_sequence}–{report.latest_sequence}</b></div>
   <div className="insight-line"><span>Retained memory records</span><b>{report.memory_records}</b></div>
   <div className="insight-line"><span>State changed in observed window</span><b>{report.observed_state_family_changed?'YES · measured':'NO'}</b></div>
   <div className="insight-line"><span>Memory digest changed</span><b>{report.observed_memory_digest_changed?'YES':'NO'}</b></div>
   <p>Checkpoint: <code>{report.latest_checkpoint_sha256.slice(0,20)}…</code>{report.history_window_limited?' · most recent 50 only':''}</p>
   <p>No model-weight training, intelligence improvement, or self-updating source code is established by these measurements.</p>
  </div>:null}
 </article>;
}
