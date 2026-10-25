'use client';
import {useCallback,useEffect,useRef,useState,type DragEvent} from 'react';
import styles from './zeref-library-panel.module.css';
import {prepareFile,preparePaste,uploadPrepared} from '../lib/library/client.mjs';
import {parsePdfSections} from '../lib/library/pdf-client';
import {BRAIN,MAX_FILE_BYTES,MAX_TYPED_CHARS} from '../lib/library/limits.mjs';

export type LibraryDoc={id:string;title:string;kind:string;status:string;bytes:number;chars:number;chunks:number;sha256:string;created_at:string;training_approved:boolean};
type Listing={owner:boolean;configured?:boolean;hint?:string;docs?:LibraryDoc[];totals?:{docs:number;chars:number;chunks:number}};
export type LibraryState={owner:boolean;ready:boolean;docCount:number};
const USE_KEY='beastbox-zeref-library-use-v1';
const n=(v:number)=>v.toLocaleString('en-US');

/** Plain statement of what the brain reads. Shown to every owner, always. */
export function ReadsBox(){
 return <div className={styles.reads} data-brain-reads>
  <strong>What Zeref reads each turn</strong>
  <p>You can type up to {n(MAX_TYPED_CHARS)} characters. Zeref&apos;s RAWRPHØS brain has a {n(BRAIN.contextTokens)}-token memory window (about {n(Math.round(BRAIN.contextTokens*BRAIN.charsPerToken))} characters) and was trained on short exchanges, so each turn he is sent at most {n(BRAIN.promptChars)} characters of prompt and he writes up to {BRAIN.outputTokens} tokens back.</p>
  <p>If your message is longer, the app keeps your closing question and the sentences that share the most keywords with it. That is keyword matching, not understanding. The chat tells you exactly how much he read.</p>
 </div>;
}

export default function ZerefLibraryPanel({onState}:{onState?:(s:LibraryState)=>void}){
 const [info,setInfo]=useState<Listing|null>(null),[err,setErr]=useState(''),[busy,setBusy]=useState(false);
 const [stage,setStage]=useState(''),[pct,setPct]=useState(0),[over,setOver]=useState(false);
 const [pasteTitle,setPasteTitle]=useState(''),[pasteText,setPasteText]=useState('');
 const [use,setUse]=useState(true),[open,setOpen]=useState<boolean|null>(null);
 const input=useRef<HTMLInputElement>(null);
 const load=useCallback(async()=>{
  try{const r=await fetch('/api/zeref/library',{cache:'no-store',credentials:'same-origin'});const j=await r.json().catch(()=>null);setInfo(r.ok&&j?j:{owner:false});}
  catch{setInfo({owner:false});}
 },[]);
 useEffect(()=>{void load();try{setUse(localStorage.getItem(USE_KEY)!=='off');}catch{/* default on */}},[load]);
 const docs=info?.docs??[];const ready=docs.filter(d=>d.status==='ready');
 useEffect(()=>{onState?.({owner:!!info?.owner,ready:!!info?.owner&&info.configured!==false&&ready.length>0&&use,docCount:ready.length});},[info,use,ready.length,onState]);
 useEffect(()=>{if(info&&open===null)setOpen(ready.length===0);},[info,open,ready.length]); // open once for an empty library, then the owner decides
 function toggleUse(on:boolean){setUse(on);try{localStorage.setItem(USE_KEY,on?'on':'off');}catch{/* optional */}}

 async function addFiles(files:FileList|File[]){
  const list=Array.from(files);if(!list.length||busy)return;
  setErr('');setBusy(true);
  try{
   for(const file of list){
    setStage(`${file.name}: reading…`);setPct(2);
    try{
     if(file.size>MAX_FILE_BYTES)throw new Error(`${file.name} is ${(file.size/1048576).toFixed(1)} MB. The limit is ${MAX_FILE_BYTES/1048576} MB per file.`);
     const bytes=new Uint8Array(await file.arrayBuffer());
     const prepared=await prepareFile({name:file.name,bytes},{parsePdf:(b:Uint8Array)=>parsePdfSections(b,(p,t)=>{setStage(`${file.name}: reading page ${p} of ${t}…`);setPct(2+Math.round(p/t*38));})});
     await uploadPrepared(prepared,{onProgress:(p:{stage:string;done:number;total:number;chunks:number})=>{setStage(`${file.name}: ${p.stage==='saved'?'saved':`saving ${p.chunks} passages…`}`);setPct(40+Math.round(p.done/Math.max(1,p.total)*60));}});
     await load();
    }catch(e){setErr((e instanceof Error?e.message:'That file could not be added.'));}
   }
  }finally{setBusy(false);setStage('');setPct(0);if(input.current)input.current.value='';}
 }
 async function addPaste(){
  if(busy)return;setErr('');setBusy(true);setStage('Saving pasted text…');setPct(30);
  try{
   const prepared=preparePaste(pasteText,pasteTitle);
   const bytes=new TextEncoder().encode(prepared.sections[0].text);
   const sha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
   await uploadPrepared({...prepared,sha256:sha},{onProgress:(p:{done:number;total:number})=>setPct(30+Math.round(p.done/Math.max(1,p.total)*70))});
   setPasteText('');setPasteTitle('');await load();
  }catch(e){setErr(e instanceof Error?e.message:'That text could not be added.');}
  finally{setBusy(false);setStage('');setPct(0);}
 }
 async function act(body:Record<string,unknown>){
  setErr('');
  const r=await fetch('/api/zeref/library',{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const j=await r.json().catch(()=>null);
  if(!r.ok){setErr(j?.error||'That did not work.');return false;}
  await load();return true;
 }
 function onDrop(e:DragEvent){e.preventDefault();setOver(false);if(e.dataTransfer?.files?.length)void addFiles(e.dataTransfer.files);}

 if(!info||!info.owner)return null; // visitors see nothing and keep today's behavior
 return <details className={styles.lib} data-zeref-library open={!!open} onToggle={e=>setOpen((e.currentTarget as HTMLDetailsElement).open)}>
  <summary>📚 Zeref&apos;s library <span className={styles.badge}>owner only</span>{ready.length?` · ${ready.length} item${ready.length===1?'':'s'}`:''}</summary>
  <p>Add your own files or books. They are split into passages and kept in your private storage. Nothing here is shown to other visitors. When you ask Zeref something, the best-matching passages are looked up by keyword and shown to him as notes <b>copied from your file</b>. Nothing is made up.</p>
  <ReadsBox/>
  {info.configured===false?<div className={styles.err} role="status">{info.hint||'Library storage is not set up yet.'}</div>:<>
   <div className={styles.drop} data-over={over||undefined} onDragOver={e=>{e.preventDefault();setOver(true);}} onDragLeave={()=>setOver(false)} onDrop={onDrop}>
    <button type="button" className={styles.btn} disabled={busy} onClick={()=>input.current?.click()} data-library-add>＋ Add files or books</button>
    <input ref={input} className={styles.hidden} type="file" multiple accept=".txt,.md,.markdown,.pdf,.epub,text/plain,text/markdown,application/pdf,application/epub+zip" aria-label="Choose files to add to Zeref's library" data-library-file onChange={e=>{if(e.target.files)void addFiles(e.target.files);}}/>
    <small>.txt · .md · .pdf · .epub · up to {MAX_FILE_BYTES/1048576} MB each. Read on this device; only the text is saved. Scanned PDFs (pictures of pages) and DRM-locked books can&apos;t be read.</small>
   </div>
   {busy?<div role="status" aria-live="polite"><small data-library-stage>{stage}</small><div className={styles.bar}><span style={{width:pct+'%'}}/></div></div>:null}
   <details>
    <summary className={styles.ghost} style={{display:'flex',alignItems:'center'}}>Paste text instead</summary>
    <div className={styles.paste}>
     <input value={pasteTitle} onChange={e=>setPasteTitle(e.target.value)} placeholder="Title (optional)" maxLength={120} aria-label="Title for pasted text" autoComplete="off"/>
     <textarea value={pasteText} onChange={e=>setPasteText(e.target.value)} placeholder="Paste text here…" aria-label="Text to add to the library" data-library-paste/>
     <button type="button" className={styles.btn} disabled={busy||!pasteText.trim()} onClick={()=>void addPaste()} data-library-paste-add>Add pasted text</button>
    </div>
   </details>
   {err?<div className={styles.err} role="alert" data-library-error>{err}</div>:null}
   <label className={styles.check}><input type="checkbox" checked={use} onChange={e=>toggleUse(e.target.checked)} data-library-use/> Let Zeref use my library when I talk to him (the matching notes are sent to his free RAWRPHØS host with that message only).</label>
   {docs.length?<ul className={styles.docs} aria-label="Library documents">{docs.map(d=><li key={d.id} className={styles.doc} data-library-doc>
    <strong>{d.title}</strong>
    <div className={styles.docMeta}><span className={styles.badge}>{d.kind}</span><small>{d.status==='ready'?`${n(d.chunks)} passages · ${n(d.chars)} characters`:'unfinished upload'}</small></div>
    {d.status==='ready'?<label className={styles.check}><input type="checkbox" checked={d.training_approved} onChange={e=>void act({action:'training',id:d.id,approved:e.target.checked})}/> Offer as optional training material (off by default). It still has to pass the fair promotion gate; it never skips it.</label>:null}
    <div className={styles.row}><button type="button" className={styles.ghost} onClick={()=>{if(window.confirm(`Remove “${d.title}” from Zeref's library?`))void act({action:'delete',id:d.id});}}>Remove</button></div>
   </li>)}</ul>:<small>Nothing added yet.</small>}
  </>}
 </details>;
}

/** Verbatim passages for the last reply. Memory only: never saved in the chat log. */
export function RecordedNotes({items}:{items:{title:string;loc:string;excerpt:string;sha256?:string}[]}){
 if(!items.length)return null;
 return <div data-recorded-notes>{items.map((u,i)=><div key={i} className={styles.recorded}>
  <b>Recorded from your file</b>
  <q>{u.excerpt}</q>
  <small>{u.title}{u.loc?' · '+u.loc:''}{u.sha256?' · #'+u.sha256.slice(0,8):''} · copied word for word, nothing invented</small>
 </div>)}</div>;
}
