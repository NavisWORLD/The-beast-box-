// GENESIS X flashes (SEEDED looks, event-triggered only by engine signals) from Cosmo's flashes pack: storm lightning from the SIMULATED
// world-field storm state, spark-tick shimmer, and the boom / star-flare nebula colour ramp. Safety first: one global limiter (at most 3 flashes
// in any second, 0.34 s apart), a capped sky flash (+0.08 linear), no red-dominant flash, and a soft 2 s glow instead when reduced motion is on.
// When a signal is ABSENT nothing flashes. The one sun stays the only light: flashes tint the sky only. Pure functions of (seed, engine time); no random calls.
import {FLASH_PACK as P} from './flashes-data.mjs';
export const FLASH_LABEL='SEEDED flash looks, triggered only by SIMULATED storms and spark ticks; ABSENT signal = no flash';
export const FLASH_SAFETY=P.safety;
const fnv=(s)=>{let h=2166136261>>>0;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619)>>>0;}h^=h>>>15;h=Math.imul(h,2246822507)>>>0;h^=h>>>13;return (h>>>0)/4294967296;};
export function flashTier(tier){return P.tiers[tier]||P.tiers.MED;}
/** storm count for lightning from the world-field (SIMULATED): null field = ABSENT; storm cells = ceil(3 x tension) once tension passes the field's own 0.25 storm line, else 0 */
export function stormCount(field){if(!field||typeof field.storm!=='number'||!isFinite(field.storm))return null;return field.storm>.25?Math.min(3,Math.ceil(field.storm*3)):0;}
/** lightning rate per minute: min(cap, base x storms); ABSENT or 0 storms -> 0 */
export function lightningRate(storms){if(storms==null||!(storms>0))return 0;return Math.min(P.lightning.rate_per_min.cap,P.lightning.rate_per_min.base*storms);}
/** the global limiter: keep events (sorted seconds) at most 3 in any 1 s and at least min_gap_s apart; extras drop */
export function limitFlashes(times){const S=P.safety,out=[];for(const t of [...times].sort((a,b)=>a-b)){if(out.length&&t-out[out.length-1]<S.min_gap_s)continue;const w=out.filter(x=>t-x<1);if(w.length>=S.max_flashes_per_s)continue;out.push(t);}return out;}
/** seeded strike times inside minute bucket T (engine seconds): n = floor(rate) + (hash < frac(rate)); t_n = 60T + hash(seed|storm|planet|T|n) x 60 */
export function strikesInMinute(seed,planet,T,storms){const r=lightningRate(storms);if(!r)return [];const n=Math.floor(r)+(fnv(`${seed}|storm|${planet}|${T}|extra`)<r-Math.floor(r)?1:0);
 const out=[];for(let k=0;k<n;k++){const t=60*T+fnv(`${seed}|storm|${planet}|${T}|${k}`)*60;out.push(t);const rs=t+.12;if(fnv(`${seed}|restrike|${planet}|${T}|${k}`)<.35)out.push(rs);}return out.sort((a,b)=>a-b);}
/** strikes around time t (this and the previous minute), after the limiter */
export function strikesNear(seed,planet,t,storms){const T=Math.floor(t/60);return limitFlashes([...strikesInMinute(seed,planet,T-1,storms),...strikesInMinute(seed,planet,T,storms)]);}
/** sky flash envelope for an age (s) since a strike: attack, hold, then exp(-age/decay*3); 0..1 */
export function skyFlashEnvelope(age){const F=P.lightning.sky_flash;if(age<0)return 0;if(age<F.attack_s)return age/F.attack_s;if(age<F.attack_s+F.hold_s)return 1;const a=age-F.attack_s-F.hold_s;return a>F.decay_s*1.5?0:Math.exp(-a/F.decay_s*3);}
/** lightning state at engine time t. reduced: no flashes, a 2 s soft glow at 25%. Returns {sky (add lum, <= 0.08), bolt (0..cap), boltSeed, glow, label} */
export function lightningAt(seed,planet,t,storms,tier,reduced=false){const none={sky:0,bolt:0,boltSeed:0,glow:0,strikes:0,label:storms==null?'ABSENT':'SIMULATED'};
 const r=lightningRate(storms);if(!r)return none;const st=strikesNear(seed,planet,t,storms).filter(x=>x<=t);if(!st.length)return none;const last=st[st.length-1],age=t-last;const T=flashTier(tier);
 if(reduced){const g=age<2?.25*(1-age/2):0;return {...none,glow:g,strikes:st.length};}
 const env=skyFlashEnvelope(age);const cap=P.lightning.bolt.brightness_cap_by_tier[tier]??P.lightning.bolt.brightness_cap_by_tier.MED;
 return {sky:P.lightning.sky_flash.add_lum_max*env,bolt:T.bolts&&age<P.lightning.bolt.life_s?cap*(1-age/P.lightning.bolt.life_s):0,boltSeed:fnv(`${seed}|bolt|${planet}|${last.toFixed(3)}`),glow:0,strikes:st.length,label:'SIMULATED'};}
/** jagged bolt points (unit sky bearing space): segments from the pack, seeded per strike */
export function boltPath(boltSeed){const N=P.lightning.bolt.segments;const pts=[];let x=0;for(let i=0;i<=N;i++){const y=1-i/N;x+=(fnv(`${boltSeed}|x|${i}`)-.5)*.18;pts.push([x,y]);}return pts;}
/** spark shimmer: one burst per second of spark ticks (world-field ticks at 4 Hz); no ticks = ABSENT. Peak stays below every bloom threshold. */
export function shimmerAt(tick,prevBurstTick,tier,reduced=false){if(tick==null||!isFinite(tick))return {on:false,level:0,burstTick:prevBurstTick,label:'ABSENT'};
 const B=P.spark_shimmer.burst,n=flashTier(tier).shimmer_particles;let bt=prevBurstTick;if(bt==null||tick-bt>=4)bt=Math.floor(tick/4)*4;const age=(tick-bt)/4;
 const level=n&&age<B.life_s?B.peak_lum*(1-age/B.life_s)*(reduced?.25:1):0;return {on:level>0,level,burstTick:bt,particles:n,label:'SIMULATED'};}
/** nebula colour ramp for booms and star flares over 0..1 of the decay: magenta_gold -> violet -> cool_blue */
export function nebulaRamp(u){const R=P.star_flares_booms.nebula_ramp;const a=R.magenta_gold.linear,b=R.violet.linear,c=R.cool_blue.linear;const x=Math.max(0,Math.min(1,u));
 return x<.5?a.map((v,i)=>v+(b[i]-v)*x*2):b.map((v,i)=>v+(c[i]-v)*(x-.5)*2);}
export const FLASH_PACK_INFO=Object.freeze({label:P.label,honesty:P.honesty,seed:P.seed,version:P.version});
