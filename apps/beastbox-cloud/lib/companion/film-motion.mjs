/**
 * FILM MOTION — animated-film character motion for pocket creatures (Zeref + artist residents).
 * Squash & stretch, anticipation, hops and walks, follow-through springs (ears/tail/lean overlap),
 * head turns toward a neighbour or the camera, and idle fidgets.
 *
 * Honest inputs only: a creature's persona comes from its own id/recorded seed string and, when the
 * caller passes them, its OWN labelled simulator counts. Artist-drawn residents have no quantum seed,
 * so they use their id only. Nothing here invents counts or receipts. Pure: no DOM, clock or network;
 * randomness is a seeded PRNG.
 */
function fnv(str){let h=0x811c9dc5;for(const ch of String(str)){h^=ch.charCodeAt(0);h=Math.imul(h,0x01000193)>>>0;}return h>>>0;}
export function prng(seed){let a=fnv(seed)||1;return()=>{a^=a<<13;a>>>=0;a^=a>>>17;a^=a<<5;a>>>=0;return a/4294967296;};}
/** Shannon entropy (0..1) of the creature's own counts, or null when there is no receipt. */
export function countsEntropy(counts){
 if(!counts||typeof counts!=='object')return null;const v=Object.values(counts).filter(n=>Number.isFinite(n)&&n>0);
 const t=v.reduce((s,n)=>s+n,0);if(!t||v.length<2)return v.length===1?0:null;
 const H=-v.reduce((s,n)=>s+(n/t)*Math.log2(n/t),0);return H/Math.log2(v.length);
}
/** Persona: how this creature likes to move. source tells the UI/tests where it came from. */
export function motionPersona({id,seed=null,counts=null}={}){
 const r=prng(String(seed||id||'anon'));const e=countsEntropy(counts);
 const base={hop:.25+r()*.5,walk:.3+r()*.5,curiosity:.3+r()*.6,fidget:.2+r()*.6,tempo:.8+r()*.5};
 // Spread-out counts → restless explorer; concentrated counts → calm homebody. Only with a receipt.
 if(e!==null){base.walk=Math.min(1,base.walk*.6+e*.5);base.hop=Math.min(1,base.hop*.7+(1-e)*.35);}
 return Object.freeze({...base,source:e!==null?'seed+labelled-counts':seed?'recorded-seed':'id-only'});
}
const spring=(s,target,k,d,dt)=>{const a=(target-s.x)*k-s.v*d;s.v+=a*dt;s.x+=s.v*dt;return s.x;};
export function createActor(persona,{x=0,z=0,radius=1.6,seed='actor'}={}){
 return {p:persona,rand:prng(seed+':acts'),state:'idle',t:0,dur:1.2,x,z,home:{x,z},radius,heading:0,target:null,
  sq:{x:1,v:0},lean:{x:0,v:0},tail:{x:0,v:0},ear:{x:0,v:0},head:{x:0,v:0},lift:0,fid:0};
}
const STATES=['idle','walk','anticipate','hop','land'];export {STATES};
/** Advance one actor. ctx: {lookAt:{x,z}|null, reduced}. Returns the pose to apply. */
export function stepActor(a,dt,ctx={}){
 dt=Math.min(.05,Math.max(0,dt));const {reduced=false}=ctx;a.t+=dt;
 if(reduced){a.state='idle';a.lift=0;a.sq.x=1;return pose(a,0,ctx);}
 const p=a.p;let squash=1;
 const next=()=>{const r=a.rand();a.t=0;
  if(a.state==='anticipate'){a.state='hop';a.dur=.42/p.tempo;return;}
  if(a.state==='hop'){a.state='land';a.dur=.16;return;}
  if(r<p.hop*.5){a.state='anticipate';a.dur=.2/p.tempo;pickTarget(a,.9);return;}
  if(r<p.hop*.5+p.walk*.6){a.state='walk';a.dur=(1.2+a.rand()*1.6)/p.tempo;pickTarget(a,1.4);return;}
  a.state='idle';a.dur=(1+a.rand()*2.2)/p.tempo;a.fid=a.rand()<p.fidget?1:0;};
 if(a.t>=a.dur)next();
 const u=Math.min(1,a.t/a.dur);
 if(a.state==='walk'||a.state==='hop'){
  const tg=a.target||a.home,dx=tg.x-a.x,dz=tg.z-a.z,dist=Math.hypot(dx,dz);
  const speed=(a.state==='hop'?1.6:.55)*p.tempo;if(dist>.02){const s=Math.min(dist,speed*dt);a.x+=dx/dist*s;a.z+=dz/dist*s;a.heading=Math.atan2(dx,dz);}
 }
 if(a.state==='anticipate'){squash=1-.22*Math.sin(u*Math.PI/2);a.lift=0;}
 else if(a.state==='hop'){a.lift=Math.sin(u*Math.PI)*.55;squash=1+.26*Math.cos(u*Math.PI);}
 else if(a.state==='land'){a.lift=0;squash=1-.2*Math.sin(u*Math.PI);}
 else if(a.state==='walk'){const c=Math.abs(Math.sin(a.t*7*p.tempo));a.lift=c*.05;squash=1-.05*(1-c);}
 else {a.lift=0;squash=1+.015*Math.sin(a.t*2.2);}
 spring(a.sq,squash,a.state==='land'||a.state==='anticipate'?260:a.state==='hop'?200:90,a.state==='hop'?14:9,dt);
 return pose(a,a.state==='walk'||a.state==='hop'?1:0,ctx);
}
function pickTarget(a,step){const ang=a.rand()*Math.PI*2,d=step*(.5+a.rand()*.5);let x=a.x+Math.cos(ang)*d,z=a.z+Math.sin(ang)*d;const r=Math.hypot(x-a.home.x,z-a.home.z);if(r>a.radius){x=a.home.x+(x-a.home.x)*a.radius/r;z=a.home.z+(z-a.home.z)*a.radius/r;}a.target={x,z};}
function pose(a,moving,ctx){
 const dt=1/60;
 // Head turn: toward the camera/neighbour when idle (curiosity), else along travel.
 let want=0;if(ctx.lookAt&&!moving){const h=Math.atan2(ctx.lookAt.x-a.x,ctx.lookAt.z-a.z)-a.heading;want=Math.atan2(Math.sin(h),Math.cos(h))*Math.min(1,a.p.curiosity*1.4);want=Math.max(-.9,Math.min(.9,want));}
 if(a.fid&&!moving)want+=Math.sin(a.t*5)*.12;
 spring(a.head,want,40,9,dt);
 const lv=moving?(a.state==='hop'?.16:.08):0;spring(a.lean,lv,60,8,dt);
 // Overlap: tail and ears lag behind body motion (follow-through).
 spring(a.tail,-a.lean.x*2.2+(a.sq.x-1)*1.5,30,4,dt);spring(a.ear,(1-a.sq.x)*1.8-a.lean.x,55,5,dt);
 const sy=a.sq.x,sx=1/Math.sqrt(Math.max(.4,sy));
 return {x:a.x,z:a.z,lift:a.lift,sx,sy,heading:a.heading,head:a.head.x,lean:a.lean.x,tail:a.tail.x,ear:a.ear.x,state:a.state};
}
