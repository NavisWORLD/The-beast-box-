import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';import {createHash} from 'node:crypto';
import {analysePpg} from '../lib/bio/ppg.mjs';import {buildBioPacket} from '../lib/bio/bio-packet.mjs';
import {savePacket,latestStatus,PACKET_PREFIX,PACKET_MAX_AGE_S} from '../lib/bio/packet-store.mjs';
import {buildFeaturePosts,heartFeatures,audioFeatures,unit} from '../lib/bio/features-feed.mjs';
import {synth} from './helpers-bio-synth.mjs';
const sha=s=>createHash('sha256').update(s).digest('hex');
const mk=async(audio=null)=>buildBioPacket({ppg:analysePpg(synth({})),light:{red_mean:200,green_mean:40,blue_mean:30,red_ac_dc:.01},audio},sha);
const mem=()=>{const m=new Map();return {m,put:async(n,t)=>{m.set(n,t);},get:async n=>m.get(n)??null};};
const NOW=Date.parse('2026-10-25T23:00:00Z');
test('the box can read what the phone saved: a valid packet is stored under its hash and as latest, numbers only',async()=>{
 const s=mem();const p=await mk();const r=await savePacket(s,p,NOW);
 assert.equal(r.status,200);assert.equal(r.body.raw_media_stored,false);
 assert.ok(s.m.has(PACKET_PREFIX+p.packet_sha256.slice(0,12)+'.json'));assert.ok(s.m.has(PACKET_PREFIX+'latest.json'));
 const env=JSON.parse(s.m.get(PACKET_PREFIX+'latest.json'));assert.deepEqual(env.packet,p);
 const st=await latestStatus(s,NOW+60000);assert.equal(st.body.valid,true);assert.equal(st.body.age_s,60);assert.equal(st.body.recent,true);assert.equal(st.body.heartbeat,'MEASURED');
 assert.ok(!('packet' in st.body)&&!JSON.stringify(st.body).includes(p.packet_sha256));});
test('invalid, tampered or raw-media packets are never stored (no valid pulse is never invented)',async()=>{
 const p=await mk();for(const bad of [null,{},{...p,raw_video_published:true},{...p,pulse:{...p.pulse,bpm:p.pulse.bpm+5}},{...p,video:'AAAA'}]){const s=mem();const r=await savePacket(s,bad,NOW);assert.equal(r.status,400);assert.equal(s.m.size,0);}});
test('status: nothing saved, and an old packet is reported as not recent',async()=>{
 const s=mem();assert.equal((await latestStatus(s,NOW)).body.found,false);
 await savePacket(s,await mk(),NOW);assert.equal((await latestStatus(s,NOW+(PACKET_MAX_AGE_S+5)*1000)).body.recent,false);});
test('packet route is owner-first, same-origin, JSON-only, size-capped, and never returns the stored packet',()=>{
 const src=readFileSync(new URL('../app/api/bio-connection/packet/route.ts',import.meta.url),'utf8');
 for(const fn of ['POST','GET']){const body=src.slice(src.indexOf('export async function '+fn));const iOwner=body.indexOf('isOwner()');assert.ok(iOwner>=0&&iOwner<body.indexOf('store()'),fn);assert.match(body.slice(iOwner,iOwner+120),/401/);}
 assert.match(src,/origin!==new URL/);assert.match(src,/415/);assert.match(src,/413/);assert.doesNotMatch(src,/SAS|CONNECTION_STRING|process\.env/);});
test('send-numbers feed: heart numbers on the bridge scale, HRV only when measured, nothing invented',async()=>{
 const p=await mk();const [h]=buildFeaturePosts(p);
 assert.equal(h.kind,'heart');assert.equal(h.opt_in,true);
 assert.deepEqual(Object.keys(h.features).sort(),['bpm_norm','hrv_norm','rr_regularity','signal_quality']);
 assert.equal(h.features.bpm_norm,Math.round(unit(p.pulse.bpm,40,180)*1e4)/1e4);
 for(const v of Object.values(h.features))assert.ok(v>=-1&&v<=1);
 const noHrv={...p,pulse:{...p.pulse,hrv_rmssd_ms:null}};assert.ok(!('hrv_norm' in heartFeatures(noHrv)));
 assert.ok(!('bpm_trend' in h.features)&&!('rest_delta' in h.features));});
test('send-numbers feed: audio only when the mic was on; light is never sent; only numbers',async()=>{
 const off=buildFeaturePosts(await mk());assert.deepEqual(off.map(x=>x.kind),['heart']);
 const p=await mk({enabled:true,rms_mean:.2,zcr:.1,centroid_norm:.3});const posts=buildFeaturePosts(p);
 assert.deepEqual(posts.map(x=>x.kind),['heart','audio']);assert.deepEqual(Object.keys(audioFeatures(p)).sort(),['rms','spectral_centroid','zero_crossing']);
 for(const x of posts){assert.deepEqual(Object.keys(x).sort(),['features','kind','opt_in']);assert.ok(Object.values(x.features).every(v=>typeof v==='number'&&Number.isFinite(v)));}
 assert.ok(!posts.some(x=>x.kind==='light'));});
test('send-numbers feed refuses anything that is not a MEASURED numbers-only packet',async()=>{
 const p=await mk();for(const bad of [null,{...p,heartbeat_label:'SIMULATED'},{...p,raw_video_published:true}])assert.throws(()=>buildFeaturePosts(bad),/no valid pulse/);});
test('UI: the Zeref feed is opt-in (default off), posts to the owner bridge only, and shows the snapshot caveat',()=>{
 const src=readFileSync(new URL('../components/real-ibm-bio.tsx',import.meta.url),'utf8');
 assert.match(src,/useState\(false\)[^\n]*sendZeref|sendZeref[^\n]*useState\(false\)/);assert.match(src,/if\(sendZeref\)/);assert.match(src,/\/api\/bridge\/features/);assert.match(src,/FEED_NOTE/);assert.match(src,/\/api\/bio-connection\/packet/);
 assert.doesNotMatch(src,/MediaRecorder|toBlob|createObjectURL/);});
