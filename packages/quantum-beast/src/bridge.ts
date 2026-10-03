import {hashObject,verifySnapshot,unsignedPayload,exactKeys,hex,requireCondition,validatePayload,MAX_EVENTS,type Snapshot,type EventKind,type EventPayload,type VerifyOptions} from './verifier';
import {recall} from './memory_adapter';
import {exportGba} from './gba_export';
import {checkHostPermission,type HostGrant} from './policy_gate';
export type Proposal={schema:'qbeast-proposal-v1';creature_id:string;expected_head:string;kind:EventKind;payload:EventPayload;proposal_id:string;status:'pending_host_approval'};
export type {HostGrant} from './policy_gate';
/** Host-only entry point. Deliberately absent from all model tool manifests. */
export async function approveProposal(snapshot:Snapshot,proposal:Proposal,grant:HostGrant,options:VerifyOptions={}):Promise<Snapshot>{
 await verifySnapshot(snapshot,options);
 exactKeys(proposal,['schema','creature_id','expected_head','kind','payload','proposal_id','status']);
 requireCondition(proposal.schema==='qbeast-proposal-v1'&&proposal.status==='pending_host_approval','Malformed proposal');hex(proposal.expected_head);hex(proposal.proposal_id);validatePayload(proposal.kind,proposal.payload);
 const {proposal_id:_id,status:_status,...body}=proposal;
 requireCondition(await hashObject(body)===proposal.proposal_id,'Tampered proposal');
 requireCondition(proposal.creature_id===snapshot.profile.id&&proposal.expected_head===snapshot.lineage_head,'Wrong creature or stale proposal');
 checkHostPermission(grant,proposal.kind);
 requireCondition(snapshot.events.length<MAX_EVENTS,'Lineage full; no silent history deletion');
 const event={generation:snapshot.generation+1,parent:snapshot.lineage_head,proposal_id:proposal.proposal_id,kind:proposal.kind,payload:structuredClone(proposal.payload)};
 const hash=await hashObject({domain:'event',...event});
 const next=structuredClone(snapshot);delete next.signature;next.events.push({...event,hash});next.generation++;next.lineage_head=hash;next.digest=await hashObject(unsignedPayload(next));return next;
}
export class BeastBridge{
 private constructor(private current:Snapshot,private options:VerifyOptions){}
 static async load(snapshot:Snapshot,options:VerifyOptions={}){await verifySnapshot(snapshot,options);return new BeastBridge(structuredClone(snapshot),{...options});}
 snapshot(){return structuredClone(this.current);}
 get_profile(){return structuredClone(this.current.profile);}
 get_state(){return {creature_id:this.current.profile.id,public_state:structuredClone(this.current.public_state),...this.current.progress,generation:this.current.generation,lineage_head:this.current.lineage_head};}
 get_lineage_head(){return this.current.lineage_head;}
 recall(query:string,limit=4){return recall(this.current,query,limit);}
 verify(){return verifySnapshot(this.current,this.options);}
 export_gba(){return exportGba(this.current,this.options);}
 private async propose(kind:EventKind,payload:EventPayload):Promise<Proposal>{
  validatePayload(kind,payload);const body={schema:'qbeast-proposal-v1' as const,creature_id:this.current.profile.id,expected_head:this.current.lineage_head,kind,payload:structuredClone(payload)};
  return {...body,proposal_id:await hashObject(body),status:'pending_host_approval'};
 }
 propose_message(text:string){return this.propose('message',{text});}
 async propose_action(action:{action:'hover'|'orbit'|'perch'|'rest'}){exactKeys(action,['action']);return this.propose('action',action);}
 async record_event(event:{summary:string;source_ref?:string}){exactKeys(event,['summary'],['source_ref']);return this.propose('memory',{summary:event.summary,source_ref:event.source_ref??'model-proposal'});}
}
