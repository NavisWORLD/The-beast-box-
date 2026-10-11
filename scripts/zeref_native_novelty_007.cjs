'use strict';
/** Zeref 007: preregistered novelty and cross-episode robustness evaluation.
 * Optical signatures are coarse proxies, NEVER earned objectives or semantics.
 */
const assert=require('node:assert/strict');
const {optic,opticsSignature}=require('./zeref_native_rollout_policy_005.cjs');
function evaluate(episodes){
 assert.ok(Array.isArray(episodes)&&episodes.length>0);
 const signatures=new Set(), transitions=new Set(), actions=new Set(), byEpisode=[];
 for(const ep of episodes){
  assert.ok(Array.isArray(ep.rows)&&ep.rows.length>0);
  let changed=0,novel=0,first=0;
  for(const r of ep.rows){
   assert.ok(optic(r.before)&&optic(r.after),'Only original native framebuffer observations');
   const a=opticsSignature(r.before),b=opticsSignature(r.after);
   if(!signatures.has(a)){signatures.add(a);novel++;}
   if(!signatures.has(b)){signatures.add(b);novel++;}
   if(a!==b)changed++;
   if(r.action!=='WAIT')actions.add(r.action);
   transitions.add(a+' -> '+r.action+' -> '+b);
   first++;
  }
  byEpisode.push({episode:ep.episode,frames:ep.rows.length,novel_optical_signatures:novel,changed_optical_steps:changed});
 }
 return {episodes:episodes.length,observed_action_slots:byEpisode.reduce((a,x)=>a+x.frames,0),
  unique_native_optical_signatures:signatures.size,unique_native_optical_transitions:transitions.size,
  distinct_nonwait_actions:actions.size,episode_observations:byEpisode,
  real_game_progress:null,real_map_coverage:null,real_dialogue_advancement:null,real_reward:null,
  independent_learning_proven:false,semantic_world_understanding_proven:false,
  optical_novelty_is_not_earned_progress:true};
}
function compare(candidate,baselines){
 assert.ok(candidate&&baselines&&typeof baselines==='object');
 const required=['WAIT','RIGHT','RANDOM','SCRIPT','original'];
 for(const b of required)assert.ok(baselines[b],'Missing required comparator '+b);
 const all=Object.fromEntries(Object.entries({candidate,...baselines}).map(([name,episodes])=>[name,evaluate(episodes)]));
 const cand=all.candidate,beats=required.filter(k=>cand.unique_native_optical_signatures>all[k].unique_native_optical_signatures);
 return {schema:'zeref-007-optical-novelty-preregistered-v1',by_policy:all,
  candidate_optical_novelty_exceeds:beats,
  candidate_exceeds_all_five_optical_baselines:beats.length===5,
  game_objective_outperformance:null,
  novel_independent_strategy_proven:false,
  rationale:'Screen-level diversity is measurable; semantic exploration or earned progress requires separate trusted game instrumentation.'};
}
module.exports={evaluate,compare};