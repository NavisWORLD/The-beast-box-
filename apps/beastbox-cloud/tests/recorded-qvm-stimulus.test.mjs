import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {buildGenome,canonicalJson} from '../public/spark/genome.mjs';
import {expandRun} from '../public/spark/runs.mjs';
import {buildQbeast} from '../public/spark/qbeast.mjs';
import {createSession,adoptBeast,advanceCreature,exportSession,importSession,swapBrain} from '../lib/companion/session.mjs';
import {serializeDeviceJourney,readDeviceJourney,restoreDeviceJourney} from '../public/spark/device-journey.mjs';
import {selectSpark,readSparkSession,saveSparkSession} from '../public/spark/identity.mjs';
const api=await import('../lib/companion/recorded-qvm-stimulus.mjs').catch(()=>({}));
const source={schema:'beastbox-recorded-azure-qvm-stimulus-v1',source_class:'RECORDED_AZURE_CLOUD_SIMULATOR',target:'rigetti.sim.qvm',job_id:'dc9a1e78-c423-11f1-ae67-e4fade257188',shots:512,counts:{'00':241,'11':271},counts_sha256:'b3b53db7eb47e7c70fa94aeea1f7c1532a8db7bf5215b3f324cbf339e9d69370',source_run_id:37989851630,receipt_origin:'SANITIZED_ACTIONS_RESULT_LOG'};
const run=expandRun(JSON.parse(readFileSync(new URL('../public/spark/ibm-marrakesh-reality-probe-20261009.json',import.meta.url))).runs[0]);
const genome=buildGenome({focus:75,calm:20,spark:95},run,'Ethereal-dragon-21',10);
function session(){const s=createSession();adoptBeast(s,genome);s.beast.qbeast=buildQbeast(genome);return s;}
function storage(){const m=new Map();return {getItem:k=>m.get(k)??null,setItem:(k,v)=>m.set(k,String(v)),removeItem:k=>m.delete(k)};}
test('a verified simulator result enters the existing core once without granting identity or game authority',()=>{
 assert.equal(typeof api.applyRecordedQvmStimulus,'function');
 const s=session(),control=session(),genesis=canonicalJson(s.beast.qbeast);
 const result=api.applyRecordedQvmStimulus(s,source);
 assert.equal(result.ok,true);assert.equal(result.duplicate,false);
 assert.equal(s.beast.behavior.tick,1);assert.equal(s.beast.behavior.events[0].place,'observatory');
 assert.equal(s.beast.behavior.events[0].input.toy,271/512);
 advanceCreature(control,{place:'observatory'});
 assert.notDeepEqual(s.beast.behavior.events[0].scores,control.beast.behavior.events[0].scores);
 assert.equal(canonicalJson(s.beast.qbeast),genesis);assert.equal(s.beast.xp,0);assert.equal(s.beast.stage,1);
 const before=canonicalJson(exportSession(s));
 assert.equal(api.applyRecordedQvmStimulus(s,source).duplicate,true);assert.equal(canonicalJson(exportSession(s)),before);
 const restored=importSession(exportSession(s));swapBrain(restored,'local-pattern');
 assert.equal(api.applyRecordedQvmStimulus(restored,source).duplicate,true);assert.equal(restored.beast.behavior.tick,1);
});
test('changed simulator source, count digest, shot total or invalid replay marker fail before state mutation',()=>{
 assert.equal(typeof api.applyRecordedQvmStimulus,'function');
 for(const change of [{source_class:'IBM_HARDWARE'},{job_id:'unknown'},{shots:513},{counts:{'00':240,'11':272}},{counts_sha256:'0'.repeat(64)}]){
  const s=session(),before=canonicalJson(exportSession(s));assert.throws(()=>api.applyRecordedQvmStimulus(s,{...source,...change}));assert.equal(canonicalJson(exportSession(s)),before);
 }
 const s=session();s.beast.qvmStimulus={job_id:source.job_id};const before=canonicalJson(exportSession(s));
 assert.throws(()=>api.applyRecordedQvmStimulus(s,source));assert.equal(canonicalJson(exportSession(s)),before);
});
test('device journey restore keeps the already applied simulator receipt even when an older same-Beast save is restored',()=>{
 assert.equal(typeof api.applyRecordedQvmStimulus,'function');
 const store=storage(),byKey=new Map([[run.key,run]]);selectSpark(store,genome);
 const old=serializeDeviceJourney(readSparkSession(store),byKey);
 const s=readSparkSession(store);api.applyRecordedQvmStimulus(s,source);saveSparkSession(store,s);
 const restored=restoreDeviceJourney(store,readDeviceJourney(old,byKey));
 assert.equal(api.applyRecordedQvmStimulus(restored,source).duplicate,true);
 const file=serializeDeviceJourney(restored,byKey);assert.equal(readDeviceJourney(file,byKey).session.beast.qvmStimulus.job_id,source.job_id);
 const forged=JSON.parse(file);forged.session.beast.qvmStimulus.counts_sha256='0'.repeat(64);
 assert.throws(()=>readDeviceJourney(JSON.stringify(forged),byKey));
});

test('the completed fresh IBM-derived Azure workload enters the same core once and survives save/load',()=>{
 const fresh=JSON.parse(readFileSync(new URL('../public/spark/azure-final-ibm-qvm-20261009.json',import.meta.url)));
 const s=session(),identity=canonicalJson(s.beast.qbeast);
 const result=api.applyRecordedQvmStimulus(s,fresh);
 assert.equal(result.duplicate,false);
 assert.equal(result.environment.attention,(219+234)/512);
 assert.equal(result.marker.job_id,'32d6fc6c-c42d-11f1-ae67-000d3ad41960');
 assert.equal(canonicalJson(s.beast.qbeast),identity);
 assert.equal(s.beast.xp,0);
 const loaded=importSession(exportSession(s));
 const before=canonicalJson(exportSession(loaded));
 assert.equal(api.applyRecordedQvmStimulus(loaded,fresh).duplicate,true);
 assert.equal(canonicalJson(exportSession(loaded)),before);
 const wrong={...fresh,source_run_id:37989851630};
 assert.throws(()=>api.applyRecordedQvmStimulus(session(),wrong));
 const changed={...fresh,counts:{...fresh.counts,'00':218,'11':235}};
 assert.throws(()=>api.applyRecordedQvmStimulus(session(),changed));
});
