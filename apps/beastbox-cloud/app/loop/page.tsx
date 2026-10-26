import {loopStatus,STATUS_WORDS} from '@/lib/loop/loop-status.mjs';
import {ZerefLoopView} from '@/components/zeref-loop-view';
export const metadata={title:'Zeref loop status'};
export default function LoopPage(){
 const s=loopStatus();
 return <main>
  <h1>Zeref&apos;s loop</h1>
  <p>{s.honesty}</p>
  <ZerefLoopView/>
  <h2>Every link, wired or not</h2>
  <table><thead><tr><th>From</th><th>To</th><th>Status</th><th>Label</th><th>Note</th></tr></thead><tbody>
   {s.links.map(l=><tr key={l.id} data-link={l.id} data-status={l.status}><td>{l.from}</td><td>{l.to}</td><td>{(STATUS_WORDS as Record<string,string>)[l.status]}</td><td>{l.label}</td><td>{l.note||''}</td></tr>)}
  </tbody></table>
  <p>JSON: <a href="/api/zeref/loop-status">/api/zeref/loop-status</a></p>
 </main>;
}
