/**
 * Wires the latest recorded "CHSH game (Bell nonlocality)" result into the creature's world.
 * Win rate above the 75% classical bound grows the biosphere and lifts mood; below it, a small storm.
 * Recorded IBM hardware result; not a loophole-free Bell test (no space-like separation).
 */
export const CHSH_GAME_SRC='/spark/chsh-game/latest.json';
/** Data-only branch the daily workflow appends to (no deploy needed). */
export const CHSH_GAME_DATA='https://raw.githubusercontent.com/NavisWORLD/The-beast-box-/chsh-game-data/';
export function historyRows(hist,fallback){
 const e=Array.isArray(hist?.entries)?hist.entries:fallback?.quantum?[{date_utc:fallback.date_utc,job_id:fallback.job_id,backend:fallback.backend,win_rate:fallback.quantum.win_rate,standard_error:fallback.quantum.standard_error,rounds:fallback.quantum.rounds}]:[];
 return e.filter(r=>Number.isFinite(r?.win_rate)).map(r=>({date:String(r.date_utc).replace(/(\d{4})(\d{2})(\d{2})/,'$1-$2-$3'),job:r.job_id,backend:r.backend,winRate:r.win_rate,se:r.standard_error,rounds:r.rounds})).reverse();
}
export function chshGameWorld(shard){
 const q=shard?.quantum;if(!q||!Number.isFinite(q.win_rate))return null;
 const edge=q.win_rate-(shard.classical_bound??.75);
 const conf=q.standard_error>0?Math.max(-3,Math.min(3,edge/q.standard_error)):0;
 return {label:'CHSH game (Bell nonlocality)',winRate:q.win_rate,se:q.standard_error,edge,
  biosphereDelta:+(Math.max(-.1,Math.min(.1,edge))).toFixed(4),
  moodDelta:+(conf/3*.5).toFixed(3),stormDelta:+(-edge*2).toFixed(4),
  jobId:shard.job_id,backend:shard.backend,date:shard.date_utc,loopholeFree:false};
}
