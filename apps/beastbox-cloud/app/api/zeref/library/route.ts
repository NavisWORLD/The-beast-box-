// Zeref's private library: list (GET) and manage (POST). Owner session only.
// Browsers parse the file and send extracted passages; raw files never reach the server.
import {isOwner,safeJson} from '@/lib/security';
import {ownerGuard,libraryStore,errorResponse,readJson} from '@/lib/library/server';
import {listLibrary,beginDoc,appendChunks,finishDoc,deleteDoc,setTraining} from '@/lib/library/store.mjs';
import {MAX_FILE_BYTES,MAX_DOC_CHARS,MAX_LIBRARY_CHARS,MAX_DOCS,MAX_TYPED_CHARS,BRAIN} from '@/lib/library/limits.mjs';
export const runtime='nodejs';
export const dynamic='force-dynamic';
const limits={max_file_bytes:MAX_FILE_BYTES,max_doc_chars:MAX_DOC_CHARS,max_library_chars:MAX_LIBRARY_CHARS,max_docs:MAX_DOCS,max_typed_chars:MAX_TYPED_CHARS,brain:BRAIN,types:['txt','md','pdf','epub','paste']};

export async function GET(){
 // Visitors learn only that they are not the owner; nothing about stored content.
 if(!await isOwner())return safeJson(200,{owner:false});
 const store=libraryStore();
 if(!store)return safeJson(200,{owner:true,configured:false,limits,docs:[],totals:{docs:0,chars:0,chunks:0},
  hint:'Library storage is not set up on this site yet. The site owner needs the Azure storage settings (AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_CONTAINER_SAS_URL) in Vercel.'});
 try{return safeJson(200,{owner:true,configured:true,limits,...await listLibrary(store)});}catch(e){return errorResponse(e);}
}

export async function POST(request:Request){
 const denied=await ownerGuard(request,{write:true});if(denied)return denied;
 const store=libraryStore();
 if(!store)return safeJson(503,{error:'Library storage is not configured on this site.'});
 const body=await readJson(request);
 if(!body||typeof body.action!=='string')return safeJson(400,{error:'Invalid request'});
 try{
  switch(body.action){
   case 'begin':return safeJson(201,await beginDoc(store,body));
   case 'append':return safeJson(200,await appendChunks(store,{id:String(body.id),seq:Number(body.seq),chunks:body.chunks as any}));
   case 'finish':return safeJson(200,{ok:true,doc:await finishDoc(store,String(body.id))});
   case 'delete':return safeJson(200,await deleteDoc(store,String(body.id)));
   case 'training':return safeJson(200,{ok:true,doc:await setTraining(store,String(body.id),body.approved as boolean)});
   default:return safeJson(400,{error:'Unknown action'});
  }
 }catch(e){return errorResponse(e);}
}
