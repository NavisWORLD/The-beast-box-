import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('dock labels match the served V12.2 cartridge',()=>{const dock=read('components/lost-cosmos-dock.tsx');const rel=read('app/api/gba-release/route.ts');
 assert.match(rel,/rom_release:'current-verified-v12\.2'/);assert.doesNotMatch(dock,/V11\.2/);assert.match(dock,/V12\.2/);});
test('phone chat launcher lives in the bottom control lane, not over page CTAs',()=>{const css=read('components/beast-chat-overlay.module.css');
 const m=css.match(/@media\(max-width:480px\)\{\.launcher\{[^}]*bottom:calc\((\d+)px/);assert.ok(m,'phone launcher rule');assert.ok(Number(m[1])<=64);
 assert.match(read('app/globals.css'),/@media\(max-width:480px\)\{body\{padding-bottom:calc\(120px/);});
