import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {buildGenome,canonicalJson} from '../public/spark/genome.mjs';
import {buildQbeast} from '../public/spark/qbeast.mjs';
import {expandRun} from '../public/spark/runs.mjs';
import {sha256Hex} from '../public/spark/sha.mjs';
import {validateRecordedQvmStimulus,recordedQvmStimulusPath} from '../lib/companion/recorded-qvm-stimulus.mjs';
const read=n=>JSON.parse(readFileSync(new URL('../public/spark/'+n,import.meta.url),'utf8'));
test('Mr Bone Pig public source is exactly the recorded original-photo IBM/Azure receipt, never a new submission',()=>{
 const ibm=read('ibm-mr-bone-pig-20261010.json'),az=read('azure-mr-bone-pig-20261010.json');
 assert.equal(ibm.source_class,'RECORDED_IBM_HARDWARE');
 assert.equal(ibm.job_id,'db4pa784qg6s73c2g5vg');
 assert.equal(ibm.counts_digest_sha256,'3d56c29500e4b010b70cc9abb41545024548be21c9ce4185217fb944116952ea');
 assert.equal(ibm.source_image_sha256,'956f9fe57bd80146dfba01f5683fe694daae26ebf9e498f377425be74b973475');
 assert.equal(ibm.source_features_sha256,'766ee1954035205368387fb407bbe0d1c4fdc6ab96b91b27f0486f8d66e3b472');
 assert.equal(ibm.runs.length,2);
 for(const row of ibm.runs){const run=expandRun(row);assert.equal(sha256Hex(canonicalJson(run.counts)),row.h);assert.equal(run.shots,4096);}
 const run=expandRun(ibm.runs[1]);
 const genome=buildGenome({focus:75,calm:55,spark:84},run,'BonePigPhoto-24',10);
 assert.equal(genome.seed,'28a3f13ee58a62a78bf2b03143f2d88210ad037e325870e947037f2a0331222c');
 assert.equal(genome.body,'pup');assert.equal(genome.names[1],'Rimepup');
 assert.equal(buildQbeast(genome).profile.id,'bb-62603ee3');
 assert.equal(az.source_run_id,38013525896);
 assert.equal(az.job_id,'6a089c00-c44a-11f1-ae67-70a8a5267256');
 assert.equal(az.counts_sha256,'f8de71823a1420b6a632aea5fc2609299a9d699054939c1bd296fb3f59b04a23');
 assert.equal(validateRecordedQvmStimulus(az).shots,512);
 assert.equal(recordedQvmStimulusPath({genome:{inputs:{quantum_run:run.key}}}),'/spark/azure-mr-bone-pig-20261010.json');
});
test('complete roster is present without local save and preserves original selects, Play and Talk',()=>{
 const html=readFileSync(new URL('../public/spark/index.html',import.meta.url),'utf8');
 const app=readFileSync(new URL('../public/spark/app.mjs',import.meta.url),'utf8');
 const css=readFileSync(new URL('../public/spark/spark.css',import.meta.url),'utf8');
 assert.match(html,/id="bone-pig"/);assert.match(html,/id="roster-search"/);
 assert.match(html,/id="roster-count"/);
 for(const label of ['Mr Bone Pig','Wraith','Lumenwisp','Zeref','Umbralet','Magmascale','Pistonwyrm','Umbrascale','Duskscale','Zeref-Nightcat-Dragon','Umbrascale-Starseed','Pistonwyrm-Gearseed','Heartflare-Moonfire','Moonwraith-Cassette-Kit'])
   assert.ok(app.includes(label),'Missing pinned gallery member '+label);
 assert.match(app,/featuredRoster\(\)/);
 assert.match(app,/\.\.\.featuredRoster\(\)\.map/);
 assert.match(app,/for\(const \[mode,label\] of \[\['select','Select'\],\['play','Play 🎮'\],\['talk','Talk'\]\]\)/);
 assert.match(app,/location\.assign\('\/sol-game'\)/);
 assert.match(css,/\.roster-actions button/);
});
