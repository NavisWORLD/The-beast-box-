// Seeded storms for the Tiny Universe (Oct 24 2026). The recorded genesis has 0 storms (tick 0); storms only appear as the SIMULATED
// growth ticks. These cyclones are drawn from lwStream(seed+':storms:'+planet.id), seed = recorded IBM ibm_marrakesh counts, one or two per
// planet with a real atmosphere (planet.atmosphere from the recorded-seed generator, hotter/brighter star flux => stronger). No Math.random.
// Every entry carries label:'SEEDED' so the UI never presents it as recorded or as part of the Rigetti SIMULATED growth.
import {lwStream} from './living-world.mjs';
export const STORM_LABEL='SEEDED';
export const STORM_MIN_ATMOSPHERE=0.18;
/** @param {{seed:any,planets:any[],storms?:any[]}} u @returns {{id:string,type:'storm',planet:string,intensity:number,lifetime:number,born:number,label:'SEEDED',kind:string,lat:number,lon:number,night:boolean}[]} */
export function seededStorms(u){
 const out=[];const seed=String(u?.seed??'tiny');
 for(const p of u?.planets||[]){
  const a=+p.atmosphere||0;if(a<STORM_MIN_ATMOSPHERE)continue;
  const r=lwStream(seed+':storms:'+p.id);
  const n=1+(r()<0.35+a*0.4?1:0);const flux=Math.max(0.05,Math.min(4,+p.flux||1));const heat=Math.min(1.5,0.5+0.5*Math.log10(1+flux*3));
  for(let i=0;i<n;i++){
   const d=[r(),r(),r(),r(),r()];// fixed draw count so a skipped storm never shifts the next
   const kind=d[0]<0.5?'cyclone':d[0]<0.8?'cloud band':'squall line';
   out.push({id:'seeded-storm-'+p.id+'-'+i,type:'storm',planet:p.id,intensity:+Math.min(0.6,0.12+a*0.35*heat*(0.6+d[1]*0.8)).toFixed(4),lifetime:9999,born:0,label:STORM_LABEL,kind,lat:+((d[2]*2-1)*70).toFixed(1),lon:+((d[3]*2-1)*180).toFixed(1),night:d[4]<0.5});
  }
 }
 return out;
}
/** Recorded/simulated storms first, then the seeded ones, at most one entry per planet for the sprite layer. */
export function allStorms(u){const live=u?.storms||[];const have=new Set(live.map(s=>s.planet));return [...live,...seededStorms(u).filter(s=>!have.has(s.planet))];}
