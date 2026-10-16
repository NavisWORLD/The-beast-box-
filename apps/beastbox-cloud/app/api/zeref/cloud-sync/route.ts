// Persist who Zeref is and grows into (profile, live model pin, approved training
// cycles) to his per-beast Azure folder. Owner session or Bearer ZEREF_DISTILL_EXPORT_TOKEN.
import {createHash,timingSafeEqual} from 'node:crypto';
import {isOwner,safeJson} from '@/lib/security';
import {storageConfig} from '@/lib/cosmos/azure-blob.mjs';
import {syncZerefCloud,ZEREF_DIR} from '@/lib/cosmos/zeref-cloud.mjs';
import PIN from '@/lib/rawrphos-public-pin.json';
export const runtime='nodejs';
export const dynamic='force-dynamic';
function tokenOk(req:Request){const want=process.env.ZEREF_DISTILL_EXPORT_TOKEN||'';const got=(req.headers.get('authorization')||'').replace(/^Bearer\s+/i,'');
 const h=(s:string)=>Buffer.from(createHash('sha256').update(s).digest('hex'));return want.length>=32&&timingSafeEqual(h(want),h(got));}
export async function POST(request:Request){
 if(!tokenOk(request)&&!await isOwner())return safeJson(401,{error:'Owner or sync token required'});
 const cfg=storageConfig();if(!cfg)return safeJson(503,{error:'Azure storage not configured'});
 let releases:any[]=[];
 try{const r=await fetch('https://api.github.com/repos/NavisWORLD/The-beast-box-/releases?per_page=100',{headers:{Accept:'application/vnd.github+json'},signal:AbortSignal.timeout(8000)});if(r.ok)releases=await r.json();}catch{/* keep going */}
 try{return safeJson(200,{ok:true,folder:ZEREF_DIR,...await syncZerefCloud(cfg,{pin:PIN,releases})});}
 catch(e:any){return safeJson(502,{ok:false,error:'Storage error: '+String(e?.message||'unknown').replace(/https?:\/\/\S+/g,'[url]').slice(0,120)});}
}
