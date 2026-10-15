import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {buildGenome} from '../public/spark/genome.mjs';import {buildQbeast,serializeQbeast} from '../public/spark/qbeast.mjs';
import {readImportedBeast,importIdFromSearch,PUBLIC_KEY} from '../lib/companion/game-import.mjs';
const row=JSON.parse(readFileSync(new URL('../public/spark/runs.json',import.meta.url))).runs[0];
const run={key:row.k,backend:row.b,job_id:row.j,pub_index:row.p,num_bits:row.n,shots:row.s,counts_sha256:row.h,counts:Object.fromEntries(row.c.split(',').map(p=>{const[k,v]=p.split(':');return[k,+v]}))};
const store=m=>({getItem:k=>m[k]??null});
test('bridge beast imports into the native handoff with its exact identity',()=>{
 const g=buildGenome({focus:30,calm:50,spark:80},run,'Sol',10),q=buildQbeast(g),id=q.profile.id;
 const b=readImportedBeast(store({[PUBLIC_KEY+'-creature-'+id]:JSON.stringify({text:serializeQbeast(q)})}),id);
 assert.equal(b.qbeast.profile.id,id);assert.equal(b.seed,q.profile.seed);assert.equal(b.visiting,true);
 assert.throws(()=>readImportedBeast(store({}),id));assert.throws(()=>readImportedBeast(store({[PUBLIC_KEY]:JSON.stringify({text:serializeQbeast(q)})}),'bb-other'));
 assert.equal(importIdFromSearch('?import='+id),id);assert.equal(importIdFromSearch('?import=../x'),null);});
test('bridge beast without a Spark card gets a friendly, honest refusal (no minted card)',()=>{const q={profile:{id:'bb-26fe92c4',seed:'x'.repeat(64),name:'X'},events:[]};
 assert.throws(()=>readImportedBeast(store({[PUBLIC_KEY+'-creature-bb-26fe92c4']:JSON.stringify({text:JSON.stringify(q)})}),'bb-26fe92c4'),/no cartridge card yet/);});
test('bridge PLAY goes to /sol-game import; web share kept under Advanced',()=>{
 const t=readFileSync(new URL('../components/quantum-beast-transfer.tsx',import.meta.url),'utf8'),p=readFileSync(new URL('../components/sol-spark-player.tsx',import.meta.url),'utf8');
 assert.match(t,/\/sol-game\?import=/);assert.match(t,/openSynapseShare/);assert.match(t,/lostCosmosShareUrl/);
 assert.match(p,/readImportedBeast\(window\.localStorage/);assert.match(p,/Journeys save only to your active Beast/);});
test('home pocket guest default is Zeref bb-deada969 from its own recorded record, display-only',()=>{
 const s=readFileSync(new URL('../components/home-pocket.tsx',import.meta.url),'utf8');
 assert.match(s,/bb-deada969/);assert.doesNotMatch(s,/bb-7f9c2a03/);assert.doesNotMatch(s,/change\(|localStorage/);
 const d=JSON.parse(readFileSync(new URL('../public/spark/zeref-live-20261010/unsigned-session.json',import.meta.url)));assert.equal(d.beast.qbeast.profile.id,'bb-deada969');});
