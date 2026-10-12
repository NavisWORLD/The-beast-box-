'use client';
import {useEffect,useState} from 'react';
import type {CosmosProfile} from '../public/spark/cosmos-profile.mjs';
import styles from './zeref-diary-panel.module.css';

type Status={configured:boolean;registered?:boolean;diary?:any;error?:string};
const ZEREF_ID='bb-7f9c2a03';

/** Explicit opt-in: register this beast's PUBLIC profile so the scheduled loop grows it in its own cosmos folder. */
export default function GrowInCosmos({profile}:{profile:CosmosProfile|null}){
 const [st,setSt]=useState<Status|null>(null),[busy,setBusy]=useState(false),[msg,setMsg]=useState('');
 const id=profile?.id||null;
 useEffect(()=>{
  if(!id)return;let alive=true;
  void (async()=>{try{const r=await fetch(`/api/cosmos/beasts/${encodeURIComponent(id)}`,{cache:'no-store'});const d=await r.json();if(alive)setSt({configured:!!d.configured,registered:!!d.registered,diary:d.diary||null,error:d.ok===false?d.error:undefined});}
   catch{if(alive)setSt({configured:false,error:'Could not reach the cosmos.'});}})();
  return()=>{alive=false;};
 },[id]);
 if(!profile)return null;
 const zeref=profile.id===ZEREF_ID;
 async function join(){
  setBusy(true);setMsg('');
  try{
   const r=await fetch('/api/cosmos/beasts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({profile})});
   const d=await r.json();
   if(d.ok){setSt(s=>({...(s||{configured:true}),configured:true,registered:true}));setMsg(d.already?'Already growing in the cosmos.':'Registered. The next loop ticks will grow it (small batches, about every 30 minutes).');}
   else setMsg(d.error||'Could not register.');
  }catch{setMsg('Could not reach the cosmos.');}
  finally{setBusy(false);}
 }
 const latest=st?.diary?.recent?.[0];
 return <div className={styles.card} data-grow-cosmos data-cosmos-configured={st?.configured?'true':'false'} data-cosmos-registered={st?.registered||zeref?'true':'false'}>
  <h3>Grow in the cosmos</h3>
  {zeref?<p className={styles.small}><b>Zeref</b> is the first registered beast; his loop diary is above.</p>
  :st&&!st.configured?<p className={styles.small} data-cosmos-state="not-configured"><b>Storage not configured yet.</b> Per-beast cosmos folders open once the owner connects Azure storage. Your beast keeps living and learning in this browser.</p>
  :st?.registered?<>
    <p className={styles.small} data-cosmos-state="registered">✓ <b>{profile.name}</b> is growing in the cosmos{st.diary?` · tick ${st.diary.tick} · stage ${st.diary.stage} ${st.diary.stage_name}`:' · waiting for its first loop tick'}.</p>
    {latest?<blockquote className={styles.thought}>“{latest.thought?.text}”</blockquote>:null}
    {latest?.growth_source?<p className={styles.small}>{latest.growth_source.kind==='rigetti-qvm-simulated'?`⚛ growth: Rigetti simulator (simulated) · job ${latest.growth_source.job_id}`:`growth: deterministic step${latest.growth_source.error?' · '+latest.growth_source.error:''}`}</p>:null}
   </>
  :<>
    <p className={styles.small}>Let the scheduled loop grow <b>{profile.name}</b> while you are away: each turn runs a small circuit on the free Rigetti simulator (simulated) from its signals and writes a diary entry to its own folder.</p>
    <p className={styles.small}>Shared (public profile only): id, name, seed provenance ({profile.provenance?.kind==='recorded-quantum-genome'?`recorded ${profile.provenance.backend} run`:'classical seed'}), visual traits and game stats. Never shared: chats, owner memory, keeper names or anything else in your save.</p>
    <button type="button" className={styles.hear} disabled={busy||!st} onClick={()=>void join()} data-cosmos-join>{busy?'Registering…':'✦ Grow in the cosmos'}</button>
   </>}
  {msg?<p className={styles.small} role="status">{msg}</p>:null}
 </div>;
}
