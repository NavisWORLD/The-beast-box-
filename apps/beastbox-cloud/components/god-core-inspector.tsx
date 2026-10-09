'use client';
import {useBeastSession} from './beast-session';
import {ASSOCIATION_LIMITS,recallAssociations} from '../lib/companion/learn.mjs';
/** Read-only evidence for the active local Beast; intentionally not an authority console. */
export default function GodCoreInspector(){
 const {ready,session,trail,storageStatus}=useBeastSession();
 const beast=session?.beast,core=beast?.behavior;
 const last=core?.events?.at(-1);
 const graph=session?.mind?.associations,quantum=beast?.genome?.quantum;
 const source=/qvm|simulator/i.test(quantum?.backend||'')?'SIMULATOR':/^ibm_/i.test(quantum?.backend||'')?'RECORDED IBM ARCHIVE LABEL':'SEEDED / SOURCE UNAVAILABLE';
 function exportEvidence(){
  if(!beast)return;
  const record={schema:'beastbox-local-observation-v1',authority:'unsigned-device-observation',qbeast_id:beast.qbeast?.profile?.id||null,seed:beast.seed,genome:beast.genome,source_class:source,care:{energy:beast.energy,bond:beast.bond,xp:beast.xp},behavior:core||null,mind:{steps:session.mind?.steps,associations:graph||null},place:trail.place,storage_status:storageStatus,note:'Bounded local observation; includes learned words. Not a public signature, new measurement or complete experiment history.'};
  const url=URL.createObjectURL(new Blob([JSON.stringify(record,null,2)+'\n'],{type:'application/json'})),link=document.createElement('a');link.href=url;link.download='beast-observation.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }
 return <section id="god-core" aria-label="God Core runtime evidence" style={{padding:'1.25rem',border:'1px solid #496887',borderRadius:16,background:'#101b36',marginBlock:'2rem',color:'#def6ff',overflowWrap:'anywhere'}}>
  <h2 style={{marginBottom:8}}>GOD CORE // THE BEAST'S LITTLE BRAINSTEM</h2>
  <p>Classical deterministic creature behavior. No claim of consciousness, new quantum measurements or autonomous model inference.</p>
  {!ready?<p role="status">Checking local Beast…</p>:!beast?<p>No active Beast yet. Create one to see its actual state.</p>:!core?<p role="status">No behavior ticks recorded yet. Keep the Beast open in a visible tab.</p>:<>
   <p><strong>{beast.displayName||'Your Beast'}</strong> · QBEAST {beast.qbeast?.profile?.id||'unverified'} · Tick {core.tick} · Current: {core.lastAction}</p>
   <p>{source} · {quantum?.backend||'Backend unavailable'}. Archive labels are retained provenance, not a fresh provider attestation.</p>
   <p>Behavior energy {core.energy} / 100 · Curiosity {core.curiosity} / 100 · Stored feedback events {core.memory?.length||0}</p>
   <p>Care energy {Math.round(beast.energy??0)} / 100 is separate from the behavior drive. Automatic ticks do not award XP or native progress.</p>
   <details><summary>Why that action? Show actual inputs and scores</summary>
    <pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify(last||{status:'No decision yet'},null,2)}</pre>
   </details>
   <details><summary>Learned memory that can affect the next decision</summary>
    <p>One existing browser mind: a 16×16 Hebbian matrix and bounded word associations. Only remembered links matching an action add to its score, capped at one. These are classical local updates; model weights are not trained.</p>
    <p>{graph?.observations||0} accepted observations · {Object.keys(graph?.concepts||{}).length} / {ASSOCIATION_LIMITS.concepts} concepts · {Object.keys(graph?.links||{}).length} / {ASSOCIATION_LIMITS.links} links</p>
    <pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify({room:trail.place,recall:recallAssociations(session.mind,trail.place,12),last_actual_inputs:last?.input?.associations||[],last_feedback:core.lastFeedback||null},null,2)}</pre>
   </details>
   <details><summary>Recent bounded events and preferences</summary>
    <pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify({preferences:core.preferences,memory:core.memory,events:core.events},null,2)}</pre>
   </details>
   <details><summary>Genesis and inherited expression</summary><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify({seed:beast.seed,quantum,body:beast.genome?.body,appearance:{ears:beast.genome?.ears,wings:beast.genome?.wings,tail:beast.genome?.tail},gait:beast.genome?.behavior,voice:beast.genome?.voice},null,2)}</pre></details>
   <button type="button" onClick={exportEvidence} style={{padding:'12px 16px',marginTop:16,minHeight:44,borderRadius:8,background:'#c2e9de',color:'#142d32',fontWeight:700}}>Export local observation</button>
   <p><small>Export includes learned words and 32 retained decisions, not private owner state or chat. {storageStatus}. No continuous quantum link; native game progress stays separate.</small></p>
  </>}
  <p><a href="https://github.com/NavisWORLD/The-beast-box-/blob/main/docs/BEAST_AWAKENS_HF_INTEGRATION.md" target="_blank" rel="noopener noreferrer" style={{color:'#9ee6e2'}}>Pinned Hugging Face source audit, paired experiments and replay instructions →</a></p>
 </section>;
}
