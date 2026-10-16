import test from 'node:test';import assert from 'node:assert/strict';
import {createCSTTurntable} from '../lib/physics/cst-turntable.mjs';
test('CST turntable is deterministic, advances, and is not a linear spin',()=>{
 const a=createCSTTurntable('res_nyxbean'),b=createCSTTurntable('res_nyxbean');const ys=[];
 for(let i=0;i<240;i++){const r=a.step(1/60);b.step(1/60);ys.push(r.yaw);}
 assert.equal(a.yaw,b.yaw);assert.ok(a.yaw>0.5,'turns');
 const d=ys.slice(1).map((y,i)=>y-ys[i]);const mean=d.reduce((s,x)=>s+x,0)/d.length;
 assert.ok(d.some(x=>Math.abs(x-mean)>mean*.05),'velocity varies (inertia + sway)');
});
