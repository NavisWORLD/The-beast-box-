import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const src=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
test('living world wires the roadster flight: lift off, thrust, brake, land, exit to orbit, cockpit camera',()=>{
 for(const m of ['data-lw-liftoff','data-lw-land','data-lw-thrust','data-lw-brake','data-lw-flight-hud','data-lw-exit','stepFlight(','landingAssist(','ascentAssist(','__lwFlight','__lwFlightCam'])assert.ok(src.includes(m),'missing '+m);});
test('flight is labelled SIMULATED and the existing Roadster · SEEDED label is kept',()=>{assert.ok(src.includes('FLIGHT_LABEL'));assert.ok(src.includes('ROADSTER_LABEL'));});
test('flight never reads walkOn and never touches the dock or the growth routine',()=>{
 const a=src.indexOf('// ---- roadster flight');const b=src.indexOf('place(travNode,pN,pF);if(rf.on)');assert.ok(a>0&&b>a);
 const blk=src.slice(a,b);assert.ok(!/walkOn|setGrowth|growthFrame|site-dock|world-menu/.test(blk));});
test('while flying: the walk input is zeroed, the ground camera far plane is left alone, the sea tint is off, and the car is taken out of the traveler group',()=>{
 assert.ok(src.includes('const mag=rf.on?0:'));assert.ok(src.includes('!rf.blend&&Math.abs(camera.far-farW)'));assert.ok(src.includes('sp&&!rf.on?mover.w.swim:0'));assert.ok(src.includes('scene.add(car.root)')&&src.includes('travNode.add(car.root)'));});
test('no limits imposed by us: the flight block has no speed or distance clamp',()=>{
 const a=src.indexOf('// ---- roadster flight');const b=src.indexOf('place(travNode,pN,pF);if(rf.on)');const blk=src.slice(a,b);
 assert.ok(!/Math\.min\([^)]*(speed|alt|\.r\b)/.test(blk.replace(/toFixed\([^)]*\)/g,'')),'no min() clamp on speed/alt/r');});
