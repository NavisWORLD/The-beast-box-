/**
 * Browser-only PDF text extraction for the Zeref library (pdf.js, no network, no OCR).
 * The file never leaves the device; only extracted passages are uploaded.
 */
import {LibraryError} from './parse.mjs';
import {MAX_DOC_CHARS} from './limits.mjs';
const MAX_PAGES=2500;
export type PdfSection={loc:string;text:string};
export async function parsePdfSections(bytes:Uint8Array,onProgress?:(page:number,pages:number)=>void):Promise<{sections:PdfSection[];pages:number;title:string}>{
 const pdfjs=await import('pdfjs-dist/legacy/build/pdf.mjs');
 pdfjs.GlobalWorkerOptions.workerSrc=new URL('pdfjs-dist/legacy/build/pdf.worker.min.mjs',import.meta.url).toString();
 // pdf.js may transfer the buffer; give it a copy so the caller's hash stays valid.
 const task=pdfjs.getDocument({data:bytes.slice(),stopAtErrors:false,isEvalSupported:false,disableFontFace:true,useSystemFonts:false,enableXfa:false});
 let doc:Awaited<typeof task.promise>|null=null;
 try{
  doc=await task.promise;
  if(doc.numPages>MAX_PAGES)throw new LibraryError(`This PDF has ${doc.numPages} pages. The limit is ${MAX_PAGES}.`);
  const sections:PdfSection[]=[];let chars=0;
  for(let n=1;n<=doc.numPages;n++){
   const page=await doc.getPage(n);
   const content=await page.getTextContent();
   let text='';
   for(const item of content.items){if('str' in item){text+=item.str+(item.hasEOL?'\n':' ');}}
   text=text.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g,' ').replace(/[ \t]+/g,' ').replace(/ ?\n ?/g,'\n').trim();
   page.cleanup();
   onProgress?.(n,doc.numPages);
   if(!text)continue;
   chars+=text.length;
   if(chars>MAX_DOC_CHARS)throw new LibraryError(`This PDF has more than ${MAX_DOC_CHARS.toLocaleString('en-US')} characters of text.`);
   sections.push({loc:'p. '+n,text});
  }
  if(!sections.length)throw new LibraryError('This PDF has no extractable text. It may be scanned pages; those need OCR, which is not available here.');
  let title='';
  try{const meta=await doc.getMetadata();const t=(meta?.info as {Title?:unknown}|undefined)?.Title;if(typeof t==='string')title=t.trim().slice(0,120);}catch{/* no metadata */}
  return {sections,pages:doc.numPages,title};
 }catch(e){
  if(e instanceof LibraryError)throw e;
  const name=(e as {name?:string})?.name;
  if(name==='PasswordException')throw new LibraryError('This PDF is password protected.');
  throw new LibraryError('This PDF could not be read. It may be damaged.');
 }finally{await doc?.destroy().catch(()=>undefined);await task.destroy?.();}
}
