'use client';
import {useMemo,useState} from 'react';
import {ArrowDownToLine,ShieldCheck} from 'lucide-react';
import {latestMeasured,makeGbaZip,type Look} from '../lib/gba-companion';

export default function OwnerGbaExport({trace}:{trace:Record<string,unknown>[]}){
 const measured=useMemo(()=>latestMeasured(trace),[trace]);
 const [approved,setApproved]=useState(false),[busy,setBusy]=useState(false);
 const [message,setMessage]=useState(''),[error,setError]=useState('');
 async function exportApproved(){
  if(!approved||!measured||busy)return;
  setBusy(true);setError('');setMessage('');
  try{
   let look:Look='nebula';
   try{
    const selected=window.localStorage.getItem('beastbox-cage-appearance-v1');
    if(selected==='aurora'||selected==='starlight')look=selected;
   }catch{/* default illustration, never guessed identity */}
   // Local file generation only. A strictly validated checkpoint with numeric
   // vectors, sequence and checksum is all that this owner-approved pack adds.
   const zip=await makeGbaZip(look,measured);
   const url=URL.createObjectURL(new Blob([Uint8Array.from(zip)],{type:'application/zip'}));
   const anchor=document.createElement('a');
   anchor.href=url;anchor.download='beast-cage-owner-verified-gba-'+measured.sequence+'.zip';
   document.body.appendChild(anchor);anchor.click();anchor.remove();
   window.setTimeout(()=>URL.revokeObjectURL(url),5000);
   setMessage('Portable pack generated from checkpoint '+measured.sequence+
    '. Only the 12+12 numeric axes, sequence and checksum were added to public character assets.');
   setApproved(false);
  }catch(e){setError(e instanceof Error?e.message:'The signal export could not be completed.');}
  finally{setBusy(false);}
 }
 return <section className="record" aria-label="Explicit owner-only GBA export">
  <strong>🎮 EXPORT THE BEAST TO YOUR GBA GAME</strong>
  <p>Portable sprite + game module, with optional measured COSMOS CNS/synaptic
   numeric signal values. This will never export conversation text, memories,
   model weights, sensor media, tokens, or execution authority.</p>
  {measured?<><p>Available checkpoint #{measured.sequence}.
    Approved export includes 12 CNS software axes and 12 synaptic state axes
    with their checkpoint sequence and SHA-256 proof.</p>
   <label className="cloud-spend"><input type="checkbox" checked={approved}
    onChange={e=>setApproved(e.target.checked)} disabled={busy}/>
    I explicitly approve placing this checkpoint&apos;s numeric state and
    checkpoint hash into a downloadable local game file. I will decide
    where to import or share the file.</label>
   <button type="button" className="outline-action" disabled={!approved||busy}
    onClick={()=>void exportApproved()}><ArrowDownToLine size={16}/>
    {busy?'Building your portable companion…':'Download selected COSMOS state + GBA character'}</button></>:
   <p role="status"><ShieldCheck size={14}/> No complete authenticated
    \`substrate-signal-v1\` trace receipt is available. Nothing will be invented.
    Use the public visual-only game export instead.</p>}
  {message?<p role="status" className="cloud-connect-success">{message}</p>:null}
  {error?<p role="alert" className="inline-error">{error}</p>:null}
 </section>;
}
