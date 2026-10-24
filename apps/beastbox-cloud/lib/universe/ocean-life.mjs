// Ocean life for the pocket world (Oct 24 2026). Pure + deterministic: every school, ray, whale and plankton point is drawn from
// lwStream(seed+':ocean'), where seed is the universe seed derived from the recorded ibm_marrakesh counts. No unseeded randomness.
// Species, sizes, depth bands, speeds and school sizes are Cosmo's ocean-life pack v1 (ocean-species.mjs); where and how many still come from the seed.
// Honest label: the recording has no ocean-life dataset (genesis tick 0 has 0 life), so all of this is SEEDED, not recorded.
import {lwStream,unitFrom} from './living-world.mjs';
import {OCEAN_SPECIES} from './ocean-species.mjs';
export const OCEAN_LABEL='Ocean life: SEEDED from the recorded IBM genesis seed (recording has no ocean-life data)';
const norm=(v)=>{const l=Math.hypot(v[0],v[1],v[2])||1;return [v[0]/l,v[1]/l,v[2]/l];};
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
/** tangent basis at unit normal n */
export function tangentBasis(n){const up=Math.abs(n[1])>.95?[1,0,0]:[0,1,0];const e1=norm(cross(up,n));const e2=cross(n,e1);return [e1,e2];}
/** Offset a unit point along its tangent plane by an angular (a) amount toward angle ang, then re-normalise. */
function around(n,e1,e2,ang,r){const c=Math.cos(ang)*r,s=Math.sin(ang)*r;return norm([n[0]+e1[0]*c+e2[0]*s,n[1]+e1[1]*c+e2[1]*s,n[2]+e1[2]*c+e2[2]*s]);}
/**
 * Place schools (fish), rays, whales and plankton in water. isWater(unit[x,y,z]) must be the world field's water test.
 * Each anchor is accepted only if the anchor and four points on its ring are water, so a school never leaves the sea.
 * @param {string|number} seed universe seed @param {(n:number[])=>boolean} isWater
 * @param {{schools?:number,rays?:number,whales?:number,plankton?:number,life?:number}} [o] life (0..1+) scales counts by the planet's recorded life, 1 = default
 */
export const KIND_SPECIES=Object.freeze({fish:['fish_a','fish_b','fish_c'],ray:['manta'],whale:['whale'],jelly:['jelly'],turtle:['turtle'],seabird:['seabird']});
/** Angular radius (rad on the unit sphere) a school may roam. Cosmo's school radii (1.6 m to 40 m) are for a 600 m patch; this planet is ~170 m round, so they are capped. */
const ROAM={fish:[.03,.012],ray:[.07,.02],whale:[.12,.03],jelly:[.04,.01],turtle:[.05,.01],seabird:[.05,.015]};
const frac=(x)=>x-Math.floor(x);
export function oceanLife(seed,isWater,o={}){
 const k=Math.max(.25,Math.min(2,o.life??1));const R=o.R??8,mpu=o.mpu??.5/1.7;// world units per metre
 const idOf=(n)=>{const w=isWater(n);return w===true?'deep_ocean':(w||null);};
 const out={label:OCEAN_LABEL,schools:[],plankton:[]};let id=0;
 const ok=(n,rad)=>{if(!idOf(n))return false;const [e1,e2]=tangentBasis(n);for(let a=0;a<4;a++)if(!idOf(around(n,e1,e2,a*Math.PI/2,rad)))return false;return true;};
 const cands=(kind,bid)=>KIND_SPECIES[kind].filter(sp=>OCEAN_SPECIES[sp].water_biomes.includes(bid));
 const make=(r,kind,want)=>{
  for(let s=0;s<want;s++){
   const rad=ROAM[kind][0]+r()*ROAM[kind][1];
   let pick=null,cs=[];for(let t=0;t<260&&!pick;t++){const n=unitFrom(r);if(!ok(n,rad))continue;const c=cands(kind,idOf(n));if(c.length){pick=n;cs=c;}}
   const draw=[r(),r(),r(),r()];// always consume the same number of draws so one miss never shifts later schools
   if(!pick)continue;
   const species=cs[Math.floor(frac(draw[3]*7919.13)*cs.length)],sp=OCEAN_SPECIES[species];
   const [n0,n1]=sp.school_n;const rEff=Math.max(.5,rad*R/mpu);// metres actually available to roam
   const [d0,d1]=sp.depth_m;
   out.schools.push({id:kind+'-'+(id++),kind,species,biome:idOf(pick),n:pick,radius:rad,
    count:n0+Math.floor(draw[0]*(n1-n0+1)),
    speed:(sp.cruise_mps/rEff)*(.8+draw[1]*.4)*(draw[2]<.5?-1:1),
    phase:draw[3]*Math.PI*2,hue:+(r()).toFixed(3),size:sp.size_m,depth:+(d0+frac(draw[1]*104729)*(d1-d0)).toFixed(2)});
  }};
 const base=lwStream(seed+':ocean');
 // the three original streams keep their order (fish, ray, whale) so positions stay the ones #538 produced
 make(base,'fish',Math.round((o.schools??14)*k));make(base,'ray',Math.round((o.rays??5)*k));make(base,'whale',Math.max(1,Math.round((o.whales??3)*k)));
 // new species get their own streams so they never shift the original ones
 make(lwStream(seed+':ocean:jelly'),'jelly',Math.round(4*k));make(lwStream(seed+':ocean:turtle'),'turtle',Math.round(3*k));make(lwStream(seed+':ocean:seabird'),'seabird',Math.round(3*k));
 const np=o.plankton??320;for(let i=0;i<np;i++){const rr=lwStream(seed+':plankton:'+(i>>5));let n=null;for(let t=0;t<(i&31)+1;t++)n=unitFrom(rr);if(n&&idOf(n))out.plankton.push({n,p:+(rr()*6.283).toFixed(3)});}
 return out;}
/** Unit position of member i of a school at time t (s). Fish circle and weave, rays glide wide, whales cruise slowly. */
export function memberAt(s,i,t){const [e1,e2]=tangentBasis(s.n);const f=((i*.6180339887)%1);const r=s.radius*(s.kind==='fish'?.3+.7*f:.5+.5*f);
 const ang=s.phase+i*2.399963+t*s.speed*(.75+.5*f);const wob=1+.18*Math.sin(t*1.3+i*1.7);return around(s.n,e1,e2,ang,r*wob);}
/** Heading (unit tangent) of member i at time t, from a small finite difference. */
export function headingAt(s,i,t){const a=memberAt(s,i,t),b=memberAt(s,i,t+.2);const d=[b[0]-a[0],b[1]-a[1],b[2]-a[2]];const dp=d[0]*a[0]+d[1]*a[1]+d[2]*a[2];return norm([d[0]-a[0]*dp,d[1]-a[1]*dp,d[2]-a[2]*dp]);}
/** Whale surfacing 0..1 (spout peaks near 1): slow seeded cycle per whale. */
export function surfacing(s,t){const c=Math.sin(t*.35+s.phase);return Math.max(0,(c-.55)/.45);}
/** Plankton glow 0..1: only in the dark (night 0..1), a gentle twinkle per point. */
export function planktonGlow(p,t,night){return Math.max(0,Math.min(1,night))*(.55+.45*Math.sin(t*1.7+p));}
