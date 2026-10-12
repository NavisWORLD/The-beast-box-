'use client';
import {useEffect,useState} from 'react';
import styles from './zeref-diary-panel.module.css';

type Loop={cells_visited:number;cells_total:number;known_rifts?:number;moves_blocked:number;moves_succeeded:number;blocked_rate?:number;favorite_spot:string|null;prefs?:Record<string,number>}|null;
type Arm={cells_visited:number;blocked:number;legal?:number};
type Status={schema:string;experiment:string;qbeast_id:string;run_url:string|null;parent_sha256:string;candidate_sha256:string|null;accepted:boolean|null;status:string;
 eval:{layouts:number;random?:Arm;pocket_learner?:Arm;greedy_frontier?:Arm;parent?:Arm;candidate_seeds?:Arm[];no_memory_seeds?:Arm[];shuffled_seeds?:Arm[]}|null;
 native:{parent?:string;candidate?:string}|null;failed_gates:string[];identity_note:string;honesty:string};

const short=(s:string|null|undefined)=>s?s.slice(0,8)+'…':'none';
const f1=(v?:number)=>typeof v==='number'?v.toFixed(1):'–';
const mean=(a?:Arm[])=>a&&a.length?(a.reduce((s,x)=>s+x.cells_visited,0)/a.length).toFixed(1):'–';

/**
 * Diagnostics: what the DETERMINISTIC pocket learner knows (running averages over
 * its own outcomes, live) versus what the NEURAL model (RAWRPHOS) has measurably
 * learned in the latest controlled experiment. Two separate systems, two ids.
 */
export default function ZerefKnowledgeDiagnostics({loop,beastId}:{loop:Loop;beastId:string}){
 const [st,setSt]=useState<Status|null>(null),[err,setErr]=useState(false);
 useEffect(()=>{let alive=true;fetch('/spark/zeref-learning/status.json',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(j=>{if(alive){if(j)setSt(j);else setErr(true);}}).catch(()=>alive&&setErr(true));return()=>{alive=false;};},[]);
 const e=st?.eval;
 return <div className={styles.card} data-zeref-knowledge data-neural-status={st?.status||'unknown'}>
  <h3>What Zeref knows · diagnostics</h3>
  <p className={styles.small}><b>Pocket learner</b> ({beastId}, deterministic rules, live): {loop?<>{loop.cells_visited}/{loop.cells_total} patches explored · {loop.known_rifts??'?'} rifts learned by bumping · {loop.moves_succeeded} moves ok / {loop.moves_blocked} blocked{loop.favorite_spot?<> · favourite: {loop.favorite_spot}</>:null}</>:'no loop data yet'}. Simple running averages over its own outcomes; this is what moves him in the habitat.</p>
  {st?<p className={styles.small} data-neural-accepted={String(st.accepted)}><b>Neural model</b> (RAWRPHOS, {st.qbeast_id}, Experiment {st.experiment}): {st.status}. Parent {short(st.parent_sha256)}{st.candidate_sha256?<> → candidate {short(st.candidate_sha256)}</>:null}.
   {e?<> On {e.layouts} pocket layouts it never trained on, mean patches explored: random {f1(e.random?.cells_visited)}, hand-coded pocket learner {f1(e.pocket_learner?.cells_visited)}, greedy frontier {f1(e.greedy_frontier?.cells_visited)}, parent model {f1(e.parent?.cells_visited)}, trained model {mean(e.candidate_seeds)} (no-memory ablation {mean(e.no_memory_seeds)}, shuffled-label control {mean(e.shuffled_seeds)}).</>:null}
   {st.failed_gates?.length?<> Failed gates: {st.failed_gates.map(g=>g.replace(/^G\d+_/,'').replace(/_/g,' ')).join('; ')}.</>:null}
   {st.run_url?<> <a href={st.run_url} rel="noreferrer" target="_blank">Evidence run</a>.</>:null}</p>
   :<p className={styles.small}>{err?'Neural experiment status unavailable; nothing is shown rather than an invented result.':'Loading neural model status…'}</p>}
  {st?<p className={styles.small}>{st.identity_note} {st.honesty}</p>:null}
 </div>;
}
