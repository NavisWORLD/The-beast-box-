import test from 'node:test';import assert from 'node:assert/strict';import {existsSync,readFileSync} from 'node:fs';
import {ARTIST_RESIDENTS,ARTIST_ORIGIN,residentView} from '../lib/companion/artist-residents.mjs';
test('five distinct artist residents with own art and no fabricated seed',()=>{
 assert.equal(ARTIST_RESIDENTS.length,5);const ids=new Set(ARTIST_RESIDENTS.map(r=>r.id));assert.equal(ids.size,5);
 for(const r of ARTIST_RESIDENTS){assert.equal(r.quantumSeed,null);assert.equal(r.origin,ARTIST_ORIGIN);assert.ok(!/bb-7f9c2a03|bb-deada969/.test(r.id));
  for(const src of Object.values(r.views))assert.ok(existsSync(new URL('../public'+src,import.meta.url)),src);}
 assert.equal(ARTIST_RESIDENTS.filter(r=>r.kind==='trainer').map(r=>r.name).join(),'Kairo');
});
test('turnaround view follows heading vs camera',()=>{const f=ARTIST_RESIDENTS[0];
 assert.equal(residentView(f,0,0).src,f.views.back);assert.equal(residentView(f,Math.PI,0).src,f.views.front);assert.equal(residentView(f,Math.PI/2,0).src,f.views.side);
 assert.equal(residentView(ARTIST_RESIDENTS[2],1,0).src,ARTIST_RESIDENTS[2].views.front);});
test('pocket renders and disposes residents',()=>{const s=readFileSync(new URL('../components/cage-pocket-dimension.tsx',import.meta.url),'utf8');
 assert.ok(s.includes('stepResidents(elapsed')&&s.includes('texCache.forEach(t=>t.dispose())')&&!/SparkBeastArena|createCreatureRig/.test(readFileSync(new URL('../components/pocket-residents.ts',import.meta.url),'utf8'))&&s.includes('data-artist-residents'));});
