import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {buildGenome} from '../public/spark/genome.mjs';
import {buildQbeast} from '../public/spark/qbeast.mjs';
import {expandRun} from '../public/spark/runs.mjs';
import {validateRecordedQvmStimulus,recordedQvmStimulusPath} from '../lib/companion/recorded-qvm-stimulus.mjs';
const read=name=>JSON.parse(readFileSync(new URL('../public/spark/'+name,import.meta.url),'utf8'));
const families=[
 {name:'Wraith',slug:'wraith',id:'bb-4a61a8d5',seed:'385f040c4f5ce01904176448585007de206cd0f92ec34f61f7e08de72256bc85',body:'moth',native:'Lunlet',ibm:'db4rg5klf4us73c34tqg',user:'WraithGlyphVideoAudio-17',traits:{focus:42,calm:54,spark:71},azure:'3c9e2a90-c45f-11f1-ae67-7ced8dda8a51',run:38022572501},
 {name:'Lumenwisp',slug:'lumenwisp',id:'bb-983f386b',seed:'4ced51bdaae978a93970996759131f610a1be5bf9c3c5dd12b16849fbc16a0e2',body:'pup',native:'Gildlet',ibm:'db4sba4lf4us73c36910',user:'Lumenwisp-Generation2',traits:{focus:36,calm:82,spark:46},azure:'ce11385c-c467-11f1-ae67-6045bdae353a',run:38025920199},
];
for(const b of families)test(b.name+' is born from REAL exact IBM gate-conditioned physical counts and independently bound cloud QVM',()=>{
 const d=read('ibm-'+b.slug+'-20261010.json');
 assert.equal(d.source_class,'RECORDED_IBM_HARDWARE');
 assert.equal(d.job_id,b.ibm);
 assert.equal(d.runs.length,2);
 assert.equal(d.runs[1].k,b.ibm+':bell-xx');
 assert.equal(d.runs[0].s,4096);assert.equal(d.runs[1].s,4096);
 const source=expandRun(d.runs[1]);
 const genome=buildGenome(b.traits,source,b.user,10);
 assert.equal(genome.seed,b.seed);assert.equal(genome.body,b.body);assert.equal(genome.names[1],b.native);
 assert.equal(buildQbeast(genome).profile.id,b.id);
 const cloud=read('azure-'+b.slug+'-20261010.json');
 assert.equal(cloud.job_id,b.azure);
 assert.equal(cloud.source_run_id,b.run);
 assert.equal(validateRecordedQvmStimulus(cloud).shots,512);
 assert.equal(recordedQvmStimulusPath({genome:{inputs:{quantum_run:source.key}}}),'/spark/azure-'+b.slug+'-20261010.json');
});
test('second generation is distinct from its parent, not a recycled QPU job',()=>{
 assert.notEqual(families[0].ibm,families[1].ibm);
 assert.notEqual(families[0].id,families[1].id);
 assert.equal(read('ibm-lumenwisp-20261010.json').parent_qbeast_id,families[0].id);
});
