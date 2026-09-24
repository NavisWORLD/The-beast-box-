import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=path=>readFileSync(new URL('../'+path,import.meta.url),'utf8');

test('PDF selected-file-only extraction is bounded and page-marked',()=>{
 const pdf=read('lib/local-pdf.ts');
 assert.match(pdf,/MAX_FILE_BYTES=4\*1024\*1024/);
 assert.match(pdf,/MAX_PAGES=12/);
 assert.match(pdf,/MAX_DOCUMENT_PAGES=100/);
 assert.match(pdf,/MAX_CHARS=10_800/);
 assert.match(pdf,/String\.fromCharCode\(\.\.\.bytes\.slice\(0,5\)\)!=='%PDF-'/);
 assert.match(pdf,/crypto\.subtle\.digest\('SHA-256',bytes\)/);
 assert.match(pdf,/data:bytes,stopAtErrors:true,isEvalSupported:false/);
 assert.match(pdf,/\[PDF page /);
 assert.match(pdf,/doc\.destroy\(\)/);
 assert.doesNotMatch(pdf,/fetch\(|navigator\.sendBeacon|localStorage|sessionStorage|XMLHttpRequest/);
});
test('owner click is required; no PDF bytes or links are submitted to model',()=>{
 const ui=read('components/studio.tsx');
 assert.match(ui,/onClick=\{\(\)=>void extractPdf\(a\)\}/);
 assert.match(ui,/const result=await extractLocalPdf\(item\.original\)/);
 assert.match(ui,/a\.text===undefined/);
 assert.match(ui,/scope:'temporary_attachment'/);
 assert.match(ui,/!!extractingPdf\|\|!prompt\.trim\(\)/);
 const lock=JSON.parse(read('package.json'));
 assert.equal(lock.dependencies['pdfjs-dist'],'4.10.38');
});
