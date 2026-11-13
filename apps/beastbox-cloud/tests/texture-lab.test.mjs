import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {SeededSimplex,tileableFbm,bakeGroundDetail,groundDetailSize,TEXTURE_LAB_LABEL} from '../lib/look/third-party/texture-lab.ts';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');

test('third-party texture lab: seeded (same seed, same bytes; new seed, new bytes), no Math.random',()=>{
 const a=bakeGroundDetail('tiny',32),b=bakeGroundDetail('tiny',32),c=bakeGroundDetail('other',32);
 assert.deepEqual(a,b);assert.notDeepEqual(a,c);
 assert.doesNotMatch(read('lib/look/third-party/texture-lab.ts'),/Math\.random/);
});
test('third-party texture lab: torus fbm wraps with no seam (u=0 matches u=1 within one 8-bit step), so no tile grid',()=>{
 const s=new SeededSimplex('tiny');
 for(const v of [0,.13,.5,.87]){assert.ok(Math.abs(tileableFbm(s,0,v,4)-tileableFbm(s,1,v,4))<2e-3);assert.ok(Math.abs(tileableFbm(s,v,0,4)-tileableFbm(s,v,1,4))<2e-3);}
});
test('third-party texture lab: tier-scaled (LOW none), MIT attribution in the header and the notices file, labelled',()=>{
 assert.equal(groundDetailSize('LOW'),0);assert.ok(groundDetailSize('GOD')>=groundDetailSize('MED'));
 const src=read('lib/look/third-party/texture-lab.ts');assert.match(src,/THIRD-PARTY \(MIT\)/);assert.match(src,/Copyright \(c\) 2026 Paulius/);
 const n=read('THIRD_PARTY_NOTICES.md');assert.match(n,/pallet-town-3d/);assert.match(n,/MIT License/);
 assert.match(TEXTURE_LAB_LABEL,/third-party/);
});
test('planet twin: seeded biomes run after the Park grade and the detail relief is tier-gated',()=>{
 const s=read('lib/look/park-planet.ts');assert.match(s,/pkBiome/);assert.match(s,/uPkDet/);assert.match(s,/groundDetailSize\(tier\)/);
});
