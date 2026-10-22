/**
 * Lost COSMOS V12.2b ecosystem bridge. Byte-compatible with the game repo's
 * tools/lc_ecosystem.py and LOST_COSMOS_V10_SOURCE/ecosystem_bridge.h.
 *
 * LCQ1 (site -> game, SRAM 25540, 60 bytes): the beast's latest Rigetti growth
 * state. The Rigetti loop is a QVM run, so it is SIMULATED, and the record
 * always carries the SIMULATED flag (the cartridge rejects it otherwise).
 * LCE1 (game -> site, SRAM 24704, 128 bytes): the cartridge's experience
 * summary (channels, mood, needs, quests, mood history).
 */
export const LCQ_OFFSET = 25540, LCQ_BYTES = 60, LCE_OFFSET = 24704, LCE_BYTES = 128, SRAM_SIZE = 32768;
export const CHANNELS = ['frequency_mass','geometric_phase','spectral_flatness','phase_velocity','entanglement','valence','arousal','dominance','audio_psi','phi_harmonics','av_coherence','quantum_entropy'];
const MOODS = ['JOY','CURIOUS','FEAR','CALM','MISCHIEF'];
export function fnvBytes(b){let h=2166136261;for(const x of b)h=Math.imul(h^x,16777619)>>>0;return h>>>0;}
export function rigettiOffsets(counts){
  const n=counts.reduce((a,b)=>a+b,0)||1,p=counts.map(c=>c/n),pairs=[[0,1],[0,2],[0,3],[1,2],[1,3],[2,3]];
  return Array.from({length:12},(_,k)=>{const [a,b]=pairs[k%6];const d=k<6?p[a]-p[b]:p[a]+p[b]-0.5;
    // Python round() is banker's rounding; match it for byte equality.
    const v=d*64,f=Math.floor(v),r=v-f===0.5?(f%2===0?f:f+1):Math.round(v);return Math.max(-32,Math.min(32,r));});
}
export function buildLCQ1(publicId,counts,cycle=0){
  if(!publicId)throw Error('public id is zero');if(counts.length!==4)throw Error('counts');
  const b=new Uint8Array(LCQ_BYTES),v=new DataView(b.buffer);b.set([76,67,81,49],0);b[4]=1;b[5]=1;// SIMULATED
  v.setUint32(8,publicId>>>0,true);rigettiOffsets(counts).forEach((o,i)=>v.setInt8(12+i,o));
  v.setUint32(24,cycle>>>0,true);counts.forEach((c,i)=>v.setUint16(28+2*i,Math.min(65535,c|0),true));
  v.setUint32(56,fnvBytes(b.subarray(0,56)),true);return b;
}
export function attachLCQ1(sav,rec){if(sav.length!==SRAM_SIZE||rec.length!==LCQ_BYTES)throw Error('size');const o=new Uint8Array(sav);o.set(rec,LCQ_OFFSET);return o;}
export function parseLCE1(sav){
  if(!sav||sav.length<LCE_OFFSET+LCE_BYTES)return null;const r=sav.subarray(LCE_OFFSET,LCE_OFFSET+LCE_BYTES),v=new DataView(r.buffer,r.byteOffset,LCE_BYTES);
  if(r[0]!==76||r[1]!==67||r[2]!==69||r[3]!==49||r[4]!==1)return null;if(v.getUint32(124,true)!==fnvBytes(r.subarray(0,124)))return null;
  const head=r[35],ring=[...r.subarray(36,68)],hist=[...ring.slice(head),...ring.slice(0,head)].filter(m=>m>=1&&m<=5).map(m=>MOODS[m-1]);
  const q=x=>Math.round(x/255*1000)/1000;
  return {format:'LCE1',lcq_applied:!!(r[5]&1),heartbeats:v.getUint16(6,true),identity:v.getUint32(8,true).toString(16).padStart(8,'0'),
    channels:Object.fromEntries(CHANNELS.map((c,i)=>[c,q(r[12+i])])),
    mood:Object.fromEntries(['coherence','joy','curiosity','fear','calm','mischief'].map((k,i)=>[k,q(r[24+i])])),
    needs:{trust:r[30],energy:r[31],curiosity:r[32],avoid:r[33]},quests_touched:r[34],mood_history:hist,cst_steps:v.getUint32(68,true),
    label:'Classical CST-12 simulation on the cartridge; any Rigetti input was SIMULATED (QVM).'};
}

/* ---------- V12.3: finish the bridge ----------
 * Site -> game: pick the beast's latest growth tick whose source is the Rigetti QVM SIMULATOR
 * (growth_source.kind 'rigetti-qvm-simulated', simulated:true) and fold its 3-bit counts to the
 * four 2-bit counts LCQ1 carries (marginal over the first two measured bits: '00x','01x','10x','11x').
 * Deterministic-fallback ticks are never used: no simulated counts, no LCQ1. */
export function countsTo2Bit(counts){
 if(!counts||typeof counts!=='object')return null;const out=[0,0,0,0];let n=0;
 for(const [k,v] of Object.entries(counts)){if(!/^[01]{2,3}$/.test(k)||!Number.isInteger(v)||v<0)return null;out[parseInt(k.slice(0,2),2)]+=v;n+=v;}
 return n>0?out:null;
}
export function latestSimulatedGrowth(recent){
 const list=Array.isArray(recent)?[...recent]:[];
 list.sort((a,b)=>(Number(b?.tick)||0)-(Number(a?.tick)||0));
 for(const e of list){const g=e?.growth_source;if(!g||g.kind!=='rigetti-qvm-simulated'||g.simulated!==true)continue;
  const c=countsTo2Bit(g.counts);if(c)return {counts:c,cycle:Number(e.tick)>>>0,job_id:g.job_id?String(g.job_id):null,simulated:true};}
 return null;
}
/** Returns {save, lcq1} where save has LCQ1 attached (or is unchanged and lcq1 is null). */
export function injectLatestGrowth(sav,publicId,recent){
 const g=latestSimulatedGrowth(recent);if(!g||!publicId||!sav||sav.length!==SRAM_SIZE)return {save:sav,lcq1:null};
 const rec=buildLCQ1(publicId>>>0,g.counts,g.cycle);
 return {save:attachLCQ1(sav,rec),lcq1:{cycle:g.cycle,job_id:g.job_id,counts:g.counts,simulated:true,label:'Rigetti QVM growth (SIMULATED)'}};
}
/* Game -> site: one ecosystem entry from a parsed LCE1 record. The beast id is 'bb-' + identity. */
export function ecosystemEntryFromLCE1(lce,{now=new Date().toISOString()}={}){
 if(!lce||lce.format!=='LCE1')throw Error('not an LCE1 record');
 return {schema:'lost-cosmos-game-experience/v1',beast_id:'bb-'+lce.identity,received_at:now,
  heartbeats:lce.heartbeats,cst_steps:lce.cst_steps,lcq_applied:lce.lcq_applied,quests_touched:lce.quests_touched,
  channels:lce.channels,mood:lce.mood,needs:lce.needs,mood_history:lce.mood_history,label:lce.label};
}
