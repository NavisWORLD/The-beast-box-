import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {validateEnvironment,wellMultipliers,environmentWeights,isFresh,seededPhase,describeChannel,ENV_NOTE,ENV_CHIPS,ENV_FRESH_MS} from '../lib/environment/environment-link.mjs';
import {saveEnvironment,readEnvironment,revokeEnvironment,ENV_PREFIX} from '../lib/environment/consent-store.mjs';
import * as E from '../lib/environment/environment-store.mjs';
import {createSandField,wellWeights} from '../lib/pocket-sand.mjs';
const src=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const good={light:{state:'MEASURED',level:.8,source:'camera-brightness'},sound:{state:'MEASURED',level:.2},motion:{state:'off'},heart:{state:'MEASURED',bpm:72,sqi:.9}};
const mem=()=>{const m=new Map();return {m,get:async n=>m.get(n)??null,put:async(n,t)=>{m.set(n,t);},del:async n=>{m.delete(n);}};};
const U='a'.repeat(40),V='b'.repeat(40);
test('valid numbers pass; unmeasured channels carry no values',()=>{
 const v=validateEnvironment(good);assert.ok(v.ok);assert.equal(v.numbers.motion.state,'off');assert.deepEqual(Object.keys(v.numbers.motion),['state']);
 assert.equal(validateEnvironment({light:{state:'denied'}}).numbers.light.state,'denied');assert.equal(validateEnvironment({}).numbers.sound.state,'off');});
test('anything that could be media or invented is refused with a plain reason',()=>{
 for(const bad of [null,[],{audio:[0.1]},{sound:{state:'MEASURED',level:.3,samples:[1,2]}},{sound:{state:'denied',level:.4}},{sound:{state:'MEASURED',level:2}},{sound:{state:'MEASURED',level:NaN}},{sound:{state:'MEASURED'}},
  {light:{state:'MEASURED',level:.5,source:'made-up'}},{heart:{state:'MEASURED',bpm:72,sqi:.3}},{heart:{state:'MEASURED',bpm:72}},{waveform:[1]},{motion:{state:'maybe'}}]){
  const v=validateEnvironment(bad);assert.equal(v.ok,false,JSON.stringify(bad));assert.equal(v.numbers,null);assert.ok(v.errors.length);}});
test('tilt is bounded, neutral when a channel is missing, and keeps the receipt weights otherwise',()=>{
 assert.deepEqual(wellMultipliers(null),[1,1,1,1]);const m=wellMultipliers(validateEnvironment(good).numbers);
 assert.ok(m.every(x=>x>=.6&&x<=1.4));assert.equal(m[2],1);
 const counts={'00':100,'01':300,'10':300,'11':300};const w=environmentWeights(counts,validateEnvironment(good).numbers);
 assert.ok(Math.abs(w.reduce((a,b)=>a+b,0)-4)<0.01);assert.notDeepEqual(w,wellWeights(counts));
 assert.deepEqual(environmentWeights(counts,null),wellWeights(counts));assert.deepEqual(environmentWeights(null,validateEnvironment({}).numbers),[1,1,1,1]);});
test('freshness: stale or all-off numbers never modulate the world',()=>{
 const n=validateEnvironment(good).numbers;assert.ok(isFresh(n,1000,1000+ENV_FRESH_MS));assert.equal(isFresh(n,1000,1001+ENV_FRESH_MS),false);
 assert.equal(isFresh(validateEnvironment({}).numbers,1000,1000),false);assert.equal(isFresh(null,1000,1000),false);});
test('sand field: environment tilts the same wells and null restores the receipt weights',()=>{
 const f=createSandField({seed:'t',count:8,counts:{'00':1,'01':1,'10':1,'11':1}});const base=f.wells.map(w=>w.w);
 f.setEnvironment([.5,1.5,1,1]);assert.equal(f.environment,true);assert.notDeepEqual(f.wells.map(w=>w.w),base);
 f.setCounts({'00':1,'01':1,'10':1,'11':1});assert.equal(f.wells[1].w,1.5);
 f.setEnvironment(null);assert.deepEqual(f.wells.map(w=>w.w),base);assert.equal(f.environment,false);f.setEnvironment([1,2]);assert.equal(f.environment,false);});
test('the same recorded seed places things deterministically (no Math.random anywhere new)',()=>{
 assert.equal(seededPhase('x'),seededPhase('x'));assert.notEqual(seededPhase('x'),seededPhase('y'));
 for(const p of ['lib/environment/environment-link.mjs','lib/environment/environment-store.mjs','lib/environment/consent-store.mjs','lib/environment/sensor-runtime.ts','components/environment-consent.tsx','app/api/environment/route.ts'])assert.doesNotMatch(src(p),/Math\.random/,p);});
test('hub: off by default; numbers are dropped without consent and at revoke',()=>{
 assert.equal(E.getEnvironment().consent,false);E.setEnvironmentNumbers(validateEnvironment(good).numbers,5);assert.equal(E.getEnvironment().numbers,null);
 E.grantEnvironment();E.setEnvironmentNumbers(validateEnvironment(good).numbers,5);assert.ok(E.getEnvironment().numbers);E.revokeEnvironmentLocal();assert.equal(E.getEnvironment().numbers,null);assert.equal(E.getEnvironment().consent,false);
 E.setHeartNumbers({bpm:70,sqi:.4,atMs:1});assert.equal(E.getHeartNumbers(2),null);E.setHeartNumbers({bpm:70,sqi:.9,atMs:1});assert.ok(E.getHeartNumbers(2));assert.equal(E.getHeartNumbers(1e7),null);E.setHeartNumbers(null);});
test('per-user private record: guest stores nothing, users are isolated, invalid is not stored, revoke erases',async()=>{
 const s=mem();assert.equal((await saveEnvironment(s,'',good,1)).status,401);assert.equal((await readEnvironment(s,'',1)).status,401);assert.equal(s.m.size,0);
 assert.equal((await saveEnvironment(s,U,{sound:{state:'MEASURED',level:9}},1)).status,400);assert.equal(s.m.size,0);
 const r=await saveEnvironment(s,U,good,1000);assert.equal(r.status,200);assert.equal(r.body.raw_media_stored,false);assert.deepEqual([...s.m.keys()],[ENV_PREFIX+U+'.json']);
 const rd=await readEnvironment(s,U,4000);assert.equal(rd.body.consent,true);assert.equal(rd.body.age_s,3);assert.equal(rd.body.numbers.heart.bpm,72);
 assert.equal((await readEnvironment(s,V,4000)).body.found,false);
 await saveEnvironment(s,'owner',good,1);assert.ok(s.m.has(ENV_PREFIX+'owner.json'));
 assert.equal((await revokeEnvironment(s,U)).body.erased,true);assert.equal((await readEnvironment(s,U,5)).body.consent,false);assert.ok(s.m.has(ENV_PREFIX+'owner.json'));
 assert.equal((await saveEnvironment(s,'../x',good,1)).status,401);});
test('route: per-user identity, same-origin writes, size cap, DELETE revokes, no secrets, and no unguarded owner features',()=>{
 const r=src('app/api/environment/route.ts');assert.match(r,/currentAccountId/);assert.match(r,/isOwner/);
 for(const fn of ['POST','DELETE'])assert.match(r.slice(r.indexOf('export async function '+fn)),/sameOrigin\(request\)/);
 assert.match(r,/415/);assert.match(r,/413/);assert.match(r,/401/);assert.match(r,/MAX_BODY=2000/);assert.doesNotMatch(r,/CONNECTION_STRING|SAS|api\/features|bridge/);});
test('UI: one consent control, default off, labels visible, revoke present, numbers only, 44px targets',()=>{
 const c=src('components/environment-consent.tsx');assert.match(c,/Share my world&apos;s signals/);assert.match(c,/Off until you turn it on\. Stop any time\./);assert.match(c,/data-environment-revoke/);assert.match(c,/validateEnvironment/);assert.match(c,/minHeight:48/);
 assert.doesNotMatch(c,/MediaRecorder|toBlob|createObjectURL|toDataURL/);
 const sr=src('lib/environment/sensor-runtime.ts');assert.doesNotMatch(sr,/MediaRecorder|toBlob|toDataURL|createObjectURL/);assert.match(sr,/denied/);assert.match(sr,/unavailable/);assert.match(sr,/getTracks\(\)\.forEach\(t=>t\.stop\(\)\)/);
 for(const w of ['RECORDED','SIMULATED','MEASURED','SEEDED'])assert.match(ENV_NOTE,new RegExp(w));
 assert.match(describeChannel('sound',{state:'denied'}),/declined/);assert.match(describeChannel('heart',{state:'unavailable'}),/no valid pulse/);
 const hp=src('components/home-pocket.tsx');assert.match(hp,/EnvironmentConsent/);assert.match(hp,/data-open-environment/);
 const cp=src('components/cage-pocket-dimension.tsx');assert.match(cp,/environmentWeights\(sand\.field\.counts/);assert.match(cp,/isFresh\(/);});
test('consent card copy: five switches plus one camera switch, short card text, long text only on /privacy',()=>{
 const c=src('components/environment-consent.tsx');
 for(const t of ['Give your universe more life','Stop sharing','Stopped\\. Saved numbers deleted\\.','No valid pulse','Waiting for permission','Needs camera switch','Paused: reading pulse','Permission declined','Unavailable here','Turn on world signals\\?','Yes, give it life','Not now','Stop sharing deletes your saved numbers\\.'])assert.match(c,new RegExp(t),t);
 for(const l of ['Time of day','Device motion','Light level','Sound level','Fingertip pulse','Uses your clock','Uses the camera\\.','Uses the microphone\\.'])assert.match(c,new RegExp(l),l);
 // five switch rows are declared, a camera switch row is added, and nothing starts on its own
 assert.equal((c.match(/\{k:'(time|motion|light|sound|pulse)'/g)||[]).length,5);assert.match(c,/row\('camera'/);assert.match(c,/const allOff:Sw=\{time:false,motion:false,light:false,sound:false,pulse:false,camera:false\}/);
 assert.match(c,/href="\/privacy#labels-and-signals"/);assert.match(c,/width:120,height:44/);
 // the long explanations moved to /privacy; the card carries only short chips
 assert.doesNotMatch(c,/ENV_NOTE|RECORDED on IBM hardware|never leaves/);assert.doesNotMatch(c,/live quantum|weather/i);
 // light waits for the camera switch and for a pulse read; the pulse flow says so explicitly
 assert.match(c,/sw\.light&&sw\.camera&&!env\.pulseReading/);
 const bio=src('components/real-ibm-bio.tsx');assert.match(bio,/signalPulse\('pulse_read_started'\)/);assert.match(bio,/finally\{signalPulse\('pulse_read_ended'\)/);
 assert.match(src('components/home-pocket.tsx'),/beastName=\{beastDisplayName\(beast\)\}/);
 assert.doesNotMatch(c,/\bconfirm\(/);assert.match(c,/onClick=\{\(\)=>void stop\(\)\}/);// Stop sharing is one tap: no confirm step
 assert.match(ENV_NOTE,/RECORDED on IBM hardware/);assert.doesNotMatch(c,/ENV_CHIPS|data-env-chips/);// honesty chips are only on /privacy; assert.deepEqual([...ENV_CHIPS],['IBM seed RECORDED','Rigetti run SIMULATED','Your reading MEASURED','Effect on your world SEEDED']);
});
test('time of day and pulse signals: bounded lean, off by default, explicit start/end',()=>{
 const t=validateEnvironment({time:{state:'MEASURED',level:0.5}});assert.ok(t.ok);assert.equal(validateEnvironment({}).numbers.time.state,'off');
 assert.equal(validateEnvironment({time:{state:'MEASURED',level:1.5}}).ok,false);assert.equal(validateEnvironment({time:{state:'MEASURED'}}).ok,false);
 for(const lv of [0,.13,.5,.77,1]){const m=wellMultipliers({...validateEnvironment(good).numbers,time:{state:'MEASURED',level:lv}});assert.ok(m.every(x=>x>=.6&&x<=1.4));}
 assert.notDeepEqual(wellMultipliers({time:{state:'MEASURED',level:0}}),wellMultipliers({time:{state:'MEASURED',level:.5}}));assert.deepEqual(wellMultipliers({time:{state:'off'}}),[1,1,1,1]);
 assert.equal(isFresh(t.numbers,1000,1000),true);assert.match(describeChannel('time',{state:'MEASURED',level:.5}),/your clock/);
 assert.equal(E.isPulseReading(),false);E.signalPulse('pulse_read_ended');assert.equal(E.isPulseReading(),false);E.signalPulse('pulse_read_started');assert.equal(E.isPulseReading(),true);
 E.grantEnvironment();E.revokeEnvironmentLocal();assert.equal(E.isPulseReading(),true);E.signalPulse('pulse_read_ended');assert.equal(E.isPulseReading(),false);
});
test('old three-channel posts still validate (additive)',()=>{const v=validateEnvironment(good);assert.ok(v.ok);assert.equal(v.numbers.time.state,'off');});
test('status lines: every server/status string on the card is 44 characters or fewer, with the approved short wording',()=>{
 const c=src('components/environment-consent.tsx'),fixes=JSON.parse(src('tests/fixtures/consent_status_fixes.json'));
 const all=[...c.matchAll(/'((?:[^'\\]|\\.)*)'/g)].map(m=>m[1].replace(/\\'/g,"'")).filter(t=>/Nothing is stored|Saved |Stopped|Couldn't|storage|Used on this device|not available/i.test(t));
 for(const k of ['status_not_signed_in','status_saved_record','status_stored','status_no_storage','status_stop_erase_failed','status_stop_unreachable','status_check_failed','pulse_not_ready_hint','pulse_not_ready_row'])assert.ok(c.replace(/\\'/g,"'").includes(fixes[k]),k+': '+fixes[k]);
 for(const t of all)assert.ok(t.length<=44,t.length+' chars: '+t);assert.ok(all.length>=8);
 for(const old of ['Not signed in: your numbers','Your account has a saved record','Stored privately for your account','Private storage is not set up on this site','could not be erased right now','could not reach the site to erase','Could not reach the site to check'])assert.ok(!c.includes(old),old);
 assert.ok(fixes.pulse_not_ready_row.length<=22,'status slot holds 22');
});
test('pulse for visitors: never faked. Not available yet, switch disabled, hint matches, owner flow unchanged',()=>{
 const c=src('components/environment-consent.tsx');
 assert.match(c,/fetch\('\/api\/session'/);assert.match(c,/useState\(false\)/);// visitor until the session says owner
 assert.match(c,/if\(k==='pulse'&&!isOwnerView\)return PULSE_NOT_READY_ROW/);assert.match(c,/disabled=\{!env\.consent\|\|locked\}/);assert.match(c,/if\(locked\)hint=PULSE_NOT_READY_HINT/);
 assert.match(c,/PULSE_NOT_READY_HINT='Not available here yet\.'/);assert.ok('Not available here yet.'.length<=35,'hint slot holds 35');assert.ok(!/hint=PULSE_NOT_READY_LONG/.test(c)&&/\{PULSE_NOT_READY_LONG\}/.test(c));// the 40-char line lives only in the full-width notice line
 assert.match(c,/w\.pulse&&w\.camera&&isOwnerRef\.current/g);// visitors never send heart numbers
 assert.match(c,/Uses the camera\. Beats per minute\./);// owner hint kept
 assert.match(c,/'No valid pulse'/);// owner flow unchanged
});
