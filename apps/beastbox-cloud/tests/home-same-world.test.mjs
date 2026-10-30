import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const h=readFileSync(new URL('../components/home-pocket.tsx',import.meta.url),'utf8');
test('home tiny universe: guests see the same embedded living world as /beast-cage/world unless they picked the pocket',()=>{
 assert.match(h,/const guestWorld=!own&&!guestPocket/);
 assert.match(h,/\(\(own&&homeView==='world'\)\|\|guestWorld\)&&!world&&!softHome\?<LivingWorld embedded/);
 assert.match(h,/genome=\{own\?\.genome\|\|null\}/);assert.doesNotMatch(h,/Math\.random/);
});
test('home bubble: Universe button and the world View/Quality chips never overlap',()=>{
 const css=readFileSync(new URL('../app/globals.css',import.meta.url),'utf8');
 assert.match(css,/\.beast-landing-art:has\(\[data-lw-view\]\) \.home-menu-layer \[data-world-menu=home\]\{right:auto!important;left:16%!important\}/);
 assert.match(css,/\.beast-landing-art \[data-lw-view-chips\]\{right:17%!important;top:13%!important\}/);
});
import {guestPickedPocket} from '../lib/world/home-guest-view.mjs';
test('guestPickedPocket reads only, defaults to the world',()=>{const st=v=>({getItem:()=>v});
 assert.equal(guestPickedPocket(st(null)),false);assert.equal(guestPickedPocket(st('world')),false);assert.equal(guestPickedPocket(st('pocket')),true);assert.equal(guestPickedPocket(st('classic')),true);assert.equal(guestPickedPocket({getItem(){throw 1}}),false);});
