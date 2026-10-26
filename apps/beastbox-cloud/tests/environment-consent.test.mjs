import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {validateEnvironment,wellMultipliers,environmentWeights,isFresh,seededPhase,describeChannel,ENV_NOTE,ENV_FRESH_MS} from '../lib/environment/environment-link.mjs';
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
 const c=src('components/environment-consent.tsx');assert.match(c,/I consent to sharing my world&apos;s signals \(off until you turn it on/);assert.match(c,/data-environment-revoke/);assert.match(c,/ENV_NOTE/);assert.match(c,/validateEnvironment/);assert.match(c,/minHeight:44/);
 assert.doesNotMatch(c,/MediaRecorder|toBlob|createObjectURL|toDataURL/);
 const sr=src('lib/environment/sensor-runtime.ts');assert.doesNotMatch(sr,/MediaRecorder|toBlob|toDataURL|createObjectURL/);assert.match(sr,/denied/);assert.match(sr,/unavailable/);assert.match(sr,/getTracks\(\)\.forEach\(t=>t\.stop\(\)\)/);
 for(const w of ['RECORDED','SIMULATED','MEASURED','SEEDED'])assert.match(ENV_NOTE,new RegExp(w));
 assert.match(describeChannel('sound',{state:'denied'}),/declined/);assert.match(describeChannel('heart',{state:'unavailable'}),/no valid pulse/);
 const hp=src('components/home-pocket.tsx');assert.match(hp,/EnvironmentConsent/);assert.match(hp,/data-open-environment/);
 const cp=src('components/cage-pocket-dimension.tsx');assert.match(cp,/environmentWeights\(sand\.field\.counts/);assert.match(cp,/isFresh\(/);});
test('consent card copy says exactly what this card does (end-game wording)',()=>{
 const c=src('components/environment-consent.tsx');
 assert.match(c,/Give your universe more life/);assert.match(c,/Stop sharing/);assert.match(c,/Stopped\. Saved numbers deleted\./);assert.match(c,/No valid pulse/);assert.match(c,/waiting for permission/);
 assert.match(c,/RECORDED on IBM hardware/);assert.doesNotMatch(c,/Revoke and erase/);
 // three switches really exist: light, sound, motion; pulse is read on IBM BIO, not here (no pulse/time/camera switch is claimed)
 assert.equal((c.match(/\{row\('/g)||[]).length,3);assert.doesNotMatch(c,/row\('(pulse|time|camera)'/);
 assert.match(ENV_NOTE,/RECORDED on IBM hardware/);assert.doesNotMatch(ENV_NOTE+c,/live quantum|weather/i);
});
