import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {parkGradeBudget,PARK_GRADE_FRAG,PARK_GRADE_LABEL} from '../lib/look/third-party/park-grade.ts';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('third-party grade: tier-scaled (LOW none, MED grade only, GOD grade + SMAA)',()=>{
 assert.equal(parkGradeBudget('LOW').grade,false);assert.equal(parkGradeBudget('MED').smaa,false);assert.equal(parkGradeBudget('GOD').smaa,true);
 assert.ok(parkGradeBudget('GOD').saturation<1.15,'gentle: our Park grade already saturates');
});
test('third-party grade: after the one ACES OutputPass, SMAA last; attributed; no random',()=>{
 const c=read('lib/universe/post-chain-three.ts');const o=c.indexOf('new OutputPass()'),g=c.indexOf('fragmentShader:PARK_GRADE_FRAG'),s=c.indexOf('new SMAAPass()');
 assert.ok(o>0&&g>o&&s>g);
 const src=read('lib/look/third-party/park-grade.ts');assert.match(src,/THIRD-PARTY \(MIT\)/);assert.match(src,/Copyright \(c\) 2026 Paulius/);assert.doesNotMatch(src,/Math\.random/);
 assert.match(read('THIRD_PARTY_NOTICES.md'),/park-grade\.ts/);assert.match(PARK_GRADE_LABEL,/third-party/);assert.match(PARK_GRADE_FRAG,/uLift/);
});
