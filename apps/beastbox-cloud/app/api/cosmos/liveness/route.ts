import {storageConfig} from '@/lib/cosmos/azure-blob.mjs';
import {countZerefCloud,readZerefModel,shapeLiveness} from '@/lib/cosmos/forever-store.mjs';
import {buildWorldLive} from '@/lib/zeref/world-live.mjs';
import {DIARY_SCHEMA,entryHash,genesisState} from '@/lib/zeref/zeref-diary.mjs';
import PIN from '@/lib/rawrphos-public-pin.json';

// FOREVER CONNECTION — public liveness (LIFE-LIVE step 4, completing the W6
// shape /api/world/live started). One read-only surface over the same
// sources the stateful door reads: the reviewed pin, his RECORDED diary
// (tick / XP / bond / stage, hash-verified recent entries), the bridge's own
// public /healthz, his Azure folder (model record, approved lessons and
// experiences counts), and the world-live life-signal channels (spark and
// per-second tick, SIMULATED as labelled there). Computed per request;
// a source that cannot be read is reported DOWN, never replaced by
// invented values. Numbers and labels only: no credentials, no guest text,
// no raw signals.
export const runtime='nodejs';
export const dynamic='force-dynamic';
const RAW='https://raw.githubusercontent.com/NavisWORLD/The-beast-box-/';
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
export async function GET(){
 const [spark,liveTick,liveHead,diaryRaw,bridge]=await Promise.all([
  get(SRC.spark),get(SRC.liveTick),get(SRC.liveHead),get(SRC.diary),bridgeHealth()]);
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
 const doc=shapeLiveness({now:new Date().toISOString(),pin:PIN,diary,diaryVerified:verified,bridge,azure,world});
 return Response.json(doc,{headers:{'Cache-Control':'no-store, max-age=0'}});
}
