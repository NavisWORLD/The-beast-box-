'use client';
import {useEffect,useState} from 'react';
import {readJournal,type Journal} from '../lib/zeref/pocket-journal';
import styles from './zeref-diary-panel.module.css';
import PocketLearningCard from './pocket-learning-card';
import GrowInCosmos from './grow-in-cosmos';
import ZerefKnowledgeDiagnostics from './zeref-knowledge-diagnostics';
import type {CosmosProfile} from '../public/spark/cosmos-profile.mjs';

type Entry={tick:number;at:string;mood:string;place:string|null;new_combo_count:number;combos_total:number;discovered_combos:{key:string;name:string}[];xp:number;xp_gain:number;stage:number;stage_name:string;grew:boolean;signals:Record<string,number>;thought:{text:string;by:string};hash:string;
 growth_source?:{kind:string;simulated:boolean;provider:string;target:string;job_id:string|null;shots?:number;counts?:Record<string,number>;error?:string}};
export type Diary={ok:boolean;source:string;verified:boolean;tick:number;xp:number;stage:number;stage_name:string;signals:Record<string,number>;combos_total:number;
 next_stage:{stage:number;name:string;xp:number}|null;recent:Entry[];last_tick_at:string|null;learning?:any;labels:{seed:string;mind:string;loop:string;growth?:string};identity:{beast_id:string;backend:string;job_id:string}};

/** Shared client fetch (same-origin, cached by the route). */
export async function fetchDiary():Promise<Diary|null>{
 try{const r=await fetch('/api/zeref/diary',{cache:'no-store'});if(!r.ok)return null;return await r.json() as Diary;}catch{return null;}
}
const when=(iso:string)=>{try{return new Date(iso).toLocaleString([], {month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'});}catch{return iso;}};
const STAGE_XP=[0,300,1200,3600,9000];
function GrowthBadge({g}:{g?:Entry['growth_source']}){
 if(!g)return null;
 return g.kind==='rigetti-qvm-simulated'
  ?<span className={styles.badgeSim} data-growth-source="rigetti-qvm-simulated" title={`Azure Quantum ${g.target} · job ${g.job_id} · ${g.shots} shots`}>⚛ growth: Rigetti simulator (simulated)</span>
  :<span className={styles.badgeFallback} data-growth-source="deterministic-fallback" title={g.error||''}>growth: deterministic step{g.error?' · simulator unavailable':''}</span>;
}

/** ZEREF'S DIARY on the Beast Cage: loop-written entries, growth, discovered combos, and this device's pocket journal. */
export default function ZerefDiaryPanel({journalId,beastName,cosmosProfile=null}:{journalId:string;beastName:string;cosmosProfile?:CosmosProfile|null}){
 const [diary,setDiary]=useState<Diary|null>(null),[failed,setFailed]=useState(false);
 const [journal,setJournal]=useState<Journal|null>(null);
 useEffect(()=>{
  let alive=true,timer=0;
  const load=async()=>{const d=await fetchDiary();if(!alive)return;if(d){setDiary(d);setFailed(false);window.dispatchEvent(new CustomEvent('beastbox:zeref-diary',{detail:{stage:d.stage}}));}else setFailed(true);};
  void load();
  const arm=()=>{timer=window.setInterval(()=>{if(!document.hidden)void load();},300000);};arm();
  return()=>{alive=false;window.clearInterval(timer);};
 },[]);
 useEffect(()=>{
  const read=()=>setJournal(readJournal(journalId));read();
  let pending=0;const on=()=>{if(!pending)pending=window.setTimeout(()=>{pending=0;read();},700);};
  window.addEventListener('beastbox:zeref-pocket',on);
  return()=>{window.removeEventListener('beastbox:zeref-pocket',on);if(pending)window.clearTimeout(pending);};
 },[journalId]);
 const stage=diary?.stage||1,xp=diary?.xp||0;
 const lo=STAGE_XP[stage-1]||0,hi=diary?.next_stage?.xp||lo;
 const pct=hi>lo?Math.round((xp-lo)/(hi-lo)*100):100;
 const latest=diary?.recent?.[0];
 return <section className={styles.panel} id="zeref-diary" aria-labelledby="zeref-diary-title" data-zeref-diary data-diary-ok={diary?.ok?'true':'false'} data-diary-tick={diary?.tick??0}>
  <div className={styles.head}>
   <p className={styles.tag}>✦ MAINFRAME MEMORY · DIMENSIONAL POCKET</p>
   <h2 id="zeref-diary-title">Zeref&apos;s Diary</h2>
   <p className={styles.lede}>While the page is closed, a scheduled loop lets Zeref keep exploring his pocket. His birth spark is a recorded IBM quantum run; each tick about every 30 minutes, a small circuit built from his current signals runs on the free Rigetti simulator, and its counts nudge his signals, mood and growth before his seeded mind replays a walk and writes one entry.</p>
  </div>
  <div className={styles.grid}>
   <div className={styles.card}>
    <h3>Growth</h3>
    <p className={styles.stage}><strong>Stage {stage} · {diary?.stage_name||'Moonling'}</strong></p>
    <meter min={0} max={100} value={pct} aria-label={`Growth toward ${diary?.next_stage?.name||'max stage'}`}/>
    <p className={styles.small}>{xp} XP{diary?.next_stage?` · ${diary.next_stage.xp-xp} to ${diary.next_stage.name}`:' · fully grown'} · {diary?.tick||0} loop ticks · {diary?.combos_total||0} combos discovered</p>
    {diary?.signals?<p className={styles.signals}>{Object.entries(diary.signals).map(([k,v])=><span key={k}>{k} <b>{v}</b></span>)}</p>:null}
    <p className={styles.small}>Size and aura in the habitat grow with the stage.</p>
   </div>
   <div className={styles.card}>
    <h3>Latest thought</h3>
    {latest?<><blockquote className={styles.thought}>“{latest.thought.text}”</blockquote>
     <p className={styles.small}>Tick {latest.tick} · {when(latest.at)} · mood {latest.mood}{latest.place?` · ${latest.place}`:''}<br/>Line by: {latest.thought.by==='deterministic-template'?'deterministic template (no model)':latest.thought.by}</p>
     <p className={styles.badges}><span className={styles.badgeBirth} data-birth-spark="ibm-recorded">✦ birth spark: IBM recorded</span><GrowthBadge g={latest.growth_source}/></p>
     {latest.growth_source?.kind==='rigetti-qvm-simulated'?<p className={styles.small}>Job {latest.growth_source.job_id} · {latest.growth_source.shots} shots · counts {Object.entries(latest.growth_source.counts||{}).map(([k,v])=>`${k}:${v}`).join(' ')}</p>
      :latest.growth_source?.error?<p className={styles.small}>Simulator note: {latest.growth_source.error}</p>:null}</>
     :<p className={styles.small}>{failed||diary&&!diary.ok?'The diary loop output could not be reached right now. No entry is shown rather than an invented one.':'Opening the diary…'}</p>}
   </div>
   <div className={styles.card}>
    <h3>In the pocket on this device</h3>
    <p className={styles.small}>{beastName} {journal?.lastPlace?<>last reached <b>{journal.lastPlace}</b></>:'is setting out'} · {journal?.arrivals||0} arrival{journal?.arrivals===1?'':'s'} · {journal?.comboCount||0} combos witnessed here · {journal?.care.taps||0} taps · {journal?.care.visits||0} visits</p>
    {journal?.combos?.length?<ul className={styles.combos}>{journal.combos.slice(0,4).map(c=><li key={c.key}>{c.name}</li>)}</ul>:null}
    <p className={styles.small}>Discovered combos are new blends of existing rig channels (action, gait, place, wings, tail, eyes, mouth), not new hand-made animations. Stored only in this browser.</p>
   </div>
   <PocketLearningCard journalId={journalId} beastName={beastName} loop={journalId==='bb-7f9c2a03'?diary?.learning||null:null}/>
   <ZerefKnowledgeDiagnostics beastId={journalId} loop={journalId==='bb-7f9c2a03'?diary?.learning||null:null}/>
   <GrowInCosmos profile={cosmosProfile}/>
  </div>
  {diary?.recent?.length?<ol className={styles.entries} aria-label="Recent diary entries">{diary.recent.slice(0,6).map(e=><li key={e.hash}>
   <span className={styles.when}>#{e.tick} · {when(e.at)}</span>
   <span>{e.thought.text}</span>
   <small><GrowthBadge g={e.growth_source}/> {e.mood}{e.place?` · ${e.place}`:''} · +{e.xp_gain} XP{e.new_combo_count?` · ${e.new_combo_count} new combo${e.new_combo_count>1?'s':''}`:''}{e.grew?` · grew to ${e.stage_name}!`:''}{(e as any).learning?` · ${(e as any).learning.new_cells} new patch${(e as any).learning.new_cells===1?'':'es'}, ${(e as any).learning.moves_blocked} blocked`:''}</small>
  </li>)}</ol>:null}
  <p className={styles.labels}>{diary?.labels?.seed||'Seeded from recorded IBM counts. Not a live quantum link.'} {diary?.labels?.mind||'Zeref is a game companion, not a conscious mind.'} {diary?.labels?.loop||'The diary is generated by the loop.'} {diary?.labels?.growth||''} {diary?.ok?(diary.verified?'Entry hashes re-checked ✓.':'Entry hashes did not verify.'):''}</p>
 </section>;
}
