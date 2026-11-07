import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {CONCEPT_CATALOGUE,CONCEPT_SPRITES,resolveConceptSprite} from '../public/spark/concept-sprites.mjs';
import {conceptCatalogueGenomes} from '../public/spark/concept-catalogue.mjs';
import {expandCompactRun} from '../lib/companion/spark-machine.mjs';
const runs=JSON.parse(readFileSync(new URL('../public/spark/runs.json',import.meta.url),'utf8')).runs.map(expandCompactRun);
test('five catalogue recipes reproduce the pack seeds exactly and resolve to their own art',()=>{
 const got=conceptCatalogueGenomes(runs);
 assert.deepEqual(got.map(g=>g.slug).sort(),['cindertot','fernling','halopip','tidefin','umbralet']);
 for(const g of got){assert.equal(g.genome.seed,CONCEPT_SPRITES.find(c=>c.slug===g.slug).seed);assert.equal(resolveConceptSprite({genome:g.genome}).slug,g.slug);}
 assert.equal(got.find(g=>g.slug==='umbralet').genome.body,'moth','catalogue Umbralet is the moth, not the registered dragonling');
});
test('a recipe that no longer reproduces is dropped, not substituted',()=>{
 const tampered=runs.map(r=>r.key===CONCEPT_CATALOGUE[0].runKey?{...r,counts:{'0':1}}:r);
 assert.ok(!conceptCatalogueGenomes(tampered).some(g=>g.slug===CONCEPT_CATALOGUE[0].slug));
 assert.deepEqual(conceptCatalogueGenomes([]),[]);
});
test('catalogue picker offers redraws by run key and picks through the existing onPick path',()=>{
 const src=readFileSync(new URL('../public/spark/catalog-picker.mjs',import.meta.url),'utf8');
 assert.match(src,/rows\.find\(x=>x\.key===c\.runKey\)/);assert.match(src,/onPick\(r,'concept'\)/);assert.ok(!/Math\.random/.test(src));
});
