import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');

test('Park site skin is scoped to html[data-look=park] and uses the Park palette',()=>{
 const css=read('app/park-skin.css');
 const rules=css.replace(/\/\*[\s\S]*?\*\//g,'').split('}').map(r=>r.trim()).filter(r=>r&&r.includes('{'));
 for(const r of rules){const sel=r.slice(0,r.indexOf('{')).replace(/^@media[^{]*\{/,'').trim();if(!sel||sel.startsWith('@'))continue;for(const one of sel.split(','))assert.match(one.trim(),/^html\[data-look=park\]/,`unscoped selector: ${one}`);}
 for(const hex of ['#1AA6FF','#3BCBFD','#E8FCFE','%2379D389','%234C9661','#000E57'])assert.ok(css.includes(hex),hex);
 assert.ok(!/Math\.random|url\(["']?https?:/i.test(css));
});

test('layout marks the default look before paint and keeps Classic and Genesis selectable',()=>{
 const lay=read('app/layout.tsx');
 assert.ok(lay.includes("import './park-skin.css'"));
 assert.match(lay,/data-look=\{DEFAULT_LOOK\}/);
 assert.match(lay,/v==='classic'\|\|v==='genesis'\|\|v==='park'/);
 const skin=read('components/look-skin.tsx');
 assert.ok(skin.includes('LOOK_EVENT')&&skin.includes("'storage'"));
 assert.ok(!/Math\.random/.test(skin));
});
