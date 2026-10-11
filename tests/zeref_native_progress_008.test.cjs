'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {crc32,decode,change}=require('../scripts/zeref_native_progress_008.cjs');
function make(base={}) {
 const a=new Uint8Array(32768);
 a.set([76,67,86,53,5],0);
 a[6]=base.visited??1;a[8]=base.chapter??0;a[9]=base.ending??0;
 a[11]=base.world??0;a[12]=base.room??0;a[13]=base.layer??1;
 a[16]=base.x??32;a[18]=base.y??32;
 a[128]=1;a[159]=base.quests??0;
 a[36]=base.beacons??0;
 a[149]=base.boss??0;
 a[150]=base.kills??0;
 let sum=0x6d;
 for(let i=0;i<190;i++)if(i!==126&&i!==127)sum=(sum+a[i]+i*7)&255;
 a[190]=sum;
 return a;
}
function addV11(a,values={}){
 const start=6400;a.set([76,67,49,49,1,1],start);
 a[start+241]=values.visited??0;a[start+242]=values.beacons??0;
 a[start+344]=values.quests??0;a[start+346]=values.bosses??0;
 a[start+648]=values.act??0;a[start+649]=values.story??0;
 a[start+650]=values.wins??0;a[start+651]=values.befriended??0;
 const crc=crc32(a,start,start+764);
 for(let i=0;i<4;i++)a[start+764+i]=(crc>>>(8*i))&255;
 return a;
}
function addCampaign(a,values={}){
 const at=7168;a.set([76,67,66,56,1],at);
 a[at+8]=values.done??0;a[at+12]=values.seen??0;
 const crc=crc32(a,at,at+124);
 for(let i=0;i<4;i++)a[at+124+i]=(crc>>>(8*i))&255;
 return a;
}
test('no raw SRAM, unsaved title pages, or malformed bytes count as progress',()=>{
 assert.equal(decode(new Uint8Array(32768)).status,'no_valid_committed_save');
 assert.equal(decode(null).status,'unavailable');
 assert.equal(change(decode(new Uint8Array(32768)),decode(make())).objective_progress,null);
 const bad=make();bad[159]=44;
 assert.equal(decode(bad).status,'no_valid_committed_save');
});
test('actual source-defined LCV5 committed quest and exploration fields are decoded read-only',()=>{
 const a=make({world:0,room:2,quests:1,visited:1,x:32,beacons:1});
 const snap=decode(a);
 assert.equal(snap.primary_valid,true);
 assert.equal(snap.base_game.quest_completed_count,1);
 assert.deepEqual(snap.committed_location,{world:0,room:2,layer:1,x:32,y:32});
 assert.equal(snap.source,'original-native-cartridge-checksummed-save');
 assert.equal(snap.raw_sram_archived,false);
});
test('CRC-invalid optional V11 pages are NEVER treated as earned quest evidence',()=>{
 const a=make();a.set([76,67,49,49,1,1],6400);
 assert.equal(decode(a).v11_valid,false);
 assert.equal(decode(a).v11,null);
});
test('V11 checksum verified source offsets include native saved visits and quests',()=>{
 const a=addV11(make(),{visited:3,beacons:1,quests:5,bosses:1,act:1,story:1,wins:1,befriended:1});
 const p=decode(a);
 assert.equal(p.v11_valid,true);
 assert.equal(p.v11.visited_count,2);
 assert.equal(p.v11.quests_completed,2);
 assert.equal(p.v11.bosses_completed,1);
});
test('native committed quest changes count, but visual-only changes and stale saves do not',()=>{
 const a=decode(addCampaign(addV11(make({quests:1}),{quests:1,visited:1}),{done:1}));
 const b=decode(addCampaign(addV11(make({quests:3,world:1,room:7}),{quests:3,visited:3}),{done:3}));
 const delta=change(a,b);
 assert.equal(delta.status,'checksum_verified_committed_save_comparison');
 assert.equal(delta.objective_progress,true);
 assert.equal(delta.objectives_changed.newly_saved_quests,1);
 assert.equal(delta.objectives_changed.v11_new_regions,1);
 assert.equal(delta.objectives_changed.campaign_new_chapters,1);
 assert.equal(delta.saved_location_changed,true);
 assert.equal(change(a,a).objective_progress,false);
 assert.equal(change(a,a).saved_location_changed,false);
});
test('SRAM decoder is a validated save reader, NOT an assertion about live RAM or sensor presence',()=>{
 const a=decode(make());const b=decode(make({x:64,y:64}));
 assert.equal(change(a,b).saved_location_changed,true);
 assert.equal(change(a,b).objective_progress,false);
 assert.equal(change(a,b).live_position_observed,false);
 assert.equal(change(a,b).game_reward_optimized,false);
});
