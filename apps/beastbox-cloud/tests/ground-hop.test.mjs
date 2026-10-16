import test from 'node:test';import assert from 'node:assert/strict';
import {createHop,stepHop} from '../lib/physics/ground-hop.mjs';
test('hops are grounded: feet never go below the ground and creatures land',()=>{
 const H=createHop('t');let minY=9,air=0;for(let i=0;i<1200;i++){const p=stepHop(H,1/60,{mode:'play',speed:.5,groundY:.1});minY=Math.min(minY,p.y);if(p.air)air++;}
 assert.ok(minY>=.1-1e-9);assert.ok(air>0);assert.ok(H.landed>2);
 const N=createHop('n');for(let i=0;i<600;i++){const p=stepHop(N,1/60,{mode:'nap',groundY:0});assert.equal(p.y,0);}
});
test('frame-rate independent (120 Hz fixed step)',()=>{const a=createHop('x'),b=createHop('x');let pa,pb;
 for(let i=0;i<240;i++)pa=stepHop(a,1/120,{mode:'play'});for(let i=0;i<60;i++)pb=stepHop(b,1/30,{mode:'play'});assert.ok(Math.abs(pa.y-pb.y)<1e-9);});
