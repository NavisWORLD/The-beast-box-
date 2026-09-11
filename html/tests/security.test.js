import test from 'node:test';import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';
const root=new URL('../',import.meta.url);
test('bundle contains no obvious secret assignments or privileged key material',async()=>{const files=['app.js','serve.py','index.html'];for(const f of files){const s=await readFile(new URL(f,root),'utf8');assert.doesNotMatch(s,/sk-[A-Za-z0-9]{20,}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----/);assert.doesNotMatch(s,/api[_-]?key\s*[:=]\s*['"][^'"]{12,}['"]/i)}});
test('rendered user content is escaped',async()=>{const s=await readFile(new URL('app.js',root),'utf8');assert.match(s,/function escapeHtml/);assert.match(s,/replace\(\/\[&<>/)});
test('standalone client does not request arbitrary filesystem access',async()=>{const s=await readFile(new URL('app.js',root),'utf8');assert.doesNotMatch(s,/showDirectoryPicker|webkitdirectory/)});
