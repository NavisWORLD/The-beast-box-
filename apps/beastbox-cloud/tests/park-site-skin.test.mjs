import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');

test('Park site skin is scoped to html[data-look=park] and stays inside the pocket window',()=>{
 const css=read('app/park-skin.css');
 const rules=css.replace(/\/\*[\s\S]*?\*\//g,'').split('}').map(r=>r.trim()).filter(r=>r&&r.includes('{'));
 for(const r of rules){const sel=r.slice(0,r.indexOf('{')).replace(/^@media[^{]*\{/,'').trim();if(!sel||sel.startsWith('@'))continue;for(const one of sel.split(','))assert.match(one.trim(),/^html\[data-look=park\]/,`unscoped selector: ${one}`);}
 for(const hex of ['#1AA6FF','#3BCBFD','#79D389','#4C9661'])assert.ok(css.includes(hex),hex);
 assert.ok(!/Math\.random|url\(["']?https?:/i.test(css));
});

test('Cory Nov 12: the page background is not the living world; the world stays in its own pocket dimension',()=>{
 const css=read('app/park-skin.css').replace(/\/\*[\s\S]*?\*\//g,'');
 for(const sel of [' body',' .hero::before',' .hero::after',' .cage-universe',' main[data-reduced-motion]',' .landing',' .cage-sky',' .public-header',' .hero-copy'])
  assert.ok(!css.includes('html[data-look=park]'+sel),'page-level Park skin is gone: '+sel);
 assert.match(css,/html\[data-look=park\] \.beast-landing-art\{background:/);
 const home=read('components/home-pocket.tsx');assert.match(home,/<LivingWorld embedded/);
});

test('layout always marks Park, with no look chooser left on the page',()=>{
 const lay=read('app/layout.tsx');
 assert.ok(lay.includes("import './park-skin.css'"));
 assert.match(lay,/<html lang="en" data-look="park">/);
 assert.doesNotMatch(lay,/look-skin|lookBoot/);
});
