// Muse's opening presence mark. Owner session only. A human (or Phera teaching for him)
// marks "I'm with Zeref" for 20 minutes; while marked, Meta Muse does not teach.
import {isOwner,safeJson} from '@/lib/security';
import {museStore} from '@/lib/muse/server';
import {markPresence,presence} from '@/lib/muse/opening.mjs';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export async function GET(){
 const store=museStore();
 if(!store)return safeJson(503,{error:'storage_not_configured'});
 return safeJson(200,await presence(store));
}
export async function POST(request:Request){
 if(!await isOwner())return safeJson(403,{error:'Owner session required'});
 if(request.headers.get('origin')!==new URL(request.url).origin)return safeJson(403,{error:'Same-origin request required'});
 const store=museStore();
 if(!store)return safeJson(503,{error:'storage_not_configured'});
 let who='human';
 try{const b=JSON.parse((await request.text()).slice(0,200)||'{}');if(b&&b.who==='phera')who='phera';}catch{}
 return safeJson(200,{ok:true,...await markPresence(store,who)});
}
