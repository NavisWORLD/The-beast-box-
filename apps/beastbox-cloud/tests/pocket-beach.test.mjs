import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {placeLine,LW_LINES} from '../lib/universe/living-alive.mjs';
import {GC} from '../lib/universe/surface-data.mjs';
test('landscape_places lines fire seeded and stable',()=>{const a=placeLine('reach_beach','s',1);assert.ok(LW_LINES.landscape_places.reach_beach.includes(a));assert.equal(a,placeLine('reach_beach','s',1));assert.equal(placeLine('nope','s',1),null);});
test('beach density merged additively',()=>{const b=GC.biomes.beach.per_m2;assert.equal(b.palm_a,0.004);assert.ok('tidepool_rock' in b);});
test('beach is not linked in nav, GLBs shipped',()=>{assert.ok(!fs.readFileSync('lib/site-nav.ts','utf8').includes("href:'/beach-two'"));for(const f of ['beach_shore_near','palm_a','palm_b','palm_c','driftwood','tidepool_rock','shell_spiral'])assert.ok(fs.existsSync('public/universe/livingworld/landforms/beach/models/'+f+'.glb'));});
