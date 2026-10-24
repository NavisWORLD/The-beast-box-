// One surface for the Cage and the living world: Cosmo's ground cover + trees planted from the seed (seeded streams only).
// Pure math only (placement, LOD fade, zoom camera); the three.js side lives in lib/universe/surface-three.ts.
import {lwStream} from './living-world.mjs';
import {GC,TR} from './surface-data.mjs';

export const GROUND_ASSETS=Object.freeze(Object.keys(GC.biomes.grassland.per_m2));
export const TREE_KINDS=Object.freeze(Object.keys(TR.biomes.grassland));
export const GRASS=new Set(['grass_tuft_a','grass_tuft_b','grass_tall_c']);
/** README fade distances (metres): grass full to 25, thinned to 60; crystals/mushrooms/rocks/flowers to 120. Trees near 40, far 150 (giant 300). */
export const LOD=Object.freeze({grassFull:25,grassThin:60,thinKeep:.3,thinScale:1.5,props:120,treeNear:40,treeFar:150,giantFar:300});
export const groundDensity=(biome,asset)=>GC.biomes[biome]?.per_m2?.[asset]??0;
export const treeDensity=(biome,kind)=>(TR.biomes[biome]?.[kind]??0)/100;// file is per 100 m²
export const isMeadow=(biome)=>GC.biomes[biome]?.ground_texture==='meadow';
/** fade limit for one instance (hash h in [0,1)): hide past lerp(near,far,h); shrink to 0 over the last 20% */
export function fadeScale(distM,h,near,far){const lim=near+(far-near)*h;const s=(lim-distM)/(lim*.2);return s>=1?1:s<=0?0:s;}
export function assetFade(asset,distM,h){if(GRASS.has(asset))return fadeScale(distM,h,LOD.grassFull,LOD.grassThin);return fadeScale(distM,h,LOD.grassThin,LOD.props);}

/** Cube-sphere cells (~cellM metres) over a planet of radius R metres. Each cell gets its own seeded stream so a cell always plants the same things. */
export function cubeCells(R,cellM=1){const N=Math.max(4,Math.ceil(R*Math.PI/2/cellM));const cells=[];
 for(let f=0;f<6;f++)for(let i=0;i<N;i++)for(let j=0;j<N;j++){const u=(i+.5)/N*2-1,v=(j+.5)/N*2-1;cells.push({f,i,j,dir:cubeDir(f,u,v),area:cellArea(u,v,N,R)});}
 return {N,cells};}
export function cubeDir(f,u,v){const p=f===0?[1,v,-u]:f===1?[-1,v,u]:f===2?[u,1,-v]:f===3?[u,-1,v]:f===4?[u,v,1]:[-u,v,-1];const l=Math.hypot(p[0],p[1],p[2]);return [p[0]/l,p[1]/l,p[2]/l];}
function cellArea(u,v,N,R){const d=2/N;return R*R*d*d/Math.pow(1+u*u+v*v,1.5);}
/** Poisson-ish count: floor(expected) + one seeded draw for the fraction */
const countOf=(exp,r)=>{const k=Math.floor(exp);return k+(r()<exp-k?1:0);};

/**
 * Plant around a focus direction. biomeAt(dir)->legend id. Returns {asset:[{dir,yaw,scale,h,biome}]}.
 * budget (0..1) thins everything on phones; thinned grass ring 25-60 m keeps 30% at 1.5x scale (README).
 */
export function plantGround({seed,R,focus,biomeAt,budget=1,cellM=1,grid,whole=false}){const g=grid||cubeCells(R,cellM);const out={};for(const a of GROUND_ASSETS)out[a]=[];
 const fx=focus[0],fy=focus[1],fz=focus[2];
 for(const c of g.cells){const dot=c.dir[0]*fx+c.dir[1]*fy+c.dir[2]*fz;const dm=R*Math.acos(Math.max(-1,Math.min(1,dot)));if(!whole&&dm>LOD.props)continue;
  const r=lwStream(seed+':gc:'+c.f+':'+c.i+':'+c.j);const biome=biomeAt(c.dir);
  for(const a of GROUND_ASSETS){let dens=groundDensity(biome,a)*budget;if(!dens)continue;let sc=1;const grass=GRASS.has(a);
   if(grass&&!whole){if(dm>LOD.grassThin)continue;if(dm>LOD.grassFull){dens*=LOD.thinKeep;sc=LOD.thinScale;}}
   const n=countOf(dens*c.area,r);for(let k=0;k<n;k++){const du=(r()-.5),dv=(r()-.5);const dir=jitter(c,du,dv,g.N);out[a].push({dir,yaw:r()*Math.PI*2,scale:sc*(.75+r()*.5),h:r(),biome});}}}
 return out;}
function jitter(c,du,dv,N){const u=(c.i+.5+du)/N*2-1,v=(c.j+.5+dv)/N*2-1;return cubeDir(c.f,u,v);}
/** Trees over the whole planet once (cells of ~4 m), density per biome from Cosmo's file. */
export function plantTrees({seed,R,biomeAt,budget=1,cellM=4}){const g=cubeCells(R,cellM);const out={};for(const k of TREE_KINDS)out[k]=[];
 for(const c of g.cells){const r=lwStream(seed+':tree:'+c.f+':'+c.i+':'+c.j);const biome=biomeAt(c.dir);
  for(const k of TREE_KINDS){const d=treeDensity(biome,k)*budget;if(!d)continue;const n=countOf(d*c.area,r);for(let q=0;q<n;q++)out[k].push({dir:jitter(c,(r()-.5)*.8,(r()-.5)*.8,g.N),yaw:r()*Math.PI*2,scale:.85+r()*.3,h:r(),biome});}}
 return out;}

/**
 * Continuous zoom: z=0 close over-the-shoulder, z=1 full planet orbit. Returns camera height above the surface (units)
 * and the blend toward the orbit framing. Log-spaced so pinch/wheel feel even across the whole range.
 */
export const ZOOM=Object.freeze({min:0,max:1,closeH:1.3,orbitD:34.4,wheelK:.0032,pinchK:1.6});
export function zoomBlend(z){const t=Math.max(0,Math.min(1,z));const s=t*t*(3-2*t);return {t,orbit:s};}
export function zoomDistance(z,closeD,orbitD){const t=Math.max(0,Math.min(1,z));return Math.exp(Math.log(closeD)+(Math.log(orbitD)-Math.log(closeD))*t);}
export function stepZoom(z,{wheel=0,pinch=1}={}){let n=z+wheel*ZOOM.wheelK;if(pinch!==1&&pinch>0)n-=Math.log(pinch)/ZOOM.pinchK;return Math.max(ZOOM.min,Math.min(ZOOM.max,n));}
/** never let the camera dip under ground: clamp radius to surface + clearance */
export function clampAboveGround(len,surfaceR,clear){return Math.max(len,surfaceR+clear);}
