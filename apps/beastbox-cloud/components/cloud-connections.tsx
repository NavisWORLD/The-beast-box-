'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import {Check,KeyRound,LockKeyhole,PlugZap,RefreshCcw,Shield,Trash2} from 'lucide-react';

type Provider='huggingface'|'ollama_cloud'|'azure_blob'|'ibm_watsonx'|'ibm_quantum';
type Connection={provider:Provider;configured:boolean;config:Record<string,string>;credential:string;mode?:string};
type Field={key:string;label:string;placeholder:string};
const PROVIDERS:{id:Provider;name:string;purpose:string;fields:Field[];secretLabel:string;help:string;activatable:boolean}[]=[
 {id:'huggingface',name:'Hugging Face',purpose:'Hosted conversational model',fields:[{key:'model',label:'Model repository',placeholder:'owner/model-name'}],secretLabel:'HF fine-grained token',help:'Choose a supported chat model and enable Inference Providers permission on your token.',activatable:true},
 {id:'ollama_cloud',name:'Ollama Cloud',purpose:'Direct Ollama API (not your localhost)',fields:[{key:'model',label:'Direct API model ID',placeholder:'gpt-oss:120b'}],secretLabel:'Ollama cloud API key',help:'For https://ollama.com/v1 use the direct API ID gpt-oss:120b. The gpt-oss:120b-cloud suffix belongs to the Ollama app/CLI. The public model list does not verify your API key or inference entitlement.',activatable:true},
 {id:'azure_blob',name:'Azure Blob Storage',purpose:'Private photos, documents and exports',fields:[{key:'account',label:'Storage account',placeholder:'myaccount'},{key:'container',label:'Private container',placeholder:'beastbox-private'}],secretLabel:'Azure storage credential',help:'Choose a scoped container SAS (recommended) or explicitly choose an account key. Account keys have broad Azure permissions, but Beast Box only verifies container metadata until separate upload/retrieval operations are authorized.',activatable:false},
 {id:'ibm_watsonx',name:'IBM watsonx.ai',purpose:'IBM-hosted Granite / Llama models',fields:[{key:'region',label:'Region',placeholder:'us-south'},{key:'project_id',label:'Project ID',placeholder:'project-id'},{key:'model',label:'Foundation model ID',placeholder:'ibm/granite-...'}],secretLabel:'IBM Cloud API key',help:'Key, region and project may be saved. A separate authorized watsonx inference adapter is required before chatting.',activatable:false},
 {id:'ibm_quantum',name:'IBM Quantum',purpose:'Authorized research workloads',fields:[{key:'instance',label:'Instance',placeholder:'service instance or CRN'}],secretLabel:'IBM Quantum credential',help:'For research only. Saving a key never launches hardware jobs, training or inference.',activatable:false},
];

async function bridge(method:'GET'|'POST',payload?:Record<string,unknown>):Promise<Record<string,unknown>>{
 const reply=await fetch('/api/bridge/connections',{
  method,headers:method==='POST'?{'Content-Type':'application/json'}:undefined,
  cache:'no-store',credentials:'same-origin',body:method==='POST'?JSON.stringify(payload):undefined,
 });
 const result:unknown=await reply.json().catch(()=>({error:'Invalid response'}));
 if(!reply.ok)throw new Error(result&&typeof result==='object'&&'error' in result?String(result.error):'Connection operation failed');
 return result as Record<string,unknown>;
}

export default function CloudConnections({backendReachable,onActivated,onAzureText}:{backendReachable:boolean;onActivated:()=>void;onAzureText?:(entry:{name:string;sha256:string;text:string})=>void}){
 const [provider,setProvider]=useState<Provider>('huggingface');
 const [rows,setRows]=useState<Connection[]>([]),[vault,setVault]=useState('HOST_KEY_REQUIRED');
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [spendApproved,setSpendApproved]=useState(false);
 const [modelUpdate,setModelUpdate]=useState('');
 const [azureMode,setAzureMode]=useState<'container_sas'|'account_key'>('container_sas');
 const [azureName,setAzureName]=useState(''),[azureApproved,setAzureApproved]=useState(false),[azureShare,setAzureShare]=useState(false);
 const [azureRead,setAzureRead]=useState<{text:string;sha256:string;blob_name:string;bytes:number}|null>(null);
 const secretRef=useRef<HTMLInputElement>(null);
 const choice=PROVIDERS.find(item=>item.id===provider)!;
 const selected=rows.find(item=>item.provider===provider);
 const ready=backendReachable&&vault==='ENCRYPTED_HOST_ONLY';
 const currentModel=selected?.config?.model||'';
 useEffect(()=>setModelUpdate(currentModel),[provider,currentModel]);
 useEffect(()=>setAzureMode(selected?.config?.auth_mode==='account_key'?'account_key':'container_sas'),[provider,selected?.config?.auth_mode]);
 useEffect(()=>{setAzureRead(null);setAzureApproved(false);setAzureShare(false);},[provider,selected?.config?.account,selected?.config?.container,selected?.config?.auth_mode]);
 const refresh=useCallback(async()=>{
  if(!backendReachable){setRows([]);setVault('HOST_KEY_REQUIRED');return;}
  const result=await bridge('GET');
  setRows(Array.isArray(result.connections)?result.connections as Connection[]:[]);
  setVault(String(result.vault||'HOST_KEY_REQUIRED'));
 },[backendReachable]);
 useEffect(()=>{void refresh().catch(()=>{setVault('UNREACHABLE');setError('Could not read cloud connections from the persistent host.');});},[refresh]);
 useEffect(()=>{setError('');setNotice('');setSpendApproved(false);if(secretRef.current)secretRef.current.value='';},[provider]);
 async function perform(action:'remove'|'activate'|'test'){
  if(!ready||busy)return;
  if(action==='activate'&&!spendApproved){setError('Approve the provider’s possible usage charges before activation.');return;}
  setBusy(true);setError('');setNotice('');
  try{
   const result=await bridge('POST',{action,provider,...(action==='activate'?{spend_approved:true}:{})});
   if(action==='test')setNotice('Read-only provider check: '+String(result.status||'UNKNOWN')+'. '+String(result.detail||'No inference was performed.'));
   if(action==='remove')setNotice('Removed local encrypted credential. Revoke the key at its provider as well.');
   if(action==='activate'){setNotice('Provider profile selected. Real inference remains unverified until an actual model response.');onActivated();}
   if(action!=='test')await refresh();
  }catch(e){setError((e as Error).message);}
  finally{setBusy(false);}
 }
 async function updateSavedModel(){
  if(!ready||busy||!choice.activatable||!selected?.configured)return;
  if(modelUpdate===currentModel){setNotice('Saved model ID is unchanged.');return;}
  setBusy(true);setError('');setNotice('');
  try{
   const result=await bridge('POST',{action:'update_model',provider,model:modelUpdate.trim()});
   if(result.credential_preserved!==true)throw new Error('Host did not confirm encrypted credential preservation');
   setNotice('Saved the new model ID using the existing encrypted key. Select it separately in Brain Bay; no inference was performed.');
   await refresh();
  }catch(e){setError((e as Error).message);}
  finally{setBusy(false);}
 }
 async function readAzure(){
  if(!ready||busy||provider!=='azure_blob'||!selected?.configured||!azureApproved)return;
  setBusy(true);setError('');setNotice('');setAzureRead(null);setAzureShare(false);
  try{
   const reply=await fetch('/api/bridge/azure-read',{method:'POST',cache:'no-store',
    credentials:'same-origin',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({blob_name:azureName.trim(),read_confirmed:true})});
   const result:unknown=await reply.json().catch(()=>({error:'Invalid response'}));
   const data=result as Record<string,unknown>;
   if(!reply.ok)throw new Error(typeof data.error==='string'?data.error:'Azure read unavailable');
   if(data.retrieval_verified!==true||typeof data.text!=='string'||typeof data.sha256!=='string'||
      typeof data.blob_name!=='string'||typeof data.bytes!=='number'||data.model_invoked!==false||
      data.persisted!==false)throw new Error('Backend did not confirm a bounded read');
   setAzureRead({text:data.text,sha256:data.sha256,blob_name:data.blob_name,bytes:data.bytes});
   setNotice('One Azure document retrieved; not stored or sent to the model. Approve separately to stage it.');
  }catch(e){setError((e as Error).message);}
  finally{setBusy(false);setAzureApproved(false);}
 }
 async function save(e:React.FormEvent<HTMLFormElement>){
  e.preventDefault();if(!ready||busy)return;
  const form=e.currentTarget;
  const values=new FormData(form);const config:Record<string,string>={};
  for(const field of choice.fields)config[field.key]=String(values.get(field.key)||'').trim();
  if(provider==='azure_blob')config.auth_mode=azureMode;
  const secret=String(values.get('credential')||'');
  setBusy(true);setError('');setNotice('');
  try{
   await bridge('POST',{action:'save',provider,config,secret});
   if(secretRef.current)secretRef.current.value='';
   setNotice('Credential encrypted on your durable host. Activate a model separately; no inference was performed.');
   await refresh();
  }catch(e){setError((e as Error).message);}
  finally{setBusy(false);}
 }
 return <section className="cloud-connect data-card wide" aria-label="Cloud provider connections">
  <div className="cloud-connect-heading"><KeyRound size={20}/><div><h2>Connect your universe</h2><p>Your cloud accounts. Your keys. Your permissions.</p></div></div>
  <p>Provider credentials are sent only through your authenticated Vercel server to the durable Beast Box bridge, where an independent host key encrypts them. No keys are stored in browser storage, conversation memory, exported substrate, or Git.</p>
  {!backendReachable?<div className="cloud-connect-alert" role="status"><Shield size={17}/> Cloud connections are locked until your separately hosted durable backend is reachable. Do not enter credentials yet.</div>:vault!=='ENCRYPTED_HOST_ONLY'?<div className="cloud-connect-alert" role="status"><LockKeyhole size={17}/> The persistent host needs its own BEASTBOX_CONNECTION_VAULT_KEY before settings can safely save keys. This is separate from your login password and session secret.</div>:null}
  <div className="cloud-connect-tabs" role="group" aria-label="Choose cloud provider">
   {PROVIDERS.map(item=><button key={item.id} type="button" disabled={busy} aria-pressed={provider===item.id} className={provider===item.id?'selected':''} onClick={()=>setProvider(item.id)}>{item.name}</button>)}
  </div>
  <h3>{choice.name}</h3><p>{choice.purpose} · {choice.help}</p>
  <div className="cloud-connect-state"><span>Status</span><strong>{selected?.configured?'Encrypted on host':'Not configured'}</strong><span>Access</span><strong>{choice.activatable?'Owner-activated inference':'Configuration only'}</strong></div>
  <form onSubmit={e=>void save(e)} autoComplete="off">
   {provider==='azure_blob'&&<label>Azure authentication mode<select value={azureMode} disabled={!ready||busy} onChange={e=>setAzureMode(e.target.value==='account_key'?'account_key':'container_sas')}><option value="container_sas">Scoped container SAS (recommended)</option><option value="account_key">Storage account access key (broad permissions)</option></select></label>}
   {provider==='azure_blob'&&azureMode==='account_key'&&<p role="status">A storage-account key can authorize broader Azure operations. It stays encrypted on the persistent host. This form does not automatically enable uploads, database access, quantum jobs, or chat retrieval.</p>}
   {choice.fields.map(field=><label key={field.key}>{field.label}<input name={field.key} type="text" required disabled={!ready||busy} defaultValue={selected?.config?.[field.key]||''} key={provider+field.key+(selected?.config?.[field.key]||'')} placeholder={field.placeholder} maxLength={180} autoComplete="off" /></label>)}
   <label>{provider==='azure_blob'?(azureMode==='account_key'?'Storage account access key':'Scoped container SAS token'):choice.secretLabel}<input ref={secretRef} name="credential" type="password" minLength={12} maxLength={4096} autoComplete="new-password" placeholder="Paste privately; never shown again" required disabled={!ready||busy}/></label>
   <button type="submit" disabled={!ready||busy}><LockKeyhole size={16}/>{busy?'Working…':'Save encrypted credential'}</button>
  </form>
  {selected?.configured&&choice.activatable&&<div className="record">
    <h3>Update saved model ID without replacing your API key</h3>
    <p>Switch to the local model in Brain Bay first if this cloud model is active. This operation re-encrypts your existing host-only key but does not make an inference request.</p>
    <label>Saved model ID<input type="text" value={modelUpdate} disabled={!ready||busy}
      onChange={e=>setModelUpdate(e.target.value)} maxLength={180} autoComplete="off" /></label>
    {provider==='ollama_cloud'&&modelUpdate.endsWith('-cloud')&&<p role="status">This is the Ollama app/CLI tag. The direct API model ID uses the name without <code>-cloud</code>. The read-only list is public and cannot verify your account or API key. Switch to local before updating an active remote model.</p>}
    <button type="button" disabled={!ready||busy||!modelUpdate.trim()||modelUpdate===currentModel}
      onClick={()=>void updateSavedModel()}>Save model ID (keep encrypted key)</button>
   </div>}
  {selected?.configured&&<div className="cloud-connect-actions">
   <button type="button" disabled={!ready||busy} onClick={()=>void perform('test')}><RefreshCcw size={15}/> Test access (no paid inference)</button>
   {choice.activatable&&<><label className="cloud-spend"><input type="checkbox" checked={spendApproved} onChange={e=>setSpendApproved(e.target.checked)} disabled={!ready||busy}/> I understand my provider may charge for model requests.</label>
    <button type="button" disabled={!ready||busy||!spendApproved} onClick={()=>void perform('activate')}><PlugZap size={16}/> Activate in BRAIN</button></>}
   <button type="button" disabled={!ready||busy} onClick={()=>void perform('remove')}><Trash2 size={16}/> Forget saved credential</button>
  </div>}
  {provider==='azure_blob'&&selected?.configured&&<div className="record" aria-label="Explicit Azure retrieval">
    <h3>Retrieve one Azure text document</h3>
    <p>Enter its exact name in the existing container, including folders. Read-only, at most 12 KB; no automatic container scan, model call, upload or persistent memory change. Azure operations may incur storage transactions.</p>
    <label>Exact blob path<input type="text" maxLength={180} autoComplete="off" value={azureName} disabled={!ready||busy} onChange={e=>{setAzureName(e.target.value);setAzureRead(null);setAzureShare(false);}} placeholder="docs/notes.txt"/></label>
    <label className="cloud-spend"><input type="checkbox" checked={azureApproved} disabled={!ready||busy} onChange={e=>setAzureApproved(e.target.checked)}/> I authorize this one read from my configured Azure container.</label>
    <button type="button" disabled={!ready||busy||!azureApproved||!azureName.trim()} onClick={()=>void readAzure()}><RefreshCcw size={15}/> Read exact document (no model inference)</button>
    {azureRead&&<div role="status"><p>Retrieved {azureRead.bytes} bytes; SHA-256: <code>{azureRead.sha256}</code>. Source contents are untrusted data, not instructions. Nothing has been shared with the selected model.</p>
      <label className="cloud-spend"><input type="checkbox" checked={azureShare} onChange={e=>setAzureShare(e.target.checked)}/> I approve including this exact text with my next chat. If my selected model is remote, it will receive this text.</label>
      <button type="button" disabled={!azureShare||!onAzureText||busy} onClick={()=>{onAzureText?.({name:azureRead.blob_name,sha256:azureRead.sha256,text:azureRead.text});setAzureRead(null);setAzureShare(false);setNotice('Verified Azure text staged for your next chat; nothing sent yet.');}}>Stage for next chat (owner-approved)</button>
    </div>}
   </div>}
  {notice&&<p className="cloud-connect-success" role="status"><Check size={15}/>{notice}</p>}
  {error&&<p className="inline-error" role="alert">{error}</p>}
  <p className="cloud-connect-foot">Single-owner Preview only. Adding an IBM or Azure key does not provision compute, grant quantum job authority, or verify a live model. Local Ollama requires an authenticated tunnel to your own host, not a URL to somebody else’s localhost.</p>
 </section>;
}
