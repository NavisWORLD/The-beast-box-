/**
 * Universe of worlds: pure, deterministic math (no three, no DOM).
 * - cstTree(): branching from Cory's CST constants: golden-angle phyllotaxis, 1/φ length ratio,
 *   Lorenz-perturbed bend so each tree is unique but stable for the same seed.
 * - WORLDS / worldAnchor(): distant planets + floating islands, each with its own gravity well.
 * - wellPull(): softened inverse-square well (mass/(d²+ε)).
 * - tunnelPath(): home → world arc bent by every well on the way (gravity tunneling), sampled once.
 * - travelPose(): eased pose along a path, out → stay → back.
 */
import {PHI,GOLDEN_ANGLE,seededRng,lorenzStep} from '../physics/cst-integrator.mjs';

export const LIMITS=Object.freeze({treeDepthLow:4,treeDepthHigh:5,homeTreesLow:6,homeTreesHigh:9,cloudsLow:10,cloudsHigh:20,puffs:5,maxSegments:900});

/** Segments {a:[x,y,z],b:[x,y,z],r,d} for one tree, trunk at origin, height ~ scale. */
export function cstTree(seed,{depth=5,scale=4}={}){
  const r=seededRng('tree:'+seed),L={x:.1+r(),y:r(),z:20+r()};const segs=[];
  const grow=(a,dir,len,rad,d,k)=>{
    lorenzStep(L,.004);const bx=L.x*.012,bz=L.y*.012;
    let dx=dir[0]+bx,dy=dir[1],dz=dir[2]+bz;const n=Math.hypot(dx,dy,dz)||1;dx/=n;dy/=n;dz/=n;
    const b=[a[0]+dx*len,a[1]+dy*len,a[2]+dz*len];segs.push({a,b,r:rad,d});
    if(d>=depth||segs.length>=LIMITS.maxSegments)return;
    const kids=d<2?3:2;
    for(let i=0;i<kids;i++){
      const az=(k+i+1)*GOLDEN_ANGLE,tilt=.42+.18*r();
      // child direction: parent tilted by `tilt` around golden-angle azimuth, biased upward
      const ux=Math.cos(az)*Math.sin(tilt),uz=Math.sin(az)*Math.sin(tilt),uy=Math.cos(tilt);
      const cd=[dx*.55+ux,dy*.55+uy,dz*.55+uz];
      grow(b,cd,len/PHI*(.92+.16*r()),rad*.62,d+1,k*kids+i+1);}
  };
  grow([0,0,0],[0,1,0],scale*.36,scale*.055,1,0);
  return segs;
}
/** Branch tips (for canopy puffs). */
export const treeTips=segs=>{const D=Math.max(...segs.map(s=>s.d));return segs.filter(s=>s.d===D).map(s=>s.b);};

export const WORLDS=Object.freeze([
  {id:'amethyst',kind:'planet',angle:.35,dist:52,y:11,radius:4.2,mass:9,color:0x6a3fb8,atmo:0xc79cff,moon:true},
  {id:'tidal',kind:'island',angle:1.55,dist:44,y:8,radius:3.2,mass:6,color:0x1f6f8b,atmo:0x7fe6ff,moon:false},
  {id:'ember',kind:'planet',angle:2.75,dist:66,y:15,radius:5.0,mass:12,color:0x8a2f52,atmo:0xff9ab8,moon:true},
  {id:'verdant',kind:'island',angle:3.95,dist:48,y:9,radius:3.6,mass:7,color:0x2f7a5a,atmo:0x9cffc9,moon:false},
  {id:'aurora',kind:'planet',angle:5.15,dist:72,y:18,radius:3.4,mass:8,color:0x2b3a8f,atmo:0x9fb6ff,moon:true},
]);
/** Gentle orbit of a world around its anchor (deterministic in t). */
export function worldAnchor(w,t=0){
  const a=w.angle+Math.sin(t*.011+w.mass)*.04;
  return {x:Math.cos(a)*w.dist,y:w.y+Math.sin(t*.23+w.angle*2)*.6,z:Math.sin(a)*w.dist};
}
/** Kepler-ish moon period from the world's mass: T ∝ sqrt(r³/M). */
export const moonPeriod=(w,orbitR=w.radius*1.9)=>2*Math.PI*Math.sqrt(orbitR**3/w.mass);
export function wellPull(p,c,mass,eps=4){const dx=c.x-p.x,dy=c.y-p.y,dz=c.z-p.z,d2=dx*dx+dy*dy+dz*dz;
  const d=Math.sqrt(d2)||1,g=mass/(d2+eps);return {x:dx/d*g,y:dy/d*g,z:dz/d*g,g};}
/** Gravity-tunneling path, `n` samples; endpoints exact, interior bent by every well (except the target's own core). */
export function tunnelPath(from,to,wells=[],{n=64,lift=10,bend=26}={}){
  const pts=[];
  for(let i=0;i<=n;i++){const s=i/n,e=Math.sin(Math.PI*s);
    const p={x:from.x+(to.x-from.x)*s,y:from.y+(to.y-from.y)*s+lift*e,z:from.z+(to.z-from.z)*s};
    for(const w of wells){const f=wellPull(p,w,w.mass);p.x+=f.x*bend*e;p.y+=f.y*bend*e;p.z+=f.z*bend*e;}
    pts.push(p);}
  pts[0]={...from};pts[n]={...to};return pts;
}
const ease=s=>s<.5?4*s*s*s:1-Math.pow(-2*s+2,3)/2;
export function samplePath(pts,s){const f=Math.min(1,Math.max(0,s))*(pts.length-1),i=Math.min(pts.length-2,Math.floor(f)),u=f-i,a=pts[i],b=pts[i+1];
  return {x:a.x+(b.x-a.x)*u,y:a.y+(b.y-a.y)*u,z:a.z+(b.z-a.z)*u};}
/** Trip timeline: go (T) → stay (S) → back (T). Returns {phase,pos,done}. */
export function travelPose(trip,t,{T=9,S=7}={}){
  if(t<T)return {phase:'go',pos:samplePath(trip.out,ease(t/T)),done:false};
  if(t<T+S)return {phase:'stay',pos:{...trip.out[trip.out.length-1]},done:false};
  if(t<2*T+S)return {phase:'back',pos:samplePath(trip.out,1-ease((t-T-S)/T)),done:false};
  return {phase:'home',pos:{...trip.out[0]},done:true};
}
