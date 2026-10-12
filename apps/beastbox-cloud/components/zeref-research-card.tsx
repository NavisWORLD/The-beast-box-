'use client';
import {useEffect,useState} from 'react';
import {researchEvidence,type ResearchEvidence} from '../lib/zeref/research-status.mjs';
import styles from './zeref-research-card.module.css';

const short=(hash:string)=>hash.slice(0,12)+'…';
const report='https://github.com/NavisWORLD/The-beast-box-/blob/main/docs/verification/living-beast-research-cloud-20261012.md';

/** Audited neural research remains separate from the selected companion and served model. */
export default function ZerefResearchCard({beastId}:{beastId?:string}){
 const [view,setView]=useState<ResearchEvidence|null>(null),[failed,setFailed]=useState(false);
 useEffect(()=>{
  const abort=new AbortController();
  fetch('/spark/zeref-learning/research-status.json',{cache:'no-store',signal:abort.signal})
   .then(r=>r.ok?r.json():null).then(raw=>{if(abort.signal.aborted)return;const parsed=researchEvidence(raw);setView(parsed);setFailed(!parsed);})
   .catch(()=>{if(!abort.signal.aborted)setFailed(true);});
  return()=>abort.abort();
 },[]);
 const a=view?.approved;
 return <section className={styles.card} aria-label="Latest Zeref neural research" data-zeref-research data-research-status={a?'approved-research-parent':'unavailable'}>
  <p className={styles.tag}>RAWRPHØS · RESEARCH RECEIPTS</p>
  <h3>Latest approved neural parent</h3>
  {view&&a?<>
   <p className={styles.summary}><strong>Experiment {a.experiment} · cycle {a.approved_cycle}</strong> · {a.training_steps.toLocaleString()} training steps</p>
   <p className={styles.small}>Checkpoint <code title={a.checkpoint_sha256}>{short(a.checkpoint_sha256)}</code> · optimizer and replay state preserved. <a href={a.run_url} target="_blank" rel="noopener noreferrer">Approval evidence</a></p>
   <p className={styles.small}>Research lineage <code>{view.trainingId}</code>{beastId&&beastId!==view.trainingId?<> · selected creature <code>{beastId}</code></>:null}. The Moonwraith display companion <code>{view.displayId}</code> has no verified association to this neural lineage.</p>
   <div className={styles.trials}>
    {view.trials.map(t=><details key={t.experiment} className={styles.trial} data-experiment={t.experiment} data-candidate-status={t.status}>
     <summary><span>{t.experiment} · {t.name}</span><b>REJECTED</b></summary>
     <p>{t.summary}</p>
     <p className={styles.small}>{t.training_updates?`${t.training_updates} RAWRPHØS optimizer updates. `:t.optimizer_updates_per_arm?`${t.optimizer_updates_per_arm} auxiliary optimizer updates per arm; RAWRPHØS weights unchanged. `:''}Failed gates: {t.failed_gates.map(g=>g.replace(/^G\d+_/,'').replace(/_/g,' ')).join('; ')}.</p>
     <p className={styles.small}>{t.boundary} <a href={t.run_url} target="_blank" rel="noopener noreferrer">Original result</a></p>
    </details>)}
   </div>
   <details className={styles.limits}>
    <summary>What these results prove</summary>
    <p className={styles.small}>The approved cycle passed its original gates, but all 14 held-out actions were RIGHT. Goal completion, native ROM objective progress and general world knowledge are unproven. Later diversity, world-vocabulary and optical-dynamics trials failed; rejected weights remain unpromoted.</p>
    {view.runtime?<p className={styles.small}>The Railway runtime loaded the separate {view.runtime.stable_training_steps.toLocaleString()}-step checkpoint <code title={view.runtime.stable_checkpoint_sha256}>{short(view.runtime.stable_checkpoint_sha256)}</code>. Host health was checked {view.runtime.audited_at}; no fresh model reply was verified by this audit. The approved research checkpoint is not the served checkpoint.</p>:null}
    <p className={styles.small}>Research audit: {view.auditedAt}. Pocket rules, generated diary lines, native game saves, recorded IBM measurements and neural weights remain distinct. <a href={report} target="_blank" rel="noopener noreferrer">Full audit</a></p>
   </details>
  </>:<p className={styles.small} role="status">{failed?'Research evidence is unavailable or inconsistent. No approval is inferred.':'Loading the audited research record…'}</p>}
 </section>;
}
