import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {expandRun} from '../public/spark/runs.mjs';
import {buildGenome} from '../public/spark/genome.mjs';
import {buildQbeast} from '../public/spark/qbeast.mjs';
import {validateRecordedQvmStimulus,recordedQvmStimulusPath} from '../lib/companion/recorded-qvm-stimulus.mjs';
const read=name=>JSON.parse(readFileSync(new URL('../public/spark/'+name,import.meta.url),'utf8'));
const entries=[
 ['Zeref-Nightcat-Dragon','zeref-nightcat-dragon','db4tc8kvf2bc73cv3np0','bb-f740d771','6c94f1ff03c7ced766b1b0281db3c93816814bbd276c10c6cda8b1cdce8c1398','serpent','Tideling',{focus:72,calm:55,spark:53},'ea5d60c6-c471-11f1-ae67-e4fade1b1144'],
 ['Umbrascale-Starseed','umbrascale-starseed','db4tdtkvf2bc73cv3qng','bb-b396edfe','4895a7212c332b0501f40a5784321aac79e07bdb7f9242ef3602c47e80968eb7','serpent','Mosscoil',{focus:72,calm:56,spark:55},'f06449d1-c471-11f1-ae67-e4fade1b1144'],
 ['Pistonwyrm-Gearseed','pistonwyrm-gearseed','db4te084qg6s73c2m3lg','bb-4c633cb5','226bd3cafa2614315a4b538d6dcb26afe118800538fae7152c5fc2d13aa3fcad','pup','Boltlet',{focus:73,calm:57,spark:56},'f4e1e2e3-c471-11f1-ae67-e4fade1b1144'],
 ['Heartflare-Moonfire','heartflare-moonfire','db4te4g4qg6s73c2m470','bb-5f6b911b','847950fde92c19fd85b591fc7932c3ba3fb586547eb0d4c0e6ba52564fc19531','biped','Regalbit',{focus:73,calm:58,spark:55},'f9ae5f31-c471-11f1-ae67-e4fade1b1144'],
 ['Moonwraith-Cassette-Kit','moonwraith-cassette-kit','db4te7slf4us73c3888g','bb-c190e914','1ea83dd020ec994e4a8d569fac2a18d86e6701d538a1f7289def97e77fb2ec6a','moth','Halolet',{focus:72,calm:56,spark:52},'fe224e3d-c471-11f1-ae67-e4fade1b1144']
];
const identities=new Set();
for(const [alias,slug,job,id,seed,body,native,traits,azureId] of entries){
 test('new physical IBM + separate Azure QVM create exact '+alias+' native Beast',()=>{
  const ibm=read('ibm-'+slug+'-20261010.json');
  assert.equal(ibm.source_class,'RECORDED_IBM_HARDWARE');
  assert.equal(ibm.job_id,job);
  assert.equal(ibm.runs.length,2);
  assert.equal(ibm.runs[1].s,4096);
  const run=expandRun(ibm.runs[1]);
  const gen=buildGenome(traits,run,alias,10);
  assert.equal(gen.seed,seed);assert.equal(gen.body,body);
  assert.equal(gen.names[1],native);
  const snapshot=buildQbeast(gen);assert.equal(snapshot.profile.id,id);
  assert.ok(!identities.has(id));identities.add(id);
  const cloud=read('azure-'+slug+'-20261010.json');
  assert.equal(cloud.job_id,azureId);
  assert.equal(cloud.source_class,'RECORDED_AZURE_CLOUD_SIMULATOR');
  assert.equal(validateRecordedQvmStimulus(cloud).shots,512);
  assert.equal(recordedQvmStimulusPath({genome:{inputs:{quantum_run:run.key}}}),'/spark/azure-'+slug+'-20261010.json');
 });
}
test('all five new jobs and five QBEASTs are distinct',()=>{
 assert.equal(new Set(entries.map(r=>r[2])).size,5);
 assert.equal(new Set(entries.map(r=>r[3])).size,5);
});
