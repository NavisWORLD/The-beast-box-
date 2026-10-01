'use client';
import {useCallback,useEffect,useState} from 'react';
type Task={id:string;kind:string;status:string;attempts:number;max_attempts:number;result?:unknown;last_error?:string|null};
type State={schema:string;stopped:boolean;counts:Record<string,number>;audit:{valid:boolean;events:number;head:string};execution_semantics:string;tasks:Task[]};
export default function ActivationDeck(){
  const [state,setState]=useState<State|null>(null);
  const [loading,setLoading]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const [reason,setReason]=useState('Explicit owner action from COSMOS cloud workspace');
  const refresh=useCallback(async()=>{
    try{
      const r=await fetch('/api/bridge/activation',{cache:'no-store'});
      const data=await r.json() as State&{error?:string};
      if(!r.ok)throw new Error(data.error||'Activation host unavailable');
      if(data.schema!=='cosmos-activation-status-v1'||data.audit?.valid!==true||!Array.isArray(data.tasks))
        throw new Error('Activation status is not an authenticated verified host receipt');
      setState(data);
    }catch(e){setError(e instanceof Error?e.message:'Activation host unavailable');}
  },[]);
  useEffect(()=>{void refresh();const interval=setInterval(()=>void refresh(),15000);return()=>clearInterval(interval);},[refresh]);
  async function act(body:Record<string,unknown>,urgent=false){
    if(!urgent&&loading)return;
    if(!urgent)setLoading(true);
    setError('');setNotice('');
    try{
      const r=await fetch('/api/bridge/'+(body.action==='master_stop'?'authority':'activation'),{
        method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),cache:'no-store'});
      const data=await r.json() as Record<string,unknown>;
      if(!r.ok)throw new Error(typeof data.error==='string'?data.error:'Host rejected operation');
      setNotice(body.action==='master_stop'?'Host revoked current authority grants and stopped queued work. In-flight provider calls are not preemptible.':
        body.action==='stop'?'Queued execution stopped; a running provider call may still finish.':
        'Operation acknowledged by the host. Inspect the durable receipts below.');
      await refresh();
    }catch(e){setError(e instanceof Error?e.message:'Operation was not confirmed');}
    finally{if(!urgent)setLoading(false);}
  }
  const why=reason.trim().slice(0,180);
  return <article className="data-card wide" aria-label="COSMOS bounded activation controls">
    <span>OWNER ACTIVATION · AUTHENTICATED HOST</span>
    <h2>Observe → act → verify → remember</h2>
    <p>Controls the existing persistent queue, not a simulated agent. Jobs are host-bounded and at-least-once after interrupted recovery. No browser-issued sensor events, tool grants or automatic paid inference.</p>
    <div className="insight-line"><span>Queue state</span><b>{state?(state.stopped?'STOPPED':'READY FOR OWNER REQUEST'):'NOT VERIFIED'}</b></div>
    <div className="insight-line"><span>Durable audit</span><b>{state?.audit.valid?'VALID · '+state.audit.events+' events':'UNAVAILABLE'}</b></div>
    {state&&<div className="insight-line"><span>Actual tasks</span><b>{JSON.stringify(state.counts)}</b></div>}
    <label htmlFor="activation-reason">Reason for stop, resume or cancellation</label>
    <input id="activation-reason" value={reason} onChange={e=>setReason(e.target.value.slice(0,180))} maxLength={180}
      style={{display:'block',width:'100%',margin:'10px 0 16px'}} />
    <div style={{display:'flex',gap:10,flexWrap:'wrap',margin:'12px 0'}}>
      <button type="button" className="outline-action" disabled={loading} onClick={()=>void refresh()}>Refresh verified state</button>
      <button type="button" className="outline-action" disabled={loading||!state} onClick={()=>void act({action:'enqueue_maintenance'})}>Queue bounded maintenance</button>
      <button type="button" className="outline-action" disabled={loading||!state||state.stopped} onClick={()=>void act({action:'run',max_tasks:1,wall_seconds:8})}>Run 1 approved task</button>
      <button type="button" className="outline-action" disabled={loading||!state||!state.stopped||!why}
        onClick={()=>void act({action:'resume',reason:why})}>Explicitly resume queue</button>
      <button type="button" className="outline-action" disabled={!why} onClick={()=>void act({action:'stop',reason:why},true)}>STOP QUEUED WORK</button>
      <button type="button" className="outline-action" onClick={()=>void act({action:'master_stop'},true)}>MASTER PRIVACY STOP</button>
    </div>
    {error&&<p role="alert" className="inline-error">{error}</p>}
    {notice&&<p role="status">{notice}</p>}
    {state?.tasks.length===0&&<p>No tasks have been recorded in the current host queue.</p>}
    {state?.tasks.map(task=><div key={task.id} className="record" style={{overflowWrap:'anywhere'}}>
      <strong>{task.kind} · {task.status}</strong>
      <small> {task.id} · attempts {task.attempts}/{task.max_attempts}</small>
      {task.result&&<pre style={{overflowWrap:'anywhere',whiteSpace:'pre-wrap'}}>{JSON.stringify(task.result,null,2)}</pre>}
      {task.last_error&&<p role="status">Recorded failure: {task.last_error}</p>}
      {task.status==='queued'&&<button className="outline-action" disabled={loading||!why}
         onClick={()=>void act({action:'cancel',task_id:task.id,reason:why})}>Cancel pending task</button>}
    </div>)}
    <p>Stop prevents future queue claims, but cannot undo an already started external call. Recovery may require owner reconciliation.</p>
  </article>;
}
