import {storageConfig} from '@/lib/cosmos/azure-blob.mjs';
import {countZerefCloud,readZerefModel,shapeLiveness} from '@/lib/cosmos/forever-store.mjs';
import {publicStatusCorsPreflight,withPublicStatusCors} from '@/lib/public-status-cors.mjs';
import {buildWorldLive} from '@/lib/zeref/world-live.mjs';
import {DIARY_SCHEMA,entryHash,genesisState} from '@/lib/zeref/zeref-diary.mjs';
import PIN from '@/lib/rawrphos-public-pin.json';

// FOREVER CONNECTION — public liveness (LIFE-LIVE step 4, completing the W6
// shape /api/world/live started). One read-only surface over the same
// sources the stateful door reads: the reviewed pin, his RECORDED diary
// (tick / XP / bond / stage / mood / learning stats, hash-verified recent
// entries), the bridge's own public /healthz, his Azure folder (model
// record, approved lessons and experiences counts), the world-live
// life-signal channels (spark and per-second tick, SIMULATED as labelled
// there), the public pin's git history (last promotion time), and the
// public Actions listing for the 006 learning heartbeat. Computed per
// request; a source that cannot be read is reported DOWN, never replaced
// by invented values. Numbers and labels only: no credentials, no guest
// text, no diary thoughts, no raw private signals.
//
// CORS: GET/HEAD/OPTIONS from https://navisworld.github.io only, so the
// Pages profile card can read this document. No wildcard, no credentials,
// no POST. Other origins stay same-origin.
export const runtime='nodejs';
export const dynamic='force-dynamic';
const RAW='https://raw.githubusercontent.com/NavisWORLD/The-beast-box-/';
const GH='https://api.github.com/repos/NavisWORLD/The-beast-box-';
const GH_HEADERS={Accept:'application/vnd.github+json','User-Agent':'beastbox-liveness'};
const SRC={
 spark:RAW+'zeref-spark/zeref/latest.json',
 liveTick:RAW+'zeref-live-tick/live/latest.json',
 liveHead:RAW+'zeref-live-tick/live/head.json',
 diary:RAW+'zeref-diary/zeref/latest.json'
};
async function get(url:string){
 try{const r=await fetch(url,{cache:'no-store',signal:AbortSignal.timeout(5000)});return r.ok?await r.json():null;}catch{return null;}
}
async function bridgeHealth(){
 const root=process.env.BEASTBOX_CLOUD_BRIDGE_URL;
 if(!root)return null;
 try{
  const r=await fetch(new URL('/healthz',root),{cache:'no-store',redirect:'error',signal:AbortSignal.timeout(4000)});
  if(!r.ok)return null;
  const d:any=await r.json();
  return d&&typeof d==='object'&&!Array.isArray(d)?d:null;
 }catch{return null;}
}

// In-isolate caches so a burst of card polls does not burn the unauthenticated
// GitHub API budget. Cached values are real previous reads, never invented.
type Cache<T>={at:number,value:T|null};
let pinCommitCache:Cache<any>={at:0,value:null};
let trainingCache:Cache<any>={at:0,value:null};
const PIN_COMMIT_TTL=5*60*1000;
const TRAINING_TTL=60*1000;

async function getPinCommit(){
 const now=Date.now();
 if(pinCommitCache.value&&now-pinCommitCache.at<PIN_COMMIT_TTL)return pinCommitCache.value;
 try{
  const r=await fetch(GH+'/commits?path=apps/beastbox-cloud/lib/rawrphos-public-pin.json&per_page=1',
   {headers:GH_HEADERS,cache:'no-store',signal:AbortSignal.timeout(5000)});
  if(!r.ok)return pinCommitCache.value;
  const arr:any=await r.json();
  const c=Array.isArray(arr)?arr[0]:null;
  const value=c?{sha:c.sha,date:c.commit?.committer?.date||c.commit?.author?.date,message:c.commit?.message}:null;
  pinCommitCache={at:now,value};
  return value;
 }catch{return pinCommitCache.value;}
}

async function getTraining(){
 const now=Date.now();
 if(trainingCache.value&&now-trainingCache.at<TRAINING_TTL)return trainingCache.value;
 try{
  const r=await fetch(GH+'/actions/workflows/zeref-continuous-learning-006.yml/runs?per_page=10',
   {headers:GH_HEADERS,cache:'no-store',signal:AbortSignal.timeout(5000)});
  if(!r.ok)return trainingCache.value;
  const d:any=await r.json();
  const runs=Array.isArray(d?.workflow_runs)?d.workflow_runs:[];
  const live=runs.find((x:any)=>x&&(x.status==='in_progress'||x.status==='queued'))||runs[0]||null;
  let job_name:string|null=null;
  if(live&&(live.status==='in_progress'||live.status==='queued')){
   try{
    const jr=await fetch(GH+'/actions/runs/'+live.id+'/jobs?per_page=10',
     {headers:GH_HEADERS,cache:'no-store',signal:AbortSignal.timeout(5000)});
    if(jr.ok){
     const jd:any=await jr.json();
     const jobs=Array.isArray(jd?.jobs)?jd.jobs:[];
     const job=jobs.find((j:any)=>j&&(j.status==='in_progress'||j.status==='queued'))||jobs[0];
     if(job&&typeof job.name==='string')job_name=job.name;
    }
   }catch{/* job name stays null */}
  }
  const value=live?{status:live.status,conclusion:live.conclusion,event:live.event,name:live.name,
   html_url:live.html_url,run_started_at:live.run_started_at,created_at:live.created_at,
   updated_at:live.updated_at,job_name}:null;
  trainingCache={at:now,value};
  return value;
 }catch{return trainingCache.value;}
}

export function OPTIONS(request:Request){
 return publicStatusCorsPreflight(request.headers.get('origin'));
}

export async function GET(request:Request){
 const [spark,liveTick,liveHead,diaryRaw,bridge,pinCommit,training]=await Promise.all([
  get(SRC.spark),get(SRC.liveTick),get(SRC.liveHead),get(SRC.diary),bridgeHealth(),getPinCommit(),getTraining()]);
 let diary:any=null,verified=false;
 if(diaryRaw&&diaryRaw.schema===DIARY_SCHEMA&&diaryRaw.identity?.beast_id===genesisState().identity.beast_id&&Number.isInteger(diaryRaw.tick)){
  diary=diaryRaw;
  const recent=Array.isArray(diaryRaw.recent)?diaryRaw.recent.slice(0,12):[];
  verified=recent.length>0&&recent.every((e:any)=>typeof e?.hash==='string'&&entryHash(e)===e.hash);
 }
 const world=buildWorldLive({spark,liveTick,liveHead,
  diary:diary?{ok:true,tick:diary.tick,last_tick_at:diary.last_tick_at}:null,pin:PIN,nowMs:Date.now()});
 let azure:any=null;
 const cfg=storageConfig();
 if(cfg){
  azure={configured:true,model:null,counts:null};
  try{azure.model=await readZerefModel(cfg);}catch{/* reported as null */}
  try{azure.counts=await countZerefCloud(cfg);}catch{/* reported as null */}
 }
 const doc=shapeLiveness({now:new Date().toISOString(),pin:PIN,diary,diaryVerified:verified,bridge,azure,world,pinCommit,training});
 const res=Response.json(doc,{headers:{'Cache-Control':'no-store, max-age=0'}});
 return withPublicStatusCors(res,request.headers.get('origin'));
}
