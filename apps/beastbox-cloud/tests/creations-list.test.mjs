import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {listCreations,savedRoamers,homeLabel,depthFar,MAX_SAVED_ROAMERS} from '../lib/companion/creations.mjs';
import {ARTIST_RESIDENTS} from '../lib/companion/artist-residents.mjs';
const src=f=>readFileSync(new URL(f,import.meta.url),'utf8');
const g=(n)=>({stage:1,names:{1:n},body:'fox',island:'Cinder Drift'});
const session={beast:{seed:'s1',displayName:'Zeref-Nightcat-Dragon',genome:g('x')},bestiary:[{seed:'s1',name:'Zeref-Nightcat-Dragon',genome:g('x')},{seed:'s2',name:'Mossy',genome:g('Mossy'),body:'fox',island:'Cinder Drift'},{seed:'s3',genome:g('Pebble')}]};
test('one list: active beast, every saved beast once, then every artist resident',()=>{
 const l=listCreations(session);assert.deepEqual(l.map(c=>c.kind),['active','saved','saved',...ARTIST_RESIDENTS.map(r=>r.kind)]);
 assert.equal(l[0].name,'Zeref \u00b7 Nightcat Dragon');assert.equal(l.filter(c=>c.id==='seed:s1').length,1);assert.equal(l[2].name,'Pebble');
 for(const r of ARTIST_RESIDENTS)assert.ok(l.some(c=>c.id===r.id&&c.art===r.views.front&&/NO QUANTUM SEED/.test(c.origin)));
 for(const c of l.filter(c=>c.seed))assert.match(c.origin,/SEEDED/);});
test('no session still lists the artist residents; the empty state reads "{beast}\u2019s home"',()=>{
 assert.equal(listCreations(null).length,ARTIST_RESIDENTS.length);assert.equal(homeLabel('Zeref \u00b7 Nightcat Dragon'),'Zeref \u00b7 Nightcat Dragon\u2019s home');assert.equal(homeLabel(null),'Your beast\u2019s home');});
test('saved roamers exclude the active beast and are capped',()=>{
 assert.deepEqual(savedRoamers(session).map(c=>c.seed),['s2','s3']);assert.equal(savedRoamers(session,1).length,1);assert.equal(savedRoamers(session,0).length,0);assert.ok(MAX_SAVED_ROAMERS>=4);
 const many={beast:null,bestiary:Array.from({length:20},(_,i)=>({seed:'k'+i,genome:g('n'+i)}))};assert.equal(savedRoamers(many).length,MAX_SAVED_ROAMERS);});
test('depth treatment: 0 near, 1 far, monotonic, never NaN',()=>{
 assert.equal(depthFar(1),0);assert.equal(depthFar(20),1);assert.ok(depthFar(5)>0&&depthFar(5)<depthFar(7));assert.equal(depthFar(NaN),0);});
test('the pocket and its legend read the same list',()=>{
 const p=src('../components/cage-pocket-dimension.tsx');assert.match(p,/readCreations\(\)\.filter\(c=>c\.kind==='saved'/);assert.doesNotMatch(p,/localStorage/);assert.match(p,/useCreations\(\)/);assert.match(p,/data-creations-empty/);assert.match(p,/homeLabel\(homeName\)/);
 assert.match(src('../components/pocket-saved-beasts.ts'),/depthFar\(/);});
