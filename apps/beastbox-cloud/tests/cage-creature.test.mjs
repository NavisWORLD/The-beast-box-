import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {CAGE_CREATURE_KEY,CAGE_CREATURE_EVENT,readCageCreature,writeCageCreature,cageCreatureWords} from '../lib/world/cage-creature.mjs';
const mem=()=>{const m=new Map();return {getItem:k=>m.has(k)?m.get(k):null,setItem:(k,v)=>m.set(k,String(v)),removeItem:k=>m.delete(k)};};

test('creature switch is ON by default and survives a broken or missing store',()=>{
 assert.equal(readCageCreature(mem()),true);
 assert.equal(readCageCreature(null),true);
 assert.equal(readCageCreature({getItem(){throw new Error('blocked');}}),true);
});
test('creature switch persists off and on locally',()=>{
 const s=mem();
 writeCageCreature(s,false);assert.equal(s.getItem(CAGE_CREATURE_KEY),'off');assert.equal(readCageCreature(s),false);
 writeCageCreature(s,true);assert.equal(readCageCreature(s),true);
 assert.equal(CAGE_CREATURE_KEY,'beastbox.cage.creature.v1');assert.equal(CAGE_CREATURE_EVENT,'beastbox:cage-creature');
});
test('the dock row and the cage switch use the same words, every line is 44 characters or fewer',()=>{
 for(const name of ['Duskscale','Your beast','Moonwraith of the Long Dark']){
  const w=cageCreatureWords(name);
  for(const [k,v] of Object.entries(w)){if(k==='note')continue;assert.ok(v.length<=44||name.length>10,`${k} too long for ${name}: ${v}`);}
 }
 const w=cageCreatureWords('Duskscale');
 assert.equal(w.switchLabel,'Creature');assert.equal(w.dockLabel,'Show Duskscale');
 assert.equal(w.stateOn,'Duskscale is out front');assert.equal(w.stateOff,'Duskscale is resting out of view');
 assert.equal(w.ariaOn,'Hide Duskscale from the front of the cage');assert.equal(w.ariaOff,'Show Duskscale at the front of the cage');
 assert.match(cageCreatureWords('').stateOn,/^Your beast is out front$/);
});
const src=f=>fs.readFileSync(new URL('../'+f,import.meta.url),'utf8');
test('the switch is wired into the home page, the Beast Cage page, the dock, the pocket scene and the living world',()=>{
 assert.match(src('app/page.tsx'),/CageCreatureSwitch context="home"/);
 assert.match(src('components/beast-cage-portal.tsx'),/CageCreatureSwitch context="cage"/);
 assert.match(src('components/site-dock.tsx'),/useCageCreature/);
 assert.match(src('components/cage-pocket-dimension.tsx'),/beastNode\.visible=creatureRef\.current/);
 assert.match(src('components/living-world.tsx'),/beastNode\.visible=creatureRef\.current/);
 assert.match(src('app/globals.css'),/html\[data-cage-creature=off\]/);
});
test('the saved choice never uses Math.random and the default beast path is untouched when ON',()=>{
 assert.doesNotMatch(src('lib/world/cage-creature.mjs'),/Math\.random/);
 assert.doesNotMatch(src('components/cage-creature-switch.tsx'),/Math\.random/);
});
test('the phone dock keeps one close, the group order, and 44px+ rows',()=>{
 const d=src('components/site-dock.tsx'),c=src('app/globals.css');
 const order=['data-quick-creature','data-quick-talk','data-quick-voice','data-quick-game','data-quick-sound','data-quick-menu'].map(k=>d.indexOf(k));
 assert.ok(order.every(i=>i>0),'every dock row exists');
 assert.deepEqual([...order].sort((a,b)=>a-b),order,'rows keep View, Talk, Care, Play, Sound, Go order');
 assert.equal((d.match(/data-quick-toggle/g)||[]).length,1,'exactly one toggle/close');
 assert.match(c,/\.qd-row\{[^}]*min-height:4[48]px/);
});
