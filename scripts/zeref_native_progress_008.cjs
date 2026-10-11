'use strict';
/**
 * SOURCE-GROUNDED / READ-ONLY native Lost COSMOS SRAM state decoder.
 * References: current homebrew game's actual lost_cosmos_v5.c::save_game,
 * save_checksum_v5; content_v11_state.h, content_v11_core.h::v11_save,
 * story_completion_persist.h::completion_save and save_journal.h.
 *
 * NEVER exports raw SRAM, never writes to game memory and never claims
 * unsaved live movement is a saved-coordinate transition.
 *
 * A checksum-valid snapshot represents last committed game SAVE STATE, not
 * live coordinates, reward oracle, dialogue or agent perception.
 */
const {createHash}=require('node:crypto');
const MIN=7296;
function bytes(input){
 if(input instanceof Uint8Array)return input;
 if(input instanceof ArrayBuffer)return new Uint8Array(input);
 if(Array.isArray(input)&&input.every(x=>Number.isInteger(x)&&x>=0&&x<=255))return Uint8Array.from(input);
 return null;
}
function hash(buffer){return createHash('sha256').update(buffer).digest('hex');}
function u16(a,i){return a[i]|(a[i+1]<<8);}
function u32(a,i){return (a[i]|(a[i+1]<<8)|(a[i+2]<<16)|(a[i+3]<<24))>>>0;}
function s16(a,i){const v=u16(a,i);return v&32768?v-65536:v;}
function pop(x){let n=0;for(x>>>=0;x;x&=x-1)n++;return n;}
const table=new Uint32Array(256);
for(let i=0;i<256;i++){let c=i;for(let j=0;j<8;j++)c=c&1?(0xedb88320^(c>>>1)):(c>>>1);table[i]=c>>>0;}
function crc32(a,start,end){let c=0xffffffff;for(let i=start;i<end;i++)c=(c>>>8)^table[(c^a[i])&255];return (c^0xffffffff)>>>0;}
function primaryValid(a){
 if(a.length<MIN)return false;
 if(a[0]!==76||a[1]!==67||a[2]!==86||a[3]!==53||a[4]!==5)return false;
 let s=0x6d;for(let i=0;i<190;i++)if(i!==126&&i!==127)s=(s+a[i]+i*7)&255;
 return s===a[190];
}
function validV11(a){
 const o=6400;
 return a[o]===76&&a[o+1]===67&&a[o+2]===49&&a[o+3]===49&&a[o+4]===1&&a[o+5]===1
  &&crc32(a,o,o+764)===u32(a,o+764);
}
function validCampaign(a){
 const o=7168;
 return a[o]===76&&a[o+1]===67&&a[o+2]===66&&a[o+3]===56&&a[o+4]===1
  &&crc32(a,o,o+124)===u32(a,o+124)
  &&a.slice(o+5,o+8).every(v=>v===0)
  &&a.slice(o+94,o+124).every(v=>v===0);
}
function decode(raw){
 const a=bytes(raw);
 if(!a||a.length<MIN)return {status:'unavailable',reason:'native SRAM inaccessible or incomplete',primary_valid:false};
 if(!primaryValid(a))return {status:'no_valid_committed_save',reason:'LCV5 native save missing, outdated, or invalid checksum',primary_valid:false};
 const v11=validV11(a),comp=validCampaign(a),q=6400;
 const result={
  status:'validated_committed_native_sram',source:'original-native-cartridge-checksummed-save',
  primary_valid:true,
  // Not live player RAM. These are ONLY the most recent saved coordinates.
  committed_location:{world:a[11],room:a[12],layer:a[13],x:s16(a,16),y:s16(a,18)},
  base_game:{chapter:a[8],ending:a[9],visited_world_mask:a[6],
   visited_world_count:pop(a[6]),quest_completed_mask:a[159],
   quest_completed_count:pop(a[159]),beacons:a[36],kill_count:u16(a,150),
   player_level:a[128],boss_flags:a[149],story_flags:u16(a,200)},
  v11_valid:v11,campaign_valid:comp,
  v11:v11?{
   visited_mask:a[q+241],visited_count:pop(a[q+241]),
   beacons_mask:a[q+242],beacons_count:pop(a[q+242]),
   quest_done_mask:u16(a,q+344),quests_completed:pop(u16(a,q+344)),
   boss_done_mask:u16(a,q+346),bosses_completed:pop(u16(a,q+346)),
   cores_found_mask:u16(a,q+348),cores_found:pop(u16(a,q+348)),
   act:a[q+648],story_flags:a[q+649],spark_wins:a[q+650],
   befriended:a[q+651],rival_phase:a[q+652],
  }:null,
  campaign:comp?{
   chapters_done_mask:u32(a,7168+8),chapters_completed:pop(u32(a,7168+8)),
   chapters_seen_mask:u32(a,7168+12),chapters_seen:pop(u32(a,7168+12)),
   cache_mask:u32(a,7168+16),caches_found:pop(u32(a,7168+16)),
  }:null,
  raw_sram_archived:false,
 };
 // Important: exact source bytes may include user data, so only hash the
 // public game progress header and validated page; not the whole SRAM.
 result.committed_primary_sha256=hash(a.subarray(0,240));
 if(v11)result.committed_v11_sha256=hash(a.subarray(q,q+768));
 if(comp)result.committed_campaign_sha256=hash(a.subarray(7168,7296));
 return result;
}
const nondecrease=(a,b)=>Number.isInteger(a)&&Number.isInteger(b)&&b>a?b-a:0;
function change(before,after){
 if(!before||!after||before.status!=='validated_committed_native_sram'||after.status!=='validated_committed_native_sram')
  return {status:'unmeasurable',reason:'No pair of checksum-valid committed native save snapshots',
   objective_progress:null,objectives_changed:null};
 const a=before.base_game,b=after.base_game;
 const changeEvents={
  newly_saved_worlds:pop(b.visited_world_mask&~a.visited_world_mask),
  newly_saved_quests:pop(b.quest_completed_mask&~a.quest_completed_mask),
  newly_saved_boss_flags:pop(b.boss_flags&~a.boss_flags),
  newly_saved_story_flags:pop(b.story_flags&~a.story_flags),
  new_saved_beacons:nondecrease(a.beacons,b.beacons),
  new_saved_kills:nondecrease(a.kill_count,b.kill_count),
  new_saved_chapters:nondecrease(a.chapter,b.chapter),
  new_saved_endings:nondecrease(a.ending,b.ending),
 };
 if(before.v11&&after.v11){
  changeEvents.v11_new_quests=pop(after.v11.quest_done_mask&~before.v11.quest_done_mask);
  changeEvents.v11_new_regions=pop(after.v11.visited_mask&~before.v11.visited_mask);
  changeEvents.v11_new_beacons=pop(after.v11.beacons_mask&~before.v11.beacons_mask);
  changeEvents.v11_new_story_flags=pop(after.v11.story_flags&~before.v11.story_flags);
  changeEvents.v11_new_befriendings=nondecrease(before.v11.befriended,after.v11.befriended);
 }
 if(before.campaign&&after.campaign){
  changeEvents.campaign_new_chapters=pop(after.campaign.chapters_done_mask&~before.campaign.chapters_done_mask);
  changeEvents.campaign_new_seen=pop(after.campaign.chapters_seen_mask&~before.campaign.chapters_seen_mask);
 }
 const saved_location_change=JSON.stringify(before.committed_location)!==JSON.stringify(after.committed_location);
 const progression_events=Object.values(changeEvents).reduce((a,b)=>a+b,0);
 const committed_changed=before.committed_primary_sha256!==after.committed_primary_sha256||
   (before.v11&&after.v11&&before.committed_v11_sha256!==after.committed_v11_sha256)||
   (before.campaign&&after.campaign&&before.committed_campaign_sha256!==after.committed_campaign_sha256);
 return {status:'checksum_verified_committed_save_comparison',source:'original-native-cartridge-checksummed-save',
  new_saved_progression_events:progression_events,objective_progress:progression_events>0,
  objectives_changed:changeEvents,saved_location_changed:saved_location_change,
  committed_save_changed:!!committed_changed,
  live_position_observed:false,dialogue_line_progress_measured:false,
  game_reward_optimized:false,interpretation:'A positive event is a real native committed game-state change, not reward-optimized RL'};
}
module.exports={crc32,decode,change};
