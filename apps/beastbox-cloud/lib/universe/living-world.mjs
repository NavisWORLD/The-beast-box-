// Living World (Oct 22 2026): pure helpers for the tiny-universe planet surface. No UI.
// Every value is derived from the genesis seed (recorded ibm_marrakesh counts) or from SIMULATED growth ticks.
import {sha256Hex} from './sha256.mjs';
export const LW_LABELS=Object.freeze({
 spark:'IBM spark: recorded ibm_marrakesh hardware counts',
 growth:'Growth: SIMULATED (Rigetti-style Bell simulator, not hardware)',
 model:'12D model simulation (visual projection, not a proven theory)'});
/** Deterministic stream keyed by a string.
 * @param {string} key @returns {()=>number} */
export function lwStream(key){let ctr=0,buf=[];return()=>{if(!buf.length){const h=sha256Hex(key+':'+(ctr++));for(let i=0;i<64;i+=8)buf.push(parseInt(h.slice(i,i+8),16)/2**32);}return /** @type {number} */(buf.shift());};}
/** Unit vector on the sphere from two stream draws. */
export function unitFrom(r){const z=r()*2-1,a=r()*Math.PI*2,s=Math.sqrt(1-z*z);return [s*Math.cos(a),z,s*Math.sin(a)];}
/** Gathering points the grass spreads from: one per planet with life plus the beast's home; capped at 8. */
export function gatheringPoints(u,beastKey='guest'){const r=lwStream(u.seed+':gather');const pts=[unitFrom(lwStream(u.seed+':home:'+beastKey))];
 for(let i=0;i<7;i++)pts.push(unitFrom(r));return pts;}
/** Spread angle (radians) of grass coverage: grows with SIMULATED growth tick and life; reaches the whole planet (PI). */
export function spreadAngle(u){const life=(u.life||[]).reduce((a,l)=>a+(l.complexity_norm||0),0);return Math.min(Math.PI,0.35+u.tick*0.018+life*0.08);}
/** Initial beast traits: seeded from the beast's own key + universe seed (no hand-picked values). */
export function initialTraits(u,beastKey){const r=lwStream(u.seed+':traits:'+beastKey);return {curiosity:+r().toFixed(4),sociality:+r().toFixed(4),calm:+r().toFixed(4),joy:+r().toFixed(4),experiences:0};}
/** Traits drift from experiences (growth events, storms, greetings). Drift size is drawn from a seeded stream keyed by the event; never locked. */
export function driftTraits(tr,u,beastKey,exp){const r=lwStream(u.seed+':drift:'+beastKey+':'+u.tick+':'+exp);const n={...tr};const d=()=> (r()-.5)*0.06;
 const cl=x=>+Math.min(1,Math.max(0,x)).toFixed(4);
 if(exp==='storm'){n.calm=cl(n.calm-Math.abs(d()));n.curiosity=cl(n.curiosity+d());}
 else if(exp==='abiogenesis'){n.curiosity=cl(n.curiosity+Math.abs(d()));n.joy=cl(n.joy+Math.abs(d()));}
 else if(exp==='supernova'){n.calm=cl(n.calm+d());n.curiosity=cl(n.curiosity+Math.abs(d()));}
 else if(exp==='build'){n.curiosity=cl(n.curiosity+Math.abs(d())*.5);n.sociality=cl(n.sociality+d());}
 else if(exp==='calm'||exp==='rest'){n.calm=cl(n.calm+Math.abs(d()));}
 else if(exp==='greet'){n.sociality=cl(n.sociality+Math.abs(d()));n.joy=cl(n.joy+Math.abs(d())*.5);}
 else {for(const k of ['curiosity','sociality','calm','joy'])n[k]=cl(n[k]+d()*.3);}
 n.experiences=(tr.experiences||0)+1;return n;}
/** 12D hypercube vertices (subset) projected to 3D with a seeded projection matrix; returns flat xyz array and edge index pairs. */
export function lattice12D(seed,maxV=256){const r=lwStream(seed+':12d');const P=Array.from({length:3},()=>Array.from({length:12},()=>r()*2-1));
 const verts=[],ids=[];for(let i=0;i<maxV;i++){const v=Math.floor(r()*4096);ids.push(v);const x=[0,0,0];for(let d=0;d<12;d++){const b=((v>>d)&1)*2-1;for(let k=0;k<3;k++)x[k]+=P[k][d]*b;}verts.push(...x);}
 const edges=[];for(let i=0;i<ids.length;i++)for(let j=i+1;j<ids.length;j++){const x=ids[i]^ids[j];if(x&&!(x&(x-1)))edges.push(i,j);}return {verts,edges};}
// ---- Fuller world (Oct 22 2026): seeded things creatures can explore, learn from, and change.
export const THING_KINDS=Object.freeze(['flower','crystal','cairn','pond','burrow','tree']);
/** Things on the planet: positions and kinds from the seed stream; how many are "awake" grows with coverage. */
export function worldThings(u,max=48){const r=lwStream(u.seed+':things');return Array.from({length:max},(_,i)=>({id:'thing-'+i,kind:THING_KINDS[Math.floor(r()*THING_KINDS.length)],n:unitFrom(r),size:+(0.6+r()*0.8).toFixed(3),level:0}));}
/** What a creature takes from touching a thing (trait channel); the amount is drawn from a seeded stream inside driftTraits. */
export const THING_LESSON=Object.freeze({flower:'abiogenesis',crystal:'supernova',cairn:'build',pond:'calm',burrow:'rest',tree:'abiogenesis'});
