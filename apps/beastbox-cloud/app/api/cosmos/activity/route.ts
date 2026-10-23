import {storageConfig,getBlob} from '@/lib/cosmos/azure-blob.mjs';
import {listRegistered} from '@/lib/cosmos/cosmos-store.mjs';

export const runtime='nodejs';
export const dynamic='force-dynamic';
const CAP=64;
const ZEREF_SOURCE='https://raw.githubusercontent.com/NavisWORLD/The-beast-box-/zeref-diary/zeref/latest.json';
const pick=(d:any,id:string,source:string)=>({id,name:typeof d?.identity?.name==='string'?d.identity.name.slice(0,40):(typeof d?.name==='string'?d.name.slice(0,40):null),
 tick:Number.isFinite(d?.tick)?d.tick:null,last_tick_at:typeof d?.last_tick_at==='string'?d.last_tick_at:null,source});

/**
 * Public, read-only loop activity for the 3D universe's "One Mind, Refracted" threads.
 * Each registered creature: tick + last_tick_at from its own Azure loop summary (beasts/<id>/latest.json).
 * Zeref: the diary loop (GitHub Actions) summary. Nothing is estimated; a missing summary is reported as null.
 */
export async function GET(){
 const headers={'Cache-Control':'public, s-maxage=120, stale-while-revalidate=600'};
 const creatures:any[]=[];let configured=false,error:string|null=null;
 try{const r=await fetch(ZEREF_SOURCE,{next:{revalidate:120},signal:AbortSignal.timeout(6000)});if(r.ok)creatures.push(pick(await r.json(),'zeref','zeref-diary loop (GitHub Actions)'));}catch{/* reported as absent */}
 const cfg=storageConfig();
 if(cfg){configured=true;try{const ids=(await listRegistered(cfg)).slice(0,CAP);
  const rows=await Promise.all(ids.map(async(id:string)=>{try{const b=await getBlob(cfg,`beasts/${id}/latest.json`);return pick(b?JSON.parse(b.text):null,id,'Azure loop');}catch{return pick(null,id,'Azure loop');}}));
  creatures.push(...rows);}catch(e:any){error='Storage error: '+String(e?.message||'unknown').replace(/https?:\/\/\S+/g,'[url]').slice(0,120);}}
 return Response.json({ok:true,configured,error,label:'Thread brightness = how recently each creature’s own loop ticked (real timestamps).',creatures},{headers});
}
