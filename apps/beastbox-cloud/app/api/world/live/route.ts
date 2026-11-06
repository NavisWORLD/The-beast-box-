import {buildWorldLive,branchRelPath,tipRelPath,parseTipSha,pickFresherSpark,sparkNeedsTipReread,WORLD_LIVE_PATHS} from '@/lib/zeref/world-live.mjs';
import {genesisState,DIARY_SCHEMA} from '@/lib/zeref/zeref-diary.mjs';
import PIN from '@/lib/rawrphos-public-pin.json';

// Always computed per request: no ISR/route cache, so the first request after idle can never serve an old payload.
export const dynamic='force-dynamic';
// Mutable branch URLs (string literals keep the contract test honest). GitHub raw CDN uses max-age=300, so a
// branch tip can look frozen for up to ~5 minutes even while the Actions loop is writing new ticks.
const RAW='https://raw.githubusercontent.com/NavisWORLD/The-beast-box-/';
const API='https://api.github.com/repos/NavisWORLD/The-beast-box-/';
const SRC={
 spark:RAW+'zeref-spark/zeref/latest.json',
 liveTick:RAW+'zeref-live-tick/live/latest.json',
 liveHead:RAW+'zeref-live-tick/live/head.json',
 diary:RAW+'zeref-diary/zeref/latest.json'
};
const NO_CACHE={cache:'no-store' as const,headers:{'Cache-Control':'no-cache','Pragma':'no-cache'},signal:AbortSignal.timeout(5000)};
async function get(url:string){
 try{const r=await fetch(url,NO_CACHE);return r.ok?await r.json():null;}catch{return null;}
}
/** Resolve the real tip sha and read the immutable raw URL (no secrets, no invented ticks). */
async function tipJson(branch:string,file:string){
 const tip=await get(API+'commits/'+branch+'?per_page=1');
 const sha=parseTipSha(tip);if(!sha)return null;
 const rel=tipRelPath(sha,file);if(!rel)return null;
 return get(RAW+rel);
}
function diaryView(diaryRaw:any){
 return diaryRaw&&diaryRaw.schema===DIARY_SCHEMA&&diaryRaw.identity?.beast_id===genesisState().identity.beast_id&&Number.isInteger(diaryRaw.tick)
  ?{ok:true,tick:diaryRaw.tick,last_tick_at:diaryRaw.last_tick_at}:null;
}
/**
 * One public, read-only status of every loop that feeds the world (Rigetti SIMULATED spark, per-second SIMULATED tick, RECORDED diary,
 * pinned RAWRPHØS brain). Numbers and labels only: no credentials, no private signals, no raw audio. A branch that cannot be read is
 * reported DOWN, never replaced by invented values.
 *
 * Stall recovery (2026-11-06): if the spark looks older than one interval after the branch read, re-fetch via the immutable
 * commit-sha raw URL. That bypasses the ~300 s raw.githubusercontent.com CDN hold without synthesising missed ticks.
 * STALE/DOWN links always carry a `stall` receipt (age + cause) so the freeze is never silent.
 */
export async function GET(){
 const nowMs=Date.now();
 const [spark0,liveTick0,liveHead0,diaryRaw0]=await Promise.all([get(SRC.spark),get(SRC.liveTick),get(SRC.liveHead),get(SRC.diary)]);
 let spark=spark0,liveTick=liveTick0,liveHead=liveHead0;
 if(sparkNeedsTipReread(spark,nowMs)){
  const fresh=await tipJson(WORLD_LIVE_PATHS.spark.branch,WORLD_LIVE_PATHS.spark.file);
  spark=pickFresherSpark(spark,fresh,nowMs);
 }
 const headAge=liveHead0&&Number.isFinite(liveHead0.at_ms)?(nowMs-liveHead0.at_ms)/1000:null;
 if(headAge===null||headAge>600){
  const [freshLive,freshHead]=await Promise.all([
   tipJson(WORLD_LIVE_PATHS.liveTick.branch,WORLD_LIVE_PATHS.liveTick.file),
   tipJson(WORLD_LIVE_PATHS.liveHead.branch,WORLD_LIVE_PATHS.liveHead.file)
  ]);
  if(freshLive)liveTick=freshLive;
  if(freshHead&&Number.isFinite(freshHead.at_ms)&&(headAge===null||freshHead.at_ms>=(liveHead0?.at_ms??0)))liveHead=freshHead;
 }
 const diary=diaryView(diaryRaw0);
 const doc=buildWorldLive({spark,liveTick,liveHead,diary,pin:PIN,nowMs});
 if(doc.stalls){
  console.warn('[world-live] stall',JSON.stringify(doc.stalls));
 }
 // Keep branchRelPath referenced so the helper stays wired to the same relative paths the contract names.
 void branchRelPath(WORLD_LIVE_PATHS.spark.branch,WORLD_LIVE_PATHS.spark.file);
 return Response.json({ok:true,...doc},{headers:{'Cache-Control':'no-store, max-age=0'}});
}
