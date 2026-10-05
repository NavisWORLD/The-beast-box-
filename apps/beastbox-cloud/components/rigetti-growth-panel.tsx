'use client';
import {useState} from 'react';
import {useBeastSession} from './beast-session';
import {nextQvmGrowth} from '../lib/companion/qvm-growth.mjs';
import css from './spark-field.module.css';

export default function RigettiGrowthPanel(){
 const {session,change}=useBeastSession();
 const [busy,setBusy]=useState(false),[status,setStatus]=useState('');
 const used=Array.isArray(session?.beast?.qvm_growth)?session.beast.qvm_growth.length:0;

 async function processNext(){
  if(busy||!session?.beast)return;
  setBusy(true);
  try{
   const response=await fetch('/spark/rigetti-qvm-growth.json',{cache:'force-cache'});
   if(!response.ok)throw new Error('Archived simulator receipt unavailable');
   const receipt=await response.json();
   let result:any=null;
   change((draft)=>{result=nextQvmGrowth(draft,receipt);});
   if(!result?.ok){
    setStatus(result?.complete?'All 8 archived simulator scenarios have already been processed for this Beast.':result?.reason||'Growth pulse unavailable');
   }else{
    setStatus(`Scenario ${result.scenario}/8 processed · +${result.gain??result.xp} XP · +${result.bond} bond · stability ${result.stability}%${result.evolved?' · EVOLVED!':''}`);
    window.dispatchEvent(new CustomEvent('beastbox:spark-chirp',{detail:{channel:'roamer',intensity:result.evolved?1:.72}}));
   }
  }catch(err){setStatus(err instanceof Error?err.message:'Growth pulse failed');}
  finally{setBusy(false);}
 }

 return <section className={css.qvm} data-rigetti-growth="archived-simulator">
  <div><strong>Rigetti growth</strong><span>{used}/8 archived simulator scenarios processed</span></div>
  <p>Uses the two historical 64-shot batches from each verified Azure-hosted Rigetti QVM scenario. No new cloud job, no QPU, and the held-out future batch is not used for growth.</p>
  <button type="button" disabled={busy||!session?.beast||used>=8} onClick={()=>void processNext()}>{busy?'Processing…':used>=8?'Growth archive complete':'Process next archived growth pulse'}</button>
  {status?<p role="status">{status}</p>:null}
 </section>;
}
