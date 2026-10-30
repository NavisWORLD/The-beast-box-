import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {VIEW_MODES,readViewMode,writeViewMode,nextViewMode,viewModeLabel,viewModeCamera,VIEW_MODE_KEY,DEFAULT_VIEW_MODE} from '../lib/world/view-mode.mjs';
const mem=()=>{const m=new Map();return {getItem:k=>m.has(k)?m.get(k):null,setItem:(k,v)=>m.set(k,String(v)),removeItem:k=>m.delete(k)};};
test('one chip cycles First person, Behind {beast}, Orbit; default is today\'s first-person eye',()=>{
 assert.deepEqual([...VIEW_MODES],['first','behind','orbit']);assert.equal(DEFAULT_VIEW_MODE,'first');
 assert.deepEqual(VIEW_MODES.map(nextViewMode),['behind','orbit','first']);
 assert.equal(viewModeLabel('first','Duskscale'),'View: First person');assert.equal(viewModeLabel('behind','Duskscale'),'View: Behind Duskscale');
 assert.equal(viewModeLabel('behind',''),'View: Behind your beast');assert.equal(viewModeLabel('orbit'),'View: Orbit');
 for(const m of VIEW_MODES)assert.ok(viewModeLabel(m,'Duskscale').length<=44);
 assert.deepEqual(viewModeCamera('first'),{eye:true,forceOrbit:false});assert.deepEqual(viewModeCamera('behind'),{eye:false,forceOrbit:false});assert.deepEqual(viewModeCamera('orbit'),{eye:false,forceOrbit:true});
});
test('the choice is remembered per device and survives a broken store',()=>{
 const s=mem();assert.equal(readViewMode(s),'first');writeViewMode(s,'orbit');assert.equal(s.getItem(VIEW_MODE_KEY),'orbit');assert.equal(readViewMode(s),'orbit');
 assert.equal(readViewMode({getItem(){throw 0;}}),'first');writeViewMode(s,'nope');assert.equal(readViewMode(s),'first');
});
test('the world wires the chip and keeps the existing eye path',()=>{
 const lw=fs.readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
 assert.match(lw,/data-lw-view=\{viewMode\}/);assert.match(lw,/viewModeCamera\(viewRef\.current\)/);assert.match(lw,/__lwEye!==false/);
});
