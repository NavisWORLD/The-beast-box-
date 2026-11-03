import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {genesis,grow} from '../lib/universe/tiny-universe.mjs';
import {seededGrowthNodes,growthNodesAt,NODE_KINDS,NODE_STAGES} from '../lib/universe/seeded-growth-nodes.mjs';
import {wishSeededGrowthNodes,wishGrowthNodesAt,WISH_NODE_SOURCE} from '../lib/universe/wish-seeded-growth-nodes.mjs';
const shard=JSON.parse(readFileSync(new URL('../public/spark/ibm-marrakesh-reality-probe-20261009.json',import.meta.url),'utf8'));
const real=genesis(shard);
const g={...real,planets:real.planets.map(p=>({...p,habitability:0.9}))};const u40=grow(g,40);
// Zeref's real first plantings, copied from the RECORDED wish records in evidence/zeref-messages-001/2026-11-02.jsonl.
const REG={schema:'zeref-seed-registry/v1',planted:['know','love'],seeds:[
 {word:'know',planted_at_utc:'2026-11-02T16:16:42+00:00',wish_text:'I know, per Simple English Wikipedia: a Medio Age of-Loing Age is the first season of Private Angeles, and the Sunday in the United States was the BCE.',wish_sha256:'b6c0348f5e7214ac921f06c64e0a83469650210702da6cf1421da4037ada69e8',prompt_seed:'655e911aa564',tag:'zeref-growing-007',step:37744,evidence:'evidence/zeref-messages-001/2026-11-02.jsonl'},
 {word:'love',planted_at_utc:'2026-11-02T21:57:31+00:00',wish_text:'I love this one!',wish_sha256:'52b85a4e3c59eddabdc2fc940d9368b45b4f23a403644a1dad8cefc1b7fb0500',prompt_seed:'73e8c948011c',tag:'zeref-growing-008',step:38064,evidence:'evidence/zeref-messages-001/2026-11-02.jsonl'}]};

test('traceability: know and love plant one node each on the home world, carrying their message-center receipts',()=>{
 const nodes=wishSeededGrowthNodes(REG,u40);assert.equal(nodes.length,2);
 const know=nodes.find(n=>n.wish_word==='know');assert.ok(know);
 assert.equal(know.wish_sha256,'b6c0348f5e7214ac921f06c64e0a83469650210702da6cf1421da4037ada69e8');
 assert.equal(know.planted_at_utc,'2026-11-02T16:16:42+00:00');assert.equal(know.prompt_seed,'655e911aa564');
 assert.equal(know.source,WISH_NODE_SOURCE);assert.equal(know.label,'SEEDED');assert.equal(know.type,'growth_node');
 assert.ok(NODE_KINDS.includes(know.kind));assert.equal(know.planet,seededGrowthNodes(u40)[0]?.planet??know.planet);
 const love=nodes.find(n=>n.wish_word==='love');assert.ok(love);assert.notEqual(love.id,know.id);
});

test('determinism: same registry and universe give the same wish forest, twice and cloned',()=>{
 assert.deepEqual(wishSeededGrowthNodes(REG,u40),wishSeededGrowthNodes(REG,structuredClone(u40)));
 assert.deepEqual(wishGrowthNodesAt(REG,u40,40),wishGrowthNodesAt(REG,structuredClone(u40),40));
});

test('isolation: recorded nodes, universe and growth are byte-identical with the wish wire on or off',()=>{
 const before=JSON.stringify(u40);const recBefore=JSON.stringify(seededGrowthNodes(u40));
 wishSeededGrowthNodes(REG,u40);wishGrowthNodesAt(REG,u40,40);
 assert.equal(JSON.stringify(u40),before);assert.equal(JSON.stringify(seededGrowthNodes(u40)),recBefore);
 assert.equal(JSON.stringify(grow(g,25)),JSON.stringify(grow({...real,planets:real.planets.map(p=>({...p,habitability:0.9}))},25)));
 const merged=[...growthNodesAt(u40,40),...wishGrowthNodesAt(REG,u40,40)];
 assert.equal(new Set(merged.map(n=>n.id)).size,merged.length);// no id collisions with the recorded nodes
});

test('no receipt, no node: unhashed entries, repeats, empty and missing registries plant nothing extra',()=>{
 assert.deepEqual(wishSeededGrowthNodes(null,u40),[]);assert.deepEqual(wishSeededGrowthNodes({},u40),[]);
 assert.deepEqual(wishSeededGrowthNodes({seeds:[{word:'ghost'}]},u40),[]);
 const dup={seeds:[REG.seeds[0],REG.seeds[0]]};assert.equal(wishSeededGrowthNodes(dup,u40).length,1);
 const noHab={...g,planets:g.planets.map(p=>({...p,habitability:0}))};assert.deepEqual(wishSeededGrowthNodes(REG,noHab),[]);
});

test('state: wish nodes take the same stages and drive as every other node',()=>{
 for(const n of wishGrowthNodesAt(REG,u40,40)){assert.ok(NODE_STAGES.includes(n.stage));assert.equal(n.tick,40);assert.ok(n.scale>0);}
 const later=wishGrowthNodesAt(REG,u40,400);assert.ok(later.every(n=>typeof n.generation==='number'));
});
