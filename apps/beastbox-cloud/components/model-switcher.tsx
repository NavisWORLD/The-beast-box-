'use client';
import {useCallback,useEffect,useState} from 'react';
import {Check,RefreshCcw,ShieldCheck} from 'lucide-react';

type Choice='local'|'rawrphos_native'|'huggingface'|'ollama_cloud';
type Option={
 choice:Choice;
 model:string;
 kind:'local'|'remote';
 configured:boolean;
 requires_spend_approval:boolean;
 readiness:string;
};
type Catalog={
 active:{model:string;kind:string;remote:boolean};
 remote_grant_active:boolean;
 reapproval_required:boolean;
 choices:Option[];
 inference_attested:boolean;
 no_automatic_fallback:boolean;
};

async function bridge(method:'GET'|'POST',payload?:Record<string,unknown>):Promise<Record<string,unknown>>{
 const r=await fetch('/api/bridge/models',{method,cache:'no-store',credentials:'same-origin',
  headers:method==='POST'?{'Content-Type':'application/json'}:undefined,
  body:method==='POST'?JSON.stringify(payload):undefined});
 const x:unknown=await r.json().catch(()=>({error:'Invalid backend response'}));
 if(!r.ok)throw new Error(x&&typeof x==='object'&&'error' in x?String(x.error):'Model selection failed');
 return x as Record<string,unknown>;
}

export default function ModelSwitcher({backendReachable,onSwitched}:{
 backendReachable:boolean;onSwitched:()=>void;
}){
 const [catalog,setCatalog]=useState<Catalog|null>(null);
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [spendApproved,setSpendApproved]=useState(false);
 const refresh=useCallback(async()=>{
  if(!backendReachable){setCatalog(null);return;}
  const result=await bridge('GET');
  setCatalog(result as unknown as Catalog);
 },[backendReachable]);
 useEffect(()=>{void refresh().catch(()=>setError('Unable to inspect the real model catalog.'));},[refresh]);

 async function choose(choice:Choice){
  if(busy||!backendReachable)return;
  const remote=choice!=='local';
  if(remote&&!spendApproved){setError('Approve possible usage charges for the selected remote provider first.');return;}
  setBusy(true);setError('');setNotice('');
  try{
   const result=await bridge('POST',{choice,...(remote?{spend_approved:true}:{})});
   await refresh();
   onSwitched();
   setSpendApproved(false);
   setNotice(
    result.brain_changed===false?'This brain was already selected; no new inference was performed.':
    choice==='local'?'Selected the verified local tiny model. Existing substrate retained; no paid inference was made.':
    'Selected a configured cloud profile. A live answer is still unverified; any future requests may incur provider charges.'
   );
  }catch(e){setError((e as Error).message);}
  finally{setBusy(false);}
 }
 return <article className="data-card wide" aria-label="Switch model">
  <h2>Choose your brain</h2>
  <p>Swap the model, not the durable COSMOS memory. Only your installed local model and encrypted, configured cloud connections appear here. A model name alone does not prove a successful inference call.</p>
  {!backendReachable?<p role="status">Connect the durable backend before selecting a model.</p>:!catalog?<p role="status">Reading available models…</p>:
   <>
    <p role="status">Active profile: <strong>{catalog.active.model}</strong> ({catalog.active.remote?'remote':'local'}).
     {catalog.reapproval_required?' Remote model needs fresh owner approval after restart.':null}
    </p>
    {catalog.active.remote&&catalog.active.model==='gpt-oss:120b'&&
     <p role="status">This is an Ollama local model ID, not the advertised cloud ID. In Settings → Ollama Cloud, correct the saved model name to <code>gpt-oss:120b-cloud</code> without re-entering your encrypted key. Switch to local before editing the active model.</p>}
    {catalog.choices.map(option=>{
     const active=catalog.active.model===option.model&&
      (option.choice==='local'?!catalog.active.remote:catalog.active.remote);
     const remote=option.requires_spend_approval;
     return <div className="record" key={option.choice}>
      <strong>{option.model}</strong> · {option.choice==='local'?'Installed CPU model':option.choice==='huggingface'?'Hugging Face':'Ollama Cloud'}
      <p>{remote?'Encrypted credential configured. Model inference, available balance and latency have not been verified.':'Local weights and loopback were verified on the host. Actual response still needs a completed chat.'}</p>
      <button type="button" className="outline-action" disabled={busy||(remote&&!spendApproved)||(!remote&&active)}
       onClick={()=>void choose(option.choice)}>
       {active?<Check size={15}/>:<ShieldCheck size={15}/>}
       {active&&!(remote&&catalog.reapproval_required)?'Currently selected':
        remote?(active?'Reapprove remote model':'Select remote model'):'Switch to local model'}
      </button>
     </div>;
    })}
    {catalog.choices.some(x=>x.requires_spend_approval)?<label className="cloud-spend">
      <input type="checkbox" checked={spendApproved} disabled={busy}
       onChange={e=>setSpendApproved(e.target.checked)}/>
      I explicitly approve this provider&apos;s possible usage charges for remote model requests. Railway Trial credit does not pay these charges.
    </label>:null}
    <button type="button" className="outline-action" disabled={busy} onClick={()=>void refresh().catch(()=>setError('Could not refresh model list.'))}><RefreshCcw size={15}/> Refresh model list</button>
   </>}
  {notice?<p role="status" className="cloud-connect-success">{notice}</p>:null}
  {error?<p role="alert" className="inline-error">{error}</p>:null}
  <p>Changing brains revokes prior model authority. No automatic cloud fallback, secret disclosure, inference charge, or memory reset is authorized by this control. Local and cloud model capabilities can differ.</p>
 </article>;
}
