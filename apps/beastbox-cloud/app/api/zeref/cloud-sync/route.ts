// Persist who Zeref is and grows into (profile, live model pin, approved training
// cycles) to his per-beast Azure folder. Owner session only (scheduled sync runs in GitHub Actions).
import {isOwner,safeJson} from '@/lib/security';
import {storageConfig} from '@/lib/cosmos/azure-blob.mjs';
import {syncZerefCloud,ZEREF_DIR} from '@/lib/cosmos/zeref-cloud.mjs';
import PIN from '@/lib/rawrphos-public-pin.json';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export async function POST(request:Request){
 if(!await isOwner())return safeJson(401,{error:'Owner session required'});
 void request;
 const cfg=storageConfig();if(!cfg)return safeJson(503,{error:'Azure storage not configured'});
 let releases:any[]=[];
 try{const r=await fetch('https://api.github.com/repos/NavisWORLD/The-beast-box-/releases?per_page=100',{headers:{Accept:'application/vnd.github+json'},signal:AbortSignal.timeout(8000)});if(r.ok)releases=await r.json();}catch{/* keep going */}
 try{return safeJson(200,{ok:true,folder:ZEREF_DIR,...await syncZerefCloud(cfg,{pin:PIN,releases})});}
 catch(e:any){return safeJson(502,{ok:false,error:'Storage error: '+String(e?.message||'unknown').replace(/https?:\/\/\S+/g,'[url]').slice(0,120)});}
}
