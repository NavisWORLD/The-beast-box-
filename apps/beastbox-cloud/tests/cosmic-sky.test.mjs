import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {COSMIC_SKY_LABEL,cosmicSkyBudget} from '../lib/look/cosmic-sky.ts';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');

test('cosmic sky: tier-scaled, LOW off (keeps the plain navy space + stars, never black)',()=>{
 assert.equal(cosmicSkyBudget('LOW').on,false);
 assert.ok(cosmicSkyBudget('MED').octaves<cosmicSkyBudget('GOD').octaves);
 assert.equal(cosmicSkyBudget('HIGH').on,true);
});
test('cosmic sky: honest label, seeded, no Math.random, no own clock',()=>{
 assert.match(COSMIC_SKY_LABEL,/SEEDED/);assert.doesNotMatch(COSMIC_SKY_LABEL,/real physics|live quantum/i);
 const s=read('lib/look/cosmic-sky.ts');assert.doesNotMatch(s,/Math\.random|Date\.now|performance\.now/);
});
test('planet twin: soft terminator, cloud shadows and sea glint ride the one sun (uPkSun), no Math.random',()=>{
 const s=read('lib/look/park-planet.ts');assert.match(s,/uPkSun/);assert.match(s,/uPkCloud/);assert.doesNotMatch(s,/Math\.random/);
 const lw=read('components/living-world.tsx');assert.match(lw,/addCosmicSky\(THREE,scene,\{seed:/);
});
