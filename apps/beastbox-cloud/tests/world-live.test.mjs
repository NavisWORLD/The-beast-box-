import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {buildWorldLive,countsFeatures,linkState,ageSeconds,STALE_AFTER_S,WORLD_LIVE_LABELS} from '../lib/zeref/world-live.mjs';
const NOW=Date.parse('2026-10-25T17:34:00Z');
const spark=(over={})=>({beast_id:'bb-deada969',simulated:true,tick:2272,status:'ok',late:false,consecutive_failures:0,interval_target_s:60,at_epoch:(NOW-55000)/1000,
 counts_sha256:'a'.repeat(64),last_ok:{tick:2272,at_epoch:(NOW-55000)/1000,counts:{'000':199,'001':40,'010':3,'011':9,'100':1,'110':1,'111':3}},...over});
const live={schema:'beast-live-tick/v1',label:'SIMULATED',recorded_tick:124,seconds_since_recorded:11238,xp_live:2532.35,signals:{energy:88.78}};
const head={at_ms:NOW-200000};
const diary={ok:true,tick:124,last_tick_at:'2026-10-25T14:22:44Z'};
const pin={training_steps:32304,checkpoint_sha256:'e60c84cd46733cc5a1def8851178a1ba565704e9a78eccaa0c7d39b175011fe5'};
test('every loop fresh -> all CONNECTED, labels stay SIMULATED / RECORDED / pinned',()=>{
 const w=buildWorldLive({spark:spark(),liveTick:live,liveHead:head,diary:{...diary,last_tick_at:'2026-10-25T17:10:00Z'},pin,nowMs:NOW});
 assert.equal(w.all_connected,true);assert.deepEqual(Object.values(w.links).map(l=>l.state),['CONNECTED','CONNECTED','CONNECTED','CONNECTED']);
 assert.deepEqual(w.labels,{spark:'SIMULATED',liveTick:'SIMULATED',diary:'RECORDED',brain:'PINNED'});
 assert.match(WORLD_LIVE_LABELS.spark,/not a QPU/);assert.equal(w.links.brain.step,32304);assert.equal(w.links.brain.checkpoint_sha256_prefix,'e60c84cd4673');
 assert.equal(w.drive.label,'SIMULATED');assert.equal(w.drive.tick,2272);
 for(const k of ['p0','p1','p2','odd','entropy']){assert.ok(w.drive[k]>=0&&w.drive[k]<=1,k);}
});
test('a 3-hour-old recorded diary is STALE (what the audit found), not CONNECTED; the rest are unaffected',()=>{
 const w=buildWorldLive({spark:spark(),liveTick:live,liveHead:head,diary:{...diary,last_tick_at:'2026-10-25T14:22:44Z'},pin,nowMs:NOW});
 assert.equal(w.links.diary.state,'STALE');assert.equal(w.links.spark.state,'CONNECTED');assert.equal(w.all_connected,false);
});
test('a stale or failing spark stops driving the world and is never refilled',()=>{
 const old=buildWorldLive({spark:spark({at_epoch:(NOW-600000)/1000}),liveTick:live,liveHead:head,diary,pin,nowMs:NOW});
 assert.equal(old.links.spark.state,'STALE');assert.equal(old.drive,null);
 const failing=buildWorldLive({spark:spark({status:'failed',consecutive_failures:3,last_ok:{tick:2269,at_epoch:(NOW-3600000)/1000,counts:{'000':256}}}),liveTick:live,liveHead:head,diary,pin,nowMs:NOW});
 assert.equal(failing.links.spark.state,'STALE');assert.equal(failing.links.spark.status,'failed');assert.equal(failing.links.spark.last_ok_tick,2269);assert.equal(failing.drive,null);
});
test('missing, real-looking-but-wrong, or unreadable records are DOWN',()=>{
 const w=buildWorldLive({spark:spark({simulated:false}),liveTick:{...live,label:'RECORDED'},liveHead:null,diary:null,pin:null,nowMs:NOW});
 assert.deepEqual(Object.values(w.links).map(l=>l.state),['DOWN','DOWN','DOWN','DOWN']);assert.equal(w.drive,null);
 assert.equal(buildWorldLive({spark:spark({beast_id:'bb-7f9c2a03'}),nowMs:NOW}).links.spark.state,'DOWN'); // bb-deada969 and bb-7f9c2a03 stay separate
 assert.equal(buildWorldLive({spark:null,nowMs:NOW}).links.liveTick.state,'DOWN');
});
test('counts features: deterministic marginals / parity / entropy, malformed counts -> null',()=>{
 const f=countsFeatures({'000':128,'111':128});assert.deepEqual(f,{p0:.5,p1:.5,p2:.5,odd:.5,entropy:.3333,shots:256});
 assert.deepEqual(countsFeatures({'000':256}),{p0:0,p1:0,p2:0,odd:0,entropy:0,shots:256});
 for(const bad of [null,{},{'00':3},{'000':-1},{'000':1.5},{'abc':3},'x'])assert.equal(countsFeatures(bad),null);
});
test('ages: future clock skew beyond a minute is unknown; link state boundaries',()=>{
 assert.equal(ageSeconds(NOW,NOW+120000),null);assert.equal(ageSeconds(NOW,NOW+30000),0);assert.equal(ageSeconds(NOW,NOW-61500),61);
 assert.equal(linkState(STALE_AFTER_S.spark,STALE_AFTER_S.spark),'CONNECTED');assert.equal(linkState(STALE_AFTER_S.spark+1,STALE_AFTER_S.spark),'STALE');assert.equal(linkState(null,5),'DOWN');
});
test('pure engine: no Math.random, clock, network or secrets; route reads only the public data branches and the public pin',()=>{
 const strip=f=>readFileSync(new URL(f,import.meta.url),'utf8').replace(/\/\*[^]*?\*\//g,'').replace(/\/\/.*$/gm,'');
 const lib=strip('../lib/zeref/world-live.mjs');assert.doesNotMatch(lib,/Math\.random|Date\.now|new Date|fetch\(|process\.env/);
 const route=strip('../app/api/world/live/route.ts');
 for(const b of ['zeref-spark/zeref/latest.json','zeref-live-tick/live/latest.json','zeref-live-tick/live/head.json','zeref-diary/zeref/latest.json'])assert.ok(route.includes(b),b);
 assert.doesNotMatch(route,/process\.env|Authorization|token/i);
 // freshness: never a cached/stale-while-revalidate payload
 assert.match(route,/export const dynamic='force-dynamic'/);assert.doesNotMatch(route,/export const revalidate|next:\{revalidate|stale-while-revalidate/);assert.match(route,/no-store/);
});
test('UI: polls only while visible, shows STALE/DOWN honestly, broadcasts the spark numbers, mounted in the diary panel and heard by the habitat',()=>{
 const ui=readFileSync(new URL('../components/world-live-links.tsx',import.meta.url),'utf8');
 assert.match(ui,/if\(!document\.hidden\)void load\(\)/);assert.match(ui,/beastbox:world-live/);assert.match(ui,/SIMULATED/);assert.match(ui,/RECORDED/);assert.doesNotMatch(ui,/Math\.random/);
 assert.match(readFileSync(new URL('../components/zeref-diary-panel.tsx',import.meta.url),'utf8'),/<WorldLiveLinks\/>/);
 const arena=readFileSync(new URL('../components/spark-beast-arena.tsx',import.meta.url),'utf8');assert.match(arena,/addEventListener\('beastbox:world-live'/);assert.match(arena,/removeEventListener\('beastbox:world-live'/);
});
