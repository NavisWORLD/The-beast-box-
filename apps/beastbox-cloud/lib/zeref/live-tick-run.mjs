/**
 * Background per-second loop (orchestrator). I/O, clock and sleep are INJECTED so the loop is testable with a fake clock.
 * Per-second state advances in memory every second (a rolling hash chain over every second, including seconds missed
 * while a run handed off to the next: they are recomputed, never skipped). Snapshots are committed in BATCHES, not per second.
 * Separate from the recorded diary loop: it only READS the last recorded tick and never writes to the recorded diary.
 */
import {liveBase,liveSecond,advanceChain,CHAIN_GENESIS,liveDiaryLine} from './live-tick.mjs';
import {sha256Hex} from '../../public/spark/sha.mjs';
export const RUN_SCHEMA='beast-live-tick-run/v1';
/**
 * io: { readDiary():object|null  (state.json-shaped + recent[]), readHead():object|null, writeBatch({head,snapshot,entry}):void,
 *       commit(msg):Promise<boolean>, refresh():Promise<void> }
 * clock: { now():number(ms), sleep(ms):Promise<void> }
 */
export async function runLiveTickLoop({io,clock,runSeconds,batchSeconds=600,log=()=>{}}){
 const startMs=clock.now();const endMs=startMs+runSeconds*1000;
 let base=liveBase(io.readDiary());
 if(!base){log('no recorded tick available; nothing to simulate');return {ok:false,reason:'no-recorded-tick',batches:0};}
 const head=io.readHead();
 const key=b=>b.beast_id+'|'+b.tick+'|'+b.last_tick_at_ms;
 let chain,done; // done = last second already folded into `chain`
 if(head&&head.key===key(base)&&Number.isInteger(head.last_sec)){chain=head.chain;done=head.last_sec;}else{chain=CHAIN_GENESIS(base);done=-1;}
 let prevEntry=head?.entry_hash||'0'.repeat(64),batches=0,lastBatchMs=startMs;
 const flush=async(nowMs,why)=>{
  const sec=Math.floor((nowMs-base.last_tick_at_ms)/1000);
  const snap=liveSecond(base,base.last_tick_at_ms+Math.max(sec,0)*1000);
  const entryBody={schema:RUN_SCHEMA,beast_id:base.beast_id,recorded_tick:base.tick,seconds_since_recorded:snap.seconds_since_recorded,at_ms:nowMs,xp_live:snap.xp_live,
   signals:snap.signals,chain:chain,label:'SIMULATED',text:liveDiaryLine(snap),prev:prevEntry};
  const entry={...entryBody,hash:sha256Hex(JSON.stringify(entryBody))};prevEntry=entry.hash;
  io.writeBatch({head:{key:key(base),last_sec:done,chain,entry_hash:entry.hash,recorded_tick:base.tick,at_ms:nowMs},snapshot:snap,entry});
  const ok=await io.commit(`beast live tick: tick ${base.tick} +${snap.seconds_since_recorded}s (${why}) [skip ci]`);batches++;lastBatchMs=nowMs;log('batch',batches,why,done,ok);
 };
 for(;;){
  let now=clock.now();
  const sec=Math.floor((now-base.last_tick_at_ms)/1000);
  if(sec>done){chain=advanceChain(base,chain,done+1,sec);done=sec;} // catches up any missed seconds exactly
  if(now-lastBatchMs>=batchSeconds*1000){
   await io.refresh();const nb=liveBase(io.readDiary());
   if(nb&&key(nb)!==key(base)){ // a NEW recorded tick landed: close the old segment, start from it
    await flush(now,'recorded tick changed');base=nb;chain=CHAIN_GENESIS(base);done=-1;
    const s2=Math.floor((now-base.last_tick_at_ms)/1000);if(s2>=0){chain=advanceChain(base,chain,0,s2);done=s2;}
   }else await flush(now,'batch');
  }
  if(now>=endMs)break;
  const wait=Math.min(1000-(now%1000),endMs-now);
  await clock.sleep(wait>0?wait:1);
 }
 await flush(clock.now(),'handoff');
 return {ok:true,batches,seconds_run:runSeconds};
}
