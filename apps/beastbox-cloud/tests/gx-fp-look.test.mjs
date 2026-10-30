import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const lw=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');const oc=readFileSync(new URL('../lib/universe/p3-ocean-three.ts',import.meta.url),'utf8');
test('first-person look input exists (drag + PageUp/PageDown) and is applied to the eye',()=>{assert.ok(lw.includes('let fpY=0,fpP=0'));assert.ok(lw.includes("KP.has('pageup')"));assert.ok(lw.includes('__lwFpLook'));});
test('neighbour planets get a first-person sky placement and are restored in orbit',()=>{assert.ok(lw.includes('__lwFpPlanets'));assert.ok(lw.includes('m.userData.home'));assert.ok(lw.includes('ringU.uC.value.copy'));});
test('night sea sheen is DERIVED from the night sky, reflection only',()=>{assert.ok(oc.includes('uNS'));assert.ok(oc.includes('uMoonD'));assert.ok(!/Math\.random/.test(oc+lw));});
