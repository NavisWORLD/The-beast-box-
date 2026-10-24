import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {zoomLineKind,doorLineKind,zoomLine,noticeLine,noticeGate,NOTICE_KEYS} from '../lib/universe/zoom-lines.mjs';
import {LW_LINES} from '../lib/universe/living-world-lines.mjs';
const J=JSON.parse(fs.readFileSync(new URL('../lib/universe/data/living_world_lines.json',import.meta.url),'utf8'));
test('Emeth text is exact and every line is toast-sized',()=>{
 assert.deepEqual(LW_LINES.zoom_out,J.zoom_out);assert.deepEqual(LW_LINES.zoom_in,J.zoom_in);assert.deepEqual(LW_LINES.creature_notices,J.creature_notices);
 assert.deepEqual(Object.keys(J.zoom_out),['leave_ground','see_globe','see_sun','see_planets','see_stars','see_black_hole','far_out']);
 assert.deepEqual(Object.keys(J.zoom_in),['toward_stars','toward_planet','arrive_home']);
 for(const g of [J.zoom_out,J.zoom_in,J.creature_notices])for(const a of Object.values(g))for(const l of a)assert.ok(l.replace('{beast}','Zeref').length<=62,l);
 assert.equal(NOTICE_KEYS.length,9);
});
test('stage changes pick the right key and a black hole only on the way out of the universe',()=>{
 assert.deepEqual(zoomLineKind('Planet','Orbit'),{kind:'zoom_out',key:'see_sun'});
 assert.deepEqual(zoomLineKind('Neighbours','Universe',{blackHole:true}),{kind:'zoom_out',key:'see_black_hole'});
 assert.deepEqual(zoomLineKind('Neighbours','Universe'),{kind:'zoom_out',key:'far_out'});
 assert.deepEqual(zoomLineKind('Orbit','System'),{kind:'zoom_out',key:'see_planets'});
 assert.deepEqual(zoomLineKind('Neighbours','System'),{kind:'zoom_in',key:'toward_stars'});
 assert.deepEqual(zoomLineKind('System','Orbit'),{kind:'zoom_in',key:'toward_planet'});
 assert.equal(zoomLineKind('Orbit','Planet').key,null);assert.equal(zoomLineKind('Orbit','Orbit'),null);
 assert.deepEqual(doorLineKind(1,.5),{kind:'zoom_out',key:'leave_ground'});assert.deepEqual(doorLineKind(.4,1),{kind:'zoom_in',key:'arrive_home'});assert.equal(doorLineKind(.3,.5),null);
});
test('lines are deterministic, verbatim from the pool, and {beast} is filled',()=>{
 const a=zoomLine('zoom_out','see_globe','s',0);assert.equal(a,zoomLine('zoom_out','see_globe','s',0));assert.ok(J.zoom_out.see_globe.includes(a));
 for(const k of NOTICE_KEYS)for(const name of ['Zeref','Luma']){const l=noticeLine(k,name,'s',3);assert.ok(!l.includes('{beast}'));assert.ok(J.creature_notices[k].map(x=>x.split('{beast}').join(name)).includes(l));}
 assert.ok(noticeLine('storm_far',null,'s').length>0);assert.equal(noticeLine('nope','x','s'),null);
});
test('notice gate spaces lines out and does not repeat one too soon',()=>{
 let g=noticeGate(null,'storm_far',0);assert.ok(g.show);
 let h=noticeGate(g.state,'sea_life_fish',5000);assert.ok(!h.show);
 h=noticeGate(g.state,'sea_life_fish',25000);assert.ok(h.show);
 const r=noticeGate(h.state,'storm_far',50000);assert.ok(!r.show);assert.ok(noticeGate(h.state,'storm_far',100000).show);
});

import {readFileSync as _rf} from 'node:fs';
test('creature_notices are wired into the 3D universe and the living world with the active beast name', () => {
  const u3=_rf(new URL('../components/universe-3d.tsx',import.meta.url),'utf8'),lw=_rf(new URL('../components/living-world.tsx',import.meta.url),'utf8');
  for(const k of ['black_hole_far','black_hole_near','black_hole_away','storm_far','storm_near','storm_passes'])assert.ok(u3.includes(`'${k}'`)||lw.includes(`'${k}'`),k);
  assert.ok(u3.includes('noticeLine(key,beastRef.current'));assert.ok(lw.includes("noticeLine(key,beastName"));
});
