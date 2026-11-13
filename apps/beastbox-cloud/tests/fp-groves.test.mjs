// Nov 12 2026 first-person composition: seeded groves of the existing eyed-tree/bush/flower cutouts, and real hills with a valley toward the bay.
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {groveBudget} from '../lib/look/fp-groves.ts';
import {terrainHeightAt,terrainValley} from '../lib/universe/one-world-look.ts';
const gv=readFileSync(new URL('../lib/look/fp-groves.ts',import.meta.url),'utf8');const w=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
test('groves are tier-scaled, LOW never empty, seeded (no Math.random), no new light, existing cutouts only',()=>{
 const g=groveBudget('GOD'),l=groveBudget('LOW');assert.ok(g.trees>groveBudget('MED').trees&&groveBudget('MED').trees>l.trees&&l.trees>0);
 assert.doesNotMatch(gv,/Math\.random|Light\(/);assert.match(gv,/round_tree/);assert.match(gv,/SEEDED/);
 assert.match(w,/addFpGroves\(THREE,lk2Ground\.group,\{rand:lwS\(u\.seed\+':fp-groves'\)/);});
test('CPU terrain: flat at your feet, hills rise beside the valley, valley floor stays low',()=>{
 const o={org:[0,0],seed:[123,456],bay:[0,0,0],on:true,r:900,valley:0};
 assert.equal(terrainHeightAt(1,1,o),0);assert.equal(terrainHeightAt(3,-2,o),0);
 let side=0,floor=0;for(let f=8;f<=14;f+=2){side+=terrainHeightAt(f,10,o)+terrainHeightAt(f,-10,o);const px=1.6*Math.sin(f*.19+123*.01);floor+=terrainHeightAt(f,px,o)*2;}
 assert.ok(side>floor*3,`side ${side} floor ${floor}`);assert.ok(terrainValley(10,1.6*Math.sin(10*.19+1.23),[123,456],[0,0,1])<.05);
 for(let i=0;i<50;i++){const h=terrainHeightAt(Math.cos(i)*i*3,Math.sin(i)*i*3,o);assert.ok(h>=0&&Number.isFinite(h));}});
