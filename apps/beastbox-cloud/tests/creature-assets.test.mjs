import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {CREATURE_RECIPES,registeredCreatures,selectRegisteredCreature,creatureVisual} from '../public/spark/creature-assets.mjs';
import {expandRun} from '../public/spark/runs.mjs';
import {SESSION_KEY,readSparkSession,saveSparkSession} from '../public/spark/identity.mjs';
import {careAction} from '../lib/companion/session.mjs';
const tables=()=>CREATURE_RECIPES.flatMap(recipe=>JSON.parse(readFileSync(new URL('../public/spark/'+recipe.file,import.meta.url))).runs.map(expandRun));
const storage=()=>{const map=new Map();return {getItem:k=>map.get(k)??null,setItem:(k,v)=>map.set(k,String(v)),removeItem:k=>map.delete(k)};};

test('all registered recipes replay their original immutable identities and distinct native sprites',()=>{
 const items=registeredCreatures(tables());
 assert.equal(items.length,14);assert.equal(new Set(items.map(item=>item.id)).size,14);
 const zeref=items.find(item=>item.name==='Zeref'),wraith=items.find(item=>item.name==='Wraith'),pig=items.find(item=>item.name==='Mr Bone Pig');
 assert.equal(zeref.id,'bb-deada969');assert.equal(zeref.genome.body,'dragonling');
 assert.equal(wraith.id,'bb-4a61a8d5');assert.equal(wraith.genome.body,'moth');
 assert.equal(pig.id,'bb-62603ee3');assert.equal(pig.genome.body,'pup');
 assert.ok(items.every(item=>item.snapshot.profile.id===item.id&&item.genome.seed===item.seed));
});
test('canonical identity, rather than a display name, chooses the Moonwraith cat presentation',()=>{
 assert.equal(creatureVisual({id:'bb-7f9c2a03',name:'Moonwraith'}).renderer,'moonwraith-rig');
 assert.equal(creatureVisual({id:'bb-deada969',name:'Zeref',genome:{body:'dragonling'}}).renderer,'native-sprite');
 assert.equal(creatureVisual({id:'bb-4a61a8d5',name:'Renamed',genome:{body:'moth'}}).accent,'wraith');
 assert.equal(creatureVisual({id:'bb-62603ee3',genome:{body:'pup'}}).accent,'bone-pig');
 assert.equal(creatureVisual({id:'bb-unknown',name:'Zeref',genome:{body:'serpent'}}).accent,'native');
});
test('selecting registered creatures preserves names, care, conversation and unmodified QBEAST provenance',()=>{
 const store=storage(),runs=tables();
 let first=selectRegisteredCreature(store,'bb-deada969',runs);
 const original=JSON.stringify(first.beast.qbeast);
 careAction(first,'pet');first.beast.displayName='Keeper Zeref';first.chat.push({role:'you',text:'Saved greeting'});saveSparkSession(store,first);
 selectRegisteredCreature(store,'bb-62603ee3',runs);
 first=selectRegisteredCreature(store,'bb-deada969',runs);
 assert.equal(first.beast.displayName,'Keeper Zeref');assert.equal(first.beast.bond,3);assert.equal(first.beast.xp,4);
 assert.equal(first.chat.at(-1).text,'Saved greeting');assert.equal(JSON.stringify(first.beast.qbeast),original);
 assert.equal(readSparkSession(store).beast.qbeast.profile.id,'bb-deada969');
});
test('a missing source or conflicting receipt cannot select a substitute or alter an existing save',()=>{
 const store=storage(),runs=tables();selectRegisteredCreature(store,'bb-deada969',runs);const before=store.getItem(SESSION_KEY);
 assert.throws(()=>selectRegisteredCreature(store,'bb-62603ee3',[]),/unavailable/);
 assert.throws(()=>selectRegisteredCreature(store,'bb-not-registered',runs),/registered/);
 const source=runs.find(item=>item.key==='db4pa784qg6s73c2g5vg:bell-xx');
 assert.throws(()=>registeredCreatures([source,{...source,shots:1}]),/Conflicting/);
 assert.equal(store.getItem(SESSION_KEY),before);
});
