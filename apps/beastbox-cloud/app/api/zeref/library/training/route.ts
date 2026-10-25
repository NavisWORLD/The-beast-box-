// Opt-in training queue view: titles, counts and hashes only (never text). Owner session only.
import {safeJson} from '@/lib/security';
import {ownerGuard,libraryStore,errorResponse} from '@/lib/library/server';
import {trainingManifest} from '@/lib/library/store.mjs';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export async function GET(request:Request){
 const denied=await ownerGuard(request);if(denied)return denied;
 const store=libraryStore();
 if(!store)return safeJson(503,{error:'Library storage is not configured on this site.'});
 try{return safeJson(200,await trainingManifest(store));}catch(e){return errorResponse(e);}
}
