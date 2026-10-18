/** Dimensional sensors of life: pure math (seeded nerve trees, growth levels, signal pulses). */
import {seededRng,GOLDEN_ANGLE,PHI} from '../physics/cst-integrator.mjs';
export const SENSOR_LIMITS=Object.freeze({nodesLow:60,nodesHigh:140,maxLevel:4,nerveSegsMax:420,pulsesMax:12});
export const CST_SEED='cst-root';
/** Shared CST seed with per-entity variation. */
export const entityRng=id=>seededRng(CST_SEED+':'+id);
export const growthLevel=xp=>Math.min(SENSOR_LIMITS.maxLevel,2+Math.floor(Math.log2(1+Math.max(0,xp)/5)));
/** Nervous system in body-local space: spine through the heart seed, fractal filaments to `limbs`. */
export function nerveTree(id,{heart,head,tail,limbs},level=1){
  const r=entityRng(id),segs=[];const push=(a,b,w,d)=>{if(segs.length<SENSOR_LIMITS.nerveSegsMax)segs.push({a,b,w,d});};
  const lerp=(a,b,t)=>({x:a.x+(b.x-a.x)*t,y:a.y+(b.y-a.y)*t,z:a.z+(b.z-a.z)*t});
  const jit=(p,s)=>({x:p.x+(r()-.5)*s,y:p.y+(r()-.5)*s,z:p.z+(r()-.5)*s});
  const spineN=6;const spine=[];for(let i=0;i<=spineN;i++)spine.push(lerp(tail,head,i/spineN));
  for(let i=0;i<spineN;i++)push(spine[i],spine[i+1],1,0);
  const L=Math.hypot(head.x-tail.x,head.y-tail.y,head.z-tail.z)||1;
  const branch=(a,b,w,d)=>{if(d>level+1)return;const n=2+(d<2?1:0);let prev=a;
    for(let k=1;k<=n;k++){const p=k===n?b:jit(lerp(a,b,k/n),L*.06/(d+1));push(prev,p,w,d);
      if(d<level)for(let q=0;q<(d<2?2:1);q++){if(r()>.85)continue;const az=(k+q*2)*GOLDEN_ANGLE+r(),len=Math.hypot(b.x-a.x,b.y-a.y,b.z-a.z)/PHI/(n)*(1.2+r()*.6);
        branch(p,{x:p.x+Math.cos(az)*len,y:p.y+(r()-.45)*len,z:p.z+Math.sin(az)*len*.5},w*.6,d+1);}
      prev=p;}};
  // ribs: paired side nerves off every interior spine vertebra (the reference's dense torso web)
  for(let i=1;i<spineN;i++)for(const sd of [-1,1]){const s0=spine[i];branch(s0,{x:s0.x+sd*L*(.18+r()*.12),y:s0.y+(r()-.6)*L*.12,z:s0.z+(r()-.5)*L*.05},.5,2);}
  for(const lm of limbs){let best=spine[0],bd=1e9;for(const s of spine){const d=Math.hypot(s.x-lm.x,s.y-lm.y,s.z-lm.z);if(d<bd){bd=d;best=s;}}branch(best,lm,.7,1);}
  return {segs,heart,tips:segs.filter(s=>s.d>=level).map(s=>s.b)};
}
/** Pulse position along a straight path a→b (0..1); null when done. */
export const pulseAt=(p,t)=>t<0||t>1?null:{x:p.a.x+(p.b.x-p.a.x)*t,y:p.a.y+(p.b.y-p.a.y)*t+Math.sin(Math.PI*t)*.4,z:p.a.z+(p.b.z-p.a.z)*t};
export function nearestNodes(nodes,p,k=3){return nodes.map((n,i)=>({i,d:Math.hypot(n.x-p.x,n.y-p.y,n.z-p.z)})).sort((a,b)=>a.d-b.d).slice(0,k).map(o=>o.i);}
export const SENSOR_KEY='beastbox-sensors-v1';
export function loadXP(st){try{const o=JSON.parse(st?.getItem(SENSOR_KEY)||'{}');return o&&typeof o==='object'?o:{};}catch{return {};}}
export function saveXP(st,m){const o={};for(const [k,v] of Object.entries(m))if(typeof v==='number'&&isFinite(v)&&v>=0)o[k]=Math.min(1e6,v);try{st?.setItem(SENSOR_KEY,JSON.stringify(o));}catch{}return o;}
