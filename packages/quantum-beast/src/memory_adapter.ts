import {boundedText,requireCondition,type Snapshot} from './verifier';
export function recall(snapshot:Snapshot,query:string,limit=4){
 boundedText(query,200,'query');requireCondition(Number.isInteger(limit)&&limit>=1&&limit<=8,'Recall limit must be 1–8');
 const terms=query.toLowerCase().match(/[\p{L}\p{N}]{3,}/gu)??[];
 const memories=snapshot.events.filter(e=>e.kind==='memory').slice(-64).map(e=>{
  const payload=e.payload as {summary:string;source_ref:string};
  return {summary:payload.summary,source_ref:payload.source_ref,event_hash:e.hash,generation:e.generation,creature_id:snapshot.profile.id,untrusted_content:true as const};
 });
 return memories.map(m=>({m,score:terms.reduce((n,t)=>n+(m.summary.toLowerCase().includes(t)?1:0),0)}))
  .filter(x=>terms.length===0||x.score>0).sort((a,b)=>b.score-a.score||b.m.generation-a.m.generation).slice(0,limit).map(x=>x.m);
}
