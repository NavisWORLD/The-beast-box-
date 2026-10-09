import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
import test from 'node:test';

const root=new URL('../../../',import.meta.url);
const script=new URL('../../../scripts/audit-creature-genesis.mjs',import.meta.url);
let audit;
async function api(){return audit??=await import(script);}

test('the audit command independently validates the entire published input inventory',()=>{
 const run=spawnSync(process.execPath,[script.pathname,'--sources-only'],{cwd:root,encoding:'utf8',timeout:30000});
 assert.equal(run.status,0,run.stderr);
 const summary=JSON.parse(run.stdout);
 assert.equal(summary.archive.rows,5676);
 assert.equal(summary.archive.uniqueJobs,267);
 assert.equal(summary.archive.shots,25576380);
 assert.equal(summary.qvm.rows,24);
 assert.equal(summary.qvm.shots,2048);
 assert.equal(summary.providerReauthenticated,false);
});

test('digest grouping distinguishes repeated identical material from hash aliases',async()=>{
 const {DigestTracker}=await api();
 const tracker=new DigestTracker();
 tracker.add('same-digest','identical','a');tracker.add('same-digest','identical','b');
 tracker.add('forced-alias','first material','c');tracker.add('forced-alias','different material','d');
 const summary=tracker.summary();
 assert.equal(summary.uniqueDigests,2);
 assert.equal(summary.repeatedDigestGroups,2);
 assert.equal(summary.identicalMaterialGroups,1);
 assert.equal(summary.conflictingMaterialGroups,1);
 assert.deepEqual(tracker.groups().map(group=>group.records),[['a','b'],['c','d']]);
});

test('the record archive keeps every canonical input with deterministic gzip time and portable header',async()=>{
 const {encodeRecordArchive}=await api();
 assert.equal(typeof encodeRecordArchive,'function');
 const first=encodeRecordArchive([{z:2,a:1},{seed:'full seed'}]);
 const second=encodeRecordArchive([{z:2,a:1},{seed:'full seed'}]);
 assert.ok(first.bytes.equals(second.bytes));
 assert.equal(first.bytes.readUInt32LE(4),0);
 assert.equal(first.bytes[9],255);
 assert.equal(gunzipSync(first.bytes).toString(),'{"a":1,"z":2}\n{"seed":"full seed"}\n');
 assert.equal(first.recordCount,2);
 assert.equal(first.decompressedBytes,35);
});

test('an actual identical-count pair exposes metadata rerolls without inventing additional information',async()=>{
 const {loadGenesisSources,duplicateCountWitness}=await api();
 const {archiveRuns}=await loadGenesisSources();
 const witness=duplicateCountWitness(archiveRuns);
 assert.equal(witness.countsSha256,'49c83391f4655d01c87dceaabc9dde8d3e1377b31f3904130285b6fc97094ad1');
 assert.equal(witness.sameRawCounts,true);
 assert.equal(witness.sameDyn12,true);
 assert.equal(witness.sameSeeds,false);
 assert.equal(witness.samePhenotypes,false);
 assert.equal(witness.sameStage2Pixels,false);
 assert.equal(witness.normalizedMetadata.sameSeeds,true);
 assert.equal(witness.normalizedMetadata.samePhenotypes,true);
 assert.equal(witness.normalizedMetadata.sameStage2Pixels,true);
});

test('the real full archive census covers every family and morphology without saved fixtures',async()=>{
 const {loadGenesisSources,censusCreatures}=await api();
 const sources=await loadGenesisSources();
 const result=censusCreatures(sources);
 assert.equal(result.records.length,5676);
 assert.equal(result.summary.failures,0);
 assert.deepEqual(Object.keys(result.summary.categories.family).sort(),['aurora','memory','nebula','plasma','signal','starlight','void']);
 assert.deepEqual(Object.keys(result.summary.categories.body).sort(),['axolotl','biped','bird','dragonling','fish','fox','golem','moth','pup','serpent','sprout']);
 assert.equal(Object.keys(result.summary.categories.gait).length,7);
 assert.equal(Object.keys(result.summary.categories.voiceStyle).length,6);
 assert.equal(Object.keys(result.summary.categories.habit).length,12);
 assert.equal(Object.keys(result.summary.categories.quirk).length,8);
 assert.ok(!Object.hasOwn(result.summary.categories.habit,'[object Object]'));
 assert.equal(result.summary.digests.seed.uniqueDigests,5676);
 assert.equal(result.summary.digests.shortId.conflictingMaterialGroups,0);
 assert.equal(result.summary.digests.counts.uniqueDigests,3091);
 assert.equal(result.summary.digests.counts.identicalMaterialGroups,1376);
 assert.equal(result.summary.digests.counts.repeatedRecords,3961);
 assert.equal(result.summary.digests.counts.conflictingMaterialGroups,0);
 assert.equal(result.summary.digests.spriteI.uniqueDigests,5676);
 assert.equal(result.summary.digests.spriteII.uniqueDigests,5676);
 assert.equal(result.summary.digests.spriteIII.uniqueDigests,5676);
});
