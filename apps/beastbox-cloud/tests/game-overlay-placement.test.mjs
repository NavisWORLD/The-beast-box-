import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const r=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('player publishes its mode for the shared overlay placement rules',()=>{
 assert.match(r('components/sol-spark-player.tsx'),/root\.dataset\.gamePlayer=minimized\?'minimized':mode/);
 const g=r('app/globals.css');
 assert.match(g,/html\[data-game-player=immersive\] aside\[aria-label="Cosmic sound controls"\]/);
 assert.match(g,/html\[data-game-player=minimized\] button\[aria-controls=beast-chat-overlay\]/);
});
test('header and TALK launcher name the same creature as the chat (no bare "Beast" fallback when a cage companion exists)',()=>{
 assert.match(r('components/sol-spark-player.tsx'),/talkPersona\(\{beast:null,cage:cageProfile\}\)\.name/);
 assert.match(r('components/sol-game-talk.tsx'),/TALK TO \{talkName\}/);
});
test('expanded portrait play widens the framebuffer edge to edge',()=>{
 assert.match(r('components/sol-spark-player.module.css'),/\[data-player-mode=immersive\]>\.screen\{max-width:none/);
});
