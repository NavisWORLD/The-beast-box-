/** Geyser Jelly (Cory, Oct 21): a volcanic Icelandic island diorama inside a translucent jelly sea block,
 * placed in the home world behind the cage (opposite the default camera). Pure logic, no three.js. */
export const GJ=Object.freeze({cx:-13.9,cz:-9.7,half:7.5,sea:.02,bed:-.7,R:5.6,
 volcano:{x:-1.6,z:-1.4,h:3.1,r:2.6,crater:.55},geyser:{x:1.9,z:.9},lagoon:{x:2.6,z:-1.6,r:.75},
 village:{x:.6,z:2.6},jetty:{x:-.4,z:4.4},lighthouse:{x:-4.3,z:2.2},channelEnd:{x:-4.9,z:-3.2},
 simHigh:64,simLow:36});
const cl=(v,a,b)=>v<a?a:v>b?b:v;
const sm=(a,b,x)=>{const t=cl((x-a)/(b-a),0,1);return t*t*(3-2*t);};
export const toLocal=(x,z)=>({x:x-GJ.cx,z:z-GJ.cz});
export const toWorld=(x,z)=>({x:x+GJ.cx,z:z+GJ.cz});
export const inBlock=(x,z)=>Math.abs(x-GJ.cx)<GJ.half&&Math.abs(z-GJ.cz)<GJ.half;
const n2=(x,z)=>Math.sin(x*1.7+z*.6)*.5+Math.sin(x*.9-z*1.9+1.3)*.35+Math.sin(x*3.1+z*2.7)*.15;
/** Local island height (y=0 is sea level inside the block). Volcano cone with crater, basalt cliffs at the shore. */
export function islandHeight(lx,lz){const V=GJ.volcano;const a=Math.atan2(lz,lx);
 const shore=GJ.R*(1+.12*Math.sin(a*3+.7)+.07*Math.sin(a*7-1.1));const r=Math.hypot(lx,lz);
 let h=r<shore?.28+.22*sm(shore,shore*.55,r)+.08*n2(lx,lz):GJ.bed+(GJ.bed*-1+.1)*sm(shore+1.6,shore,r);
 if(r<shore&&r>shore-.35)h+=.35*sm(shore-.35,shore-.12,r);// cliff lip (columnar basalt)
 const dv=Math.hypot(lx-V.x,lz-V.z);const av=Math.atan2(lz-V.z,lx-V.x);const cone=V.h*Math.max(0,1-dv/(V.r*(1+.1*Math.sin(av*5+1)+.05*Math.sin(av*11))))**1.4*(1+.06*Math.sin(av*9)*Math.min(1,dv));h=Math.max(h,cone>0?.3+cone:h);
 if(dv<V.crater)h=Math.min(h,V.h*.78+.3);// crater floor (lava lake)
 const L=GJ.lagoon;const dl=Math.hypot(lx-L.x,lz-L.z);if(dl<L.r)h=Math.min(h,.05-.12*(1-dl/L.r));
 return Number.isFinite(h)?h:0;}
/** World ground for creatures inside the block (never below the seabed, wades in shallows). */
export function islandGround(x,z){const p=toLocal(x,z);return Math.max(GJ.bed+.05,islandHeight(p.x,p.z));}
/** Sea stacks around the island (local). */
export const STACKS=Object.freeze([{x:-5.9,z:3.6,r:.35,h:1.4},{x:-6.3,z:2.7,r:.22,h:.9},{x:5.8,z:3.9,r:.3,h:1.1},{x:4.9,z:-5.2,r:.26,h:1.2}]);
/** Strokkur cycle: refill → rest → surge → dome → burst → drain. Returns {phase,k(0..1),jet(0..1),dome(0..1)}. */
export const GEYSER_PHASES=Object.freeze([['refill',3.2],['rest',2.6],['surge',1.2],['dome',.55],['burst',2.1],['drain',1.6]]);
export const GEYSER_PERIOD=GEYSER_PHASES.reduce((s,p)=>s+p[1],0);
export function geyserCycle(t){let u=((t%GEYSER_PERIOD)+GEYSER_PERIOD)%GEYSER_PERIOD;if(!Number.isFinite(u))u=0;for(const [ph,d] of GEYSER_PHASES){if(u<d){const k=u/d;
  return {phase:ph,k,dome:ph==='dome'?Math.sin(k*Math.PI*.5):ph==='surge'?k*.3:0,jet:ph==='burst'?Math.sin(Math.min(1,k*1.6)*Math.PI*.5)*(1-sm(.55,1,k)):0,pool:ph==='drain'?1-k*.7:ph==='refill'?.3+.7*k:1};}u-=d;}
 return {phase:'refill',k:0,dome:0,jet:0,pool:.3};}
/** Damped spring for the jelly wobble (tip and spring back). state {a,v}; returns new state. */
export function springStep(s,dt,k=38,c=3.2){const d=Math.min(.05,Math.max(0,dt||0));const v=(s.v+(-k*s.a-c*s.v)*d);const a=s.a+v*d;return {a:Number.isFinite(a)?Math.max(-1,Math.min(1,a)):0,v:Number.isFinite(v)?Math.max(-20,Math.min(20,v)):0};}
/** Shallow-water heightfield (wave equation, damped, land-masked). h,p: Float32Array n*n, mask 1=water. Stable for any dt. */
export function waterStep(h,p,mask,n,dt,c2=.18,damp=.985){const s=Math.min(1,Math.max(0,(dt||0)*60));if(s<=0)return;const k=c2*s;
 for(let j=1;j<n-1;j++)for(let i=1;i<n-1;i++){const q=j*n+i;if(!mask[q]){p[q]=0;continue;}
  const lap=h[q-1]+h[q+1]+h[q-n]+h[q+n]-4*h[q];let v=(2*h[q]-p[q]+k*lap)*damp-h[q]*(1-damp)*0;v=v>2?2:v<-2?-2:v;p[q]=Number.isFinite(v)?v:0;}
 for(let q=0;q<n*n;q++){const t=h[q];h[q]=p[q];p[q]=t;}}
export function waterDrop(h,n,u,v,amp,rad=2){const ci=Math.round(u*(n-1)),cj=Math.round(v*(n-1));for(let j=-rad;j<=rad;j++)for(let i=-rad;i<=rad;i++){const x=ci+i,y=cj+j;if(x<1||y<1||x>=n-1||y>=n-1)continue;const f=Math.exp(-(i*i+j*j)/(rad*.8+.01));h[y*n+x]+=amp*f;}}
/** Boat Hafdis: bay loop from the jetty (local), period P seconds. */
export function boatPose(t,P=34){const u=((t/P)%1+1)%1,a=u*Math.PI*2;const x=GJ.jetty.x+Math.sin(a)*2.6,z=GJ.jetty.z+1.1-Math.cos(a)*1.1;return {x,z,heading:Math.atan2(Math.cos(a)*2.6,Math.sin(a)*1.1)};}
/** Humpback: slow offshore circuit; breach arc 0..1 lifts it out of the water. */
export function whalePose(t,breach=0){const a=t*.05;const R=6.4;const x=Math.cos(a)*R,z=Math.sin(a)*R*.9;const b=Math.max(0,Math.min(1,breach));
 return {x,z,y:-.25+Math.sin(b*Math.PI)*1.3,heading:a+Math.PI/2,pitch:(b<.5?-.9:.9)*Math.sin(b*Math.PI)};}
/** Lava bomb ballistic position after time s from launch (local). */
export function bombAt(b,s){return {x:b.x+b.vx*s,y:b.y+b.vy*s-4.9*s*s,z:b.z+b.vz*s};}
export function rng(seed){let a=[...String(seed)].reduce((h,ch)=>Math.imul(h^ch.charCodeAt(0),16777619),2166136261)>>>0;return()=>{a=(a+0x6D2B79F5)>>>0;let t=a;t=Math.imul(t^t>>>15,t|1);t^=t+Math.imul(t^t>>>7,t|61);return((t^t>>>14)>>>0)/4294967296;};}
/** Roam goals on the island (world coords). */
export function islandSpots(){const w=(p,id,label)=>{const q=toWorld(p.x,p.z);return {id,kind:'far',label,x:q.x,z:q.z,color:'#ffb27a',island:true};};
 return [w({x:GJ.geyser.x-.5,z:GJ.geyser.z+.4},'gj-geyser','Strokkur boardwalk'),w({x:GJ.volcano.x+1.6,z:GJ.volcano.z+.6},'gj-volcano','Scoria slope'),w({x:GJ.village.x,z:GJ.village.z-.3},'gj-village','Turf houses'),w({x:GJ.lighthouse.x+.5,z:GJ.lighthouse.z-.3},'gj-lighthouse','Lighthouse cliffs')];}
