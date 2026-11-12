// Public-safe slices of already-public sources for the liveness document.
// Numbers and labels only: no diary thoughts, no transcripts, no secrets,
// no guest data. A missing source stays null / unpublished — never invented.
const clip=(s,n)=>{s=String(s??'');return s.length>n?s.slice(0,n):s;};
const intOrNull=v=>Number.isInteger(v)?v:null;
const numOrNull=v=>{const n=Number(v);return Number.isFinite(n)?n:null;};
const MOOD_RE=/^[a-z][a-z0-9_-]{0,31}$/i;
const RUN_URL_RE=/^https:\/\/github\.com\/NavisWORLD\/The-beast-box-\/actions\/runs\/\d+\/?$/;
const FIRST_LINE=s=>String(s||'').split(/\r?\n/)[0].trim();

/** Latest hash-chained diary mood (the diary publishes mood, not a separate tone). */
export function publicDiaryMood(diary){
 const recent=Array.isArray(diary?.recent)?diary.recent:[];
 for(const e of recent){
  if(typeof e?.mood==='string'&&MOOD_RE.test(e.mood.trim())){
   return {mood:e.mood.trim().toLowerCase(),tick:intOrNull(e.tick),source:'zeref-diary recent entry',label:'RECORDED'};
  }
 }
 if(typeof diary?.mood==='string'&&MOOD_RE.test(diary.mood.trim())){
  return {mood:diary.mood.trim().toLowerCase(),tick:intOrNull(diary.tick),source:'zeref-diary latest.json',label:'RECORDED'};
 }
 return null;
}

/** Diary learning stats already on the public diary branch. Drops thought/text/prefs. */
export function publicDiaryLearning(diary){
 const L=diary?.learning;
 if(!L||typeof L!=='object'||Array.isArray(L))return null;
 return {
  cells_visited:intOrNull(L.cells_visited),
  cells_total:intOrNull(L.cells_total),
  known_rifts:intOrNull(L.known_rifts),
  moves_succeeded:intOrNull(L.moves_succeeded),
  moves_blocked:intOrNull(L.moves_blocked),
  blocked_rate:numOrNull(L.blocked_rate),
  decisions:intOrNull(L.decisions),
  favorite_spot:typeof L.favorite_spot==='string'?clip(L.favorite_spot,40):null,
  label:typeof L.label==='string'?clip(L.label,160):'learned behaviour from its own experience, not consciousness',
  source:'zeref-diary branch (public latest.json learning stats; thought text is not republished)',
 };
}

/** Last published promotion from the public pin + optional public git metadata. */
export function publicPromotion(pin,pinCommit){
 const p=pin?.promotion&&typeof pin.promotion==='object'?pin.promotion:{};
 const at=typeof pinCommit?.date==='string'?pinCommit.date:null;
 const run=typeof p.workflow_run==='string'&&RUN_URL_RE.test(p.workflow_run)?p.workflow_run:null;
 return {
  release_tag:typeof p.release_tag==='string'?clip(p.release_tag,80):null,
  chat_not_worse:p.chat_not_worse===true?true:p.chat_not_worse===false?false:null,
  workflow_run:run,
  promoted_at:at,
  promoted_at_source:at?'latest commit on apps/beastbox-cloud/lib/rawrphos-public-pin.json':null,
  pin_commit:typeof pinCommit?.sha==='string'?pinCommit.sha.slice(0,12):null,
  pin_commit_message:typeof pinCommit?.message==='string'?clip(FIRST_LINE(pinCommit.message),140):null,
  step:intOrNull(pin?.training_steps),
  label:'PINNED',
  source:'reviewed public pin + public git history of the pin file',
 };
}

/** Published promotion bars (zeref-gate-v2 + chat_not_worse on the pin). G1–G10 unchanged. */
export function publicGate(pin){
 const g=pin?.gate_v2&&typeof pin.gate_v2==='object'?pin.gate_v2:null;
 const p=pin?.promotion&&typeof pin.promotion==='object'?pin.promotion:{};
 if(!g&&p.chat_not_worse==null){
  return {status:'DOWN',reason:'pin has no gate_v2 or chat_not_worse',label:'RECORDED',source:'lib/rawrphos-public-pin.json',
   note:'G1–G10 unchanged.'};
 }
 return {
  schema:typeof g?.schema==='string'?clip(g.schema,40):null,
  chat_not_worse:p.chat_not_worse===true?true:p.chat_not_worse===false?false:null,
  candidate_leaks:intOrNull(p.candidate_leaks),
  set_a_pin_nll:numOrNull(g?.set_a_pin_nll),
  set_b_pin_nll:numOrNull(g?.set_b_pin_nll),
  result:'published on the public pin (zeref-gate-v2 bars + chat_not_worse)',
  label:'RECORDED',
  source:'lib/rawrphos-public-pin.json',
  note:'G1–G10 unchanged. fair_gate is an owner-feed candidate field, not this promotion bar.',
 };
}

/** fair_gate is not published as a global live field; do not invent a result. */
export function publicFairGate(){
 return {
  status:'no public global result',
  note:'fair_gate is recorded on owner-feed candidates only and is not published as a global live field. Guest records stay training_eligible:false. The last published promotion gate is zeref-gate-v2 + chat_not_worse on the public pin. G1–G10 unchanged.',
  label:'unpublished as a global live field',
 };
}

/**
 * 12D lived state. Only a real public-safe vector passed in is shown.
 * Historical traces and the owner-only sensorium (which strips state12)
 * are not used as a ticking public live vector.
 */
export function publicLivedState(snapshot){
 const vec=Array.isArray(snapshot?.state12)?snapshot.state12:Array.isArray(snapshot?.dyn12)?snapshot.dyn12:null;
 if(vec&&vec.length===12&&vec.every(n=>Number.isFinite(Number(n)))){
  const rounded=vec.map(n=>Math.round(Number(n)*1000)/1000);
  return {
   state12:rounded,dyn12:rounded,status:'published',
   label:typeof snapshot.label==='string'?clip(snapshot.label,80):'RECORDED',
   source:typeof snapshot.source==='string'?clip(snapshot.source,160):'public-safe 12-D snapshot',
  };
 }
 return {
  state12:null,dyn12:null,status:'unpublished',
  reason:'No public live 12-D snapshot is exported. The owner sensorium strips state12; committed traces are historical, not a ticking public vector. This surface will not invent one.',
  label:'unpublished on this public surface',
 };
}

/** Public Actions status for the 006 learning heartbeat. Cycle/step only if the listing itself carries them. */
export function publicTraining(run,pin){
 const pinStep=intOrNull(pin?.training_steps);
 if(!run||typeof run!=='object'){
  return {state:'DOWN',reason:'training workflow status unreachable',pin_step:pinStep,
   source:'GitHub Actions workflow zeref-continuous-learning-006.yml (public runs)',
   label:'RECORDED (Actions run status)'};
 }
 const status=run.status==='in_progress'?'in_progress':run.status==='queued'?'queued':run.status==='completed'?'completed':(typeof run.status==='string'?clip(run.status,32):'unknown');
 const url=typeof run.html_url==='string'&&RUN_URL_RE.test(run.html_url)?run.html_url:null;
 return {
  status,
  conclusion:typeof run.conclusion==='string'?clip(run.conclusion,32):null,
  event:typeof run.event==='string'?clip(run.event,32):null,
  name:typeof run.name==='string'?clip(run.name,120):null,
  html_url:url,
  started_at:typeof (run.run_started_at||run.created_at)==='string'?(run.run_started_at||run.created_at):null,
  updated_at:typeof run.updated_at==='string'?run.updated_at:null,
  job:typeof run.job_name==='string'?clip(run.job_name,80):null,
  cycle:intOrNull(run.cycle),
  step:intOrNull(run.training_step),
  pin_step:pinStep,
  source:'GitHub Actions workflow zeref-continuous-learning-006.yml (public runs)',
  label:'RECORDED (Actions run status)',
  note:(intOrNull(run.cycle)==null&&intOrNull(run.training_step)==null)
   ?'cycle and step are not on the public run listing for this run; they stay null rather than being invented'
   :null,
 };
}
