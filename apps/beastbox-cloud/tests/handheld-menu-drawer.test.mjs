import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const src=readFileSync(new URL('../components/sol-spark-player.tsx',import.meta.url),'utf8');
const nav=src.slice(src.indexOf('aria-label="Game actions"'),src.indexOf('</nav>',src.indexOf('aria-label="Game actions"')));
const drawer=src.slice(src.indexOf('id="handheld-menu"'));
test('essentials stay on the toolbar; settings move into the handheld MENU drawer',()=>{
 for(const k of ['FULL SCREEN','MINIMIZE','☰ MENU'])assert.ok(nav.includes(k),k);
 for(const k of ['PAUSE','RELOAD SAVE','SAVE JOURNEY','BEAST BOX ↗'])assert.ok(!nav.includes(k)&&drawer.includes(k),k);
 for(const k of ['SOUND','DISPLAY','CARTRIDGE','INPUT'])assert.ok(drawer.includes(`<span>${k}</span>`),k);
 assert.match(src,/onMenu=\{\(\)=>setMenuOpen/);
});
test('pre-boot poster is page-level and clears when the cartridge reports running',()=>{
 assert.match(src,/\{bound&&!running&&!starting\?<div className=\{css\.preboot\} data-preboot-poster/);
 assert.match(src,/Tap START LOST COSMOS/);
});
test('sound lives in the handheld MENU: mute toggle posts to the cartridge, no stray in-frame sound row space',()=>{
 assert.match(src,/post\(\{type:'sol-spark-audio-mute',muted:audio\.wanted\}\)/);
 const css=readFileSync(new URL('../components/sol-spark-player.module.css',import.meta.url),'utf8');
 assert.match(css,/\.screen\[data-has-frame=true\]\{padding-bottom:0\}\s*$/m);
});
