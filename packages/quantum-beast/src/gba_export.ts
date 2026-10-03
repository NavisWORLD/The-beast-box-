import {profileSpriteTiles,profilePaletteBytes,creatureProfileBytes,stateBytes} from './canonical/gba-companion';
import {canonical,verifySnapshot,type Snapshot,type VerifyOptions,requireCondition} from './verifier';
function crc32(raw:Uint8Array){let c=0xffffffff;for(const b of raw){c^=b;for(let i=0;i<8;i++)c=(c>>>1)^((c&1)?0xedb88320:0);}return (c^0xffffffff)>>>0;}
/** Store-only ZIP with a fixed file allowlist. No input paths or extract operation. */
function zip(files:Record<string,Uint8Array>){
 const local:Uint8Array[]=[],central:Uint8Array[]=[];let offset=0;
 for(const [name,bytes] of Object.entries(files).sort(([a],[b])=>a.localeCompare(b))){
  requireCondition(/^[a-zA-Z0-9_./-]+$/.test(name)&&!name.includes('..')&&!name.startsWith('/'),'Unsafe output path');
  const path=new TextEncoder().encode(name),checksum=crc32(bytes),header=new Uint8Array(30+path.length),v=new DataView(header.buffer);
  v.setUint32(0,0x04034b50,true);v.setUint16(4,20,true);v.setUint16(6,0x800,true);v.setUint32(14,checksum,true);v.setUint32(18,bytes.length,true);v.setUint32(22,bytes.length,true);v.setUint16(26,path.length,true);header.set(path,30);
  local.push(header,bytes);const c=new Uint8Array(46+path.length),d=new DataView(c.buffer);d.setUint32(0,0x02014b50,true);d.setUint16(4,20,true);d.setUint16(6,20,true);d.setUint16(8,0x800,true);d.setUint32(16,checksum,true);d.setUint32(20,bytes.length,true);d.setUint32(24,bytes.length,true);d.setUint16(28,path.length,true);d.setUint32(42,offset,true);c.set(path,46);central.push(c);offset+=header.length+bytes.length;
 }
 const size=central.reduce((n,a)=>n+a.length,0),end=new Uint8Array(22),d=new DataView(end.buffer);d.setUint32(0,0x06054b50,true);d.setUint16(8,central.length,true);d.setUint16(10,central.length,true);d.setUint32(12,size,true);d.setUint32(16,offset,true);
 const parts=[...local,...central,end],output=new Uint8Array(parts.reduce((n,a)=>n+a.length,0));let at=0;for(const p of parts){output.set(p,at);at+=p.length;}return output;
}
async function rawSha(raw:Uint8Array){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',Uint8Array.from(raw))),b=>b.toString(16).padStart(2,'0')).join('');}
export async function exportGba(snapshot:Snapshot,options:VerifyOptions={}){
 const verification=await verifySnapshot(snapshot,options),p=snapshot.profile,enc=new TextEncoder();
 const files:Record<string,Uint8Array>={
  'gba/companion_tiles.4bpp':profileSpriteTiles(p),'gba/companion_palette.bgr555':profilePaletteBytes(p),
  // Distributable ROMs never carry a live/private sensory projection.
  'gba/companion_state.bin':stateBytes(p.baseLook,null),'gba/companion_profile.bin':creatureProfileBytes(p),
  'companion.profile.json':enc.encode(canonical(p)+'\n'),
  'quantum-beast.receipt.json':enc.encode(canonical({schema:'qbeast-gba-export-v1',creature_id:p.id,snapshot_sha256:snapshot.digest,lineage_head:snapshot.lineage_head,signature_status:verification.signature,BCG1:'unmeasured-public-art',BCP1:'canonical-seeded-game-stats',memory_included:false,authority:false})+'\n')
 };
 const checksums:Record<string,string>={};for(const [name,raw] of Object.entries(files))checksums[name]=await rawSha(raw);
 files['checksums.json']=enc.encode(canonical(checksums)+'\n');const archive=zip(files);
 return {zip:archive,files,sha256:await rawSha(archive),creature_id:p.id};
}
