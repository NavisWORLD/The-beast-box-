// GENESIS X P3 ocean: engine sea + one sun + storm; SEEDED bay; no random calls; honest labels.
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {OCEAN3,bayFrom,oceanAt,waveLayers} from '../lib/universe/p3-ocean.mjs';
import {lwStream} from '../lib/universe/living-world.mjs';
const three=readFileSync(new URL('../lib/universe/p3-ocean-three.ts',import.meta.url),'utf8');
const pure=readFileSync(new URL('../lib/universe/p3-ocean.mjs',import.meta.url),'utf8');
const lw=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
test('labels are honest',()=>{assert.equal(OCEAN3.label,'SEEDED');assert.equal(OCEAN3.motion,'SIMULATED');const o=oceanAt({day:1,sunElev:.5});assert.equal(o.label,'DERIVED');assert.equal(o.motion,'SIMULATED');
 for(const s of [three,pure])assert.doesNotMatch(s,/real physics|\bAI\b/);});
test('no Math.random, no own clock',()=>{for(const s of [three,pure]){assert.doesNotMatch(s,/Math\.random/);assert.doesNotMatch(s,/Date\.now|performance\.now/);}});
test('storm roughens the sea and dims the glitter',()=>{const calm=oceanAt({storm:0,day:1,sunElev:.6}),st=oceanAt({storm:1,day:1,sunElev:.6});
 assert.ok(st.rough>calm.rough);assert.ok(st.ampM>calm.ampM);assert.ok(st.whitecap>calm.whitecap);assert.ok(st.glint<calm.glint);});
test('only the one sun lights it: no glitter at night',()=>{assert.equal(oceanAt({day:0,sunElev:-.3}).glint,0);assert.ok(oceanAt({day:1,sunElev:.5}).glint>0);});
test('bay is seeded and repeatable',()=>{const a=bayFrom(lwStream('s1:p3-bay')),b=bayFrom(lwStream('s1:p3-bay')),c=bayFrom(lwStream('s2:p3-bay'));assert.deepEqual(a,b);assert.notDeepEqual(a,c);
 assert.ok(a.halfWidth>=OCEAN3.halfWidthDeg[0]*Math.PI/180-1e-6&&a.halfWidth<=OCEAN3.halfWidthDeg[1]*Math.PI/180+1e-6);});
test('waves use the SEA layers with deep-water speeds',()=>{const L=waveLayers();assert.equal(L.length,4);for(const l of L)assert.ok(Math.abs(l[2]-Math.sqrt(9.81*l[0]/(2*Math.PI)))<1e-3);});
test('wired to the engine clock and the one sun in first person',()=>{assert.match(lw,/p3\.update\(field\?\(field\.tick\+field\.clock\.alpha\)\/4:t,o3,sunDir/);assert.match(lw,/addP3Ocean\(THREE,lk2Ground\.group/);});
