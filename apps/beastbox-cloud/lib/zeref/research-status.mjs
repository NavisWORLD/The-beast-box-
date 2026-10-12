const HASH=/^[0-9a-f]{64}$/;
const RUN=/^https:\/\/github\.com\/NavisWORLD\/The-beast-box-\/actions\/runs\/\d+$/;

/** Read an audited research snapshot without treating workflow success as approval. */
export function researchEvidence(raw){
 if(!raw||raw.schema!=='zeref-research-status/v2')return null;
 const approved=raw.latest_approved_research_parent;
 if(raw.training_identity?.qbeast_id!=='bb-deada969'||raw.display_identity?.qbeast_id!=='bb-7f9c2a03')return null;
 if(!approved||approved.status!=='APPROVED_RESEARCH_PARENT'||!HASH.test(approved.checkpoint_sha256)||!RUN.test(approved.run_url))return null;
 if(!Number.isInteger(approved.training_steps)||approved.training_steps<=0||approved.production_promoted!==false)return null;
 if(approved.optimizer_and_rng_present!==true||!HASH.test(approved.optimizer_training_state_sha256))return null;
 if(!approved.gate_results||!Object.values(approved.gate_results).length||Object.values(approved.gate_results).some(x=>x!==true))return null;
 if(!Array.isArray(raw.latest_research)||!Array.isArray(raw.preserved_history))return null;
 const rejected=[...raw.latest_research,...raw.preserved_history];
 if(rejected.some(x=>x.status!=='REJECTED'||x.eligible_as_parent!==false||x.production_promoted!==false||!RUN.test(x.run_url)))return null;
 const rejectedHashes=new Set(rejected.flatMap(x=>[x.checkpoint_candidate,x.candidate_sha256]).filter(x=>HASH.test(x)));
 if(rejectedHashes.has(approved.checkpoint_sha256))return null;
 if(raw.claims?.native_objective_progress_proven!==false||raw.display_identity.association_to_training_identity!=='UNVERIFIED')return null;
 return {approved,trials:raw.latest_research,history:raw.preserved_history,runtime:raw.production_runtime||null,
  trainingId:raw.training_identity.qbeast_id,displayId:raw.display_identity.qbeast_id,auditedAt:raw.audited_at};
}
