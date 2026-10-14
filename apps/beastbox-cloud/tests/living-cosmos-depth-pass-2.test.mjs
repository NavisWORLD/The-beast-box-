import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const r=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('companion 3D keeps rig and adds disposed contact shadow + back glow',()=>{const s=r('components/cosmic-companion-3d.tsx');
 assert.match(s,/createCreatureRig\(profile,look,quality\)/);assert.match(s,/shadowTex\.dispose\(\)/);assert.match(s,/backGlow\.geometry\.dispose\(\)/);});
test('controller, chat sheet and spark nav polish are additive and motion-safe',()=>{
 assert.match(r('components/gba-controls.module.css'),/\.handheld\{filter:drop-shadow/);
 const c=r('components/beast-chat-overlay.module.css');assert.match(c,/prefers-reduced-motion:no-preference\)\{\.panel\{animation:lcSheetRise/);
 assert.match(r('public/spark/spark.css'),/\.mobile-nav\{-webkit-backdrop-filter/);});
