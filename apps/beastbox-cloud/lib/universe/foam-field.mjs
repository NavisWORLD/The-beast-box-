// Visual Life Pass, B1: the FOAM FIELD, an engine output. Foam is BORN where the sea makes it (wave crests and the shore), CARRIED by the engine's own wind,
// and FADES with age until it is gone. It is the "advected foam" the sea needs: sea-state's crestFoam is a per-point trace; this is a field that travels.
// Drivers (nothing else moves it): seaFrom(F) = the CST wind (motionParams(F.S).wind) and storm tension (F.storm); the ONE wave function waveHeightAt (same as the GLSL mirror);
// the field's own height map (water = height < 0). Engine time t = F.tick / 4 seconds, the same t the sea phase uses.
// Pure: no DOM, no clock, no Math.random. Same seed + same ticks = same foam, byte for byte. It reads the world field and never writes to it.
// Label: SIMULATED (stepped by the world loop), derived visuals only. Nothing here is stored in the engine JSON.
import {seaFrom,waveHeightAt,SEA} from './sea-state.mjs';
import {cellN} from './world-field.mjs';
import {VL_WATER,pairTable} from './vislife-look.mjs';
const PK=VL_WATER.foam.const_block; // Cosmo's look pack (SEEDED look-hints): age caps in ticks, fade table, birth tables
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
export const FOAM=Object.freeze({
 ageCapTicks:PK.age_cap_ticks.storm_lingering, // the longest cap (storm, 40 ticks = 10 s of engine time); every patch has its own cap <= this and is exactly 0 at its cap
 capCrest:PK.age_cap_ticks.crest,capShore:PK.age_cap_ticks.shore,capStorm:PK.age_cap_ticks.storm_lingering,stormAt:0.5, // crest 8 = sea-state foamLifeS x 4 ticks/s (engine); shore 24 and storm 40 are the pack's own numbers
 cellsPerTick:0.35,     // cells a patch travels per tick at engine wind 1 (it never exceeds 1 cell per tick, so the advection stays stable)
 crestBias:0.55,crestGain:2.2, // the same crest window sea-state.crestFoam uses
 shoreK:0.9,            // shore birth strength (times whitecap coverage and the swell pulse)
 crestK:1,
});
const hashK=(k)=>{let h=(Math.imul(k+1,0x9E3779B1)^0x85EBCA6B)>>>0;h=Math.imul(h^(h>>>15),0x2C1B3C6D)>>>0;h=Math.imul(h^(h>>>12),0x297A2D39)>>>0;return ((h^(h>>>15))>>>0)/4294967296;};
/** Make a foam field for a world field F (same W x H grid). Starts at F.tick with no foam. */
export function createFoamField(F){
 const N=F.N,dirs=new Float32Array(N*3),gate=new Float32Array(N);
 for(let j=0;j<F.H;j++)for(let i=0;i<F.W;i++){const k=j*F.W+i,n=cellN(F,i,j);dirs[k*3]=n[0];dirs[k*3+1]=n[1];dirs[k*3+2]=n[2];gate[k]=hashK(k);}
 return {W:F.W,H:F.H,N,tick:F.tick|0,born:new Float32Array(N),cap:new Float32Array(N).fill(FOAM.capShore),age:new Float32Array(N).fill(FOAM.capShore),foam:new Float32Array(N),drift:[0,0],dirs,gate,sea:null};
}
const FADE=PK.age_fade_alpha_by_age01;
const fade=(age,cap)=>age>=cap?0:pairTable(FADE,age/cap); // the pack's fade curve over age/cap
/** The foam amount of each cell right now = born strength x fade(age). */
function refresh(f){for(let k=0;k<f.N;k++)f.foam[k]=f.born[k]*fade(f.age[k],f.cap[k]);}
/** Advance ONE engine tick. Order: age, carry downwind, kill foam on land, fade, then birth at crests and the shore. */
export function stepFoam(f,F,seaIn){
 const sea=seaIn||seaFrom(F);f.sea=sea;f.tick++;const t=f.tick/4,{W,H,N}=f;
 // 1) carry: semi-Lagrangian, source = here minus the wind step, bilinear on the (wrapping) lon axis
 const vi=sea.wind*Math.cos(sea.dir)*FOAM.cellsPerTick,vj=sea.wind*Math.sin(sea.dir)*FOAM.cellsPerTick;
 const nb=new Float32Array(N),na=new Float32Array(N),nc=new Float32Array(N);
 for(let j=0;j<H;j++)for(let i=0;i<W;i++){const k=j*W+i;let si=i-vi,sj=clamp(j-vj,0,H-1);
  const i0=Math.floor(si),j0=Math.floor(sj),fx=si-i0,fy=sj-j0,j1=Math.min(H-1,j0+1);
  const ia=((i0%W)+W)%W,ib=(((i0+1)%W)+W)%W;
  const w=[(1-fx)*(1-fy),fx*(1-fy),(1-fx)*fy,fx*fy],ks=[j0*W+ia,j0*W+ib,j1*W+ia,j1*W+ib];
  let bb=0,ag=0,vis=0,cg=0;for(let q=0;q<4;q++){const kk=ks[q],fv=f.foam[kk];bb+=f.born[kk]*w[q];vis+=fv*w[q];ag+=f.age[kk]*fv*w[q];cg+=f.cap[kk]*fv*w[q];}
  // amount-weighted age: an empty neighbour adds no age to a patch that drifts into it
  nb[k]=vis>1e-4?bb:0;na[k]=vis>1e-4?ag/vis+1:FOAM.capShore;nc[k]=vis>1e-4?cg/vis:FOAM.capShore;}
 // 2) land holds no foam; foam is also exactly 0 once it reaches the age cap
 for(let k=0;k<N;k++){if(F.height[k]>=0||na[k]>=nc[k]){nb[k]=0;na[k]=nc[k];}}
 f.born.set(nb);f.age.set(na);f.cap.set(nc);
 // 3) birth: crests (the ONE wave function) gated by whitecap coverage; shore (water cell touching land) swings with the swell. Strengths come from the pack's tables; both are 0 on a calm tick.
 const wc=sea.whitecap,amp=Math.max(1e-9,sea.amp),pulse=0.5+0.5*Math.sin(Math.PI*2*SEA.shoreSwellHz*t+0.7);
 const crestA=pairTable(PK.birth_alpha_by_whitecap,wc),shoreA=pairTable(PK.shore_birth_by_wind01,sea.wind),stormy=sea.storm>=FOAM.stormAt;
 if(crestA>0||shoreA>0)for(let j=0;j<H;j++)for(let i=0;i<W;i++){const k=j*W+i;if(F.height[k]>=0)continue;
  let born=0,cap=stormy?FOAM.capStorm:FOAM.capCrest;
  if(crestA>0&&f.gate[k]<Math.max(wc,0.05)){const c=clamp((waveHeightAt(sea,[f.dirs[k*3],f.dirs[k*3+1],f.dirs[k*3+2]],t)/amp-FOAM.crestBias)*FOAM.crestGain,0,1);born=c*FOAM.crestK*crestA;}
  const kl=j*W+(i+W-1)%W,kr=j*W+(i+1)%W,ku=Math.min(H-1,j+1)*W+i,kd=Math.max(0,j-1)*W+i;
  if(shoreA>0&&(F.height[kl]>=0||F.height[kr]>=0||F.height[ku]>=0||F.height[kd]>=0)){const sb=FOAM.shoreK*shoreA*(0.35+0.65*pulse);if(sb>born){born=sb;cap=stormy?FOAM.capStorm:FOAM.capShore;}}
  born=clamp(born,0,1);
  if(born>f.born[k]*fade(f.age[k],f.cap[k])){f.born[k]=born;f.cap[k]=cap;f.age[k]=0.08*cap;}} // starts at the fade table's peak
 // 4) the drift the renderer scrolls its foam detail by: the integral of the engine wind, in UV units (wraps at 1)
 f.drift[0]=(((f.drift[0]+vi/W)%1)+1)%1;f.drift[1]=(((f.drift[1]+vj/H)%1)+1)%1;
 refresh(f);return f;
}
/** Catch the foam up to the world field's tick (at most maxSteps, one per engine tick). Called every frame, it steps exactly once per world tick. */
export function syncFoam(f,F,maxSteps=4){let n=0;if(F.tick<f.tick){f.tick=F.tick;}while(f.tick<F.tick&&n<maxSteps){stepFoam(f,F);n++;}return n;}
/** Foam 0..1 at a unit direction (nearest cell: the renderer samples the same grid as a texture). */
export function foamAt(f,F,d){const lon=Math.atan2(d[2],d[0]),lat=Math.asin(clamp(d[1],-1,1));const i=Math.min(f.W-1,Math.floor((lon/(Math.PI*2)+.5)*f.W)),j=Math.min(f.H-1,Math.floor((lat/Math.PI+.5)*f.H));return f.foam[j*f.W+i];}
/** Cover (mean foam over water cells) and peak: the numbers the HUD receipt can quote. */
export function foamStats(f,F){let s=0,n=0,m=0;for(let k=0;k<f.N;k++){if(F.height[k]>=0)continue;n++;s+=f.foam[k];if(f.foam[k]>m)m=f.foam[k];}return {cover:n?s/n:0,peak:m,waterCells:n,wind:f.sea?f.sea.wind:0,dir:f.sea?f.sea.dir:0,tick:f.tick};}
/** Foam as bytes (one per cell) for a data texture. */
export function foamBytes(f,out){const o=out||new Uint8Array(f.N);for(let k=0;k<f.N;k++)o[k]=Math.round(clamp(f.foam[k],0,1)*255);return o;}
