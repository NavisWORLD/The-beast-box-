import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync,existsSync} from 'node:fs';import {createHash} from 'node:crypto';
import {ROADSTER_LABEL,bodyVariantIndex,wheelOmega,steerAngle,driveState,bodyBob,headlamp,underglow} from '../lib/universe/roadster-view.mjs';
test('label is exactly Roadster · SEEDED',()=>assert.equal(ROADSTER_LABEL,'Roadster · SEEDED'));
test('cherry is the fixed default and the most common; 1..3 are seeded variants',()=>{
 assert.equal(bodyVariantIndex(0),0);assert.equal(bodyVariantIndex(.39),0);assert.equal(bodyVariantIndex(.4),1);assert.equal(bodyVariantIndex(.65),2);assert.equal(bodyVariantIndex(.99),3);assert.equal(bodyVariantIndex(NaN),0);});
test('rolling numbers match Cosmo pack: omega=v/r (6.2 rad/s at 2 m/s, r=.32), steer max 28 deg',()=>{
 assert.ok(Math.abs(wheelOmega(2)-6.25)<.01);assert.ok(Math.abs(wheelOmega(6,.32)-18.75)<.01);assert.ok(Math.abs(steerAngle(5)-28*Math.PI/180)<1e-9);});
test('states, bob and lamps are pure and respect reduced motion',()=>{
 assert.equal(driveState(0),'idle');assert.equal(driveState(-3),'drive');assert.equal(bodyBob(6,1.3,true),0);
 assert.ok(Math.abs(bodyBob(6,.01))<=.014+1e-9);assert.deepEqual(headlamp('idle',1,0),headlamp('idle',1,0));
 assert.equal(underglow('drive',0).hex,'#5fe7ff');assert.equal(underglow('idle',0).hex,'#b48cff');});
test('module reads no clock and no Math.random',()=>{const s=readFileSync(new URL('../lib/universe/roadster-view.mjs',import.meta.url),'utf8').replace(/\/\*[\s\S]*?\*\//g,'');assert.ok(!/Math\.random|Date\.|performance\./.test(s));});
test('Cosmo asset copied byte-identical',()=>{const f=new URL('../public/universe/livingworld/roadster/roadster.glb',import.meta.url);assert.ok(existsSync(f));assert.equal(createHash('sha256').update(readFileSync(f)).digest('hex'),'b600ff17ac6bb4e6c761f03b96b1bfa166e9d452f64a28a2eb34bf57a68bd328');});
test('living world adds the button and keeps motion on the existing mover',()=>{const lw=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
 assert.match(lw,/data-lw-roadster/);assert.match(lw,/ROADSTER_LABEL/);assert.ok(!/roadster[^\n]{0,80}walkOn/i.test(lw));});
