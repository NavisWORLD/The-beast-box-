import {NextResponse} from 'next/server';
import {parseLCE1,ecosystemEntryFromLCE1,SRAM_SIZE} from '@/lib/companion/lc-ecosystem.mjs';
import {storageConfig} from '@/lib/cosmos/azure-blob.mjs';
import {recordGameExperience} from '@/lib/cosmos/cosmos-store.mjs';
export const runtime='nodejs';
export const dynamic='force-dynamic';
/* game -> site: POST the 32 KiB Lost COSMOS .sav (application/octet-stream).
   Returns the cartridge's LCE1 experience summary and (V12.3) persists it into the beast's
   ecosystem folder (beasts/<id>/game-experience.jsonl + game-latest.json) when cosmos storage is
   configured and the beast is registered. `persisted` reports what happened; parsing never depends on it. */
export async function POST(req:Request){
 const len=Number(req.headers.get('content-length')||0);if(len>SRAM_SIZE)return NextResponse.json({error:'save too large'},{status:413});
 const buf=new Uint8Array(await req.arrayBuffer());if(buf.length!==SRAM_SIZE)return NextResponse.json({error:'expected a 32768-byte Lost COSMOS save'},{status:400});
 const lce=parseLCE1(buf);if(!lce)return NextResponse.json({error:'no LCE1 experience record (play the V12.2 first-person view first)'},{status:422});
 let ecosystem:any={persisted:false,reason:'cosmos storage not configured'};
 const cfg=storageConfig();
 if(cfg){try{ecosystem=await recordGameExperience(cfg,ecosystemEntryFromLCE1(lce));}
  catch(e:any){ecosystem={persisted:false,error:'Storage error: '+String(e?.message||'unknown').replace(/https?:\/\/\S+/g,'[url]').slice(0,120)};}}
 return NextResponse.json({...lce,ecosystem},{headers:{'Cache-Control':'no-store'}});
}
