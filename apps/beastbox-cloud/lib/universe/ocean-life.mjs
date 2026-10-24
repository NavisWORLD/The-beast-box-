// Ocean life for the pocket world (Oct 24 2026). Pure + deterministic: every school, ray, whale and plankton point is drawn from
// lwStream(seed+':ocean'), where seed is the universe seed derived from the recorded ibm_marrakesh counts. No unseeded randomness.
// Honest label: the recording has no ocean-life dataset (genesis tick 0 has 0 life), so all of this is SEEDED, not recorded.
import {lwStream,unitFrom} from './living-world.mjs';
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
export function oceanLife(seed,isWater,o={}){
 const r=lwStream(seed+':ocean');const k=Math.max(.25,Math.min(2,o.life??1));
 const want={fish:Math.round((o.schools??14)*k),ray:Math.round((o.rays??5)*k),whale:Math.max(1,Math.round((o.whales??3)*k))};
 const out={label:OCEAN_LABEL,schools:[],plankton:[]};let id=0;
 const ok=(n,rad)=>{if(!isWater(n))return false;const [e1,e2]=tangentBasis(n);for(let a=0;a<4;a++)if(!isWater(around(n,e1,e2,a*Math.PI/2,rad)))return false;return true;};
 for(const kind of ['fish','ray','whale']){
  for(let s=0;s<want[kind];s++){
   const rad=kind==='fish'?.012+r()*.01:kind==='ray'?.02+r()*.01:.03+r()*.02;
   let pick=null;for(let t=0;t<260&&!pick;t++){const n=unitFrom(r);if(ok(n,rad))pick=n;}
   const draw=[r(),r(),r(),r()];// always consume the same number of draws so one miss never shifts later schools
   if(!pick)continue;
   out.schools.push({id:kind+'-'+(id++),kind,n:pick,radius:rad,
    count:kind==='fish'?10+Math.floor(draw[0]*14):kind==='ray'?1+Math.floor(draw[0]*3):1,
    speed:(kind==='fish'?.5+draw[1]*.5:kind==='ray'?.16+draw[1]*.12:.07+draw[1]*.05)*(draw[2]<.5?-1:1),
    phase:draw[3]*Math.PI*2,hue:+(r()).toFixed(3),size:kind==='fish'?.05+r()*.04:kind==='ray'?.5+r()*.4:2.2+r()*1.6});
  }}
 const np=o.plankton??320;for(let i=0;i<np;i++){const rr=lwStream(seed+':plankton:'+(i>>5));let n=null;for(let t=0;t<(i&31)+1;t++)n=unitFrom(rr);if(n&&isWater(n))out.plankton.push({n,p:+(rr()*6.283).toFixed(3)});}
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
