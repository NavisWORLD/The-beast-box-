// Owner-side store for the NUMBERS-ONLY bio packet, so the real-IBM run can be started from the box even when the phone cannot dispatch.
// Server only. The caller (route) has already checked the owner session. Raw video/audio never reach here: the packet schema forbids them.
// Blobs: owner/bio-packets/<sha12>.json and owner/bio-packets/latest.json (private container, never public).
import {checkPacket} from './dispatch.mjs';
export const PACKET_PREFIX='owner/bio-packets/';
export const PACKET_MAX_AGE_S=6*3600;
const envelope=(packet,nowMs)=>JSON.stringify({schema:'beastbox-bio-packet-envelope-v1',saved_at_ms:nowMs,saved_at:new Date(nowMs).toISOString(),packet});
/** Validate (strict schema + hash recompute) then store. `store` = {put(name,text)}. */
export async function savePacket(store,packet,nowMs){
  const c=await checkPacket(packet);
  if(!c.ok)return {status:c.status||400,body:{ok:false,error:c.error}};
  const text=envelope(packet,nowMs);
  await store.put(PACKET_PREFIX+c.sha12+'.json',text);
  await store.put(PACKET_PREFIX+'latest.json',text);
  return {status:200,body:{ok:true,saved:true,sha12:c.sha12,packet_sha256:packet.packet_sha256,where:'owner-private storage',raw_media_stored:false}};
}
/** Numbers-only status of the latest saved packet; never returns the raw envelope. */
export async function latestStatus(store,nowMs){
  const raw=await store.get(PACKET_PREFIX+'latest.json');
  if(!raw)return {status:200,body:{ok:true,found:false}};
  let env;try{env=JSON.parse(raw);}catch{return {status:200,body:{ok:true,found:false,error:'unreadable'}};}
  const c=await checkPacket(env?.packet);
  if(!c.ok)return {status:200,body:{ok:true,found:true,valid:false}};
  const age=Math.max(0,Math.round((nowMs-Number(env.saved_at_ms||0))/1000));
  return {status:200,body:{ok:true,found:true,valid:true,sha12:c.sha12,age_s:age,recent:age<=PACKET_MAX_AGE_S,bpm:env.packet.pulse.bpm,sqi:env.packet.pulse.sqi,heartbeat:'MEASURED'}};
}
