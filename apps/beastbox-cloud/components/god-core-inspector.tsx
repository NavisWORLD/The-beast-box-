'use client';
import {useBeastSession} from './beast-session';
/** Read-only evidence for the active local Beast; intentionally not an authority console. */
export default function GodCoreInspector(){
 const {ready,session}=useBeastSession();
 const beast=session?.beast,core=beast?.behavior;
 const last=core?.events?.at(-1);
 return <section aria-label="God Core runtime evidence" style={{padding:'1.25rem',border:'1px solid #496887',borderRadius:16,background:'#101b36',marginBlock:'2rem',color:'#def6ff'}}>
  <h2 style={{marginBottom:8}}>GOD CORE // THE BEAST'S LITTLE BRAINSTEM</h2>
  <p>Classical deterministic creature behavior. No claim of consciousness, new quantum measurements or autonomous model inference.</p>
  {!ready?<p role="status">Checking local Beast…</p>:!beast?<p>No active Beast yet. Create one to see its actual state.</p>:!core?<p role="status">No behavior ticks recorded yet. Keep the Beast open in a visible tab.</p>:<>
   <p><strong>{beast.displayName||'Your Beast'}</strong> · QBEAST {beast.qbeast?.profile?.id||'unverified'} · Tick {core.tick} · Current: {core.lastAction}</p>
   <p>Behavior energy {core.energy} / 100 · Curiosity {core.curiosity} / 100 · Stored memories {core.memory?.length||0}</p>
   <details><summary>Why that action? Show actual inputs and scores</summary>
    <pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify(last||{status:'No decision yet'},null,2)}</pre>
   </details>
   <details><summary>Recent bounded events and preferences</summary>
    <pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify({preferences:core.preferences,memory:core.memory,events:core.events},null,2)}</pre>
   </details>
   <p><small>Saved on this browser only. No continuous quantum link. Native game progress remains separate.</small></p>
  </>}
 </section>;
}
