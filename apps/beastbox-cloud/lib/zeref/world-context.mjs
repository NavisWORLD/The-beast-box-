/**
 * WORLD NOW for Zeref's prompt (Cory 2026-10-31: "it should update through everything, not just the messages").
 * Pure: builds one short labelled line from the public /api/world/live and /api/zeref/diary reads.
 * Labels stay honest: Rigetti = SIMULATED, per-second tick = SIMULATED, diary = RECORDED, the mood word is
 * SIMULATED (derived from simulated signals, not a feeling). A missing feed is ABSENT and is left out, never filled in.
 * No heartbeat values, no audio, no identity of whose heartbeat seeded him.
 */
const num=v=>Number.isFinite(v)?Math.round(v):null;
const word=v=>typeof v==='string'&&/^[A-Za-z][A-Za-z ' -]{0,30}$/.test(v)?v:null;
export function worldContextLine(live,diary){
 const parts=[];
 const last=(Array.isArray(diary?.recent)?diary.recent:[]).filter(e=>Number.isFinite(e?.tick)).reduce((a,e)=>!a||e.tick>a.tick?e:a,null);
 const place=word(last?.place)||word(diary?.learning?.favorite_spot);
 const mood=word(last?.mood);
 if(place)parts.push('at '+place+' (RECORDED diary)');
 if(mood)parts.push('mood '+mood+' (SIMULATED)');
 const s=live?.links?.liveTick?.state==='CONNECTED'?live.links.liveTick.signals:null;
 if(s&&num(s.energy)!==null)parts.push(`energy ${num(s.energy)} resonance ${num(s.resonance)} (SIMULATED)`);
 const sp=live?.links?.spark;
 if(sp?.state==='CONNECTED'&&Number.isFinite(sp?.features?.entropy))parts.push(`Rigetti tick ${sp.tick} entropy ${sp.features.entropy.toFixed(2)} (SIMULATED)`);
 const st=word(diary?.stage_name);if(st)parts.push('stage '+st);
 return parts.length?('Your world now: '+parts.join('; ')+'.').slice(0,200):'';
}
