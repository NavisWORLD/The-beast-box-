import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {conceptEyeFrame,resolveConceptSprite,CONCEPT_SPRITES} from '../public/spark/concept-sprites.mjs';
import {CREATURE_RECIPES} from '../public/spark/creature-assets.mjs';
const app=readFileSync(new URL('../public/spark/app.mjs',import.meta.url),'utf8');
test('static /spark page uses the shared id/seed resolver, not names',()=>{
 assert.match(app,/from '\.\/concept-sprites\.mjs'/);
 assert.match(app,/resolveConceptSprite\(\{genome:gen\}\)/);
 assert.match(app,/if\(conceptEyes\(gen\)\)return;/,'concept first, original cache build kept as fallback');
 assert.match(app,/blit\(canvas\.getContext\('2d'\),renderBeast\(gen,which,eye\),0,0,2\)/,'original paintStage kept');
});
test('eye to frame: blink uses frame 2; reduced motion always frame 0',()=>{
 assert.equal(conceptEyeFrame('closed'),2);assert.equal(conceptEyeFrame('open'),0);
 for(const e of ['open','closed','sleepy','sparkle'])assert.equal(conceptEyeFrame(e,true),0);
 assert.match(app,/conceptEyeFrame\(eye,reduceMotion\)/);
});
test('exclusions hold for /spark genomes',()=>{
 for(const id of ['bb-deada969','bb-1e1759f3','bb-4c633cb5']){const r=CREATURE_RECIPES.find(x=>x.id===id);assert.equal(resolveConceptSprite({genome:{seed:r.seed}}),null,id);}
 assert.equal(resolveConceptSprite({genome:{seed:CONCEPT_SPRITES[0].seed}})?.slug,CONCEPT_SPRITES[0].slug);
});
test('no new Math.random in /spark concept code',()=>{
 const added=app.split('\n').filter(l=>/concept/i.test(l));assert.ok(added.length>3);
 for(const l of added)assert.ok(!/Math\.random/.test(l));
});
