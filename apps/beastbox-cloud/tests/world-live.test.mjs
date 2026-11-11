import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {buildWorldLive,countsFeatures,linkState,ageSeconds,STALE_AFTER_S,WORLD_LIVE_LABELS,branchRelPath,tipRelPath,parseTipSha,pickFresherSpark,sparkNeedsTipReread,WORLD_LIVE_PATHS} from '../lib/zeref/world-live.mjs';
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
 assert.equal(w.stalls,null);assert.equal(w.river,null);
 assert.equal(w.senses.find(s=>s.id==='face').label,'ESTIMATE');
 assert.equal(w.senses.find(s=>s.id==='pulse').label,'ESTIMATE');
 assert.equal(w.senses.find(s=>s.id==='pulse').in_this_read,false);
 assert.equal(w.senses.find(s=>s.id==='sight').label,'DERIVED');
 assert.match(w.senses.find(s=>s.id==='spark').note,/SIMULATOR/);
});
test('live tick behind the diary tick is a river stall and is not filled in',()=>{
 const even=buildWorldLive({spark:spark(),liveTick:live,liveHead:head,diary:{...diary,last_tick_at:'2026-10-25T17:10:00Z'},pin,nowMs:NOW});
 assert.equal(even.river,null);assert.equal(even.all_connected,true);
 const behind=buildWorldLive({spark:spark(),liveTick:{...live,recorded_tick:123},liveHead:head,diary:{...diary,tick:124,last_tick_at:'2026-10-25T17:10:00Z'},pin,nowMs:NOW});
 assert.equal(behind.links.liveTick.state,'CONNECTED');assert.equal(behind.links.diary.state,'CONNECTED');
 assert.equal(behind.river.cause,'live_tick_behind_diary');assert.equal(behind.river.lag_ticks,1);
 assert.equal(behind.river.diary_tick,124);assert.equal(behind.river.live_recorded_tick,123);
 assert.equal(behind.stalls.river.lag_ticks,1);assert.equal(behind.all_connected,false);
 assert.equal(behind.links.liveTick.recorded_tick,123);
 const ahead=buildWorldLive({spark:spark(),liveTick:{...live,recorded_tick:125},liveHead:head,diary:{...diary,tick:124,last_tick_at:'2026-10-25T17:10:00Z'},pin,nowMs:NOW});
 assert.equal(ahead.river,null);assert.equal(ahead.all_connected,true);
 const missing=buildWorldLive({spark:spark(),liveTick:null,liveHead:head,diary:{...diary,tick:124,last_tick_at:'2026-10-25T17:10:00Z'},pin,nowMs:NOW});
 assert.equal(missing.river,null);
});
test('a 3-hour-old recorded diary is STALE (what the audit found), not CONNECTED; the rest are unaffected',()=>{
 const w=buildWorldLive({spark:spark(),liveTick:live,liveHead:head,diary:{...diary,last_tick_at:'2026-10-25T14:22:44Z'},pin,nowMs:NOW});
 assert.equal(w.links.diary.state,'STALE');assert.equal(w.links.spark.state,'CONNECTED');assert.equal(w.all_connected,false);
 assert.equal(w.links.diary.stall.cause,'source_age');
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

test('STALE/DOWN spark carries a stall receipt (age + cause); CONNECTED has none',()=>{
 const stale=buildWorldLive({spark:spark({at_epoch:(NOW-600000)/1000}),liveTick:live,liveHead:head,diary:{...diary,last_tick_at:'2026-10-25T17:10:00Z'},pin,nowMs:NOW});
 assert.equal(stale.links.spark.state,'STALE');
 assert.equal(stale.links.spark.stall.cause,'source_age');
 assert.equal(stale.links.spark.stall.stale_after_s,STALE_AFTER_S.spark);
 assert.ok(stale.links.spark.stall.age_s>STALE_AFTER_S.spark);
 assert.equal(stale.stalls.spark.cause,'source_age');
 assert.equal(stale.all_connected,false);
 const down=buildWorldLive({spark:null,liveTick:live,liveHead:head,diary:{...diary,last_tick_at:'2026-10-25T17:10:00Z'},pin,nowMs:NOW});
 assert.equal(down.links.spark.state,'DOWN');assert.equal(down.links.spark.stall.cause,'missing');
 const failed=buildWorldLive({spark:spark({status:'failed',at_epoch:(NOW-600000)/1000,consecutive_failures:2,last_ok:{tick:2269,at_epoch:(NOW-3600000)/1000,counts:{'000':256}}}),liveTick:live,liveHead:head,diary:{...diary,last_tick_at:'2026-10-25T17:10:00Z'},pin,nowMs:NOW});
 assert.equal(failed.links.spark.stall.cause,'failed_status');
 const ok=buildWorldLive({spark:spark(),liveTick:live,liveHead:head,diary:{...diary,last_tick_at:'2026-10-25T17:10:00Z'},pin,nowMs:NOW});
 assert.equal(ok.links.spark.stall,undefined);assert.equal(ok.stalls,null);
});

test('sparkNeedsTipReread: past one interval (or missing) asks for tip; fresh does not',()=>{
 assert.equal(sparkNeedsTipReread(null,NOW),true);
 assert.equal(sparkNeedsTipReread(spark({at_epoch:(NOW-55000)/1000}),NOW),false);
 assert.equal(sparkNeedsTipReread(spark({at_epoch:(NOW-90000)/1000}),NOW),true);
 assert.equal(sparkNeedsTipReread(spark({interval_target_s:60,at_epoch:(NOW-61000)/1000}),NOW),true);
});

test('tip path helpers + parseTipSha: only real 40-char shas; branch paths stay exact',()=>{
 assert.equal(branchRelPath('zeref-spark','zeref/latest.json'),'zeref-spark/zeref/latest.json');
 assert.equal(tipRelPath('deadbeef','zeref/latest.json'),null);
 const sha='a'.repeat(40);
 assert.equal(tipRelPath(sha,'zeref/latest.json'),sha+'/zeref/latest.json');
 assert.equal(parseTipSha([{sha}]),sha);
 assert.equal(parseTipSha({sha}),sha);
 assert.equal(parseTipSha([{sha:'nope'}]),null);
 assert.equal(parseTipSha(null),null);
 assert.equal(WORLD_LIVE_PATHS.spark.file,'zeref/latest.json');
});

test('pickFresherSpark: chain continuity across a stall — prefers the younger REAL record, never invents ticks',()=>{
 const older=spark({tick:19346,at_epoch:(NOW-200000)/1000});
 const newer=spark({tick:19350,at_epoch:(NOW-30000)/1000,last_ok:{tick:19350,at_epoch:(NOW-30000)/1000,counts:{'000':256}}});
 assert.equal(pickFresherSpark(older,newer,NOW).tick,19350);
 assert.equal(pickFresherSpark(newer,older,NOW).tick,19350);
 assert.equal(pickFresherSpark(older,null,NOW).tick,19346);
 assert.equal(pickFresherSpark(null,newer,NOW).tick,19350);
 assert.equal(pickFresherSpark(null,null,NOW),null);
 assert.equal(pickFresherSpark({...newer,beast_id:'bb-7f9c2a03'},older,NOW).tick,19346);
 assert.equal(pickFresherSpark({...newer,simulated:false},null,NOW),null);
 const a=spark({tick:10,at_epoch:(NOW-10000)/1000});
 const b=spark({tick:11,at_epoch:(NOW-10000)/1000});
 assert.equal(pickFresherSpark(a,b,NOW).tick,11);
});

test('route recovery: tip refetch + stall log + no secrets; UI shows stall cause',()=>{
 const strip=f=>readFileSync(new URL(f,import.meta.url),'utf8').replace(/\/\*[^]*?\*\//g,'').replace(/\/\/.*$/gm,'');
 const route=strip('../app/api/world/live/route.ts');
 assert.match(route,/sparkNeedsTipReread/);assert.match(route,/pickFresherSpark/);assert.match(route,/tipRelPath|tipJson/);
 assert.match(route,/async function get[\s\S]*AbortSignal\.timeout\(5000\)/);
 // Must NOT pin one AbortSignal on a module const (warm isolates would abort every fetch after 5s).
 assert.doesNotMatch(route,/const NO_CACHE\s*=\s*\{[^}]*signal:AbortSignal/);

 assert.match(route,/\[world-live\] stall/);
 assert.match(route,/export const dynamic='force-dynamic'/);assert.match(route,/no-store/);
 assert.doesNotMatch(route,/process\.env|Authorization|token/i);
 for(const b of ['zeref-spark/zeref/latest.json','zeref-live-tick/live/latest.json','zeref-live-tick/live/head.json','zeref-diary/zeref/latest.json'])assert.ok(route.includes(b),b);
 const ui=readFileSync(new URL('../components/world-live-links.tsx',import.meta.url),'utf8');
 assert.match(ui,/stall \$\{spark\.stall\.cause\}/);
 assert.match(ui,/data-river-lag/);
 assert.match(ui,/Face and pulse on this surface are ESTIMATE/);
});

import {parseRefsTipSha} from '../lib/zeref/world-live.mjs';
test('git ref advertisement fallback: exact branch only, real 40-char sha only, never invented', () => {
  const a = 'a'.repeat(40), b = 'b'.repeat(40), c = 'c'.repeat(40);
  const adv = `001e# service=git-upload-pack\n0000015b${a} HEAD\u0000multi_ack thin-pack\n003f${b} refs/heads/zeref-spark\n0044${c} refs/heads/zeref-spark-old\n0000`;
  assert.equal(parseRefsTipSha(adv, 'zeref-spark'), b);
  assert.equal(parseRefsTipSha(adv, 'zeref-spark-old'), c);
  assert.equal(parseRefsTipSha(adv, 'zeref-diary'), null);
  assert.equal(parseRefsTipSha(null, 'zeref-spark'), null);
  assert.equal(parseRefsTipSha(adv, 'bad branch;'), null);
  const src = readFileSync(new URL('../app/api/world/live/route.ts', import.meta.url), 'utf8');
  assert.match(src, /parseRefsTipSha\(await getText\(REFS\),branch\)/);
});

const LOCAL_LABEL='LOCAL SIMULATED (runner statevector, not Rigetti, not a QPU)';
const localSpark=(over={})=>({backend:'local-sim',label:LOCAL_LABEL,beast_id:'bb-deada969',simulated:true,status:'ok',tick:12,
 at_epoch:(NOW-20000)/1000,shots:256,counts:{'000':100,'111':156},counts_sha256:'b'.repeat(64),
 last_ok:{tick:12,at_epoch:(NOW-20000)/1000,counts:{'000':100,'111':156},shots:256},...over});
test('local-sim is its own labeled source and the Rigetti last-ok stays separate until Azure succeeds',()=>{
 const failing=spark({status:'failed',consecutive_failures:1500,tick:24304,at_epoch:(NOW-20000)/1000,
  last_ok:{tick:24303,at_epoch:(NOW-90000000)/1000,counts:{'000':256}}});
 const fresh={liveTick:live,liveHead:head,diary:{...diary,last_tick_at:'2026-10-25T17:10:00Z'},pin,nowMs:NOW};
 const on=buildWorldLive({spark:failing,localSpark:localSpark(),...fresh});
 assert.equal(on.links.spark.source,'local-sim');
 assert.equal(on.links.spark.label,LOCAL_LABEL);
 assert.equal(on.links.spark.state,'CONNECTED');
 assert.equal(on.links.spark.last_ok_tick,24303);
 assert.equal(on.links.spark.local_last_ok_tick,12);
 assert.equal(on.drive.source,'local-sim');
 assert.equal(on.drive.label,LOCAL_LABEL);
 assert.match(on.senses.find(s=>s.id==='spark').note,/not Rigetti/);
 const back=buildWorldLive({spark:spark(),localSpark:localSpark(),...fresh});
 assert.equal(back.links.spark.source,'rigetti.sim.qvm');
 assert.match(back.links.spark.label,/Rigetti SIMULATED/);
 assert.equal(back.links.spark.last_ok_tick,2272);
 assert.equal(back.links.spark.local_last_ok_tick,12);
 assert.equal(back.drive.source,'spark');
 const stale=buildWorldLive({spark:failing,localSpark:localSpark({at_epoch:(NOW-600000)/1000,last_ok:{tick:9,at_epoch:(NOW-600000)/1000,counts:{'000':256},shots:256}}),...fresh});
 assert.equal(stale.links.spark.state,'STALE');
 assert.notEqual(stale.links.spark.source,'local-sim');
 assert.equal(stale.links.spark.local_last_ok_tick,9);
 assert.equal(stale.drive,null);
 const wrong=buildWorldLive({spark:failing,localSpark:localSpark({backend:'rigetti.sim.qvm',label:'Rigetti SIMULATED'}),...fresh});
 assert.notEqual(wrong.links.spark.source,'local-sim');
 const route=readFileSync(new URL('../app/api/world/live/route.ts',import.meta.url),'utf8');
 assert.ok(route.includes('zeref-spark/zeref/local-sim/latest.json'));
 assert.equal(WORLD_LIVE_PATHS.localSpark.file,'zeref/local-sim/latest.json');
 const decl=readFileSync(new URL('../lib/zeref/world-live.d.mts',import.meta.url),'utf8');
 assert.match(decl,/localSpark\?:unknown/);
 assert.match(decl,/LOCAL_SIM_LABEL/);
});
