import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {createIdleLife,catchUpIdleLife,MAX_CATCHUP_TICKS,describeIdleSource,IDLE_ORIGIN_ARTIST,classicalArtistSeed} from '../lib/companion/idle-life.mjs';
import {explainCreature} from '../lib/companion/family-explain.mjs';
const r=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const zeref=JSON.parse(r('public/spark/zeref-live-20261010/unsigned-session.json')).beast;
test('idle-life catch-up is bounded and makes no network or receipt claims',()=>{
 const src=r('lib/companion/idle-life.mjs');assert.doesNotMatch(src,/fetch\(|XMLHttpRequest|localStorage/);
 assert.ok(MAX_CATCHUP_TICKS<=24);});
test('family explanation is honest: recorded seed, no invented jobs',()=>{
 const e=explainCreature(zeref,{mode:'friendly'});for(const k of ['seed','memory','behavior','growth','next'])assert.equal(typeof e.friendly[k],'string');
 assert.equal(e.advanced,null);const a=explainCreature(zeref,{mode:'advanced'}).advanced;assert.equal(a.hardwareClass,'recorded-ibm-hardware');
 assert.equal(explainCreature({},{mode:'advanced'}).advanced.jobId,null);});
test('only one grow button per saved creature; Spark eyebrow is plain words',()=>{
 assert.match(r('components/beast-cage-portal.tsx'),/showGrow=\{!sameSpark\}/);assert.match(r('components/zeref-diary-panel.tsx'),/showGrow\?<GrowInCosmos/);
 assert.doesNotMatch(r('public/spark/index.html'),/ACTIVE QBEAST/);assert.match(r('components/creature-dashboard.tsx'),/<FamilyExplain input=\{beast\}\/>/);});
test('3D Zeref toggle on home; flat-art and classic guide toggles kept',()=>{const h=r('components/homepage-creature.tsx');
 for(const k of ['>Zeref<','>3D Zeref<','>Classic 3D guide<'])assert.ok(h.includes(k),k);assert.match(h,/dimensionalId=/);});
