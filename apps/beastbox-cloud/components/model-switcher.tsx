'use client';
import {useCallback,useEffect,useState} from 'react';
import {Check,RefreshCcw,ShieldCheck} from 'lucide-react';

type Choice='local'|'rawrphos_native'|'huggingface'|'ollama_cloud';
type Option={
 choice:Choice;model:string;kind:'local'|'remote';configured:boolean;
 requires_spend_approval:boolean;readiness:string;
 label?:string;loaded_step?:number|null;
};
type Catalog={
 active:{model:string;kind:string;remote:boolean;loaded_step?:number|null};
 remote_grant_active:boolean;reapproval_required:boolean;choices:Option[];
 inference_attested:boolean;no_automatic_fallback:boolean;
};
type Inventory={
 models:string[];status:'PUBLIC_MODEL_LIST_ONLY';account_access_verified:false;
 inference_attested:false;model_invoked:false;
};

async function bridge(method:'GET'|'POST',endpoint:'models'|'model-inventory',payload?:Record<string,unknown>):Promise<Record<string,unknown>>{
 const response=await fetch('/api/bridge/'+endpoint,{method,cache:'no-store',credentials:'same-origin',
  headers:method==='POST'?{'Content-Type':'application/json'}:undefined,
  body:method==='POST'?JSON.stringify(payload):undefined});
 const data:unknown=await response.json().catch(()=>({error:'Invalid backend response'}));
 if(!response.ok)throw new Error(data&&typeof data==='object'&&'error' in data?String(data.error):'Model selection failed');
 return data as Record<string,unknown>;
}

export default function ModelSwitcher({backendReachable,onSwitched}:{
 backendReachable:boolean;onSwitched:()=>void;
}){
 const [catalog,setCatalog]=useState<Catalog|null>(null);
 const [ollamaModels,setOllamaModels]=useState<string[]>([]);
 const [selectedModel,setSelectedModel]=useState('');
 const [inventoryStatus,setInventoryStatus]=useState<'loading'|'ready'|'unavailable'|'not-configured'>('loading');
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [spendApproved,setSpendApproved]=useState(false);
 const refresh=useCallback(async()=>{
  if(!backendReachable){
   setCatalog(null);setOllamaModels([]);setInventoryStatus('not-configured');return;
  }
  const result=await bridge('GET','models');
  const next=result as unknown as Catalog;
  setCatalog(next);
  const ollama=next.choices.find(option=>option.choice==='ollama_cloud'&&option.configured);
  if(!ollama){setOllamaModels([]);setInventoryStatus('not-configured');return;}
  setInventoryStatus('loading');
  try {
   const response=await bridge('GET','model-inventory') as unknown as Inventory;
   if(response.status!=='PUBLIC_MODEL_LIST_ONLY'||response.account_access_verified!==false||
      response.model_invoked!==false||!Array.isArray(response.models)||
      response.models.some(id=>typeof id!=='string'||!/^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,179}$/.test(id))) {
    throw new Error('Unverified model inventory');
   }
   setOllamaModels(response.models);
   setSelectedModel(previous=>response.models.includes(previous)?previous:
    response.models.includes(next.active.model)?next.active.model:
    response.models.includes(ollama.model)?ollama.model:response.models[0]||'');
   setInventoryStatus('ready');
  } catch {
   setOllamaModels([]);setInventoryStatus('unavailable');
  }
 },[backendReachable]);
 useEffect(()=>{void refresh().catch(()=>setError('Unable to inspect the model catalog.'));},[refresh]);

 async function choose(choice:Choice,model?:string){
  if(busy||!backendReachable)return;
  const remote=choice==='huggingface'||choice==='ollama_cloud';
  if(remote&&!spendApproved){setError('Approve possible usage charges before selecting a remote model.');return;}
  if(model&&(!ollamaModels.includes(model)||inventoryStatus!=='ready')){
   setError('Refresh the public Ollama inventory before switching models.');return;
  }
  setBusy(true);setError('');setNotice('');
  try {
   const result=await bridge('POST','models',{
    choice,...(model?{model}:{}),...(remote?{spend_approved:true}:{})
   });
   await refresh();
   onSwitched();
   setSpendApproved(false);
   setNotice(
    result.brain_changed===false?'This brain was already selected; no new inference was performed.':
    choice==='local'?'Selected the verified local CPU model. Existing substrate retained; no paid inference was made.':
    choice==='rawrphos_native'?'Selected the verified native 12K CPU checkpoint. COSMOS history retained; no paid inference was made.':
    'Selected '+String(result.model||'the cloud model')+'. The encrypted key was retained. Actual inference and account entitlement still require a completed chat.'
   );
  }catch(e){setError((e as Error).message);}
  finally{setBusy(false);}
 }
 return <article className="data-card wide" aria-label="Switch model">
  <h2>Choose your brain</h2>
  <p>Swap the model, not the durable COSMOS substrate. Cloud models reuse the existing encrypted provider credential; the public catalog does not prove account entitlement, remaining usage, or a successful response.</p>
  {!backendReachable?<p role="status">Connect the durable backend before selecting a model.</p>:!catalog?<p role="status">Reading available models…</p>:
   <>
    <p role="status">Active profile: <strong>{catalog.active.model}</strong> ({catalog.active.remote?'remote':'local'}).
     {catalog.reapproval_required?' Remote model needs owner approval after restart.':null}
    </p>
    {catalog.choices.map(option=>{
     const active=catalog.active.model===option.model&&
      (option.choice==='local'?!catalog.active.remote:catalog.active.remote);
     const remote=option.requires_spend_approval;
     return <div className="record" key={option.choice}>
      <strong>{option.model}</strong> · {option.choice==='local'?'Installed CPU model':option.choice==='huggingface'?'Hugging Face':'Ollama Cloud'}
      <p>{remote?'Encrypted credential configured. Model inference, account entitlement, available balance and latency are not attested.':'Local weights and loopback were verified on the host. Actual response still requires a completed chat.'}</p>
      <button type="button" className="outline-action"
       disabled={busy||(remote&&!spendApproved)||(!remote&&active)}
       onClick={()=>void choose(option.choice)}>
       {active?<Check size={15}/>:<ShieldCheck size={15}/>}
       {active&&!(remote&&catalog.reapproval_required)?'Currently selected':
        remote?(active?'Reapprove saved remote model':'Select saved remote model'):'Switch to local model'}
      </button>
      {option.choice==='ollama_cloud'&&<div className="record" aria-label="Ollama cloud model choices">
       <h3>Ollama cloud models</h3>
       <p>Read-only direct API inventory, not an account-specific entitlement test. Select a model without re-entering your API key. Your same durable conversation remains outside its weights.</p>
       {inventoryStatus==='loading'?<p role="status">Reading Ollama&apos;s public model inventory…</p>:
        inventoryStatus==='unavailable'?<p role="status">Public inventory unavailable. Saved model selection remains available; no cloud call was made.</p>:
        inventoryStatus==='ready'&&ollamaModels.length>0?
        <>
         <label htmlFor="ollama-model-choice">Available direct API model IDs</label>
         <select id="ollama-model-choice" value={selectedModel} disabled={busy}
          onChange={e=>setSelectedModel(e.target.value)}>
          {ollamaModels.map(id=><option value={id} key={id}>{id}</option>)}
         </select>
         <button type="button" className="outline-action"
          disabled={busy||!spendApproved||!selectedModel||
            (catalog.active.remote&&catalog.active.model===selectedModel&&!catalog.reapproval_required)}
          onClick={()=>void choose('ollama_cloud',selectedModel)}>
          <ShieldCheck size={15}/>
          {catalog.active.remote&&catalog.active.model===selectedModel?'Reapprove selected model':'Switch to '+selectedModel}
         </button>
         <p>Listing only. The provider may reject this model for your account. No inference or automatic fallback is performed by switching.</p>
        </>:null}
      </div>}
     </div>;
    })}
    {catalog.choices.some(x=>x.requires_spend_approval)?<label className="cloud-spend">
      <input type="checkbox" checked={spendApproved} disabled={busy}
       onChange={e=>setSpendApproved(e.target.checked)}/>
      I explicitly approve this provider&apos;s possible usage charges for remote model requests. Railway Trial credit does not pay these charges.
    </label>:null}
    <button type="button" className="outline-action" disabled={busy}
     onClick={()=>void refresh().catch(()=>setError('Could not refresh model inventory.'))}>
     <RefreshCcw size={15}/> Refresh model list
    </button>
   </>}
  {notice?<p role="status" className="cloud-connect-success">{notice}</p>:null}
  {error?<p role="alert" className="inline-error">{error}</p>:null}
  <p>Changing brains revokes previous model authority. No automatic cloud fallback, credential disclosure, inference charge, or memory reset is authorized by this control. Models can give incorrect descriptions of COSMOS memory; use checkpoint and source evidence to verify software continuity.</p>
 </article>;
}