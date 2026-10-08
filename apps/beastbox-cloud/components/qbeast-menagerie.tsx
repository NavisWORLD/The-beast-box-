'use client';
import {useEffect,useMemo,useState} from 'react';
import Link from 'next/link';
import PixelBeast from './pixel-beast';
import {useBeastSession} from './beast-session';
import {shownName} from '../lib/companion/session.mjs';
import {loadSparkRuns} from '../public/spark/runs.mjs';
import {makeArchiveMenagerie} from '../lib/companion/archive-menagerie.mjs';
import styles from './qbeast-menagerie.module.css';

type Specimen={
 id:string;name:string;family:string;body:string;island:string;
 genome:{seed:string;facing?:string};runKey:string;jobId:string;
 countsHash:string;backend:string;origin:string;sourceClass:string;stage:number;
};

/**
 * A living book of *actual* rendered Spark genomes.
 * Archive previews are generated from published counts but are not persisted
 * player profiles and do not acquire any host authority or earned progress.
 */
export default function QbeastMenagerie(){
 const {session,ready}=useBeastSession();
 const [specimens,setSpecimens]=useState<Specimen[]>([]);
 const [status,setStatus]=useState<'loading'|'ready'|'unavailable'>('loading');
 const [family,setFamily]=useState('all');
 useEffect(()=>{
  let cancelled=false;
  void loadSparkRuns().then(runs=>{
   if(cancelled)return;
   const items=makeArchiveMenagerie(runs,12) as Specimen[];
   setSpecimens(items);setStatus(items.length?'ready':'unavailable');
  }).catch(()=>{if(!cancelled)setStatus('unavailable');});
  return()=>{cancelled=true;};
 },[]);
 const families=useMemo(()=>Array.from(new Set(specimens.map(item=>item.family))).sort(),[specimens]);
 const visible=family==='all'?specimens:specimens.filter(item=>item.family===family);
 const beast=ready&&session?.beast?.qbeast?.profile?.id?session.beast:null;
 const active=beast?.genome?.seed&&beast?.qbeast?.profile?.id?beast:null;
 const earnedStage=active?Math.max(1,Math.min(3,Math.floor(Number(active.nativeStage||active.stage||1)))):1;
 return <section id="menagerie" className={styles.room} aria-labelledby="menagerie-title" data-menagerie="recorded-archive">
  <div className={styles.heading}>
   <span className={styles.eyebrow}>THE QBEAST MENAGERIE · ACTUAL SEED-DERIVED SPRITES</span>
   <h2 id="menagerie-title">Every strange little form has <em>an origin.</em></h2>
   <p>Explore real renderings from the approved recorded-count archive. These are <strong>generated previews</strong>, not collected or evolved pets. Your own verified QBEAST is shown separately.</p>
   <Link href="/spark/index.html" className={styles.portal}>Meet or create your own Beast →</Link>
  </div>
  {active?<article className={styles.yours} data-saved-qbeast-id={active.qbeast.profile.id}>
   <div className={styles.portrait}>
    <PixelBeast genome={active.genome} publicSpark stage={earnedStage} reduced label={shownName(active)+' · saved QBEAST, earned form '+earnedStage}/>
   </div>
   <div className={styles.yourText}>
    <span className={styles.origin}>YOUR SAVED BEAST · SAME IDENTITY</span>
    <h3>{shownName(active)}</h3>
    <p>QBEAST <code>{active.qbeast.profile.id}</code></p>
    <p>{active.qbeast.profile.family} · earned form {earnedStage} · {String(active.mood||'idle')}</p>
    <p>XP {Number(active.xp)||0} · Bond {Number(active.bond)||0} · Energy {Number(active.energy)||0}</p>
    <Link href="/beast-cage#habitat">Visit your Beast →</Link>
   </div>
  </article>:<p className={styles.empty}>Your own saved Beast appears here after creation. Nothing is generated into your save by opening this gallery.</p>}
  {status==='loading'?<p className={styles.note} role="status">Opening the recorded seed archive…</p>:null}
  {status==='unavailable'?<p className={styles.note} role="status">Archive unavailable right now. Your saved Beast and its local progress are unchanged.</p>:null}
  {status==='ready'?<>
   <div className={styles.filters}><label htmlFor="menagerie-family">Explore by family</label><select id="menagerie-family" value={family} onChange={event=>setFamily(event.target.value)}>
    <option value="all">All available families</option>
    {families.map(name=><option value={name} key={name}>{name}</option>)}
   </select><small>{visible.length} archived examples · stage 1 preview</small></div>
   <div className={styles.grid}>
    {visible.map(item=><article className={styles.card} key={item.id} data-archive-qbeast-id={item.id} data-origin={item.origin}>
     <div className={styles.portrait}>
      <PixelBeast genome={item.genome} stage={1} publicSpark reduced label={item.name+' · '+item.body+' · generated recorded-seed example'}/>
     </div>
     <div className={styles.cardText}><span className={styles.origin}>{item.origin}</span><h3>{item.name}</h3><p>{item.family} · {item.body} · {item.island}</p>
      <span className={styles.preview}>DERIVED EXAMPLE · NOT IN YOUR SAVE</span>
      <details><summary>View seed receipt</summary>
       <dl><dt>Deterministic QBEAST ID</dt><dd><code>{item.id}</code></dd>
       <dt>Source backend</dt><dd>{item.backend}</dd>
       <dt>Recorded run</dt><dd><code>{item.runKey}</code></dd>
       <dt>Count SHA-256</dt><dd><code>{item.countsHash}</code></dd></dl>
       <p>No live hardware connection. A recorded count distribution seeds classical creature generation. No gameplay XP or ownership is inferred.</p>
      </details>
     </div>
    </article>)}
   </div>
  </>:null}
  <p className={styles.boundary}>Recorded counts ≠ a continuously quantum-computed creature. Simulator records must remain SIMULATOR; a visual preview does not confer a verified saved identity or game authority.</p>
 </section>;
}
