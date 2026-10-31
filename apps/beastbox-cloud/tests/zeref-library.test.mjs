import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {deflateRawSync,crc32} from 'node:zlib';
import {MAX_TYPED_CHARS,BRAIN,MAX_FILE_BYTES,MAX_APPEND_CHUNKS,CHUNK_MAX,LIBRARY_PASSAGES} from '../lib/library/limits.mjs';
import {fitMessage,tokenize,bestWindow} from '../lib/library/text.mjs';
import {chunkSections,chunkText} from '../lib/library/chunker.mjs';
import {buildIndex,search} from '../lib/library/bm25.mjs';
import {detectKind,parsePlain,parseEpub,checkSize,sha256Hex,htmlToText,LibraryError} from '../lib/library/parse.mjs';
import {memoryAdapter,beginDoc,appendChunks,finishDoc,deleteDoc,listLibrary,searchLibrary,setTraining,trainingManifest,approvedTrainingChunks,validateChunks} from '../lib/library/store.mjs';
import {prepareFile,preparePaste,uploadPrepared,batches} from '../lib/library/client.mjs';
import {libraryContext} from '../lib/library/context.mjs';
import {MAX_MESSAGE,GUEST_LIMIT,framePrompt,readInfo,talkPersona,talkToBeast} from '../lib/companion/beast-talk.mjs';
import {mkdtempSync,writeFileSync,existsSync} from 'node:fs';

const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
const enc=s=>new TextEncoder().encode(s);
const sha=async s=>sha256Hex(enc(s));
const PRIVATE='SENTINEL-PRIVATE-PASSAGE-9f3a';

// ---------- the typed limit and what the brain really reads ----------
test('typed limit is 8000 in the UI constant, the API and the saved-chat checks',()=>{
 assert.equal(MAX_TYPED_CHARS,8000);assert.equal(MAX_MESSAGE,8000);
 assert.match(read('../components/beast-talk-panel.tsx'),/maxLength=\{MAX_MESSAGE\}/);
 assert.match(read('../lib/companion/private-chat.mjs'),/value\.text\.length>8000/);
 assert.match(read('../lib/cosmos/private-memory.mjs'),/text\(action\.text,8000\)/);
});
test('the real brain context is stated truthfully and is smaller than the typed limit',()=>{
 assert.equal(BRAIN.contextTokens,2048);assert.equal(BRAIN.outputTokens,64);
 assert.ok(BRAIN.promptChars<=Math.floor(BRAIN.promptTokenBudget*BRAIN.charsPerToken));
 assert.ok(BRAIN.promptChars<MAX_TYPED_CHARS);assert.equal(GUEST_LIMIT,BRAIN.promptChars);
});
test('API and bridge accept the longer prompt, with a fallback for an older bridge',()=>{
 const route=read('../app/api/guest/route.ts');
 assert.match(route,/MAX_PROMPT=1800/);assert.match(route,/LEGACY_BRIDGE_PROMPT=700/);assert.match(route,/prompt_chars:sent\.length/);
 assert.match(read('../../../beastbox/guest_local.py'),/^MAX_PROMPT = 1800$/m);
});
test('a long message is cut by keyword extraction, keeps the closing question and the Zeref cue',()=>{
 const filler=Array.from({length:300},(_,i)=>`Filler sentence number ${i} talks about nothing at all.`).join(' ');
 const key='The dragon Tavrel guards the silver gate at dawn. ';
 const said=filler.slice(0,2000)+' '+key+filler.slice(2000,4000)+' Who guards the silver gate?';
 assert.ok(said.length>4000&&said.length<=MAX_MESSAGE);
 const prompt=framePrompt(talkPersona({}),[],said);
 assert.ok(prompt.length<=GUEST_LIMIT,'prompt '+prompt.length);
 assert.ok(prompt.endsWith('Who guards the silver gate?\nZeref:'));
 assert.match(prompt,/Tavrel guards the silver gate/);
 const info=readInfo(said);
 assert.equal(info.extracted,true);assert.equal(info.totalChars,said.length);assert.ok(info.readChars<info.totalChars);
 assert.match(info.note,/Zeref read [\d,]+ of [\d,]+ characters/);assert.match(info.note,/keyword match/);assert.doesNotMatch(info.note,/understood|aware/i);
});
test('messages of 400 characters or fewer are framed exactly as before',()=>{
 const p=talkPersona({});const said='hello there '.repeat(30).trim().slice(0,380);
 assert.equal(readInfo(said).extracted,false);
 assert.ok(framePrompt(p,[],said).endsWith('Keeper: '+said+'\nZeref:'));
 assert.match(readInfo('hi').note,/read all 2 characters/);
});
test('fitMessage is deterministic and never invents words',()=>{
 const text=Array.from({length:80},(_,i)=>`Sentence ${i} about topic${i%7} and moon. `).join('')+'What is topic3?';
 const a=fitMessage(text,500),b=fitMessage(text,500);
 assert.deepEqual(a,b);assert.ok(a.text.length<=500);
 for(const piece of a.text.split(' … '))assert.ok(text.includes(piece.trim()),'extracted text must be verbatim: '+piece.slice(0,40));
});
test('the guest request carries only the framed prompt and reports what Zeref read',async()=>{
 const calls=[];
 const fetchImpl=async(url,init)=>{calls.push({url,body:JSON.parse(init.body)});return new Response(JSON.stringify({provider:'rawrphos-local',model:'rawrphos-native',step:14000,guest_stateless:true,reply:'Purr.',prompt_chars:900}));};
 const long='Moon words and more moon words. '.repeat(120)+'What is the moon?';
 const r=await talkToBeast({text:long,fetchImpl,library:'[Book, ch 1] The moon is a rock.'});
 assert.equal(r.ok,true);assert.equal(r.read.extracted,true);assert.equal(r.promptChars,900);
 assert.ok(calls[0].body.text.length<=GUEST_LIMIT);assert.match(calls[0].body.text,/Notes copied from the keeper's file: \[Book, ch 1\] The moon is a rock\./);
 assert.ok(calls[0].body.text.endsWith('What is the moon?\nZeref:'));
});

// ---------- chunking ----------
test('chunking covers every character, stays under the cap and keeps its place name',()=>{
 const para=n=>Array.from({length:n},(_,i)=>`This is sentence ${i}, and it is a normal length sentence.`).join(' ');
 const text=[para(40),para(60),'x'.repeat(2500)].join('\n\n');
 const chunks=chunkSections([{loc:'Chapter 1',text}]);
 assert.ok(chunks.length>3);
 for(const c of chunks){assert.ok(c.text.length<=CHUNK_MAX);assert.equal(c.loc,'Chapter 1');}
 const joined=chunks.map(c=>c.text).join('').replace(/\s+/g,'');
 assert.equal(joined,text.replace(/\s+/g,''));
 assert.deepEqual(chunkText(text),chunkText(text));
});

// ---------- parsing ----------
test('txt and md parse; BOM, latin-1 and binary files are handled',()=>{
 const bom=new Uint8Array([0xef,0xbb,0xbf,...enc('Hello\r\nworld')]);
 assert.equal(parsePlain(bom,'txt').sections[0].text,'Hello\nworld');
 assert.match(parsePlain(new Uint8Array([0x63,0x61,0x66,0xe9]),'txt').sections[0].text,/caf/);
 const md=parsePlain(enc('# My Book\nintro text\n## Chapter One\nmoon facts\n## Chapter Two\nsun facts'),'md');
 assert.equal(md.title,'My Book');assert.deepEqual(md.sections.map(s=>s.loc),['My Book','Chapter One','Chapter Two']);
 assert.throws(()=>detectKind('a.txt',new Uint8Array([65,0,66])),/binary/);
 assert.throws(()=>parsePlain(enc('   \n  '),'txt'),LibraryError);
});
test('type and size checks give clear errors',()=>{
 assert.equal(detectKind('Book.EPUB',new Uint8Array([0x50,0x4b,3,4])),'epub');
 assert.equal(detectKind('a.pdf',enc('%PDF-1.7')),'pdf');
 assert.throws(()=>detectKind('a.exe',enc('MZ')),/Only \.txt, \.md, \.pdf and \.epub/);
 assert.throws(()=>detectKind('a.pdf',enc('hello')),/not a PDF/);
 assert.throws(()=>detectKind('a.epub',enc('hello')),/not an EPUB/);
 assert.throws(()=>checkSize(MAX_FILE_BYTES+1),/20 MB/);assert.throws(()=>checkSize(0),/empty/);
});
function zip(files,{encrypted=false,method='deflate'}={}){
 const parts=[],central=[];let off=0;
 for(const [name,content] of Object.entries(files)){
  const raw=Buffer.from(content),data=method==='deflate'?deflateRawSync(raw):raw,nm=Buffer.from(name),crc=crc32(raw);
  const lh=Buffer.alloc(30);lh.writeUInt32LE(0x04034b50,0);lh.writeUInt16LE(20,4);lh.writeUInt16LE(encrypted?1:0,6);lh.writeUInt16LE(method==='deflate'?8:0,8);lh.writeUInt32LE(crc,14);lh.writeUInt32LE(data.length,18);lh.writeUInt32LE(raw.length,22);lh.writeUInt16LE(nm.length,26);
  parts.push(lh,nm,data);
  const ch=Buffer.alloc(46);ch.writeUInt32LE(0x02014b50,0);ch.writeUInt16LE(20,4);ch.writeUInt16LE(20,6);ch.writeUInt16LE(encrypted?1:0,8);ch.writeUInt16LE(method==='deflate'?8:0,10);ch.writeUInt32LE(crc,16);ch.writeUInt32LE(data.length,20);ch.writeUInt32LE(raw.length,24);ch.writeUInt16LE(nm.length,28);ch.writeUInt32LE(off,42);
  central.push(ch,nm);off+=30+nm.length+data.length;
 }
 const dir=Buffer.concat(central),end=Buffer.alloc(22);end.writeUInt32LE(0x06054b50,0);end.writeUInt16LE(Object.keys(files).length,8);end.writeUInt16LE(Object.keys(files).length,10);end.writeUInt32LE(dir.length,12);end.writeUInt32LE(off,16);
 return new Uint8Array(Buffer.concat([...parts,dir,end]));
}
const epubFiles=()=>({
 'mimetype':'application/epub+zip',
 'META-INF/container.xml':'<?xml version="1.0"?><container><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
 'OEBPS/content.opf':'<package><metadata><dc:title>The Moon Atlas</dc:title></metadata><manifest><item id="c1" href="ch1.xhtml" media-type="application/xhtml+xml"/><item id="c2" href="text/ch2.xhtml" media-type="application/xhtml+xml"/><item id="css" href="s.css" media-type="text/css"/></manifest><spine><itemref idref="c1"/><itemref idref="c2"/></spine></package>',
 'OEBPS/ch1.xhtml':'<html><head><title>x</title><style>p{color:red}</style></head><body><h1>The First Light</h1><p>The moon is made of grey rock &amp; dust.</p><script>alert(1)</script></body></html>',
 'OEBPS/text/ch2.xhtml':'<html><body><h2>Tides</h2><p>Tides follow the moon&#39;s pull.</p><p>Second&nbsp;paragraph.</p></body></html>',
});
test('epub: title, spine order, chapter names, entities; scripts and styles are dropped',async()=>{
 const r=await parseEpub(zip(epubFiles()));
 assert.equal(r.title,'The Moon Atlas');assert.deepEqual(r.sections.map(s=>s.loc),['The First Light','Tides']);
 assert.match(r.sections[0].text,/grey rock & dust/);assert.doesNotMatch(r.sections[0].text,/alert|color:red|<p>/);
 assert.match(r.sections[1].text,/moon's pull/);
 const stored=await parseEpub(zip(epubFiles(),{method:'stored'}));assert.equal(stored.sections.length,2);
});
test('epub: DRM, damage and zip bombs are refused with plain errors',async()=>{
 await assert.rejects(parseEpub(zip(epubFiles(),{encrypted:true})),/DRM/);
 await assert.rejects(parseEpub(enc('PK not really a zip file at all.....')),/not a valid EPUB/);
 await assert.rejects(parseEpub(zip({'a.txt':'hi'})),/not look like an EPUB/);
 const bomb=zip({...epubFiles(),'big.bin':'0'.repeat(1000)});
 // lie about the uncompressed size in the central directory: 200 MB > total cap
 const dv=new DataView(bomb.buffer);let p=-1;for(let i=bomb.length-22;i>0;i--){if(dv.getUint32(i,true)===0x06054b50){p=dv.getUint32(i+16,true);break;}}
 for(let n=0;n<6;n++){const nlen=dv.getUint16(p+28,true);if(new TextDecoder().decode(bomb.subarray(p+46,p+46+nlen))==='big.bin')dv.setUint32(p+24,200*1024*1024,true);p+=46+nlen+dv.getUint16(p+30,true)+dv.getUint16(p+32,true);}
 await assert.rejects(parseEpub(bomb),/too much data|too large/);
 assert.equal(htmlToText('<p>a</p><p>b&#xZZ;</p>').includes('<'),false);
});
test('prepareFile hashes, titles and routes by kind; pdf needs the browser parser',async()=>{
 const p=await prepareFile({name:'my_story.txt',bytes:enc('Once upon a time there was a moon.')});
 assert.equal(p.kind,'txt');assert.equal(p.title,'my story');assert.equal(p.sha256,await sha('Once upon a time there was a moon.'));
 await assert.rejects(prepareFile({name:'a.pdf',bytes:enc('%PDF-1.4 x')}),/not available/);
 const pdf=await prepareFile({name:'a.pdf',bytes:enc('%PDF-1.4 x')},{parsePdf:async()=>({sections:[{loc:'p. 1',text:'Page one text.'}],title:'PDF Title'})});
 assert.equal(pdf.title,'PDF Title');assert.equal(pdf.sections[0].loc,'p. 1');
 assert.throws(()=>preparePaste('   ','x'),/Paste some text/);assert.equal(preparePaste('hello','').title,'Pasted text');
});

// ---------- retrieval ----------
const docs=[
 {id:'a',title:'Dragons',chunks:[{loc:'ch 1',text:'Dragons hoard gold in deep mountain caves and guard it fiercely.'},{loc:'ch 2',text:'The silver gate of Tavrel opens only at dawn for the keeper.'}]},
 {id:'b',title:'Cooking',chunks:[{loc:'',text:'Bread rises when yeast ferments the dough in a warm kitchen.'},{loc:'',text:'Soup needs salt, water and patience.'}]},
];
test('BM25 retrieval ranks the matching passage first, is deterministic, and respects doc filters',()=>{
 const idx=buildIndex(docs);
 const hits=search(idx,'When does the silver gate open?',{k:3});
 assert.equal(hits[0].docId,'a');assert.equal(hits[0].index,1);assert.equal(hits[0].loc,'ch 2');
 assert.deepEqual(search(idx,'yeast dough',{k:2}).map(h=>h.docId),['b']);
 assert.deepEqual(search(idx,'gate',{k:3}),search(idx,'gate',{k:3}));
 assert.deepEqual(search(idx,'gate',{docIds:['b']}),[]);
 assert.deepEqual(search(idx,'zzzzqqq'),[]);assert.deepEqual(search(buildIndex([]),'gate'),[]);
 assert.ok(tokenize('The dragons were guarding gates').includes('dragon'));
});
test('retrieved notes are verbatim excerpts, capped, and labeled RECORDED in the UI',()=>{
 const long='Intro words here. '.repeat(30)+'The silver gate of Tavrel opens only at dawn. '+'Outro words here. '.repeat(30);
 const w=bestWindow(long,'silver gate dawn',200);
 assert.ok(w.length<=200);assert.match(w,/silver gate of Tavrel/);assert.ok(long.replace(/\s+/g,' ').includes(w.slice(0,60)));
 const c=libraryContext([{doc_id:'a',title:'Dragons',loc:'ch 2',text:long,sha256:'ab'.repeat(32)}],'silver gate dawn');
 assert.equal(c.used.length,1);assert.match(c.text,/^\[Dragons, ch 2\] /);
 assert.ok(libraryContext(Array(9).fill({title:'t',text:'moon'}),'moon').used.length<=LIBRARY_PASSAGES);
 const panel=read('../components/zeref-library-panel.tsx');
 assert.match(panel,/Recorded from your file/);assert.match(panel,/copied word for word, nothing invented/);
 for(const f of ['../components/zeref-library-panel.tsx','../components/beast-talk-panel.tsx','../lib/library/store.mjs','../lib/library/context.mjs']){
  assert.doesNotMatch(read(f).replace(/RAWRPHØS[^.]*\./g,''),/\b(an? (AI|LLM)|large language model|understands|is aware|conscious)\b/i,f);
 }
});

// ---------- storage, owner scope and privacy ----------
async function addDoc(store,{title='Dragons',kind='txt',text=`${PRIVATE} The silver gate of Tavrel opens at dawn.`,hash}={}){
 const chunks=chunkText(text,'ch 1');
 const {id}=await beginDoc(store,{title,kind,sha256:hash||await sha(text+title),bytes:text.length,chars:chunks.reduce((a,c)=>a+c.text.length,0)});
 await appendChunks(store,{id,seq:1,chunks:chunks.map(c=>({l:c.loc,t:c.text}))});
 return finishDoc(store,id);
}
test('library lifecycle: begin, append, finish, list, search, delete',async()=>{
 const store=memoryAdapter();
 const doc=await addDoc(store);
 assert.equal(doc.status,'ready');assert.equal(doc.training_approved,false);assert.ok(/^[a-f0-9]{64}$/.test(doc.content_sha256));
 const list=await listLibrary(store);assert.equal(list.docs.length,1);assert.equal(list.totals.docs,1);
 const found=await searchLibrary(store,'when does the silver gate open',{k:3});
 assert.equal(found.hits.length,1);assert.match(found.hits[0].text,/Tavrel/);assert.equal(found.hits[0].title,'Dragons');
 await assert.rejects(addDoc(store),/already in the library/);
 await deleteDoc(store,doc.id);
 assert.equal((await listLibrary(store)).docs.length,0);assert.equal((await searchLibrary(store,'silver gate')).hits.length,0);
 assert.deepEqual([...store.m.keys()].filter(k=>k.includes('/docs/')),[]);
});
test('library API validation: bad ids, kinds, sizes, batches and unfinished uploads',async()=>{
 const store=memoryAdapter();const h=await sha('x');
 await assert.rejects(beginDoc(store,{title:'',kind:'txt',sha256:h,bytes:1,chars:1}),/title/);
 await assert.rejects(beginDoc(store,{title:'t',kind:'exe',sha256:h,bytes:1,chars:1}),/Unsupported/);
 await assert.rejects(beginDoc(store,{title:'t',kind:'txt',sha256:'zz',bytes:1,chars:1}),/hash/);
 await assert.rejects(beginDoc(store,{title:'t',kind:'txt',sha256:h,bytes:1,chars:5_000_000}),/Too long/);
 await assert.rejects(appendChunks(store,{id:'../../etc',seq:1,chunks:[{l:'',t:'a'}]}),/Invalid document id/);
 const {id}=await beginDoc(store,{title:'t',kind:'txt',sha256:h,bytes:9,chars:9});
 await assert.rejects(appendChunks(store,{id,seq:1,chunks:[{l:'',t:'x'.repeat(9000)}]}),/too long|more text/);
 await assert.rejects(appendChunks(store,{id,seq:1,chunks:[]}),/Send 1 to/);
 await assert.rejects(appendChunks(store,{id,seq:1,chunks:Array(MAX_APPEND_CHUNKS+1).fill({l:'',t:'a'})}),/Send 1 to/);
 await assert.rejects(appendChunks(store,{id,seq:1,chunks:[{l:'',t:12}]}),/Invalid passage/);
 await appendChunks(store,{id,seq:1,chunks:[{l:'',t:'nine char'}]});
 await assert.rejects(appendChunks(store,{id,seq:2,chunks:Array(3).fill({l:'',t:'y'.repeat(900)})}),/More text arrived/);
 await assert.rejects(finishDoc(store,'a'.repeat(24)),/not open/);
 const unfinished=await listLibrary(store);assert.equal(unfinished.docs[0].status,'uploading');
 assert.equal((await searchLibrary(store,'nine char')).hits.length,0,'unfinished uploads are never searchable');
 assert.throws(()=>validateChunks('nope'),/Send 1 to/);
});
test('library cap: documents and total characters are limited',async()=>{
 const store=memoryAdapter();
 for(let i=0;i<40;i++)await beginDoc(store,{title:'d'+i,kind:'txt',sha256:await sha('d'+i),bytes:1,chars:1});
 await assert.rejects(beginDoc(store,{title:'x',kind:'txt',sha256:await sha('x'),bytes:1,chars:1}),/at most 40/);
});
test('owner-only: every library route checks the owner session before touching storage, and visitors learn nothing',()=>{
 const base=read('../app/api/zeref/library/route.ts'),search=read('../app/api/zeref/library/search/route.ts'),training=read('../app/api/zeref/library/training/route.ts'),server=read('../lib/library/server.ts');
 assert.match(base,/if\(!await isOwner\(\)\)return safeJson\(200,\{owner:false\}\)/);
 assert.ok(base.indexOf('isOwner()')<base.indexOf('libraryStore()'));
 for(const [name,src] of [['POST',base],['search',search],['training',training]]){
  assert.ok(src.indexOf('ownerGuard(')>-1&&src.indexOf('ownerGuard(')<src.lastIndexOf('libraryStore()'),name);
 }
 assert.match(server,/if\(!await isOwner\(\)\)return safeJson\(401/);
 assert.match(server,/origin!==new URL\(request\.url\)\.origin/);
 assert.match(server,/replace\(\/https\?:\\\/\\\/\\S\+\/g,'\[url\]'\)/);
 assert.match(read('../components/zeref-library-panel.tsx'),/if\(!info\|\|!info\.owner\)return null/);
 assert.match(read('../components/beast-talk-panel.tsx'),/persona\.source==='zeref'\?<ZerefLibraryPanel/);
 assert.match(read('../components/beast-talk-panel.tsx'),/persona\.source==='zeref'&&lib\.owner&&lib\.ready/);
});
test('raw passages never appear in listings, training manifests, chat logs or teacher requests',async()=>{
 const store=memoryAdapter();const doc=await addDoc(store);
 assert.equal(JSON.stringify(await listLibrary(store)).includes(PRIVATE),false);
 await setTraining(store,doc.id,true);
 assert.equal(JSON.stringify(await trainingManifest(store)).includes(PRIVATE),false);
 const panel=read('../components/beast-talk-panel.tsx');
 // passages are held in memory state only, and are passed to RAWRPHØS only (not to the teacher call)
 assert.match(panel,/talkToBeast\(\{\.\.\.ask,route,?\}\)/);assert.match(panel,/talkToBeast\(\{\.\.\.ask,route:'guest-rawrphos',library:libraryText[,}]/);
 assert.match(panel,/libraryUsed:used\.length\?used\.map\(u=>\(\{title:u\.title,loc:u\.loc\}\)\)/);
 assert.doesNotMatch(panel,/excerpt[^;]*writeTalkLog/);
});

// ---------- training: opt-in, default off, never a bypass ----------
test('training is opt-in per document, off by default, and metadata-only in the public view',async()=>{
 const store=memoryAdapter();const a=await addDoc(store,{title:'A'}),b=await addDoc(store,{title:'B',text:'Another book about bread and yeast.'});
 let m=await trainingManifest(store);assert.equal(m.default,'off');assert.equal(m.docs.length,0);assert.equal(m.scope,'owner-only');assert.equal(m.redistribution,'none');
 assert.match(m.note,/Gate v2/);
 await setTraining(store,a.id,true);
 m=await trainingManifest(store);assert.deepEqual(m.docs.map(d=>d.title),['A']);assert.deepEqual(Object.keys(m.docs[0]).sort(),['approved_at','chars','chunks','content_sha256','id','kind','sha256','title']);
 const rows=await approvedTrainingChunks(store);assert.ok(rows.length>=1&&rows.every(r=>r.doc_id===a.id));
 await setTraining(store,a.id,false);assert.equal((await approvedTrainingChunks(store)).length,0);
 await assert.rejects(setTraining(store,a.id,'yes'),/true or false/);await assert.rejects(setTraining(store,'f'.repeat(24),true),/No such document/);
});
test('training queue is gated and does not touch the growth routine, signal loop or Gate v2',()=>{
 const script=read('../scripts/zeref-library-queue.mjs');
 assert.match(script,/ZEREF_LIBRARY_TRAINING/);assert.match(script,/!==\s*'on'/);assert.match(script,/Gate v2/);
 for(const f of ['../../../.github/workflows/zeref-continuous-learning-006.yml']){
  assert.doesNotMatch(read(f),/zeref-library/,'the continuous-learning workflow was not edited by this feature');
 }
});

// ---------- the browser half end to end against the real store ----------
function fakeApi(store,{failAt=0}={}){
 let n=0;const log=[];
 const fetchImpl=async(url,init)=>{
  const body=JSON.parse(init.body);log.push(body.action);n++;
  try{
   if(failAt&&n===failAt)return new Response(JSON.stringify({error:'Disk full'}),{status:507});
   if(body.action==='begin')return Response.json(await beginDoc(store,body),{status:201});
   if(body.action==='append')return Response.json(await appendChunks(store,body));
   if(body.action==='finish')return Response.json({ok:true,doc:await finishDoc(store,body.id)});
   if(body.action==='delete')return Response.json(await deleteDoc(store,body.id));
  }catch(e){return Response.json({error:e.publicMessage||e.message},{status:e.status||500});}
 };
 return {fetchImpl,log};
}
test('upload flow sends batches, finishes, and the text is then searchable',async()=>{
 const store=memoryAdapter(),api=fakeApi(store);
 const text=Array.from({length:400},(_,i)=>`Paragraph ${i}. ${i===321?'The lantern keeper hides the brass key under the third stair.':'Nothing happens here today.'}`).join('\n\n');
 const prepared=await prepareFile({name:'novel.md',bytes:enc(text)});
 const stages=[];
 const saved=await uploadPrepared(prepared,{fetchImpl:api.fetchImpl,onProgress:p=>stages.push(p.stage)});
 assert.equal(saved.status,'ready');assert.ok(saved.chunkCount>20);assert.deepEqual([api.log[0],api.log.at(-1)],['begin','finish']);assert.ok(stages.includes('saved'));
 const hit=(await searchLibrary(store,'where is the brass key hidden')).hits[0];assert.match(hit.text,/brass key under the third stair/);
});
test('a failed upload is cleaned up and reports the server\'s plain error',async()=>{
 const store=memoryAdapter(),api=fakeApi(store,{failAt:3});
 const text='Alpha beta gamma. '.repeat(400);
 await assert.rejects(uploadPrepared(await prepareFile({name:'a.txt',bytes:enc(text)}),{fetchImpl:api.fetchImpl}),/Disk full/);
 assert.equal((await listLibrary(store)).docs.length,0);
 assert.ok(api.log.includes('delete'));
});
test('batches respect the count and byte caps',()=>{
 const chunks=Array.from({length:1000},(_,i)=>({loc:'p. '+i,text:'x'.repeat(900)}));
 const parts=batches(chunks);assert.ok(parts.length>1);
 for(const part of parts){assert.ok(part.length<=MAX_APPEND_CHUNKS);assert.ok(JSON.stringify(part).length<1_500_000);}
 assert.equal(parts.flat().length,1000);
});
