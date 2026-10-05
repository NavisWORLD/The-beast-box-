import {NextResponse} from 'next/server';
import {createHash} from 'node:crypto';
export const dynamic='force-dynamic';
const RELEASE='https://navisworld.github.io/Cosmic-synapse-the-living-universe-sim-engine-/arcade/lost-cosmos/rom/lost-cosmos.gba';
const SHA='6f9c22fa22b32694d606c854b4da26b4394b2ecaa86842cc1998c8cfe57b1fb3';
export async function GET(){
 try{
  const upstream=await fetch(RELEASE+'?v='+SHA,{cache:'no-store',signal:AbortSignal.timeout(20000)});
  if(!upstream.ok||!upstream.body)throw Error('Cartridge unavailable');
  const chunks:Uint8Array[]=[];let total=0;const reader=upstream.body.getReader();
  while(true){const next=await reader.read();if(next.done)break;total+=next.value.byteLength;if(total>1_500_000){await reader.cancel();throw Error('Cartridge size limit');}chunks.push(next.value);}
  const body=new Uint8Array(total);let offset=0;for(const chunk of chunks){body.set(chunk,offset);offset+=chunk.byteLength;}
  if(total!==1048576||body[0xb2]!==0x96||createHash('sha256').update(body).digest('hex')!==SHA)throw Error('Cartridge hash mismatch');
  return new Response(body,{headers:{'Content-Type':'application/octet-stream','Content-Length':String(total),'Cache-Control':'public, max-age=300','X-Lost-Cosmos-SHA256':SHA,'X-Content-Type-Options':'nosniff'}});
 }catch{return NextResponse.json({error:'The verified current LOST COSMOS cartridge is not available. Reload after the release completes.'},{status:502});}
}
