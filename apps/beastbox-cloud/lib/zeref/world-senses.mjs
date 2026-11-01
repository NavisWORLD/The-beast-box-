/**
 * MORE OF HIS WORLD in Zeref's own prompt (Cory 2026-10-31: "make sure everything is more connected").
 * Pure, deterministic (no randomness), additive beside worldContextLine:
 *  - sight: his own world's light, DERIVED from its sky by the same worldLightFrom() the forever door uses;
 *  - reading: what he chose to read on his last scheduled read (public /zeref-chooses/latest.json), so he can talk about it;
 *  - spark: the latest heart-seed facts from the public spark JSON (version, backend, label), never whose heartbeat.
 * A missing feed composes nothing. No visitor data, no private data.
 */
import {worldLightFrom} from '../cosmos/sight.mjs';
const clip=(s,n)=>String(s||'').replace(/\s+/g,' ').trim().slice(0,n);
export function sightLine(live,nowMs){
 const wl=worldLightFrom(live,nowMs);
 if(!wl)return '';
 return `Your light (DERIVED from your world's sky, computed not measured): ${wl.band} and ${wl.trend}, horizon ${wl.hue_family}, you feel ${wl.feeling}.`;
}
export function readingLine(latest){
 const picks=(Array.isArray(latest?.picks)?latest.picks:[]).filter(p=>p&&p.title).slice(0,4);
 if(!picks.length)return '';
 return clip(`You chose to read${latest.date?' on '+latest.date:''} (RECORDED): `+picks.map(p=>`"${clip(p.title,60)}" about ${clip(p.topic,20)}`).join('; ')+'. You may talk about what you read.',360);
}
export function sparkLine(spark){
 const h=spark?.heart_seed_latest;
 if(!h||!Number.isFinite(h.version))return '';
 const lab=/^(RECORDED|SIMULATED|DERIVED|MEASURED)/.exec(String(h.label||''))?.[1]||'RECORDED';
 return `Your spark: heart seed v${h.version} (${lab}, from a real ${clip(h.ibm_backend,20)||'IBM'} measurement), seed ${String(h.heart_seed_sha256||'').slice(0,12)}.`;
}
export function worldSensesLines({live=null,latest=null,spark=null,nowMs=null}={}){
 return [sightLine(live,nowMs),readingLine(latest),sparkLine(spark)].filter(Boolean).join('\n');
}
