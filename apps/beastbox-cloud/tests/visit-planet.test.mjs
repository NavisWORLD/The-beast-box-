import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const lw=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
const tv=readFileSync(new URL('../components/tiny-universe-view.tsx',import.meta.url),'utf8');
test('?planet=<id> re-seeds from the recorded seed and the planet id (no clock, no random)',()=>{
 assert.match(lw,/seed:u\.seed\+':visit:'\+visitPl\.id/);assert.match(lw,/get\('planet'\)/);
 const blk=lw.slice(lw.indexOf('?planet=<id>'),lw.indexOf('?planet=<id>')+1500);assert.ok(!/Math\.random/.test(blk));});
test('a visit saves nothing and keeps growth nodes a home-world feature',()=>{
 assert.match(lw,/lwStore:Pick<Storage,'setItem'>=VISIT\?\{setItem:\(\)=>\{\}\}:localStorage/);assert.ok(!/localStorage\.setItem\(/.test(lw));
 assert.match(lw,/const gOn=!VISIT&&/);});
test('visit pill is labelled SEEDED and not a measured surface; default home world untouched',()=>{
 assert.match(lw,/data-lw-visit/);assert.match(lw,/SEEDED \(not a measured surface\)/);assert.match(lw,/const VISIT=!!visitPl/);});
test('/universe offers the visit link only for a non-home planet',()=>{assert.match(tv,/data-visit-planet/);assert.match(tv,/beast-cage\/world\?planet=/);});
