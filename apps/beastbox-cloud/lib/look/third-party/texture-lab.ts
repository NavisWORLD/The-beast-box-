/*
 * THIRD-PARTY (MIT) — technique and code ported from pallet-town-3d by Paulius,
 * src/core/Noise.ts (Simplex, tileableFbm) and src/core/TextureLab.ts (bakeNormalMap).
 * Copyright (c) 2026 Paulius. Licensed under the MIT License; see apps/beastbox-cloud/THIRD_PARTY_NOTICES.md.
 * Changes for The Beast Box: the permutation shuffle is seeded from our sha256 stream (stream01),
 * never an unseeded RNG; returns raw RGBA bytes (a THREE.DataTexture is made by the caller); no
 * creature, character or model content is ported, only the texture technique.
 *
 * Tileable fbm samples noise on a torus embedded in 4D so a baked tile wraps with no seam, and the
 * normal map comes from that height field through a wrap-around Sobel filter, so the detail never
 * shows a tile grid. Labelled: designed surface detail, not measured terrain.
 */
import {stream01} from '../seed.ts';

export const TEXTURE_LAB_LABEL='Ground detail · third-party technique (pallet-town-3d, MIT) · SEEDED';

const G3=[1,1,0,-1,1,0,1,-1,0,-1,-1,0,1,0,1,-1,0,1,1,0,-1,-1,0,-1,0,1,1,0,-1,1,0,1,-1,0,-1,-1];
const F3=1/3,K3=1/6;

export class SeededSimplex{
 private perm=new Uint8Array(512);private pm12=new Uint8Array(512);
 constructor(seed:string){
  const p=new Uint8Array(256);for(let i=0;i<256;i++)p[i]=i;
  for(let i=255;i>0;i--){const j=Math.floor(stream01(seed+':perm:'+i)*(i+1));const t=p[i];p[i]=p[j];p[j]=t;}
  for(let i=0;i<512;i++){this.perm[i]=p[i&255];this.pm12[i]=this.perm[i]%12;}
 }
 noise3D(x:number,y:number,z:number){
  const {perm,pm12}=this;const s=(x+y+z)*F3;const i=Math.floor(x+s),j=Math.floor(y+s),k=Math.floor(z+s);const t=(i+j+k)*K3;
  const x0=x-(i-t),y0=y-(j-t),z0=z-(k-t);let i1,j1,k1,i2,j2,k2;
  if(x0>=y0){if(y0>=z0){i1=1;j1=0;k1=0;i2=1;j2=1;k2=0;}else if(x0>=z0){i1=1;j1=0;k1=0;i2=1;j2=0;k2=1;}else{i1=0;j1=0;k1=1;i2=1;j2=0;k2=1;}}
  else{if(y0<z0){i1=0;j1=0;k1=1;i2=0;j2=1;k2=1;}else if(x0<z0){i1=0;j1=1;k1=0;i2=0;j2=1;k2=1;}else{i1=0;j1=1;k1=0;i2=1;j2=1;k2=0;}}
  const c=[[x0,y0,z0,0,0,0],[x0-i1+K3,y0-j1+K3,z0-k1+K3,i1,j1,k1],[x0-i2+2*K3,y0-j2+2*K3,z0-k2+2*K3,i2,j2,k2],[x0-1+3*K3,y0-1+3*K3,z0-1+3*K3,1,1,1]];
  const ii=i&255,jj=j&255,kk=k&255;let n=0;
  for(const [a,b,d,oi,oj,ok] of c){let q=.6-a*a-b*b-d*d;if(q<0)continue;const g=pm12[ii+oi+perm[jj+oj+perm[kk+ok]]]*3;q*=q;n+=q*q*(G3[g]*a+G3[g+1]*b+G3[g+2]*d);}
  return 32*n;
 }
}

/** Tileable fbm over [0,1)^2 (torus in 4D, two 3D lookups per octave), band-limited to the bake size. */
export function tileableFbm(s:SeededSimplex,u:number,v:number,frequency:number,octaves=5,gain=.5,bakeSize=0){
 let amp=1,freq=frequency,sum=0,norm=0;const nyq=bakeSize>0?bakeSize*.5:Infinity;
 for(let o=0;o<octaves;o++){if(o>0&&freq>nyq)break;const a=u*Math.PI*2,b=v*Math.PI*2,r=freq/(Math.PI*2);
  const nx=Math.cos(a)*r,ny=Math.sin(a)*r,nz=Math.cos(b)*r,nw=Math.sin(b)*r;
  sum+=amp*.5*(s.noise3D(nx,ny,nz)+s.noise3D(ny,nz,nw));norm+=amp;amp*=gain;freq*=2;}
 return sum/norm;
}

/** Wrap-around Sobel normal bake of a tileable height field. Returns RGBA bytes (size*size*4). */
export function bakeNormalBytes(size:number,height:(u:number,v:number)=>number,strength=1.6){
 const h=new Float32Array(size*size);for(let y=0;y<size;y++)for(let x=0;x<size;x++)h[y*size+x]=height(x/size,y/size);
 const at=(x:number,y:number)=>h[(((y%size)+size)%size)*size+(((x%size)+size)%size)];const out=new Uint8Array(size*size*4);
 for(let y=0;y<size;y++)for(let x=0;x<size;x++){
  const dx=at(x-1,y-1)+2*at(x-1,y)+at(x-1,y+1)-(at(x+1,y-1)+2*at(x+1,y)+at(x+1,y+1));
  const dy=at(x-1,y-1)+2*at(x,y-1)+at(x+1,y-1)-(at(x-1,y+1)+2*at(x,y+1)+at(x+1,y+1));
  let nx=dx*strength,ny=dy*strength;const len=Math.hypot(nx,ny,1)||1;const i=(y*size+x)*4;
  out[i]=(nx/len*.5+.5)*255;out[i+1]=(ny/len*.5+.5)*255;out[i+2]=(1/len*.5+.5)*255;out[i+3]=255;}
 return out;
}

/** Rolling ground relief tile: broad swells plus fine grain, seeded per world. Tier sets the bake size (LOW: none). */
export function groundDetailSize(tier:string){return tier==='LOW'?0:tier==='GOD'?256:128;}
export function bakeGroundDetail(seed:string,size:number){
 const s=new SeededSimplex(seed+':ground-detail');
 return bakeNormalBytes(size,(u,v)=>.5+.5*(tileableFbm(s,u,v,4,5,.5,size)*.7+tileableFbm(s,u,v,24,3,.5,size)*.3),2.2);
}
