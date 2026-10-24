import test from 'node:test';import assert from 'node:assert/strict';
import {doorProgress,doorPreload,altFull,groundAlpha,doorZoomStep,DOOR_FAR,DOOR_NEAR} from '../lib/universe/door.mjs';
test('door dissolve is 0 far out, 1 at the matched orbit framing, monotonic and never a step',()=>{
  assert.equal(doorProgress(20),0);assert.equal(doorProgress(DOOR_FAR),0);assert.equal(doorProgress(DOOR_NEAR),1);assert.equal(doorProgress(2),1);
  let prev=0,maxJump=0;for(let r=DOOR_FAR;r>=DOOR_NEAR;r-=0.01){const v=doorProgress(r);assert.ok(v>=prev-1e-12);maxJump=Math.max(maxJump,v-prev);prev=v;}
  assert.ok(maxJump<0.05,'no frame-sized jump');assert.ok(doorPreload(8)&&!doorPreload(12));
});
test('ground layer follows ZOOM_GUIDE: alt_full = min(3000 m, 0.05 R); opaque below, gone at 2x',()=>{
  assert.equal(altFull(6371000),3000);assert.equal(altFull(10000),500);
  assert.equal(groundAlpha(0,6371000),1);assert.equal(groundAlpha(3000,6371000),1);assert.equal(groundAlpha(6000,6371000),0);assert.equal(groundAlpha(1e6,6371000),0);
  const m=groundAlpha(4500,6371000);assert.ok(m>0.4&&m<0.6);
});
test('door zoom buttons route into the pocket world and leave only from full orbit',()=>{
  assert.deepEqual(doorZoomStep(1,-1),{z:0.8,leave:false});assert.deepEqual(doorZoomStep(0.1,-1),{z:0,leave:false});
  assert.deepEqual(doorZoomStep(0.5,1),{z:0.7,leave:false});assert.deepEqual(doorZoomStep(1,1),{z:1,leave:true});
});
