// Oct 30 2026 live-shot fixes on /beast-cage/world: orbit shows space + stars (no olive dome band), no boom-ring arcs over the sea in orbit,
// the View chip names the camera you are actually in, and the label stack folds into "How this look is made".
import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {viewChipLabel,viewModeLabel} from '../lib/world/view-mode.mjs';
const src=fs.readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
test('chip says Orbit until you spawn in',()=>{
 assert.equal(viewChipLabel('first','Glacecoil',false),'View: Orbit · Spawn in for First person');
 assert.equal(viewChipLabel('first','Glacecoil',true),viewModeLabel('first','Glacecoil'));
 assert.equal(viewChipLabel('orbit','x',false),'View: Orbit');
 assert.match(src,/viewChipLabel\(viewMode,beastName,spawned\)/);});
test('orbit: space background, stars on (LOW and no-GPU too), dome + boom rings off',()=>{
 const i=src.indexOf("orbAlt>=ORBIT_SPACE_ALT");assert.ok(i>0);const seg=src.slice(i,i+1300);
 assert.match(seg,/lk2Sky\.dome\.visible=false/);assert.match(seg,/copy\(SPACE_BG\)/);assert.match(seg,/lwStars\.visible=true/);
 assert.match(seg,/ringOut\.visible=ringIn\.visible=ringBody\.visible=false/);assert.doesNotMatch(seg,/softGL|tier/);
 assert.doesNotMatch(src,/Math\.random/);});
test('labels fold into How this look is made (closed by default)',()=>{
 assert.doesNotMatch(src,/open=\{!spawned\}/);assert.match(src,/display:'inline-block',fontSize:12[^>]*>How this look is made<\/summary>/);});
