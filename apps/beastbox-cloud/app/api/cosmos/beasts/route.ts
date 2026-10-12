import {storageConfig} from '@/lib/cosmos/azure-blob.mjs';
import {registerBeast} from '@/lib/cosmos/cosmos-store.mjs';

export const runtime='nodejs';
export const dynamic='force-dynamic';

/**
 * "Grow in the cosmos" opt-in. POST {profile} with a PUBLIC profile only
 * (id, name, seed provenance, visual traits, stats; see public/spark/cosmos-profile.mjs).
 * The server re-validates and rebuilds it from allowlisted fields, so chat,
 * owner memory or other save data are dropped even if sent. Create-only:
 * an existing beast's folder is never overwritten. Rate-limited per address.
 * GET returns whether storage is configured.
 */
const WINDOW=10*60*1000,PER_IP=5,PER_INSTANCE=60;
const hits=new Map<string,number[]>();let global:number[]=[];
function limited(ip:string){
 const now=Date.now();
 global=global.filter(t=>now-t<WINDOW);
 const mine=(hits.get(ip)||[]).filter(t=>now-t<WINDOW);
 if(mine.length>=PER_IP||global.length>=PER_INSTANCE)return true;
 mine.push(now);hits.set(ip,mine);global.push(now);
 if(hits.size>5000)hits.clear();
 return false;
}
const json=(body:unknown,status=200)=>Response.json(body,{status,headers:{'Cache-Control':'no-store'}});

export async function GET(){
 return json({configured:!!storageConfig(),label:'Opt-in, public profile only. Growth runs on a free Rigetti simulator (simulated). Learned behaviour, not consciousness.'});
}

export async function POST(req:Request){
 const cfg=storageConfig();
 if(!cfg)return json({ok:false,configured:false,error:'Cosmos storage is not configured yet.'},503);
 const origin=req.headers.get('origin'),host=req.headers.get('host');
 if(origin){try{if(new URL(origin).host!==host)return json({ok:false,error:'Cross-site registration is not allowed.'},403);}catch{return json({ok:false,error:'Bad origin.'},403);}}
 const ip=(req.headers.get('x-forwarded-for')||'').split(',')[0].trim()||req.headers.get('x-real-ip')||'unknown';
 if(limited(ip))return json({ok:false,error:'Too many requests. Try again in a few minutes.'},429);
 const text=await req.text();
 if(text.length>6000)return json({ok:false,error:'Request too large.'},413);
 let body:any;try{body=JSON.parse(text);}catch{return json({ok:false,error:'Expected JSON.'},400);}
 try{
  const r=await registerBeast(cfg,body?.profile);
  return json({...r,configured:true},r.status);
 }catch(e:any){
  return json({ok:false,configured:true,error:'Storage error: '+String(e?.message||'unknown').replace(/https?:\/\/\S+/g,'[url]').slice(0,120)},502);
 }
}
