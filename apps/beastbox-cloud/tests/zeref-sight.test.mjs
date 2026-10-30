import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {buildWorldLive} from '../lib/zeref/world-live.mjs';
import {assembleBridgeContext,BRIDGE_CONTEXT_CAPS} from '../lib/cosmos/live-context.mjs';
import {composeSight,visitorLightFrom,worldLightFrom,SIGHT_LABELS,WORLD_DAY_S} from '../lib/cosmos/sight.mjs';
import {ENV_FRESH_MS} from '../lib/environment/environment-link.mjs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');

const PIN={training_steps:34224,checkpoint_sha256:'f'.repeat(64)};
/** A timestamp whose position in his world's 240 s day is exactly `phase` seconds. */
const msForPhase=p=>{const base=1767225600000;const r=((base/1000)%WORLD_DAY_S+WORLD_DAY_S)%WORLD_DAY_S;return base+(((p-r)%WORLD_DAY_S+WORLD_DAY_S)%WORLD_DAY_S)*1000;};
function worldAt(phase,{headAgeMs=0,liveTickDown=false}={}){
 const at=msForPhase(phase),sec=Math.floor(at/1000);
 return buildWorldLive({
  spark:{simulated:true,beast_id:'bb-deada969',tick:6900,at_epoch:sec,status:'ok',late:false,
   consecutive_failures:0,interval_target_s:60,counts_sha256:'a'.repeat(64),
   last_ok:{tick:6900,at_epoch:sec,counts:{'000':100,'111':156}}},
  liveTick:liveTickDown?null:{schema:'beast-live-tick/v1',label:'SIMULATED',recorded_tick:250,seconds_since_recorded:12,xp_live:4306,signals:{}},
  liveHead:{at_ms:at-headAgeMs},
  diary:{ok:true,tick:250,last_tick_at:new Date(at).toISOString()},
  pin:PIN,nowMs:at});
}
const envAt=(now,ageMs,over={})=>({numbers:{light:{state:'MEASURED',level:0.7,source:'camera-brightness',...over}},measured_at_ms:now-ageMs});

test('world light: dawn rising fires his own notice() rule — brightening is joy',()=>{
 const w=worldAt(20);
 const wl=worldLightFrom(w,w.at_ms);
 assert.equal(wl.band,'bright');
 assert.equal(wl.trend,'rising');
 assert.equal(wl.feeling,'joy');
 assert.equal(wl.event,'the lights getting bright','the event text is field-perception notice() verbatim');
 const s=composeSight({world:w,nowMs:w.at_ms});
 assert.equal(s.receipt.world_light.composed,true);
 assert.equal(s.receipt.world_light.label,'DERIVED');
 assert.equal(s.receipt.world_light.feeling,'joy');
 assert.match(s.text,/DERIVED from its sky \(computed, not measured\)/);
 assert.match(s.text,/the lights getting bright/);
});

test('world light: night is the low band, darkening is fear, midday steady is calm',()=>{
 const night=worldLightFrom(worldAt(230),worldAt(230).at_ms);
 assert.equal(night.band,'night');
 assert.equal(night.trend,'falling');
 assert.equal(night.feeling,'fear');
 assert.equal(night.event,'the lights going dark');
 const noonWorld=worldAt(60);
 const noon=worldLightFrom(noonWorld,noonWorld.at_ms);
 assert.equal(noon.band,'bright');
 assert.equal(noon.trend,'steady');
 assert.equal(noon.feeling,'calm','no notice fires on steady light; calm is his resting emotion');
 assert.equal(noon.event,null);
});

test('world light: an unreadable universe clock composes nothing — DOWN is never faked',()=>{
 const down=worldAt(20,{liveTickDown:true});
 assert.equal(down.links.liveTick.state,'DOWN');
 assert.equal(worldLightFrom(down,down.at_ms),null);
 const s=composeSight({world:down,nowMs:down.at_ms});
 assert.equal(s.receipt.world_light.composed,false);
 assert.equal(s.receipt.world_light.label,'DERIVED');
 assert.match(s.receipt.world_light.reason,/live tick DOWN/);
 assert.equal(composeSight({world:null,nowMs:Date.now()}).receipt.world_light.composed,false);
 assert.equal(composeSight({world:null,nowMs:Date.now()}).text,'');
 // STALE is old but readable (world-live semantics): the light still derives
 const stale=worldAt(20,{headAgeMs:2000_000});
 assert.equal(stale.links.liveTick.state,'STALE');
 assert.equal(composeSight({world:stale,nowMs:stale.at_ms}).receipt.world_light.composed,true);
});

test('visitor light: a fresh measured summary composes, labelled MEASURED with its source',()=>{
 const w=worldAt(60),now=w.at_ms;
 const s=composeSight({world:w,environment:envAt(now,1000),nowMs:now});
 assert.equal(s.receipt.visitor_light.composed,true);
 assert.equal(s.receipt.visitor_light.label,'MEASURED');
 assert.equal(s.receipt.visitor_light.source,'camera-brightness');
 assert.match(s.text,/MEASURED by their camera brightness/);
 assert.match(s.text,/site's light conversion, numbers only/);
 const als=composeSight({world:w,environment:envAt(now,0,{source:'ambient-light-sensor',level:0.1}),nowMs:now});
 assert.equal(als.receipt.visitor_light.composed,true);
 assert.match(als.text,/ambient light sensor/);
 assert.match(als.text,/dark \(0\.1\)/);
});

test('visitor light: stale, malformed or absent composes nothing — no fallback text',()=>{
 const w=worldAt(60),now=w.at_ms;
 const cases=[
  envAt(now,ENV_FRESH_MS+1000),                       // stale past the conversion's own freshness window
  envAt(now,-5000),                                   // timestamped in the future
  envAt(now,0,{level:2}),                             // level out of range
  envAt(now,0,{source:'webcam'}),                     // not one of the light conversion's sources
  envAt(now,0,{state:'off'}),                         // a channel that is not measuring carries no numbers
  {numbers:{light:{state:'MEASURED',level:0.5,source:'camera-brightness'}}}, // no measured-at timestamp
  {measured_at_ms:now},                               // no numbers at all
  {numbers:{light:{state:'MEASURED',level:0.5,source:'camera-brightness'},evil:{state:'MEASURED',level:1}},measured_at_ms:now}, // unknown channel
  'a string is not a summary',
  ['an','array'],
  null,undefined,42,
 ];
 for(const c of cases){
  assert.equal(visitorLightFrom(c,now),null,JSON.stringify(c)?.slice(0,60));
  const s=composeSight({world:w,environment:c,nowMs:now});
  assert.equal(s.receipt.visitor_light.composed,false);
  assert.equal(s.receipt.visitor_light.label,'absent');
  assert.equal(s.receipt.visitor_light.source,null);
  assert.doesNotMatch(s.text,/MEASURED/,'nothing measured is claimed');
 }
});

test('sight budget: lines are whole or absent — a label is never truncated',()=>{
 const w=worldAt(60),now=w.at_ms;
 const full=composeSight({world:w,environment:envAt(now,0),nowMs:now});
 assert.ok(full.text.includes('DERIVED')&&full.text.includes('MEASURED'));
 // pressure drops the visitor line first; the world line survives whole
 const squeezed=composeSight({world:w,environment:envAt(now,0),nowMs:now,maxChars:full.text.length-10});
 assert.ok(squeezed.text.includes('DERIVED'));
 assert.doesNotMatch(squeezed.text,/MEASURED/);
 assert.equal(squeezed.receipt.world_light.composed,true);
 assert.equal(squeezed.receipt.visitor_light.composed,false);
 assert.equal(squeezed.receipt.visitor_light.label,'MEASURED','received and valid, just not composed — the receipt says both');
 // a budget that fits no whole line composes nothing at all
 const none=composeSight({world:w,environment:envAt(now,0),nowMs:now,maxChars:20});
 assert.equal(none.text,'');
 assert.equal(none.receipt.world_light.composed,false);
 assert.equal(none.receipt.visitor_light.composed,false);
});

test('assembly: sight is its own fourth bridge field — key order, caps and receipts',()=>{
 const world=worldAt(20);
 const env=envAt(world.at_ms,1000);
 const sight=composeSight({world,environment:env,nowMs:world.at_ms});
 const shelfHits=[{shelf:'zeref-lessons-006',topic:'senses-light',user:'Zeref, what do your eyes measure?',
  assistant:'My eyes measure brightness and colour, and whether things are moving.',source:'zeref-lessons-006',license:null,score:9}];
 const refitSight=n=>composeSight({world,environment:env,nowMs:world.at_ms,maxChars:n});
 const full=assembleBridgeContext({continuity:'You are yourself. The guest is a returning friend.',world,shelfHits,
  sight:sight.text,sightMeta:sight.receipt,refitSight});
 // The contract keys, in order — the pre-sight pin (['continuity','universe',
 // 'library']) gains exactly one key, appended: sight. Deliberate update.
 assert.deepEqual(Object.keys(full.context),['continuity','universe','library','sight']);
 assert.equal(full.sight.world_light.composed,true);
 assert.equal(full.sight.world_light.label,SIGHT_LABELS.world);
 assert.ok(full.bytes.sight>0&&full.bytes.sight<=BRIDGE_CONTEXT_CAPS.sight,'sight rides within its own cap');
 assert.ok(full.bytes.total<=BRIDGE_CONTEXT_CAPS.total);
 // The two-line sight (405 chars) exceeds the 300-byte field cap, so the
 // assembly refits it: his own world's line survives whole, the visitor
 // line yields inside the block, and the receipt says so — never a cut label.
 assert.equal(full.sight.visitor_light.composed,false);
 assert.match(full.context.sight,/DERIVED from its sky/);
 assert.doesNotMatch(full.context.sight,/MEASURED/);
 // Under total pressure continuity and sight stay whole; the library
 // lives on exactly what budget remains.
 const pressured=assembleBridgeContext({continuity:'C'.repeat(BRIDGE_CONTEXT_CAPS.continuity),
  recompose:n=>'C'.repeat(n),world,shelfHits,sight:sight.text,sightMeta:sight.receipt,refitSight});
 assert.equal(pressured.bytes.continuity,BRIDGE_CONTEXT_CAPS.continuity,'continuity is never traded away');
 assert.equal(pressured.bytes.sight,full.bytes.sight,'sight keeps its whole block under pressure');
 assert.ok(pressured.bytes.library<=BRIDGE_CONTEXT_CAPS.total-pressured.bytes.continuity
  -pressured.bytes.universe-pressured.bytes.sight,'the library gets the leftovers, nothing more');
 assert.ok(pressured.bytes.total<=BRIDGE_CONTEXT_CAPS.total);
 // No sight offered: the field is omitted (the pre-sight key set, byte for
 // byte) and the receipt is honestly absent-shaped.
 const plain=assembleBridgeContext({continuity:'You are yourself.',world,shelfHits});
 assert.deepEqual(Object.keys(plain.context),['continuity','universe','library']);
 assert.equal(plain.bytes.sight,0);
 assert.equal(plain.sight.world_light.composed,false);
 assert.equal(plain.sight.world_light.label,SIGHT_LABELS.world);
 assert.equal(plain.sight.visitor_light.label,'absent');
 assert.equal(plain.live.composed,true);
 assert.equal(plain.library.composed,true);
});

test('forever door route: sight is wired in, receipts state it, writes stay guestbook-only',()=>{
 const src=read('app/api/guest/forever/route.ts');
 assert.match(src,/sight\.mjs/);
 assert.match(src,/composeSight\(\{world,environment:item\.environment,nowMs:world\.at_ms\}\)/);
 assert.match(src,/sight:sightBlock\.text,sightMeta:sightBlock\.receipt/);
 assert.match(src,/refitSight/,'the door hands the assembly a sight refit, the continuity recompose idiom');
 assert.match(src,/sight:sightReceipt/,'the sight receipt rides the response beside live_universe and library');
 assert.match(src,/world_light:\{\.\.\.bridgeContext\.sight\.world_light,composed:false\}/,'unsent context forces the sight receipt uncomposed, same as the other receipts');
 assert.match(src,/'environment'\]/,'the optional environment summary is the one new accepted key');
 assert.match(src,/appendExchange/,'the only writes remain the #668 guestbook writes');
 assert.doesNotMatch(src,/putBlob|storeLesson|stepDiary/);
});

test('the stateless door gains no sight, and sight has no writer and no intake wire',()=>{
 const guest=read('app/api/guest/route.ts');
 assert.match(guest,/guest_stateless:true/);
 assert.doesNotMatch(guest,/sight|composeSight|environment/);
 const src=read('lib/cosmos/sight.mjs');
 assert.doesNotMatch(src,/putBlob|appendExchange|appendGuestEvent|createWriteStream|writeFileSync|fetch\(/,'no writes, no network: composition only');
 // code lines only (the header comment documents the boundary in prose):
 const code=src.split('\n').filter(l=>!/^\s*(\*|\/\/)/.test(l)).join('\n');
 assert.doesNotMatch(code,/perception\/route|zeref-perception|PENDING_REVIEW/,'the Open Field intake is not touched or read');
 assert.doesNotMatch(code,/azure-blob|forever-store/,'nothing is stored — the response receipt is the only record');
});
