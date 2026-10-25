// Deterministic keyword (BM25) lookup in the owner's library. Owner session only.
import {safeJson} from '@/lib/security';
import {ownerGuard,libraryStore,errorResponse,readJson} from '@/lib/library/server';
import {searchLibrary} from '@/lib/library/store.mjs';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export async function POST(request:Request){
 const denied=await ownerGuard(request,{write:true});if(denied)return denied;
 const store=libraryStore();
 if(!store)return safeJson(503,{error:'Library storage is not configured on this site.'});
 const body=await readJson(request);
 if(!body||typeof body.query!=='string')return safeJson(400,{error:'Send {query}'});
 const k=Number.isInteger(body.k)?Math.min(5,Math.max(1,body.k as number)):3;
 try{
  const out=await searchLibrary(store,body.query,{k,docIds:Array.isArray(body.doc_ids)?body.doc_ids as string[]:null});
  return safeJson(200,{ok:true,method:'bm25-keyword',label:'RECORDED from your uploaded files; passages are copied verbatim, nothing is invented.',...out});
 }catch(e){return errorResponse(e);}
}
