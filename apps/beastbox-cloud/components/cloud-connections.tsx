'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import {Check,KeyRound,LockKeyhole,PlugZap,RefreshCcw,Shield,Trash2} from 'lucide-react';

type Provider='huggingface'|'ollama_cloud'|'azure_blob'|'ibm_watsonx'|'ibm_quantum';
type Connection={provider:Provider;configured:boolean;config:Record<string,string>;credential:string;mode?:string};
type Field={key:string;label:string;placeholder:string};
const PROVIDERS:{id:Provider;name:string;purpose:string;fields:Field[];secretLabel:string;help:string;activatable:boolean}[]=[
 {id:'huggingface',name:'Hugging Face',purpose:'Hosted conversational model',fields:[{key:'model',label:'Model repository',placeholder:'owner/model-name'}],secretLabel:'HF fine-grained token',help:'Choose a supported chat model and enable Inference Providers permission on your token.',activatable:true},
 {id:'ollama_cloud',name:'Ollama Cloud',purpose:'Hosted Ollama model (not your localhost)',fields:[{key:'model',label:'Cloud model',placeholder:'gpt-oss:120b-cloud'}],secretLabel:'Ollama cloud API key',help:'Connect the official ollama.com API. Your personal localhost:11434 is not reachable from Vercel.',activatable:true},
 {id:'azure_blob',name:'Azure Blob Storage',purpose:'Private photos, documents and exports',fields:[{key:'account',label:'Storage account',placeholder:'myaccount'},{key:'container',label:'Private container',placeholder:'beastbox-private'}],secretLabel:'Scoped container SAS token',help:'Use a short-lived, least-privilege container SAS, not a storage-account master key. Saving a key alone does not enable uploads.',activatable:false},
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

export default function CloudConnections({backendReachable,onActivated}:{backendReachable:boolean;onActivated:()=>void}){
 const [provider,setProvider]=useState<Provider>('huggingface');
 const [rows,setRows]=useState<Connection[]>([]),[vault,setVault]=useState('HOST_KEY_REQUIRED');
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [spendApproved,setSpendApproved]=useState(false);
 const secretRef=useRef<HTMLInputElement>(null);
 const choice=PROVIDERS.find(item=>item.id===provider)!;
 const selected=rows.find(item=>item.provider===provider);
 const ready=backendReachable&&vault==='ENCRYPTED_HOST_ONLY';
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
   if(action==='test')setNotice('Credential check: '+String(result.status||'UNKNOWN')+'. '+String(result.detail||'No inference was performed.'));
   if(action==='remove')setNotice('Removed local encrypted credential. Revoke the key at its provider as well.');
   if(action==='activate'){setNotice('Provider profile selected. Real inference remains unverified until an actual model response.');onActivated();}
   if(action!=='test')await refresh();
  }catch(e){setError((e as Error).message);}
  finally{setBusy(false);}
 }
 async function save(e:React.FormEvent<HTMLFormElement>){
  e.preventDefault();if(!ready||busy)return;
  const form=e.currentTarget;
  const values=new FormData(form);const config:Record<string,string>={};
  for(const field of choice.fields)config[field.key]=String(values.get(field.key)||'').trim();
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
   {choice.fields.map(field=><label key={field.key}>{field.label}<input name={field.key} type="text" required disabled={!ready||busy} defaultValue={selected?.config?.[field.key]||''} key={provider+field.key+(selected?.config?.[field.key]||'')} placeholder={field.placeholder} maxLength={180} autoComplete="off" /></label>)}
   <label>{choice.secretLabel}<input ref={secretRef} name="credential" type="password" minLength={12} maxLength={4096} autoComplete="new-password" placeholder="Paste privately; never shown again" required disabled={!ready||busy}/></label>
   <button type="submit" disabled={!ready||busy}><LockKeyhole size={16}/>{busy?'Working…':'Save encrypted credential'}</button>
  </form>
  {selected?.configured&&<div className="cloud-connect-actions">
   <button type="button" disabled={!ready||busy} onClick={()=>void perform('test')}><RefreshCcw size={15}/> Test access (no paid inference)</button>
   {choice.activatable&&<><label className="cloud-spend"><input type="checkbox" checked={spendApproved} onChange={e=>setSpendApproved(e.target.checked)} disabled={!ready||busy}/> I understand my provider may charge for model requests.</label>
    <button type="button" disabled={!ready||busy||!spendApproved} onClick={()=>void perform('activate')}><PlugZap size={16}/> Activate in BRAIN</button></>}
   <button type="button" disabled={!ready||busy} onClick={()=>void perform('remove')}><Trash2 size={16}/> Forget saved credential</button>
  </div>}
  {notice&&<p className="cloud-connect-success" role="status"><Check size={15}/>{notice}</p>}
  {error&&<p className="inline-error" role="alert">{error}</p>}
  <p className="cloud-connect-foot">Single-owner Preview only. Adding an IBM or Azure key does not provision compute, grant quantum job authority, or verify a live model. Local Ollama requires an authenticated tunnel to your own host, not a URL to somebody else’s localhost.</p>
 </section>;
}
