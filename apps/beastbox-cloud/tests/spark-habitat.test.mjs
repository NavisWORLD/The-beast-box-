import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {habitatPose} from '../public/spark/habitat.mjs';
test('all generated gait families stay bounded and reduced motion rests in place',()=>{
 for(const gait of ['bob','hop','sway','float','wobble','scuttle','pulse'])for(const temperament of ['Playful','Serene','Dreamy']){
  const gen={behavior:{gait,tempo_hz:2,amplitude_px:3},temperament},samples=new Set();
  for(let i=0;i<360;i++){
   const p=habitatPose(gen,i/10);assert.ok(p.x>=10&&p.x<=134&&p.y>=10&&p.y<=54);assert.ok(Number.isFinite(p.rotation));samples.add([p.x,p.y,p.scale].join('|'));
   const reduced=habitatPose(gen,i/10,'idle',true);assert.deepEqual([reduced.x,reduced.y,reduced.rotation,reduced.scale],[72,38,0,1]);
   const rest=habitatPose(gen,i/10,'rest');assert.deepEqual([rest.x,rest.y,rest.rotation,rest.scale],[72,38,0,1]);
  }
  assert.ok(samples.size>100,`${gait} moves`);
 }
});
test('the public care modules are the existing Beast Box rules byte for byte',()=>{
 for(const name of ['session','learn','adventure'])assert.equal(readFileSync(new URL(`../public/spark/shared/${name}.mjs`,import.meta.url),'utf8'),readFileSync(new URL(`../lib/companion/${name}.mjs`,import.meta.url),'utf8'));
});
