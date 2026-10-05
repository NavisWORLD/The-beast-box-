import {canonical,type Snapshot,verifySnapshot,type VerifyOptions} from './verifier';

export const LOST_COSMOS_SOURCE_SHA='d70a666e93d5fc4d9c8a44bad9d323938bf146ac' as const;
export const LOST_COSMOS_URL='https://navisworld.github.io/Cosmic-synapse-the-living-universe-sim-engine-/arcade/lost-cosmos/synapse.html' as const;

const PRIVATE=/(?:api[_ -]?key|password|credential|authorization|biometric|owner[_ -]?memory|private[_ -]?(?:key|state)|-----BEGIN|\bBearer\s|\bsk-[a-z0-9_-]{8,})/i;

async function sha256Hex(text:string){
 const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text));
 return [...new Uint8Array(digest)].map(b=>b.toString(16).padStart(2,'0')).join('');
}
function callsign(name:string){
 const value=String(name||'').toUpperCase().replace(/[^A-Z0-9 ]/g,'').trim().slice(0,12);
 return value||'BEAST';
}
function publicMemories(snapshot:Snapshot){
 const out:string[]=[];
 for(let i=snapshot.events.length-1;i>=0&&out.length<8;i--){
  const event=snapshot.events[i];
  if(event.kind!=='memory'||!('summary' in event.payload))continue;
  const clean=String(event.payload.summary||'').replace(/[\u0000-\u001f\u007f]/g,' ').replace(/\s+/g,' ').trim().slice(0,48);
  if(clean&&!PRIVATE.test(clean))out.push(clean);
 }
 return out.reverse();
}

export async function lostCosmosShare(snapshot:Snapshot,options:VerifyOptions={}){
 await verifySnapshot(snapshot,options);
 const p=snapshot.profile;
 const transfer=(await sha256Hex(`beastbox-lost-cosmos-transfer-v1\0${p.id}\0${p.seed}`)).slice(0,32);
 const body={
  format:'LCSHARE1' as const,
  version:1 as const,
  origin:'beast' as const,
  focus:50,calm:50,spark:50,
  callsign:callsign(p.name),
  note:'FROM BEAST BOX QBEAST.',
  growth:{epoch:'0',layer:0,points:0,trade:true,grown:false},
  memories:publicMemories(snapshot),
  transfer,
  seed:p.seed,
  family:p.family,
  hue:p.appearance.hueShift,
 };
 const checksum=await sha256Hex(canonical(body));
 return {...body,checksum};
}

export async function lostCosmosShareUrl(snapshot:Snapshot,options:VerifyOptions={}){
 const share=await lostCosmosShare(snapshot,options);
 return `${LOST_COSMOS_URL}#lcshare=${encodeURIComponent(canonical(share))}`;
}
