import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import {lookSubjectLabels,captionKeepsHonesty} from '../lib/look-closer-subjects.mjs';
const labels=JSON.parse(readFileSync(new URL('../lib/look-closer-labels.json',import.meta.url),'utf8'));
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('defaults keep today\'s wording and the honesty caption',()=>{
 const m=lookSubjectLabels('moonwraith',{labels});
 assert.equal(m.button,'Zeref 3D');assert.match(m.caption,/Artistic 3D model of Zeref's display form/);assert.match(m.caption,/not a measured quantum phenotype/);assert.doesNotMatch(m.caption,/Moonwraith/);
 const d=lookSubjectLabels('dragonling',{labels});assert.equal(d.button,'Saved Zeref 3D');assert.match(d.caption,/not a newly measured quantum phenotype/);assert.doesNotMatch(d.caption,/recorded|Moonwraith/);
 const w=lookSubjectLabels('workshop',{activeName:'Pip',labels});assert.equal(w.button,'Pip');assert.equal(w.headingName,'Pip');assert.equal(w.caption,null);
});
test('a label set changes names and buttons as data, with no page edit',()=>{
 const L={subjects:{moonwraith:{button:'Aster 3D',headingName:'Aster',stageName:'Aster',caption:null}}};
 const m=lookSubjectLabels('moonwraith',{labels:L});assert.equal(m.button,'Aster 3D');assert.equal(m.headingName,'Aster');assert.equal(m.explainName,'Aster');
});
test('a replacement caption must keep the honesty wording or the built-in caption stays',()=>{
 const ok='Artistic 3D representation of Aster. Not a measured quantum phenotype.';
 assert.equal(lookSubjectLabels('moonwraith',{labels:{subjects:{moonwraith:{caption:ok}}}}).caption,ok);
 assert.match(lookSubjectLabels('moonwraith',{labels:{subjects:{moonwraith:{caption:'Aster is real and quantum.'}}}}).caption,/Not saved Zeref/);//built-in stays
 assert.equal(captionKeepsHonesty('x'),false);
});
test('the page reads labels from data and pads for the floating dock',()=>{
 const p=read('app/beast-cage/turntable/page.tsx'),c=read('app/beast-cage/turntable/turntable.module.css');
 assert.match(p,/lookSubjectLabels\(/);assert.doesNotMatch(p,/>Moonwraith 3D</);assert.doesNotMatch(p,/>Saved Zeref 3D</);
 assert.match(c,/\.page\{[^}]*padding:0 18px calc\(170px \+ env\(safe-area-inset-bottom/);
});

test('per-character labels: a raw creature name is shown friendly, and a named character uses its own button and subtitle',()=>{
 assert.equal(lookSubjectLabels('workshop',{activeName:'Zeref-Nightcat-Dragon',labels}).button,'Zeref · Nightcat Dragon');
 const k=lookSubjectLabels('workshop',{activeName:'Kitten',labels});assert.equal(k.button,'Kitten 3D');assert.equal(k.caption,'Artistic 3D model of Kitten. Not a measured quantum phenotype.');
 assert.equal(lookSubjectLabels('workshop',{activeName:'Pip',labels}).caption,null);
 const L={...labels,characters:{kitten:{name:'Kitten',model_button:'Kitten 3D',subtitle_long:'Kitten is real and quantum.'}}};assert.equal(lookSubjectLabels('workshop',{activeName:'Kitten',labels:L}).caption,null);
 for(const c of Object.values(labels.characters))assert.ok(captionKeepsHonesty(c.subtitle_long),c.name);
});
test('no Moonwraith display persona wording on the page labels',()=>{assert.doesNotMatch(JSON.stringify(labels.subjects),/Moonwraith|display persona/);});
