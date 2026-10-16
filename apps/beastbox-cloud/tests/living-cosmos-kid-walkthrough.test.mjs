import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const r=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('kid-friendly copy keeps technical detail behind a disclosure',()=>{const g=r('app/sol-game/page.tsx');
 assert.match(g,/Tap <b>SEND BEAST<\/b>/);assert.match(g,/<summary[^>]*>About this cartridge<\/summary><p[^>]*>Cartridge V11\.9 · Act II/);
 assert.match(r('components/beast-talk-panel.tsx'),/Type below, then tap Send\.<small> \{persona\.name\}&apos;s replies come from RAWRPHØS, never from a script\./);});
test('phone minimized player is a small bottom-left pill clear of the hero CTAs',()=>{const c=r('components/sol-spark-player.module.css');
 assert.match(c,/@media\(max-width:480px\)\{\.shell\[data-player-mode=minimized\]\{[^}]*left:80px/);});
