// Cory Nov 12 (iPhone, First person, LOW): "the background shouldn't be 2D". Locks the fix: 3D displaced ridge bands on every tier, LOW far hills,
// no rain out of a clear sky, phones keep MED unless really slow, a round tiered pine instead of the 5-sided cone.
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {autoTier} from '../lib/universe/post-tiers.mjs';
import {dropTierIfSlow} from '../lib/look/tiers.ts';
import {ringPlan} from '../lib/look/terrain-lod.ts';
const rd=f=>readFileSync(new URL('../'+f,import.meta.url),'utf8');
test('ridges are real 3D displaced bands (no flat card cut by discard), lit by the one sun',()=>{
 const s=rd('lib/universe/one-world-look.ts');const a=s.indexOf('const mkRidge='),b=s.indexOf('for(const r of RIDGES){');const r=s.slice(a,b);
 assert.match(r,/attribute float aS/);assert.match(r,/p\.y=h\*uTop\*pr/);assert.doesNotMatch(r,/\)discard;/);assert.doesNotMatch(r,/CylinderGeometry/);
 assert.match(s,/for\(const u of RU\)u\.uSun\?\.value\.copy\(v\)/);});
test('ridges stay visible under the Park look (they are 3D hills now)',()=>{assert.doesNotMatch(rd('components/living-world.tsx'),/conceal:\(\)=>\[[^\]]*renderOrder===-11/);});
test('LOW and MED reach the haze with real terrain',()=>{assert.equal(ringPlan('LOW').length,4);assert.ok(ringPlan('LOW').at(-1).r1>=400);assert.ok(ringPlan('MED').at(-1).r1>=480);});
test('a modern iPhone (Safari reports 4 cores, no deviceMemory) starts on MED; MED only drops when really slow',()=>{
 assert.equal(autoTier({phone:true,cores:4}),'MED');assert.equal(autoTier({phone:true,cores:2}),'LOW');assert.equal(autoTier({phone:true,cores:4,memoryGB:2}),'LOW');
 assert.equal(dropTierIfSlow('MED',25,'MED'),'MED');assert.equal(dropTierIfSlow('MED',40,'MED'),'LOW');assert.equal(dropTierIfSlow('HIGH',21,'HIGH'),'MED');});
test('no rain streaks out of a clear sky',()=>{const lw=rd('components/living-world.tsx');assert.match(lw,/weather\.rain\*Math\.min\(1,Math\.max\(0,\(\(weather\.cloud\?\?1\)-\.45\)\/\.25\)\)/);});
test('Genesis pine is a round tiered lathe, not a 5-sided cone; far sea hazes to the horizon',()=>{const f=rd('lib/look/foliage.ts');assert.doesNotMatch(f,/ConeGeometry\(\.28,1\.15,5\)/);assert.match(f,/LatheGeometry/);
 assert.match(rd('lib/look/water.ts'),/smoothstep\(25\.0,110\.0,vDl\)/);});
test('no random calls in the touched files',()=>{for(const f of ['lib/universe/one-world-look.ts','lib/look/foliage.ts','lib/look/water.ts','lib/look/terrain-lod.ts'])assert.doesNotMatch(rd(f),/Math\.random/);});
