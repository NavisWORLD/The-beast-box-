/**
 * WORLD FIELD: the tiny world's surface driven by Cory's engine, not a re-implementation.
 *  - physics loop: lib/physics/cst-integrator.mjs (createCSTState / stepCSTState / motionParams /
 *    createCSTClock: continuous Lorenz + Hebbian retention + coherence feedback). One world state.
 *  - quantum affinity: lib/companion/spark/engine.mjs gaussianAffinity (who is drawn to whom).
 *  - stream RNG: lwStream (sha256 stream) keyed by u.seed, which tiny-universe derives ONLY from
 *    recorded IBM hardware counts. quantum_entropy comes from those recorded counts when given.
 *  - experiences: lib/zeref/experience-record.mjs makeRecord (hash-chained, origin live_browser).
 *    Training still takes them through scripts/zeref_experience_rows.py, capped at 5% / 150 rows.
 * Cosmo's maps only give the FIRST LOOK (initial cells). After that each cell's temperature,
 * moisture and growth evolve from the loop and the biome (legend index) is re-derived per cell.
 * Tension is not a module: it is the loop's chaos/instability channels. Pure: no DOM or clock.
 */
import {createCSTState,stepCSTState,motionParams,createCSTClock,clamp} from '../physics/cst-integrator.mjs';
import {DAY_LENGTH_TICKS,sunDirAt} from './genesis-sun.mjs';
import {gaussianAffinity} from '../companion/spark/engine.mjs';
import {makeRecord} from '../zeref/experience-record.mjs';
import {lwStream} from './living-world.mjs';

/** Legend prototypes (index order of home_biomes.json): [temp, moisture, growth]; water/height gates below. */
export const LEGEND=Object.freeze(['deep_ocean','shallow_ocean','beach','grassland','heartwood_forest','rainforest','savanna','desert_dunes',
 'mountain_rock','snow_cap','glacier','jelly_geyser','sunflower_ring','crystal_moss','volcano','ember_fields','paper_marsh','celestial_peaks','pine_forest','frozen_sea']);
const PROTO={beach:[.65,.5,.2],grassland:[.6,.5,.5],heartwood_forest:[.55,.7,.8],rainforest:[.75,.9,.9],savanna:[.78,.32,.35],desert_dunes:[.88,.1,.05],
 glacier:[.05,.5,.1],sunflower_ring:[.68,.55,.65],crystal_moss:[.25,.55,.35],ember_fields:[.97,.15,.1],paper_marsh:[.5,.92,.5],pine_forest:[.32,.6,.6]};
const HIGH={mountain_rock:[.4,.3,.15],snow_cap:[.08,.5,.05],celestial_peaks:[.3,.5,.3],volcano:[.95,.1,.05]};
const WATER={deep_ocean:[.5,1,0],shallow_ocean:[.6,1,.2],jelly_geyser:[.75,1,.4],frozen_sea:[.05,1,0]};
const SEA=0.0,PEAK=.62;

export function createWorldField({seed,W=64,H=32,counts=null,initial}){
 const N=W*H,F={seed:String(seed),W,H,N,temp:new Float32Array(N),moist:new Float32Array(N),grow:new Float32Array(N),height:new Float32Array(N),
  idx:new Uint8Array(N),t0:new Float32Array(N),m0:new Float32Array(N),g0:new Float32Array(N),idx0:new Uint8Array(N),hold:new Float32Array(N),S:createCSTState('world:'+seed,{counts}),
  clock:createCSTClock({seed:'world:'+seed,hz:4,maxSubsteps:4,maxFrame:1}),tick:0,changed:0,storm:0,
  // engine-owned sun: advances one step per engine tick inside the stepped clock; the phase is seeded from the recorded counts (own stream, never the field's)
  dayLength:DAY_LENGTH_TICKS,sunAngle:lwStream(seed+':sunphase')()*Math.PI*2,sunDir:null};
 F.sunDir=sunDirAt(F.sunAngle);
 const r=lwStream(seed+':field');
 for(let j=0;j<H;j++)for(let i=0;i<W;i++){const k=j*W+i,n=cellN(F,i,j);const init=initial(n)||{};const id=init.id&&LEGEND.includes(init.id)?init.id:'grassland';
  const p=PROTO[id]||HIGH[id]||WATER[id];F.idx[k]=F.idx0[k]=LEGEND.indexOf(id);
  F.height[k]=Number.isFinite(init.h)?init.h:(WATER[id]?-.2:HIGH[id]?.7:.2);
  F.temp[k]=p[0]+(r()-.5)*.04;F.moist[k]=p[1]+(r()-.5)*.04;F.grow[k]=p[2];F.t0[k]=F.temp[k];F.m0[k]=F.moist[k];F.g0[k]=p[2];}
 return F;
}
export function cellN(F,i,j){const lon=((i+.5)/F.W-.5)*Math.PI*2,lat=((j+.5)/F.H-.5)*Math.PI;const c=Math.cos(lat);return [c*Math.cos(lon),Math.sin(lat),c*Math.sin(lon)];}
export function cellOf(F,n){const lon=Math.atan2(n[2],n[0]),lat=Math.asin(clamp(n[1],-1,1));const i=Math.min(F.W-1,Math.floor((lon/(Math.PI*2)+.5)*F.W)),j=Math.min(F.H-1,Math.floor((lat/Math.PI+.5)*F.H));return j*F.W+i;}
function classify(t,m,g,h){const set=h<SEA?WATER:h>PEAK?HIGH:PROTO;let best=null,bd=1e9;for(const [id,p] of Object.entries(set)){const d=(t-p[0])**2+(m-p[1])**2+.5*(g-p[2])**2;if(d<bd){bd=d;best=id;}}return [LEGEND.indexOf(best),bd];}

/**
 * Advance the field by frameDt seconds of wall time. sun: unit vector to the star; starHeat: 0..1 from the
 * star temperature. Returns the list of cells whose biome changed this call.
 */
export function stepWorldField(F,frameDt,{sun=null,starHeat=.5,mood=null,activity=0}={}){
 const changed=[];
 F.clock.tick(frameDt,h=>{
  F.sunAngle=(F.sunAngle+Math.PI*2/F.dayLength)%(Math.PI*2);F.sunDir=sunDirAt(F.sunAngle);const sun_=sun||F.sunDir; // an explicit `sun` stays an OVERRIDE (tests, special views); otherwise the engine's own sun
  // one world tick of Cory's loop: arousal follows the field's own storms, valence its mean growth
  let gSum=0;for(let k=0;k<F.N;k+=17)gSum+=F.grow[k];const meanG=gSum/Math.ceil(F.N/17);
  for(let q=0;q<10;q++)stepCSTState(F.S,h/10,{valence:meanG,arousal:clamp(.45+.2*(activity??0)+.5*F.storm),curiosity:mood?.curiosity??.5,fear:F.storm*.5});
  const mp=motionParams(F.S),c=F.S.ch;F.mp=mp;
  const raw=c.chaos*.8+c.instability*.4;F.tMean=F.tMean==null?raw:F.tMean+(raw-F.tMean)*h*.01;F.storm=clamp((raw-F.tMean)*3)*Math.min(1,F.tick/240); // the attractor settles before storms count // emergent tension: no separate module
  const lorenzHeat=clamp((F.S.L.z-25)/25,-1,1)*.06,wx=mp.wind.x,wz=mp.wind.z;
  const {W,H,temp,moist,grow,height,idx,hold}=F,nt=new Float32Array(temp),nm=new Float32Array(moist);
  for(let j=0;j<H;j++)for(let i=0;i<W;i++){const k=j*W+i,n=cellN(F,i,j);
   const lat=Math.abs(n[1]),ins=Math.max(0,n[0]*sun_[0]+n[1]*sun_[1]+n[2]*sun_[2]);
   const kL=j*W+(i+W-1)%W,kR=j*W+(i+1)%W,kU=Math.min(H-1,j+1)*W+i,kD=Math.max(0,j-1)*W+i;
   const lap=(a)=>(a[kL]+a[kR]+a[kU]+a[kD])*.25-a[k];
   const up=wx>=0?kL:kR,adv=Math.abs(wx)+Math.abs(wz)*.5; // moisture rides the Lorenz wind from upwind
   const teq=clamp(F.t0[k]+(starHeat-.5)*.2+lorenzHeat*2+.04*(ins-.3)); // first look is the baseline; the loop moves it
   nt[k]=temp[k]+h*(.02*(teq+.06*ins-temp[k])+.02*lap(temp));
   if(height[k]<SEA)nm[k]=1;
   else nm[k]=clamp(moist[k]+h*(.05*lap(moist)+.04*adv*(moist[up]-moist[k])+.03*F.storm*(1-moist[k])+.02*(F.m0[k]-moist[k])-.03*Math.max(0,temp[k]-F.t0[k])));
   const light=.2+.8*ins;const geq=clamp(F.g0[k]+.8*(nm[k]-F.m0[k])-.8*Math.max(0,nt[k]-F.t0[k]-.05)+.1*(light-.5)-.15*F.storm);grow[k]=clamp(grow[k]+h*.01*(geq-grow[k])); // growth by light + water
  }
  F.temp.set(nt);F.moist.set(nm);F.tick++;
  for(let k=0;k<F.N;k++){const [b,d]=classify(temp[k],moist[k],grow[k],height[k]);
   if(b!==idx[k]){const p0=(PROTO[LEGEND[idx[k]]]||HIGH[LEGEND[idx[k]]]||WATER[LEGEND[idx[k]]]);const dc=(temp[k]-p0[0])**2+(moist[k]-p0[1])**2+.5*(grow[k]-p0[2])**2;
    if(dc-d>.012){hold[k]+=h;if(hold[k]>20){idx[k]=b;hold[k]=0;changed.push(k);}}else hold[k]=0;}else hold[k]=0;}
  F.changed+=changed.length;
 });
 return changed;
}
export const legendAt=(F,n)=>LEGEND[F.idx[cellOf(F,n)]];
/** Per-cell legend index image (RGBA, a=255 if the cell left its first-look biome). */
export function fieldRGBA(F,rgbOf){const out=new Uint8Array(F.N*4);for(let k=0;k<F.N;k++){const c=rgbOf(F.idx[k]);out[k*4]=c[0];out[k*4+1]=c[1];out[k*4+2]=c[2];out[k*4+3]=F.idx[k]!==F.idx0[k]?255:0;}return out;}

// ---------------------------------------------------------------- creatures in the same loop
const CH=['valence','arousal','dominance','quantum_entropy','phi_harmonics','coherence','chaos','instability','curiosity','resonance','avoid'];
export function createCreatureLoop(id,seed,{counts=null,qbeast_id=null}={}){return {id,qbeast_id,S:createCSTState(id+':'+seed,{counts}),seen:new Set(),prev:null,step:0};}
export const creatureVec=c=>CH.map(k=>c.S.ch[k]);
/**
 * One world tick for a creature standing on cell n of field F. Emotion comes from the cell + the world's
 * tension; returns {mood, drift, events, records}. Trait drift is the mood pulling traits (rate 0.02).
 */
export function stepCreature(c,F,n,dt,traits,{others=[],origin='live_browser'}={}){
 const k=cellOf(F,n),b=LEGEND[F.idx[k]],novel=!c.seen.has(b);
 for(let q=0,nq=Math.max(1,Math.ceil(dt/.02));q<nq;q++)stepCSTState(c.S,dt/nq,{valence:F.grow[k]*.7+.3*(1-F.storm),arousal:clamp(.3+F.storm*.7),curiosity:novel?.9:.4,fear:F.storm*.6});
 const mood=motionParams(c.S).mood,events=[];
 if(novel){c.seen.add(b);events.push({type:'new-biome',biome:b});}
 if(F.storm>.25&&!c.stormy&&F.tick-(c.lastStorm??-1e9)>240){c.stormy=true;c.lastStorm=F.tick;events.push({type:'storm'});}else if(F.storm<.1)c.stormy=false;
 for(const o of others){const a=gaussianAffinity(creatureVec(c),creatureVec(o));if(a>.6&&!c['met:'+o.id]){c['met:'+o.id]=true;events.push({type:'affinity',with:o.id,affinity:+a.toFixed(4)});}}
 const drift={};if(traits)for(const [t,m] of [['curiosity','curiosity'],['joy','joy'],['calm','calm']])if(Number.isFinite(traits[t]))drift[t]=+(traits[t]+.02*dt*(mood[m]-traits[t])).toFixed(4);
 const records=[];
 if(c.qbeast_id&&events.length)for(const ev of events){c.step++;try{const rec=makeRecord({qbeast_id:c.qbeast_id,origin,step:c.step,
  observation:{cell:k,biome:b,temp:+F.temp[k].toFixed(4),moist:+F.moist[k].toFixed(4),grow:+F.grow[k].toFixed(4),world_tension:+F.storm.toFixed(4),world_tick:F.tick},
  decision:{policy:'cst-world-loop/v1'},action:{key:'WAIT'},outcome:{kind:ev.type,observed:true,...ev},
  reward:{kind:'computed_reward',value:ev.type==='new-biome'?1:ev.type==='affinity'?.5:0,rule:'world-v1: new biome +1, affinity +0.5, else 0'},
  memory:{biomes_seen:[...c.seen].sort()},labels:[{kind:'observed_outcome',value:ev.type,by:'cst-world-loop'}],source:{ref:'world-field/v1'},prev:c.prev});
  records.push(rec);c.prev=rec.hash;}catch{}}
 return {mood,drift,events,records,biome:b};
}
