import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync,statSync} from 'node:fs';
import {CONCEPT_SPRITES,resolveConceptSprite,conceptFrameAt,conceptSourceRect,conceptSheet,drawConceptFrame,paintConceptThumb,_resetConceptCache,CONCEPT_CYCLE_MS} from '../public/spark/concept-sprites.mjs';
import {CREATURE_RECIPES} from '../public/spark/creature-assets.mjs';

const seedOf=slug=>CONCEPT_SPRITES.find(c=>c.slug===slug).seed;
const ZEREF=CREATURE_RECIPES.find(r=>r.id==='bb-deada969');
const REG_UMBRALET=CREATURE_RECIPES.find(r=>r.id==='bb-1e1759f3');
const GEARSEED=CREATURE_RECIPES.find(r=>r.id==='bb-4c633cb5');

test('six creatures, exact seeds resolve',()=>{
 assert.deepEqual(CONCEPT_SPRITES.map(c=>c.slug).sort(),['cindertot','fernling','halopip','pistonwyrm','tidefin','umbralet']);
 for(const c of CONCEPT_SPRITES)assert.equal(resolveConceptSprite({genome:{seed:c.seed}})?.slug,c.slug);
});
test('registered Pistonwyrm resolves by id and by its recorded seed',()=>{
 const p=CREATURE_RECIPES.find(r=>r.id==='bb-d41e5bd4');
 assert.equal(p.seed,seedOf('pistonwyrm'));
 assert.equal(resolveConceptSprite({id:'bb-d41e5bd4'})?.slug,'pistonwyrm');
 assert.equal(resolveConceptSprite({genome:{seed:p.seed}})?.slug,'pistonwyrm');
 assert.equal(resolveConceptSprite({id:'bb-d41e5bd4',genome:{seed:'0'.repeat(64)}}),null,'id with a foreign seed does not swap');
});
test('display names and archetypes never match',()=>{
 for(const name of ['Umbralet','Pistonwyrm','Cindertot','Halopip','Tidefin','Fernling'])
  assert.equal(resolveConceptSprite({name,displayName:name,genome:{names:['x',name],body:'moth'}}),null);
 assert.equal(resolveConceptSprite({genome:{seed:seedOf('umbralet').toUpperCase()}}),null);
});
test('exclusions: Zeref, registered Umbralet dragonling, Gearseed, Moonwraith rig',()=>{
 assert.equal(resolveConceptSprite({genome:{seed:ZEREF.seed}}),null);
 assert.equal(resolveConceptSprite({id:'bb-deada969'}),null);
 assert.equal(resolveConceptSprite({id:'bb-7f9c2a03'}),null);
 assert.equal(resolveConceptSprite({id:'bb-1e1759f3',genome:{seed:REG_UMBRALET.seed}}),null);
 assert.equal(resolveConceptSprite({genome:{seed:REG_UMBRALET.seed,body:'dragonling',names:['Umbralet','Umbralet']}}),null);
 assert.equal(resolveConceptSprite({id:'bb-1e1759f3',genome:{seed:seedOf('umbralet')}}),null,'excluded id wins even with the moth seed');
 assert.equal(resolveConceptSprite({genome:{seed:GEARSEED.seed}}),null);
 assert.equal(resolveConceptSprite({id:'bb-4c633cb5'}),null);
 assert.ok(!existsSync(new URL('../public/creatures/concept-v1/pistonwyrm-gearseed',import.meta.url)),'gearseed approximation not shipped');
});
test('unknown / invalid input falls back without throwing',()=>{
 for(const v of [null,undefined,0,'x',{},{genome:null},{genome:{seed:123}},{genome:{seed:'abc'}},{get genome(){throw Error('bad');}}])
  assert.equal(resolveConceptSprite(v),null);
});
test('reduced motion is frame 0; animation is deterministic and covers all frames',()=>{
 const e=CONCEPT_SPRITES[0];
 for(const t of [0,123,999999,4567])assert.equal(conceptFrameAt(e,t,true),0);
 const seen=new Set();for(let t=0;t<CONCEPT_CYCLE_MS;t+=20)seen.add(conceptFrameAt(e,t));
 assert.deepEqual([...seen].sort(),[0,1,2,3]);
 assert.equal(conceptFrameAt(e,777),conceptFrameAt(e,777));
 assert.equal(conceptFrameAt(e,NaN),0);
});
test('source rectangles select horizontal frames',()=>{
 assert.deepEqual(conceptSourceRect(2),{sx:128,sy:0,sw:64,sh:64});
 assert.deepEqual(conceptSourceRect(3,128),{sx:384,sy:0,sw:128,sh:128});
 assert.deepEqual(conceptSourceRect(9),{sx:192,sy:0,sw:64,sh:64});
});
test('no Math.random in the adapter or its hooks',()=>{
 for(const f of ['../public/spark/concept-sprites.mjs','../components/pixel-beast.tsx','../components/creation-thumb.tsx','../components/pocket-saved-beasts.ts','../components/spark-field-roster.tsx'])
  assert.ok(!/Math\.random/.test(readFileSync(new URL(f,import.meta.url),'utf8')),f);
});
test('assets exist with expected sheet sizes',()=>{
 for(const c of CONCEPT_SPRITES)for(const u of [c.sheet,c.sheetHd]){
  const buf=readFileSync(new URL('../public'+u,import.meta.url));
  assert.equal(buf.readUInt32BE(16),u.includes('128')?512:256);assert.equal(buf.readUInt32BE(20),u.includes('128')?128:64);
 }
});
test('image load failure keeps the original; success draws the chosen frame',()=>{
 const imgs=[];globalThis.Image=class{constructor(){imgs.push(this);}set src(v){this._src=v;}};
 try{
  _resetConceptCache();
  const e=CONCEPT_SPRITES.find(c=>c.slug==='tidefin');const calls=[];
  const ctx={imageSmoothingEnabled:true,drawImage:(...a)=>calls.push(a),clearRect(){},save(){},restore(){},translate(){},scale(){}};
  let ready=0;
  assert.equal(drawConceptFrame(ctx,e,2,0,0,64,{onReady:()=>ready++}),false,'not loaded yet -> original');
  assert.equal(conceptSheet(e),null);assert.equal(imgs.length,1,'one request per url');
  imgs[0].onerror();
  assert.equal(drawConceptFrame(ctx,e,2,0,0,64),false,'failed -> original');assert.equal(imgs.length,1,'no retry storm');
  assert.equal(ready,0);
  const h=CONCEPT_SPRITES.find(c=>c.slug==='halopip');
  assert.equal(paintConceptThumb(ctx,{seed:h.seed},128,{onReady:()=>ready++}),false);
  imgs[1].onload();assert.equal(ready,1);
  assert.equal(paintConceptThumb(ctx,{seed:h.seed},128,{frame:2}),true);
  assert.deepEqual(calls.at(-1).slice(1,5),[256,0,128,128]);
  assert.equal(paintConceptThumb(ctx,{seed:ZEREF.seed},128),false,'Zeref untouched');
 }finally{delete globalThis.Image;_resetConceptCache();}
});
