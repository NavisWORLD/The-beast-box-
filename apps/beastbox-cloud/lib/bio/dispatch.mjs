// Real IBM Bio Connection: server-side dispatch logic. The GitHub token is read from the server environment only
// (BEASTBOX_GITHUB_DISPATCH_TOKEN), is never returned and never sent to the browser. The caller (route.ts) enforces owner auth.
// Every limit here is checked BEFORE a dispatch; the workflow itself enforces the IBM 60 s plan reserve and holds the IBM secret.
import {createHash} from 'node:crypto';
import {validateBioPacket,packetHash} from './bio-packet.mjs';
export const BIO_REPO='NavisWORLD/The-beast-box-';
export const BIO_WORKFLOW='real-ibm-bio-connection.yml';
export const BIO_REF='main';
export const BIO_LIMITS=Object.freeze({
  cooldown_ms:15*60*1000,      // at least 15 minutes between dispatches
  max_runs_24h:6,              // never more than 6 dispatched runs in 24 hours
  burst_per_min:5,             // per server instance, any request
  max_body_bytes:4096,
});
export const sha256Sync=s=>createHash('sha256').update(s).digest('hex');
const ghHeaders=token=>({Authorization:'Bearer '+token,Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'beastbox-bio-connection'});
const redact=(s,token)=>String(s||'').replace(token||'\u0000','[token]').replace(/gh[pousr]_[A-Za-z0-9_]{10,}|github_pat_[A-Za-z0-9_]{10,}/g,'[token]').slice(0,160);
let burst={w:-1,n:0};
/** Per-instance burst limiter (a fixed one-minute window). `nowMs` is passed in so tests do not need the clock. */
export function burstLimit(nowMs,limit=BIO_LIMITS.burst_per_min){const w=Math.floor(nowMs/60000);if(burst.w!==w)burst={w,n:0};burst.n+=1;return burst.n<=limit;}
export function resetBurst(){burst={w:-1,n:0};}
/** Decide from recent runs (newest first, as GitHub returns them) whether a new dispatch is allowed. */
export function limitDecision(runs,nowMs,{sha12=null}={}){
  const list=Array.isArray(runs)?runs:[];
  if(sha12&&list.some(r=>String(r.display_title||r.name||'').includes(sha12)))return {ok:false,status:409,error:'This exact measurement was already dispatched. Take a new measurement.'};
  if(list.some(r=>r.status==='queued'||r.status==='in_progress'||r.status==='waiting'||r.status==='requested'||r.status==='pending'))return {ok:false,status:429,retry_after_s:300,error:'A Real IBM Bio Connection run is already in progress.'};
  const created=list.map(r=>Date.parse(r.created_at)).filter(Number.isFinite);
  const latest=created.length?Math.max(...created):0;
  if(latest&&nowMs-latest<BIO_LIMITS.cooldown_ms)return {ok:false,status:429,retry_after_s:Math.ceil((BIO_LIMITS.cooldown_ms-(nowMs-latest))/1000),error:'Cooling down between IBM runs to protect the plan time.'};
  if(created.filter(c=>nowMs-c<86400000).length>=BIO_LIMITS.max_runs_24h)return {ok:false,status:429,retry_after_s:3600,error:'Daily IBM run limit reached.'};
  return {ok:true};
}
/** Validate the browser's packet again on the server. Never trusts the client's hash or its claim of a valid pulse. */
export async function checkPacket(packet){
  const v=validateBioPacket(packet);
  if(!v.ok)return {ok:false,status:400,error:'Packet rejected: '+v.errors.slice(0,3).join('; ')};
  if(await packetHash(packet,sha256Sync)!==packet.packet_sha256)return {ok:false,status:400,error:'Packet hash does not match its numbers.'};
  return {ok:true,sha12:packet.packet_sha256.slice(0,12)};
}
async function gh(fetchImpl,token,path,init={}){
  const r=await fetchImpl('https://api.github.com'+path,{...init,headers:{...ghHeaders(token),...(init.headers||{})},signal:AbortSignal.timeout(10000),cache:'no-store'});
  return r;
}
export async function listRuns(fetchImpl,token,perPage=20){
  const r=await gh(fetchImpl,token,`/repos/${BIO_REPO}/actions/workflows/${BIO_WORKFLOW}/runs?event=workflow_dispatch&per_page=${perPage}`);
  if(!r.ok)throw new Error('GitHub runs list failed ('+r.status+')');
  const j=await r.json();return Array.isArray(j.workflow_runs)?j.workflow_runs:[];
}
/**
 * Dispatch. All inputs are validated; returns {status, body}. `deps` = {fetch, token, nowMs, sleep}.
 * Never includes the token in any return value.
 */
export async function dispatchBio(packet,deps){
  const {fetch:f,token,nowMs}=deps;
  if(!token)return {status:503,body:{ok:false,error:'GitHub dispatch is not configured on the server.',missing:['BEASTBOX_GITHUB_DISPATCH_TOKEN']}};
  if(!burstLimit(nowMs))return {status:429,body:{ok:false,error:'Too many requests. Wait a minute.',retry_after_s:60}};
  const pk=await checkPacket(packet);
  if(!pk.ok)return {status:pk.status,body:{ok:false,error:pk.error}};
  // the heartbeat must be a real, quality-gated pulse (the packet schema already enforces sqi >= 0.6)
  let runs;
  try{runs=await listRuns(f,token);}catch(e){return {status:502,body:{ok:false,error:redact(e.message,token)}};}
  const lim=limitDecision(runs,nowMs,{sha12:pk.sha12});
  if(!lim.ok)return {status:lim.status,body:{ok:false,error:lim.error,retry_after_s:lim.retry_after_s}};
  const body=JSON.stringify({ref:BIO_REF,inputs:{packet_sha12:pk.sha12,packet_json:JSON.stringify(packet)}});
  let r;try{r=await gh(f,token,`/repos/${BIO_REPO}/actions/workflows/${BIO_WORKFLOW}/dispatches`,{method:'POST',body,headers:{'Content-Type':'application/json'}});}catch(e){return {status:502,body:{ok:false,error:redact(e.message,token)}};}
  if(r.status!==204){let m='';try{m=(await r.json()).message;}catch{}return {status:r.status===404||r.status===403||r.status===401?502:502,body:{ok:false,error:'GitHub refused the dispatch ('+r.status+'). '+redact(m,token)}};}
  // dispatch returns no run id: look for the run whose title carries the packet hash
  let run=null;for(let i=0;i<4&&!run;i++){if(i)await deps.sleep(1500);try{run=(await listRuns(f,token,10)).find(x=>String(x.display_title||x.name||'').includes(pk.sha12))||null;}catch{}}
  return {status:200,body:{ok:true,dispatched:true,sha12:pk.sha12,packet_sha256:packet.packet_sha256,run_url:run?.html_url||`https://github.com/${BIO_REPO}/actions/workflows/${BIO_WORKFLOW}`,run_found:!!run,run_id:run?.id||null,
    labels:{heartbeat:'MEASURED',ibm_spark:'RECORDED only after the run finishes',rigetti:'SIMULATED'}}};
}
/** Status of the run for a packet hash (owner-only poll). Reads step names the workflow sets: "Result · IBM <state> · QVM <state>". */
export async function bioStatus(sha12,deps){
  const {fetch:f,token}=deps;
  if(!token)return {status:503,body:{ok:false,error:'GitHub dispatch is not configured on the server.',missing:['BEASTBOX_GITHUB_DISPATCH_TOKEN']}};
  if(!/^[a-f0-9]{12}$/.test(String(sha12)))return {status:400,body:{ok:false,error:'Invalid run reference.'}};
  let runs;try{runs=await listRuns(f,token,20);}catch(e){return {status:502,body:{ok:false,error:redact(e.message,token)}};}
  const run=runs.find(x=>String(x.display_title||x.name||'').includes(sha12));
  if(!run)return {status:200,body:{ok:true,found:false}};
  const out={ok:true,found:true,status:run.status,conclusion:run.conclusion,run_url:run.html_url,ibm:null,rigetti:null};
  if(run.status==='completed'||run.status==='in_progress'){
    try{const jr=await gh(f,token,`/repos/${BIO_REPO}/actions/runs/${run.id}/jobs`);if(jr.ok){const jobs=(await jr.json()).jobs||[];for(const j of jobs)for(const s of j.steps||[]){const m=/^Result · IBM ([a-z_]+) · QVM ([a-z_]+)$/.exec(s.name||'');if(m){out.ibm=m[1];out.rigetti=m[2];}}}}catch{}
  }
  return {status:200,body:out};
}
export {IBM_STATES,QVM_STATES} from './bio-states.mjs';
