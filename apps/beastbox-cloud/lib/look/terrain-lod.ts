// Chunked rings over a caller-supplied height function. The function is only read.
import {seededNoise} from './seed.ts';
import {budgetFor} from './tiers.ts';

export type Ring={r0:number;r1:number;a:number;rad:number};
const PLANS:Record<string,Ring[]>={
 LOW:[
  {r0:.5,r1:16,a:96,rad:24},
  {r0:16,r1:48,a:112,rad:28},
  {r0:48,r1:180,a:128,rad:40},
  {r0:180,r1:420,a:96,rad:18}, /* Cory Nov 12: LOW gets real 3D far hills too (coarse, ~3.5k tris), not water or a flat card at the horizon */
 ],
 MED:[
  {r0:.4,r1:12,a:128,rad:28},
  {r0:12,r1:36,a:144,rad:28},
  {r0:36,r1:90,a:160,rad:32},
  {r0:90,r1:240,a:180,rad:40},
  {r0:240,r1:480,a:128,rad:20}, /* Cory Nov 12: 3D far hills out to the haze on phones */
 ],
 HIGH:[
  {r0:.4,r1:10,a:160,rad:32},
  {r0:10,r1:28,a:176,rad:28},
  {r0:28,r1:70,a:192,rad:32},
  {r0:70,r1:160,a:200,rad:36},
  {r0:160,r1:420,a:220,rad:56},
 ],
 GOD:[
  {r0:.35,r1:8,a:192,rad:40},
  {r0:8,r1:22,a:192,rad:28},
  {r0:22,r1:56,a:200,rad:28},
  {r0:56,r1:120,a:208,rad:32},
  {r0:120,r1:260,a:220,rad:36},
  {r0:260,r1:560,a:240,rad:48},
 ],
};

export function ringPlan(tier:string):Ring[]{return PLANS[tier]||PLANS.MED;}
export function plannedTris(rings:Ring[]){return rings.reduce((s,r)=>s+r.a*r.rad*2,0);}

export function centralNormal(heightAt:(x:number,z:number)=>number,x:number,z:number,e=.45){
 const hx=heightAt(x-e,z)-heightAt(x+e,z);
 const hz=heightAt(x,z-e)-heightAt(x,z+e);
 const ny=e*2;
 const len=Math.hypot(hx,ny,hz)||1;
 return [hx/len,ny/len,hz/len] as [number,number,number];
}

/** Average the central difference at two steps so a coarse ring does not facet. */
export function smoothNormal(heightAt:(x:number,z:number)=>number,x:number,z:number,e=Math.max(.35,Math.hypot(x,z)*.02)){
 const a=centralNormal(heightAt,x,z,e);
 const b=centralNormal(heightAt,x,z,e*2.5);
 const s=[a[0]+b[0],a[1]+b[1],a[2]+b[2]];
 const len=Math.hypot(s[0],s[1],s[2])||1;
 return [s[0]/len,s[1]/len,s[2]/len] as [number,number,number];
}

export function terrainTrisBudget(tier:string){return budgetFor(tier).tris;}

export function buildTerrainLod(THREE:typeof import('three'),o:{
 heightAt:(x:number,z:number)=>number;
 tier?:string;
 seed?:string;
 waterLevel?:number;
}){
 const tier=o.tier||'MED';
 const rings=ringPlan(tier);
 const cap=terrainTrisBudget(tier);
 if(plannedTris(rings)>cap)throw new Error('terrain rings exceed the '+tier+' triangle budget');
 const heightAt=o.heightAt;
 const pos:number[]=[];const nrm:number[]=[];const ao:number[]=[];const noise:number[]=[];const idx:number[]=[];
 const skirt=.35;
 const push=(x:number,y:number,z:number,nx:number,ny:number,nz:number)=>{
  pos.push(x,y,z);nrm.push(nx,ny,nz);
  const h=y;
  let occ=0;const step=1.6;
  for(const [dx,dz] of [[step,0],[-step,0],[0,step],[0,-step]] as const){
   const nh=heightAt(x+dx,z+dz);
   if(nh>h+.02)occ+=Math.min(1,(nh-h)/.8);
  }
  ao.push(1-Math.min(.65,occ*.22));
  noise.push(seededNoise(o.seed||'genesis',x,z));
  return (pos.length/3)-1;
 };
 for(const ring of rings){
  const base=pos.length/3;
  const cols=ring.a,rows=ring.rad;
  for(let j=0;j<=rows;j++){
   const r=ring.r0+(ring.r1-ring.r0)*(j/rows);
   for(let i=0;i<=cols;i++){
    const a=i/cols*Math.PI*2;
    const x=Math.cos(a)*r,z=Math.sin(a)*r;
    const y=heightAt(x,z);
    const n=smoothNormal(heightAt,x,z);
    push(x,y,z,n[0],n[1],n[2]);
   }
  }
  const row=cols+1;
  for(let j=0;j<rows;j++)for(let i=0;i<cols;i++){
   const a=base+j*row+i,b=a+row;
   idx.push(a,a+1,b,a+1,b+1,b);
  }
  // Skirt on the outer edge so a coarser neighbour does not crack open.
  const edge=base+rows*row;
  const sBase=pos.length/3;
  for(let i=0;i<=cols;i++){
   const v=edge+i;
   const x=pos[v*3],y=pos[v*3+1],z=pos[v*3+2];
   push(x,y-skirt,z,nrm[v*3],nrm[v*3+1],nrm[v*3+2]);
  }
  for(let i=0;i<cols;i++){
   const a=edge+i,b=sBase+i;
   idx.push(a,b,a+1,a+1,b,b+1);
  }
 }
 const geo=new THREE.BufferGeometry();
 geo.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));
 geo.setAttribute('normal',new THREE.Float32BufferAttribute(nrm,3));
 geo.setAttribute('ao',new THREE.Float32BufferAttribute(ao,1));
 geo.setAttribute('noise',new THREE.Float32BufferAttribute(noise,1));
 geo.setIndex(idx);
 geo.computeBoundingSphere();
 const tris=idx.length/3;
 return {geometry:geo,tris,rings:rings.length,tier};
}
