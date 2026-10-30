import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const lw=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');const oc=readFileSync(new URL('../lib/universe/p3-ocean-three.ts',import.meta.url),'utf8');
test('first-person look input exists (drag + PageUp/PageDown) and is applied to the eye',()=>{assert.ok(lw.includes('let fpY=0,fpP=0'));assert.ok(lw.includes("KP.has('pageup')"));assert.ok(lw.includes('__lwFpLook'));});
test('neighbour planets get a first-person sky placement and are restored in orbit',()=>{assert.ok(lw.includes('__lwFpPlanets'));assert.ok(lw.includes('m.userData.home'));assert.ok(lw.includes('ringU.uC.value.copy'));});
test('night sea sheen is DERIVED from the night sky, reflection only',()=>{assert.ok(oc.includes('uNS'));assert.ok(oc.includes('uMoonD'));assert.ok(!/Math\.random/.test(oc+lw));});
test('first-person tilt is clamped to about ±85° everywhere it is set',()=>{assert.ok(lw.includes('const FP_TILT=85*Math.PI/180'));assert.ok(!/fpP=Math\.max\(-1\.2/.test(lw));assert.ok(!/Math\.min\(1\.3,fpP/.test(lw));});
test('arrow keys and the wheel turn and tilt the eye in first person; orbit drag stays off',()=>{assert.ok(lw.includes("KP.has('arrowleft')"));assert.ok(lw.includes("KP.has('arrowup')"));assert.ok(lw.includes('if(fpOn){fpP=Math.max(-FP_TILT'));assert.ok(lw.includes('const AW=!fpOn'));assert.ok(lw.includes('const pd=(e:PointerEvent)=>{if(fpOn)return;'));});
test('12D lattice lines hide in first person',()=>{assert.ok(lw.includes('latPivot.visible=!want'));});
test('far night sea sheen ~0.04, DERIVED reflection only',()=>{assert.ok(/far night sheen ~0\.04/.test(oc));assert.ok(oc.includes('vec3(.034,.04,.048)*(1.0-fd)'));});
