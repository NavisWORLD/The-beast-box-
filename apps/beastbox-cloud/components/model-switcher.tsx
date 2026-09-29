'use client';
import {useCallback,useEffect,useState} from 'react';
import {Check,RefreshCcw,ShieldCheck} from 'lucide-react';

type Choice='local'|'rawrphos_native'|'rawrphos_native_18k_experimental'|'rawrphos_hf'|'qc67_phos'|'qc67_samgo'|'huggingface'|'ollama_cloud';
type Option={
 choice:Choice;model:string;kind:'local'|'remote';configured:boolean;
 requires_spend_approval:boolean;readiness:string;
 label?:string;loaded_step?:number|null;experimental?:boolean;promotion_checks_pass?:boolean;
};
type Catalog={
 active:{model:string;kind:string;remote:boolean;loaded_step?:number|null;experimental?:boolean};
 remote_grant_active:boolean;reapproval_required:boolean;choices:Option[];
 inference_attested:boolean;no_automatic_fallback:boolean;
};
type HFEntry={id:string;task:string;library:string;router_candidate:boolean;selection_state:string};
type HFInventory={models:HFEntry[];owner:string;status:'PUBLIC_OWNER_CATALOG_ONLY';account_access_verified:false;inference_attested:false;model_invoked:false};
type Inventory={
 models:string[];status:'PUBLIC_MODEL_LIST_ONLY';account_access_verified:false;
 inference_attested:false;model_invoked:false;
};

async function bridge(method:'GET'|'POST',endpoint:'models'|'model-inventory'|'hf-model-inventory',payload?:Record<string,unknown>):Promise<Record<string,unknown>>{
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
 const [hfModels,setHFModels]=useState<HFEntry[]>([]);
 const [hfStatus,setHFStatus]=useState<'loading'|'ready'|'unavailable'>('loading');
 const [selectedHF,setSelectedHF]=useState('');
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
 const refreshHF=useCallback(async()=>{
  if(!backendReachable){setHFModels([]);setHFStatus('unavailable');return;}
  setHFStatus('loading');
  try{
   const received=await bridge('GET','hf-model-inventory') as unknown as HFInventory;
   if(received.status!=='PUBLIC_OWNER_CATALOG_ONLY'||received.owner!=='phera-ra'||
      received.account_access_verified!==false||received.model_invoked!==false||
      !Array.isArray(received.models)||received.models.length>100||
      received.models.some(x=>typeof x.id!=='string'||
       !/^phera-ra\/[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(x.id)||
       typeof x.router_candidate!=='boolean'))throw new Error('Unverified HF inventory');
   setHFModels(received.models);
   setSelectedHF(old=>received.models.some(x=>x.id===old&&x.router_candidate)?old:
     received.models.find(x=>x.router_candidate)?.id||'');
   setHFStatus('ready');
  }catch{setHFModels([]);setHFStatus('unavailable');}
 },[backendReachable]);
 useEffect(()=>{void refresh().catch(()=>setError('Unable to inspect the model catalog.'));},[refresh]);
 useEffect(()=>{void refreshHF();},[refreshHF]);

 async function choose(choice:Choice,model?:string){
  if(busy||!backendReachable)return;
  const remote=choice==='huggingface'||choice==='ollama_cloud'||choice==='rawrphos_hf';
  if(remote&&!spendApproved){setError('Approve possible usage charges before selecting a remote model.');return;}
  if(model&&choice==='ollama_cloud'&&(!ollamaModels.includes(model)||inventoryStatus!=='ready')){
   setError('Refresh the public Ollama inventory before switching models.');return;
  }
  if(model&&choice==='huggingface'&&(hfStatus!=='ready'||
     !hfModels.some(x=>x.id===model&&x.router_candidate))){
   setError('Only listed, compatible candidate owner models can be selected.');return;
  }
  setBusy(true);setError('');setNotice('');
  try {
   const result=await bridge('POST','models',{
    choice,...(model?{model}:{}),...(remote?{spend_approved:true}:{})
   });
   await Promise.all([refresh(),refreshHF()]);
   onSwitched();
   setSpendApproved(false);
   setNotice(
    result.brain_changed===false?'This brain was already selected; no new inference was performed.':
    choice==='local'?'Selected the verified local CPU model. Existing substrate retained; no paid inference was made.':
    choice==='rawrphos_native'?'Selected the stable native 14K CPU checkpoint. COSMOS history retained; no paid inference was made.':
    choice==='rawrphos_native_18k_experimental'?'Selected the experimental 18K CPU checkpoint. Its quality gate FAILED; instruction and multi-turn replies may be wrong. Stable 14K is still available, and COSMOS memory was preserved.':
     choice==='rawrphos_hf'?'Selected your private Hugging Face ZeroGPU RAWRPHØS 12K. Checkpoint identity was verified; try a real chat. Free quota and queue limits apply.':
    choice==='qc67_phos'?'Selected original pinned PHOS CPU checkpoint. Experimental character model: short research replies, not proven conversational performance. COSMOS memory preserved.':
    choice==='qc67_samgo'?'Selected original pinned SAMGO 54D CPU checkpoint. Experimental limited-context research replies; COSMOS memory preserved.':
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
     {catalog.active.model==='rawrphos-native'&&catalog.active.loaded_step?' Loaded native step: '+catalog.active.loaded_step+'.':null}
     {catalog.reapproval_required?' Remote model needs owner approval after restart.':null}
    </p>
    {catalog.choices.map(option=>{
     const active=catalog.active.model===option.model&&
      (option.kind==='local'?!catalog.active.remote:catalog.active.remote)&&
      (option.choice==='rawrphos_native'?catalog.active.experimental!==true:
       option.choice==='rawrphos_native_18k_experimental'?catalog.active.experimental===true:true);
     const remote=option.requires_spend_approval;
     const experimental=option.choice==='rawrphos_native_18k_experimental';
     const native=option.choice==='rawrphos_native'||experimental;
     const hosted=option.choice==='rawrphos_hf';
     const original=option.choice==='qc67_phos'||option.choice==='qc67_samgo';
     const ready=option.readiness==='INSTALLED_AND_READY';
     return <div className="record" key={option.choice}>
      <strong>{option.label||option.model}</strong> · {native||original?'Native PyTorch CPU':hosted?'Private Hugging Face ZeroGPU':option.choice==='local'?'Installed CPU model':option.choice==='huggingface'?'Hugging Face':'Ollama Cloud'}
      <p>{original?'Status: '+option.readiness.replaceAll('_',' ')+'. '+(ready?'Exact published weights and original architecture loaded; bounded research prompt only, chat quality is not attested.':'Not installed or not checkpoint-verified on this host; unavailable until exact pinned model is deployed.') :native?'Status: '+option.readiness.replaceAll('_',' ')+(option.loaded_step?' · Loaded step '+option.loaded_step:'')+'. '+(ready?(experimental?'Pinned unpromoted 18K identity verified. The original quality gate FAILED; responses may be inaccurate. Owner-only test use; real chat still needs completion.':'Pinned 14K identity and loopback verified; real chat still needs completion.'):'Not selectable until Railway installs and verifies the model. No automatic fallback.'):hosted?'Private HF Space. '+(option.configured?'Ready for owner-authenticated checkpoint check when selected. Free daily GPU quota and queuing apply.':'Save a private Hugging Face token under Connections first. No browser token exposure.'):remote?'Encrypted credential configured. Model inference, account entitlement, available balance and latency are not attested.':'Local weights and loopback were verified on the host. Actual response still requires a completed chat.'}</p>
      <button type="button" className="outline-action"
       disabled={busy||(remote&&!spendApproved)||(!remote&&active)||((native||original)&&!ready)||(hosted&&!option.configured)}
       onClick={()=>void choose(option.choice)}>
       {active?<Check size={15}/>:<ShieldCheck size={15}/>}
       {active&&!(remote&&catalog.reapproval_required)?'Currently selected':
        remote?(active?'Reapprove saved remote model':hosted?'Select RAWRPHØS via Hugging Face':'Select saved remote model'):original?('Select original '+(option.choice==='qc67_phos'?'PHOS':'SAMGO')):native?(experimental?'Select experimental 18K':'Select stable 14K'):'Switch to local model'}
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
    <div className="record" aria-label="My Hugging Face models">
     <h3>My Hugging Face models · phera-ra</h3>
     <p>Read-only public inventory. Research checkpoints are listed, but custom PHOS/SAMGO architectures need their own tested serving adapters. A Transformers tag is only a candidate, not proof the Router will serve it.</p>
     {hfStatus==='loading'?<p role="status">Reading published owner models…</p>:
      hfStatus==='unavailable'?<p role="status">Hugging Face public owner catalog unavailable. Saved model settings were not changed.</p>:
      hfModels.length===0?<p>No public owner models returned.</p>:
      <>
       {hfModels.map(item=><p key={item.id}>
        <strong>{item.id}</strong> · {item.task} · {item.library}
        {' · '}{item.router_candidate?'Hosted text-generation candidate (not attested)':'Research model; requires verified serving adapter'}
       </p>)}
       {hfModels.some(x=>x.router_candidate)&&<>
        <label htmlFor="my-hf-model">Select a hosted candidate</label>
        <select id="my-hf-model" value={selectedHF} disabled={busy}
         onChange={e=>setSelectedHF(e.target.value)}>
         {hfModels.filter(x=>x.router_candidate).map(x=><option key={x.id} value={x.id}>{x.id}</option>)}
        </select>
        {catalog.choices.some(x=>x.choice==='huggingface'&&x.configured)?
        <button type="button" className="outline-action"
         disabled={busy||!spendApproved||!selectedHF}
         onClick={()=>void choose('huggingface',selectedHF)}>
         <ShieldCheck size={15}/> Switch to {selectedHF}
        </button>:
        <p>Add your encrypted Hugging Face credential in Connections before selecting a model.</p>}
       </>}
      </>}
    </div>
    <div className="record" aria-label="COSMOS custom engines">
     <h3>Existing COSMOS custom models &amp; engines</h3>
     <p><strong>PHOS / dyn12</strong> and <strong>SAMGO / 54D</strong> — original pinned native PyTorch models when their verified loopback sidecar is installed; otherwise unavailable. Published provenance:
      {' '}<a href="https://huggingface.co/phera-ra/QC67_cosmo" target="_blank" rel="noopener noreferrer">QC67 COSMOS</a>.
      These original research models use small bounded prompt windows; a successful CPU forward is not proof of useful conversational responses.</p>
     <p><strong>COSMIC.CYPHER</strong> — installed coding-agent engine, not a separate language-model checkpoint. Its CLI can register these two local model endpoints (or RAWRPHØS/SmolLM2) with explicit workspace permissions. Experimental PHOS/SAMGO may not reliably produce tool-action JSON.</p>
     <p>RAWRPHØS stable/experimental native options and the private hosted checkpoint remain separate above. No research weights are substituted or discarded.</p>
    </div>
    {catalog.choices.some(x=>x.requires_spend_approval)?<label className="cloud-spend">
      <input type="checkbox" checked={spendApproved} disabled={busy}
       onChange={e=>setSpendApproved(e.target.checked)}/>
      I explicitly approve this provider&apos;s possible usage charges for remote model requests. Railway Trial credit does not pay these charges.
    </label>:null}
    <button type="button" className="outline-action" disabled={busy}
     onClick={()=>void Promise.all([refresh(),refreshHF()]).catch(()=>setError('Could not refresh model inventory.'))}>
     <RefreshCcw size={15}/> Refresh model list
    </button>
   </>}
  {!catalog?.choices?.some(option=>option.choice==='rawrphos_native')?
   <div className="record" role="status" data-testid="rawrphos-native-unavailable">
    <strong>RAWRPHØS Native — Local CPU (14K)</strong> · Native PyTorch CPU
    <p>{!backendReachable?'The durable backend is offline. RAWRPHØS cannot be verified.':
      !catalog?'Reading the real model catalog; native checkpoint not yet attested.':
      'The connected backend does not advertise RAWRPHØS. Deploy the reconciled Railway owner bridge and pinned 14K checkpoint first.'}</p>
    <button type="button" className="outline-action" disabled aria-disabled="true">RAWRPHØS unavailable</button>
   </div>:null}
  {notice?<p role="status" className="cloud-connect-success">{notice}</p>:null}
  {error?<p role="alert" className="inline-error">{error}</p>:null}
  <p>Changing brains revokes previous model authority. No automatic cloud fallback, credential disclosure, inference charge, or memory reset is authorized by this control. Models can give incorrect descriptions of COSMOS memory; use checkpoint and source evidence to verify software continuity.</p>
 </article>;
}