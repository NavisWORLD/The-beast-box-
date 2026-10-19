import {NextResponse} from 'next/server';
import {parseLCE1,SRAM_SIZE} from '@/lib/companion/lc-ecosystem.mjs';
export const dynamic='force-dynamic';
/* V12.2b game -> site: POST the 32 KiB Lost COSMOS .sav (application/octet-stream).
   Returns the cartridge's LCE1 experience summary. Stateless: nothing is stored here yet;
   the caller (the beast's ecosystem page) decides what to keep. */
export async function POST(req:Request){
 const len=Number(req.headers.get('content-length')||0);if(len>SRAM_SIZE)return NextResponse.json({error:'save too large'},{status:413});
 const buf=new Uint8Array(await req.arrayBuffer());if(buf.length!==SRAM_SIZE)return NextResponse.json({error:'expected a 32768-byte Lost COSMOS save'},{status:400});
 const lce=parseLCE1(buf);if(!lce)return NextResponse.json({error:'no LCE1 experience record (play the V12.2 first-person view first)'},{status:422});
 return NextResponse.json(lce,{headers:{'Cache-Control':'no-store'}});
}
