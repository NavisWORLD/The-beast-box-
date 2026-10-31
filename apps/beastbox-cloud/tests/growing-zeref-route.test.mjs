import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('growing route is its own door, labelled, and refuses anything claiming to be the pin',()=>{
 const r=read('app/api/guest-growing/route.ts');
 assert.match(r,/'Growing Zeref · not the pin'/);
 assert.match(r,/\/api\/guest-growing/);assert.doesNotMatch(r,/\/api\/guest-local/);
 assert.match(r,/r\.checkpoint_sha256===PUBLIC_PIN\.checkpoint_sha256/);
 assert.match(r,/r\.is_public_pin!==false/);
 assert.doesNotMatch(r,/Math\.random/);
});
test('growing page and chat say "not the pin" on every reply',()=>{
 assert.match(read('app/growing/page.tsx'),/Growing Zeref · not the pin/);
 const c=read('components/growing-chat.tsx');
 assert.match(c,/\$\{r\.label\} · \$\{r\.tag\} · step \$\{r\.step\}/);
 assert.doesNotMatch(c,/\bAI\b/);
});
test('the pin guest door is untouched by the growing route',()=>{
 const g=read('app/api/guest/route.ts');
 assert.doesNotMatch(g,/growing/i);
});
