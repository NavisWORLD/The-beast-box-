import {NextResponse} from 'next/server';
import {createHash} from 'node:crypto';
export const dynamic='force-dynamic';
const RELEASE='https://navisworld.github.io/Cosmic-synapse-the-living-universe-sim-engine-/arcade/lost-cosmos/rom/lost-cosmos.gba';
const SHA='0f5c91554d03aa0facfb41b6af472e948f62fa2c0cad53e33019fe9eb8f661e7';
// V12.1 stays accepted only so the site does not error if a Pages cache still serves it.
const ACCEPTED=new Set([SHA,'42cf6a470990cffaabcc3d205b2ac502e4c0c5610fcaeeb5b1b044efaf531b6b']);
export async function GET(){
 try{
  const upstream=await fetch(RELEASE+'?v='+SHA,{cache:'no-store',signal:AbortSignal.timeout(20000)});
  if(!upstream.ok||!upstream.body)throw Error('Cartridge unavailable');
  const chunks:Uint8Array[]=[];let total=0;const reader=upstream.body.getReader();
  while(true){const next=await reader.read();if(next.done)break;total+=next.value.byteLength;if(total>17_000_000){await reader.cancel();throw Error('Cartridge size limit');}chunks.push(next.value);}
  const body=new Uint8Array(total);let offset=0;for(const chunk of chunks){body.set(chunk,offset);offset+=chunk.byteLength;}
  if(total!==16777216||body[0xb2]!==0x96||!ACCEPTED.has(createHash('sha256').update(body).digest('hex')))throw Error('Cartridge hash mismatch');
  return new Response(body,{headers:{'Content-Type':'application/octet-stream','Content-Length':String(total),'Cache-Control':'public, max-age=300','X-Lost-Cosmos-SHA256':createHash('sha256').update(body).digest('hex'),'X-Content-Type-Options':'nosniff'}});
 }catch{return NextResponse.json({error:'The verified current LOST COSMOS cartridge is not available. Reload after the release completes.'},{status:502});}
}
