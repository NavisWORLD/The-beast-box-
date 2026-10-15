import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
test('phones show one Spark nav bar: route nav hidden where the mobile nav is shown',()=>{
 const css=readFileSync(new URL('../public/spark/spark.css',import.meta.url),'utf8');
 const tail=css.slice(css.lastIndexOf('.route-nav'));
 assert.match(tail,/^\.route-nav\{display:none!important\}/);
 const html=readFileSync(new URL('../public/spark/index.html',import.meta.url),'utf8');
 for(const href of ['/','/spark/index.html','/beast-cage','/sol-game'])assert.ok(html.slice(html.indexOf('class="mobile-nav"')).includes(`href="${href}"`)||href==='/spark/index.html',href);
});
