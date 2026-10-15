/**
 * Wires the latest recorded "CHSH game (Bell nonlocality)" result into the creature's world.
 * Win rate above the 75% classical bound grows the biosphere and lifts mood; below it, a small storm.
 * Recorded IBM hardware result; not a loophole-free Bell test (no space-like separation).
 */
export const CHSH_GAME_SRC='/spark/chsh-game/latest.json';
export function chshGameWorld(shard){
 const q=shard?.quantum;if(!q||!Number.isFinite(q.win_rate))return null;
 const edge=q.win_rate-(shard.classical_bound??.75);
 const conf=q.standard_error>0?Math.max(-3,Math.min(3,edge/q.standard_error)):0;
 return {label:'CHSH game (Bell nonlocality)',winRate:q.win_rate,se:q.standard_error,edge,
  biosphereDelta:+(Math.max(-.1,Math.min(.1,edge))).toFixed(4),
  moodDelta:+(conf/3*.5).toFixed(3),stormDelta:+(-edge*2).toFixed(4),
  jobId:shard.job_id,backend:shard.backend,date:shard.date_utc,loopholeFree:false};
}
