import {buildWorldLive} from '@/lib/zeref/world-live.mjs';
import {genesisState,DIARY_SCHEMA} from '@/lib/zeref/zeref-diary.mjs';
import PIN from '@/lib/rawrphos-public-pin.json';

// Always computed per request: no ISR/route cache, so the first request after idle can never serve an old payload.
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
/**
 * One public, read-only status of every loop that feeds the world (Rigetti SIMULATED spark, per-second SIMULATED tick, RECORDED diary,
 * pinned RAWRPHØS brain). Numbers and labels only: no credentials, no private signals, no raw audio. A branch that cannot be read is
 * reported DOWN, never replaced by invented values.
 */
export async function GET(){
 const [spark,liveTick,liveHead,diaryRaw]=await Promise.all([get(SRC.spark),get(SRC.liveTick),get(SRC.liveHead),get(SRC.diary)]);
 const diary=diaryRaw&&diaryRaw.schema===DIARY_SCHEMA&&diaryRaw.identity?.beast_id===genesisState().identity.beast_id&&Number.isInteger(diaryRaw.tick)
  ?{ok:true,tick:diaryRaw.tick,last_tick_at:diaryRaw.last_tick_at}:null;
 const doc=buildWorldLive({spark,liveTick,liveHead,diary,pin:PIN,nowMs:Date.now()});
 return Response.json({ok:true,...doc},{headers:{'Cache-Control':'no-store, max-age=0'}});
}
