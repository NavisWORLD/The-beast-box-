import {storageConfig} from '@/lib/cosmos/azure-blob.mjs';
import {readBeast} from '@/lib/cosmos/cosmos-store.mjs';
import {entryHash} from '@/lib/zeref/zeref-diary.mjs';

export const runtime='nodejs';
export const dynamic='force-dynamic';

/** One beast's cosmos folder (beasts/<id>/latest.json), read-only. Entry hashes are re-checked. */
export async function GET(_req:Request,{params}:{params:Promise<{id:string}>}){
 const {id}=await params;
 const headers={'Cache-Control':'public, s-maxage=60, stale-while-revalidate=300'};
 const cfg=storageConfig();
 if(!cfg)return Response.json({ok:true,configured:false,id},{headers});
 try{
  const r=await readBeast(cfg,id);
  if(!r.ok)return Response.json(r,{status:r.status||400});
  const recent=r.diary?.recent||[];
  const verified=recent.every((e:any)=>typeof e?.hash==='string'&&entryHash(e)===e.hash);
  return Response.json({...r,configured:true,verified},{headers});
 }catch(e:any){
  return Response.json({ok:false,configured:true,id,error:'Storage error: '+String(e?.message||'unknown').replace(/https?:\/\/\S+/g,'[url]').slice(0,120)},{status:502});
 }
}
