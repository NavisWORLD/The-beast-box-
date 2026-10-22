// Tiny Universe seed + growth engine (data only, no UI). Schema: tiny-universe/v1.
// Genesis is derived ONLY from recorded IBM hardware counts. Every number comes from
// a hash stream over those counts: nothing hand-picked. Growth ticks use a seeded
// Rigetti-style Bell SIMULATOR and are always labeled SIMULATED.
import {sha256Hex} from './sha256.mjs';
export const SCHEMA='tiny-universe/v1';
const sha=s=>sha256Hex(s);
function stream(seedHex){let ctr=0,buf=[];return()=>{if(!buf.length){const h=sha(seedHex+':'+(ctr++));for(let i=0;i<64;i+=8)buf.push(parseInt(h.slice(i,i+8),16)/2**32);}return buf.shift();};}
export function parseCounts(c){const o={};for(const p of String(c).split(',')){const[k,v]=p.split(':');o[k]=Number(v);}return o;}
// Entanglement correlation E = P(same) - P(diff) for a 2-qubit run.
export function correlation(counts){let s=0,d=0;for(const[k,v]of Object.entries(counts))(k[0]===k[k.length-1]?(s+=v):(d+=v));return (s-d)/(s+d);}
export function seedFromShard(shard){
 if(shard?.source_class!=='RECORDED_IBM_HARDWARE')throw new Error('Genesis requires RECORDED_IBM_HARDWARE counts');
 const runs=shard.runs.map(r=>({key:r.k,backend:r.b,job:r.j,shots:r.s,counts:parseCounts(r.c),E:correlation(parseCounts(r.c))}));
 const canon=runs.map(r=>r.key+'|'+Object.entries(r.counts).sort().map(e=>e.join(':')).join(',')).join(';');
 return {seed:sha(canon),source:{class:'RECORDED_IBM_HARDWARE',backend:shard.source_backend,job_id:shard.source_job_id,counts_digest:shard.source_counts_digest_sha256},runs};
}
const pick=(r,a)=>a[Math.floor(r()*a.length)];
// Body generators: parameters are emergent from the stream, scaled by measured correlation.
function makeStar(r,i,E){const mass=+(0.1+r()*r()*20*E).toFixed(3);return{id:'star-'+i,type:'star',mass_solar:mass,temperature_k:Math.round(2500+mass**0.55*5200*(0.6+r()*0.8)),luminosity:+(mass**3.5).toFixed(4),age:0,hue:+r().toFixed(4),x:+r().toFixed(4),y:+r().toFixed(4)};}
function makePlanet(r,star,j){const orbit=+(0.2+j*0.6*(1+r())).toFixed(3);const flux=star.luminosity/orbit**2;return{id:star.id+'-p'+j,type:'planet',star:star.id,orbit_au:orbit,radius_earth:+(0.3+r()*r()*11).toFixed(3),water:+r().toFixed(4),atmosphere:+r().toFixed(4),flux:+flux.toFixed(4),temperature_k:Math.round(278*flux**0.25),phase:+r().toFixed(4)};}
function habitability(p){const t=p.temperature_k;const tScore=Math.max(0,1-Math.abs(t-288)/120);return +(tScore*p.water*Math.min(1,p.atmosphere*2)).toFixed(4);}
// Additive view fields (Oct 22 2026). None of these draw from the growth stream, so bodies are unchanged.
// complexity_norm = 1 - exp(-complexity / COMPLEXITY_K), K = 2 (raw complexity is unbounded; 4.33 -> 0.885).
export const COMPLEXITY_K=2;
export const LIFE_STAGES=[['Glimmer',0.3],['Drifters',0.6],['Choirs',0.9],['Dreamers',Infinity]];
export function stageOf(norm){return LIFE_STAGES.find(([,hi])=>norm<hi)[0];}
function decorateLife(L){L.complexity_norm=+(1-Math.exp(-L.complexity/COMPLEXITY_K)).toFixed(4);L.stage=stageOf(L.complexity_norm);if(L.scars==null)L.scars=0;L.scarred=L.scars>0;return L;}
// Entangled planet pairs: Fisher-Yates over sorted planet ids, keyed by sha256(seed+':pairs:'+i); consecutive ids pair.
// E on each pair is the measured hardware entanglement_E (one recorded run set, shared by every pair).
export function derivePairs(u){const ids=u.planets.map(p=>p.id).sort();for(let i=ids.length-1;i>0;i--){const j=parseInt(sha(u.seed+':pairs:'+i).slice(0,8),16)%(i+1);[ids[i],ids[j]]=[ids[j],ids[i]];}
 const out=[];for(let i=0;i+1<ids.length;i+=2)out.push({a:ids[i],b:ids[i+1],E:u.entanglement_E});return out;}
export function genesis(shard){
 const g=seedFromShard(shard);const r=stream(g.seed);const E=Math.max(0.05,Math.abs(g.runs.reduce((a,x)=>a+x.E,0)/g.runs.length));
 const stars=Array.from({length:3+Math.floor(r()*6)},(_,i)=>makeStar(r,i,E));
 const planets=stars.flatMap(s=>Array.from({length:Math.floor(r()*6)},(_,j)=>makePlanet(r,s,j)));
 planets.forEach(p=>p.habitability=habitability(p));
 const u={schema:SCHEMA,seed:g.seed,source:g.source,entanglement_E:+E.toFixed(5),tick:0,growth_label:null,stars,planets,storms:[],life:[],history:[]};u.pairs=derivePairs(u);return u;
}
// Rigetti Bell SIMULATOR: shots sampled with fidelity that drifts from the hardware E.
export function simulatedBellCounts(r,E,shots=1024){const pSame=(1+E)/2;const c={'00':0,'01':0,'10':0,'11':0};for(let i=0;i<shots;i++){const same=r()<pSame,b=r()<0.5?'0':'1';c[same?b+b:b+(b==='0'?'1':'0')]++;}return c;}
export function grow(u,steps=1){
 u=structuredClone(u);if(!u.pairs)u.pairs=derivePairs(u);u.life.forEach(decorateLife);
 for(let s=0;s<steps;s++){
  u.tick++;const r=stream(sha(u.seed+':tick:'+u.tick));const counts=simulatedBellCounts(r,u.entanglement_E);const e=correlation(counts);
  const events=[];
  u.stars.forEach(st=>{st.age++;if(st.mass_solar>8&&st.age>40+Math.floor(r()*40)&&!st.remnant){st.remnant=st.mass_solar>15?'black_hole':'neutron_star';st.luminosity=0;events.push({kind:'supernova',star:st.id});}});
  if(r()<(1-e)*0.9){const p=pick(r,u.planets.length?u.planets:[null]);if(p)u.storms.push({id:'storm-'+u.tick,type:'storm',planet:p.id,intensity:+(r()*p.atmosphere).toFixed(4),lifetime:1+Math.floor(r()*12),born:u.tick});}
  u.storms=u.storms.filter(st=>st.born+st.lifetime>=u.tick);
  for(const p of u.planets){const star=u.stars.find(x=>x.id===p.star);if(star.remnant)p.habitability=0;
   const L=u.life.find(l=>l.planet===p.id);
   if(!L&&r()<p.habitability*0.08){u.life.push({id:'life-'+p.id,type:'life',planet:p.id,complexity:0,diversity:1,born:u.tick,traits:{hue:+r().toFixed(4),motility:+r().toFixed(4),sociality:+r().toFixed(4)}});events.push({kind:'abiogenesis',planet:p.id});}
   else if(L){const storm=u.storms.some(st=>st.planet===p.id);L.complexity=+Math.max(0,L.complexity+(p.habitability*r()*e)-(storm?0.05:0)-(p.habitability===0?0.5:0)).toFixed(4);if(storm)L.scars=(L.scars||0)+1;L.diversity=Math.max(0,L.diversity+(r()<p.habitability*0.3?1:0)-(r()<0.05?1:0));}}
  u.life=u.life.filter(l=>l.diversity>0);u.life.forEach(decorateLife);
  u.growth_label='SIMULATED (Rigetti Bell simulator, not hardware)';
  u.history.push({tick:u.tick,source:'SIMULATED',sim_E:+e.toFixed(5),counts,events});if(u.history.length>64)u.history.shift();
 }
 return u;
}
