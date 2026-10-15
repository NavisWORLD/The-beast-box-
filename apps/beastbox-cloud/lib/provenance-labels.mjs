/**
 * PROVENANCE LABELS — one shared Friendly → Advanced vocabulary for seed,
 * memory, and growth displays.
 *
 * Display-only: these formatters never change evidence, never invent job IDs
 * or receipts, and never relabel a simulator as hardware. Kind strings align
 * with lib/zeref/experience-record.mjs ORIGINS, the public cosmos-profile
 * allowlist, and lib/zeref/zeref-diary.mjs growth_source kinds.
 *
 * Pure module: no DOM, storage, clock, or network.
 */

/** Closed kind vocabulary. Simulator kinds always render with "(simulated)". */
export const PROVENANCE_KINDS=Object.freeze([
 'recorded-quantum-genome',
 'classical-seed',
 'artist-drawn',
 'recorded-ibm-hardware',
 'rigetti-qvm-simulated',
 'deterministic-fallback',
 'local-classical-qvm-inspired',
 'unsigned-local',
]);

const KIND_FRIENDLY=Object.freeze({
 'recorded-quantum-genome':'Recorded quantum count sheet',
 'classical-seed':'Classical seed',
 'artist-drawn':'Artist-drawn (no quantum seed)',
 'recorded-ibm-hardware':'Recorded IBM hardware counts (historical)',
 'rigetti-qvm-simulated':'Rigetti simulator (simulated)',
 'deterministic-fallback':'Honest fallback step (no simulator job)',
 'local-classical-qvm-inspired':'Classical on-device pattern',
 'unsigned-local':'Local-only preview',
});

/** Friendly teacher names. Mirrors the talk-panel TEACHER_LABEL contract. */
export const TEACHER_FRIENDLY=Object.freeze({
 'guest-rawrphos':'Beast Box free host',
 'local-ollama':'My local Ollama',
 'hf-byok':'My Hugging Face key',
 'brain-bay':'Brain Bay',
});

/** Technical route identities. Mirrors lib/companion/beast-talk.mjs ROUTE_INFO. */
export const ROUTE_TECHNICAL=Object.freeze({
 'guest-rawrphos':{label:'RAWRPHØS guest',provider:'rawrphos-local'},
 'local-ollama':{label:'Local Ollama',provider:'ollama-host'},
 'hf-byok':{label:'Hugging Face (own key)',provider:'huggingface-byok'},
 'brain-bay':{label:'Brain Bay',provider:'brain-bay-status'},
});

export function friendlyKind(kind){
 return KIND_FRIENDLY[kind]||'Unknown source';
}

/**
 * Birth/genesis receipt. `input` accepts a saved beast, a cosmos profile, or
 * a bare receipt object. Missing fields stay missing — never synthesized.
 */
export function formatGenesisReceipt(input={}){
 const receipt=input?.provenance||input?.genesis||input||{};
 const kind=receipt.kind||(input?.genome?.quantum?.backend?'recorded-quantum-genome':null)||(input?.genome?.seed?'classical-seed':null)||'unsigned-local';
 const backend=receipt.backend||input?.genome?.quantum?.backend||null;
 const jobId=receipt.job_id||input?.genome?.quantum?.job_id||null;
 const countsSha=receipt.counts_sha256||input?.genome?.quantum?.counts_sha256||null;
 const seed=receipt.seed||input?.genome?.seed||input?.seed||null;
 const qbeastId=input?.qbeast?.profile?.id||input?.id||receipt.qbeast_id||null;
 const advanced={kind,backend,job_id:jobId,counts_sha256:countsSha,seed,qbeast_id:qbeastId};
 let friendly;
 if(kind==='artist-drawn')friendly='This look was drawn by an artist. It has no quantum seed, and that is fine — it is still fully yours to play with.';
 else if(kind==='recorded-quantum-genome')friendly=`This Beast's look was rolled from a fixed recipe tied to a recorded quantum count sheet${backend?` (${backend})`:''} — not from live hardware today.`;
 else if(kind==='recorded-ibm-hardware')friendly='This temperament leans on recorded IBM hardware counts from the archive. The numbers are replayed, never re-measured.';
 else if(kind==='classical-seed')friendly='This Beast started from a classical seed: fully deterministic, fully replayable, no quantum hardware involved.';
 else friendly='This is a local preview. Give it a seed or a recorded sheet to make its look permanent.';
 return {friendly,advanced};
}

/**
 * Later growth events. Accepts a diary `growth_source`, a private-cosmos
 * growth record, or a bare object. Simulator vs fallback is explicit.
 */
export function formatGrowthReceipt(growth={}){
 const kind=growth.kind||growth.status||'deterministic-fallback';
 const jobId=growth.job_id||null;
 const shots=Number.isFinite(Number(growth.shots))?Number(growth.shots):null;
 const countsSha=growth.counts_sha256||null;
 const error=growth.error||null;
 const simulated=kind==='rigetti-qvm-simulated'?true:kind==='deterministic-fallback'?false:Boolean(growth.simulated);
 const advanced={kind,simulated,provider:growth.provider||null,target:growth.target||null,job_id:jobId,shots,counts_sha256:countsSha,error};
 let friendly;
 if(kind==='rigetti-qvm-simulated')friendly=`A small simulator job${jobId?` (job ${jobId})`:''} nudged mood and signals. Simulated counts, not hardware.`;
 else if(kind==='RIGETTI_QVM_REMOTE')friendly='A remote simulator receipt was validated and applied to cloud growth.';
 else if(kind==='QUEUED')friendly='Growth is queued. No simulator job is claimed until a real receipt arrives.';
 else if(kind==='OFF')friendly='Cloud growth is off. This Beast lives on this device only.';
 else if(kind==='BLOCKED_EXTERNAL')friendly=`The simulator could not be reached${error?`: ${error}`:''}. Nothing was invented; the Beast kept its honest fallback step.`;
 else friendly=`An honest fallback step${error?` (${error})`:''}: the diary advanced with local rules and said so.`;
 return {friendly,advanced};
}

/**
 * Unified teacher attribution: friendly name for the header, technical model
 * identity for the advanced line. The route is a preference until a reply is
 * verified; pass verifiedAt only after a real verified response.
 * @param {{route?:string,model?:string|null,verifiedAt?:string|null}} args
 */
export function formatTeacherAttribution({route='guest-rawrphos',model=null,verifiedAt=null}={}){
 const friendlyName=TEACHER_FRIENDLY[route]||'Chosen teacher';
 const technical=ROUTE_TECHNICAL[route]||{label:String(route),provider:String(route)};
 const advanced={route,teacher:technical.label,model:model||null,provider:technical.provider,verified_at:verifiedAt||null};
 const friendly=verifiedAt
  ?`${friendlyName} voiced this reply${model?` (${model})`:''}. Your Beast's name and story stay the same.`
  :`${friendlyName} will voice the next reply. The teacher is who speaks; your Beast keeps its own identity.`;
 return {friendly,advanced};
}
