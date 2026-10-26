import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {OPEN_STAGE_RIG} from '../lib/universe/open-stage-rig-data.mjs';
import {stageRig,stageTimeOfHour,dirFromCam,STAGE_TIMES} from '../lib/universe/open-stage-rig.mjs';
test('generated data equals the JSON it came from',()=>{
 assert.deepEqual(JSON.parse(JSON.stringify(OPEN_STAGE_RIG)),JSON.parse(readFileSync(new URL('../lib/universe/data/open_stage_rig.json',import.meta.url),'utf8')));
 assert.match(OPEN_STAGE_RIG._label,/SEEDED/);
});
test('every class x time has key, fill, rim and a hemisphere, and a phone never goes black at night',()=>{
 for(const c of ['thin','mid','thick'])for(const t of STAGE_TIMES){const r=stageRig(c,t);
  for(const k of ['key','fill','rim']){assert.match(r[k].hex,/^#[0-9A-Fa-f]{6}$/);assert.ok(r[k].i>0&&r[k].i<10);assert.ok(Number.isFinite(r[k].az)&&r[k].el>=0&&r[k].el<=90);}
  assert.ok(r.floor>=0&&(t!=='night'||r.floor>=1.5),'night keeps a readability floor');assert.ok(r.hemi.i>=OPEN_STAGE_RIG.night_floor_hemisphere_min);assert.ok(r.exposure>0);}
});
test('hour -> time of day is total and deterministic',()=>{
 const m={3:'night',7:'dusk',9:'day',12:'day',17.6:'dusk',19.5:'twilight',22:'night',24:'night','-1':'night'};
 for(const [h,t] of Object.entries(m))assert.equal(stageTimeOfHour(+h),t,h);
 assert.equal(stageTimeOfHour(NaN),'day');
});
test('camera-relative directions: az 0 comes from the camera, +90 from the right, 180 from behind',()=>{
 const a=dirFromCam(0,0),b=dirFromCam(90,0),c=dirFromCam(180,0),u=dirFromCam(0,90);
 assert.ok(Math.abs(a[2]-1)<1e-9&&Math.abs(b[0]-1)<1e-9&&Math.abs(c[2]+1)<1e-9&&Math.abs(u[1]-1)<1e-9);
 for(const [az,el] of [[-38.5,35],[56.2,10],[-167.7,25]]){const d=dirFromCam(az,el);assert.ok(Math.abs(Math.hypot(...d)-1)<1e-9);}
});
test('the Look Closer canvas uses the stage rig only in turntable / angle mode, no Math.random',()=>{
 const s=readFileSync(new URL('../components/cosmic-companion-3d.tsx',import.meta.url),'utf8');
 assert.match(s,/stageLit/);assert.match(s,/stageRig\('thick'/);
 for(const f of ['../lib/universe/open-stage-rig.mjs'])assert.doesNotMatch(readFileSync(new URL(f,import.meta.url),'utf8'),/Math\.random/);
});
