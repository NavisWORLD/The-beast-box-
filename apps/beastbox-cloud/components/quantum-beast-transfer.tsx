'use client';
import {useEffect,useRef,useState} from 'react';
import type {CreatureProfile} from '../lib/creature-profile';
import {createSnapshot,parseSnapshot,serializeSnapshot,verifySnapshot,MAX_BYTES,canonical,type Snapshot} from '../../../packages/quantum-beast/src/verifier';
import {exportGba} from '../../../packages/quantum-beast/src/gba_export';
import css from './quantum-beast-transfer.module.css';
const KEY='beastbox-quantum-beast-public-v1';
function assertContinuation(next:Snapshot,previous:Snapshot){
 if(next.profile.id!==previous.profile.id)return;
 if(canonical(next.profile)!==canonical(previous.profile)||canonical(next.public_state)!==canonical(previous.public_state)||canonical(next.progress)!==canonical(previous.progress)||next.generation<previous.generation||canonical(next.events.slice(0,previous.generation))!==canonical(previous.events))throw Error('Import would rewind or fork this Beast’s saved history. Export and review it in a separate runtime.');
}
async function storedSnapshot(raw:string){
 if(raw.length>MAX_BYTES*2)throw Error('Stored file too large');
 const stored=JSON.parse(raw),options=stored.trustedPublicKey?{trustedPublicKey:stored.trustedPublicKey}:{};
 return parseSnapshot(stored.text,options);
}
function download(bytes:BlobPart,name:string,type:string){const url=URL.createObjectURL(new Blob([bytes],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
export default function QuantumBeastTransfer({profile,onImport}:{profile:CreatureProfile|null;onImport:(profile:CreatureProfile)=>void}){
 const [snapshot,setSnapshot]=useState<Snapshot|null>(null),[key,setKey]=useState('');
 const [status,setStatus]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const [verifiedKey,setVerifiedKey]=useState<string|undefined>(),[signature,setSignature]=useState('absent');
 const [ready,setReady]=useState(false);
 const input=useRef<HTMLInputElement>(null),storedRaw=useRef<string|null>(null),running=useRef(false);
 const importCallback=useRef(onImport);importCallback.current=onImport;
 useEffect(()=>{let active=true;
  void(async()=>{let failed=false;try{const raw=localStorage.getItem(KEY);storedRaw.current=raw;if(!raw)return;const s=await storedSnapshot(raw),stored=JSON.parse(raw),options=stored.trustedPublicKey?{trustedPublicKey:stored.trustedPublicKey}:{};const known=localStorage.getItem(KEY+'-creature-'+s.profile.id);if(known)assertContinuation(s,await storedSnapshot(known));const v=await verifySnapshot(s,options);if(active){setSnapshot(s);setVerifiedKey(stored.trustedPublicKey);setKey(stored.trustedPublicKey??'');setSignature(v.signature);importCallback.current(s.profile);}}catch{failed=true;if(active)setError('A previous portable save could not be verified. It has been retained for recovery; transfers are blocked until it is recovered.');}finally{if(active)setReady(!failed);}})();
  return()=>{active=false;};
 },[]);
 const matches=!!profile&&!!snapshot&&canonical(profile)===canonical(snapshot.profile);
 async function run(work:()=>Promise<void>){if(!ready||running.current)return;running.current=true;setBusy(true);setError('');try{await work();}catch(e){setError(e instanceof Error?e.message:'Could not transfer this creature.');}finally{running.current=false;setBusy(false);}}
 async function remember(s:Snapshot,trustedPublicKey?:string){
  const options=trustedPublicKey?{trustedPublicKey}:{};const text=await serializeSnapshot(s,options),verification=await verifySnapshot(s,options);
  if(!navigator.locks)throw Error('This browser cannot safely coordinate portable saves. Use the local CLI or a browser with Web Locks.');
  await navigator.locks.request(KEY,async()=>{
   if(localStorage.getItem(KEY)!==storedRaw.current)throw Error('Another tab changed this Beast’s saved history. Reload before continuing.');
   const index=KEY+'-creature-'+s.profile.id,known=localStorage.getItem(index);if(known)assertContinuation(s,await storedSnapshot(known));
   if(storedRaw.current){const previous=await storedSnapshot(storedRaw.current),oldIndex=KEY+'-creature-'+previous.profile.id;if(!localStorage.getItem(oldIndex))localStorage.setItem(oldIndex,storedRaw.current);}
   const raw=JSON.stringify({text,trustedPublicKey});localStorage.setItem(index,raw);
   try{localStorage.setItem(KEY,raw);}catch(e){if(known===null)localStorage.removeItem(index);else localStorage.setItem(index,known);throw e;}
   storedRaw.current=raw;
  });
  setSnapshot(s);setVerifiedKey(trustedPublicKey);setSignature(verification.signature);return text;
 }
 async function exportPortable(){if(!profile)return;
  if(snapshot&&!matches)throw Error('The selected genome differs from the saved Beast. Import its file or choose “Start a new portable life” explicitly.');
  const s=snapshot??await createSnapshot(profile),text=await remember(s,verifiedKey);
  download(text,s.profile.id+'.qbeast','application/json');setStatus('Portable public identity and approved lineage downloaded. Host permissions stay with the host.');
 }
 async function importFile(file:File){
  if(file.size>MAX_BYTES)throw Error('Quantum Beast files must be at most 512 KiB.');
  const trustedPublicKey=key.trim()||undefined,options=trustedPublicKey?{trustedPublicKey}:{};
  const s=await parseSnapshot(await file.text(),options);
  if(snapshot){
   assertContinuation(s,snapshot);
   localStorage.setItem(KEY+'-backup-'+snapshot.digest,await serializeSnapshot(snapshot,verifiedKey?{trustedPublicKey:verifiedKey}:{}));
  }
  await remember(s,trustedPublicKey);onImport(s.profile);
  setStatus('Imported the same public Beast, including its approved history. No owner memory or permissions imported.');
 }
 return <section className={css.panel} data-critical-control aria-label="Quantum Beast portable companion bridge">
  <div><span className={css.kicker}>QUANTUM BEAST BRIDGE</span><h3>One Beast. Many brains.</h3>
   <p>Carry this creature’s identity, appearance and approved memories to a compatible runtime. Its host approves every new event.</p></div>
  <div className={css.actions}>
   <button type="button" disabled={!profile||busy||!ready} onClick={()=>void run(exportPortable)}>DOWNLOAD QUANTUM BEAST</button>
   <button type="button" disabled={busy||!ready} onClick={()=>input.current?.click()}>IMPORT QUANTUM BEAST</button>
   {snapshot&&matches?<button type="button" disabled={busy||!ready} onClick={()=>void run(async()=>{const pack=await exportGba(snapshot,verifiedKey?{trustedPublicKey:verifiedKey}:{});download(Uint8Array.from(pack.zip).buffer,snapshot.profile.id+'-gba.zip','application/zip');setStatus('Exported original BCG1 art and BCP1 seeded stats for offline LOST COSMOS import.');})}>Export this Beast to GBA</button>:null}
   <input ref={input} disabled={busy||!ready} className={css.file} type="file" accept=".qbeast,application/json" aria-label="Quantum Beast file" onChange={e=>{const file=e.target.files?.[0];e.target.value='';if(file)void run(()=>importFile(file));}}/>
  </div>
  {snapshot?<div className={css.receipt} aria-label="Portable Beast verification">
   <strong>{snapshot.profile.name} · {snapshot.profile.id}</strong>
   <span>{snapshot.generation} approved events · Signature: {signature.replaceAll('_',' ')}</span>
   <code title={snapshot.lineage_head}>Lineage {snapshot.lineage_head.slice(0,16)}…</code>
   <span>Trust {snapshot.progress.trust} · Bond {snapshot.progress.bond} · Evolution {snapshot.progress.evolution_stage}</span>
   <span>{snapshot.public_state.mode==='unavailable'?'No approved dyn12 projection attached.':'Approved host dyn12 projection preserved.'}</span>
   {!matches?<p>Select or import this Beast to keep its existing genome and history.</p>:null}
  </div>:null}
  {snapshot&&!matches&&profile?<><p>To start another portable life, generate a different seed and creature ID.</p><button type="button" disabled={busy||!ready||profile.id===snapshot.profile.id} className={css.newLife} onClick={()=>void run(async()=>{if(profile.id===snapshot.profile.id)throw Error('A new life requires a different creature ID.');const previous=await serializeSnapshot(snapshot,verifiedKey?{trustedPublicKey:verifiedKey}:{});download(previous,snapshot.profile.id+'-previous.qbeast','application/json');const s=await createSnapshot(profile);await remember(s);setKey('');setStatus('Previous Beast backed up. Started a separate portable life for the selected genome.');})}>Start a new portable life (backs up previous Beast)</button></>:null}
  <details className={css.details}><summary>Verify a trusted publisher</summary><label>Publisher public key (optional)<input value={key} maxLength={64} placeholder="Externally verified 64-character public key" onChange={e=>setKey(e.target.value)} /></label><p>A checksum proves integrity. A source signature is trusted only when its public key matches a key you supply independently.</p></details>
  {error?<p className={css.error} role="alert">{error}</p>:null}
  {status?<p className={css.status} role="status">{status}</p>:null}
  <small>Quantum-inspired game identity; no quantum hardware or cloud inference runs here. Portable files contain public data only. GBA receives a fixed game snapshot.</small>
 </section>;
}
