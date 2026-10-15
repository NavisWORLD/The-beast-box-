/**
 * FILM MOTION — animated-film character motion for pocket creatures (Zeref + artist residents + catalogue 3D).
 * Squash & stretch, anticipation, hops and walks, curious lean, scared scoot, happy zoomies,
 * smooth crossfade pose blending, grounded contact shadow metrics, follow-through springs (ears/tail/lean overlap),
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
export const STATES=['idle','walk','anticipate','hop','land','curious','scared','zoomies'];
export const FILM_CLIPS=Object.freeze({
 idle:'idle',
 walk:'walk',
 hop:'hop',
 'curious lean':'curious',
 curious:'curious',
 'scared scoot':'scared',
 scared:'scared',
 'happy zoomies':'zoomies',
 zoomies:'zoomies',
});
export function createActor(persona,{x=0,z=0,radius=1.6,seed='actor'}={}){
 return {p:persona,rand:prng(seed+':acts'),state:'idle',prevState:'idle',blend:1,t:0,dur:1.2,x,z,home:{x,z},radius,heading:0,target:null,
  sq:{x:1,v:0},lean:{x:0,v:0},tail:{x:0,v:0},ear:{x:0,v:0},head:{x:0,v:0},lift:0,fid:0,stepCount:0,lastPose:null};
}
/** Trigger a named film animation cue ('curious', 'scared', 'zoomies', 'hop', 'walk', 'idle'). */
export function triggerCue(a,cue,target=null){
 if(!a)return a;
 const nextState=FILM_CLIPS[cue]||cue;
 if(!STATES.includes(nextState))return a;
 a.prevState=a.state;
 a.state=nextState;
 a.blend=0;
 a.t=0;
 const p=a.p||{tempo:1};
 if(nextState==='curious'){
  a.dur=1.1/p.tempo;
  if(target)clampTarget(a,target.x,target.z);
 }else if(nextState==='scared'){
  a.dur=0.95/p.tempo;
  if(target){
   const dx=a.x-target.x,dz=a.z-target.z,d=Math.hypot(dx,dz)||1;
   clampTarget(a,a.x+(dx/d)*0.75,a.z+(dz/d)*0.75);
  }else pickTarget(a,0.65);
 }else if(nextState==='zoomies'){
  a.dur=1.45/p.tempo;
  pickTarget(a,1.25);
 }else if(nextState==='hop'){
  a.state='anticipate';
  a.dur=0.2/p.tempo;
  if(target)clampTarget(a,target.x,target.z);else pickTarget(a,0.9);
 }else if(nextState==='walk'){
  a.dur=1.3/p.tempo;
  if(target)clampTarget(a,target.x,target.z);else pickTarget(a,1.2);
 }else{
  a.dur=1.1/p.tempo;
 }
 return a;
}
/** Grounded contact shadow metrics from vertical lift and squash. */
export function contactShadow({lift=0,sy=1}={}){
 const h=Math.max(0,lift);
 const squashSpread=Math.max(0.82,Math.min(1.28,1+(1-sy)*0.45));
 const scale=Math.max(0.38,Math.min(1.3,squashSpread*(1-Math.min(0.58,h*0.85))));
 const opacity=Math.max(0.18,Math.min(0.75,0.62*(1-Math.min(0.68,h*0.95))));
 const blurPx=Math.round((3+h*10)*10)/10;
 return {scale,opacity,blurPx,grounded:h<0.03};
}
/** Smoothly blend two film poses by factor alpha (0..1). */
export function blendPose(prev,next,alpha=1){
 if(!prev||alpha>=1)return next;
 const w=Math.max(0,Math.min(1,alpha));
 const k=1-w;
 const dh=Math.atan2(Math.sin(next.heading-prev.heading),Math.cos(next.heading-prev.heading));
 return {
  ...next,
  x:prev.x*k+next.x*w,
  z:prev.z*k+next.z*w,
  lift:prev.lift*k+next.lift*w,
  sx:prev.sx*k+next.sx*w,
  sy:prev.sy*k+next.sy*w,
  heading:prev.heading+dh*w,
  head:prev.head*k+next.head*w,
  lean:prev.lean*k+next.lean*w,
  tail:prev.tail*k+next.tail*w,
  ear:prev.ear*k+next.ear*w,
  blend:w,
 };
}
/** Advance one actor. ctx: {lookAt:{x,z}|null, emotion?:any, cue?:string|null, reduced?:boolean}. Returns the pose to apply. */
export function stepActor(a,dt,ctx={}){
 dt=Math.min(.05,Math.max(0,dt));const {reduced=false,emotion=null,cue=null}=ctx;a.t+=dt;
 if(reduced){a.state='idle';a.lift=0;a.sq.x=1;a.blend=1;return pose(a,0,ctx);}
 if(cue)triggerCue(a,cue,ctx.lookAt||null);
 const p=a.p;let squash=1;
 const switchState=(st,dur)=>{a.prevState=a.state;a.state=st;a.t=0;a.dur=dur;a.blend=0;a.stepCount=(a.stepCount||0)+1;};
 const next=()=>{
  const r=a.rand();
  if(a.state==='anticipate'){switchState('hop',.42/p.tempo);return;}
  if(a.state==='hop'){switchState('land',.16);return;}
  if(a.state==='zoomies'){switchState('land',.16);return;}
  const dom=emotion?.dominant||null;
  // Emotion-aware or periodic expressive film states (curious lean, scared scoot, happy zoomies)
  const sc=a.stepCount||0;
  if(dom==='fear'&&r<.28){switchState('scared',.85/p.tempo);pickTarget(a,.65);return;}
  if((dom==='joy'||dom==='mischief')&&r<.28){switchState('zoomies',1.25/p.tempo);pickTarget(a,1.25);return;}
  if(dom==='curiosity'&&r<.26){switchState('curious',1.0/p.tempo);pickTarget(a,.55);return;}
  if(sc>=6&&sc%9===0){switchState('curious',.95/p.tempo);pickTarget(a,.5);return;}
  if(sc>=8&&sc%13===0){switchState('zoomies',1.15/p.tempo);pickTarget(a,1.15);return;}
  if(sc>=11&&sc%17===0){switchState('scared',.75/p.tempo);pickTarget(a,.55);return;}
  if(r<p.hop*.5){switchState('anticipate',.2/p.tempo);pickTarget(a,.9);return;}
  if(r<p.hop*.5+p.walk*.6){switchState('walk',(1.2+a.rand()*1.6)/p.tempo);pickTarget(a,1.4);return;}
  switchState('idle',(1+a.rand()*2.2)/p.tempo);a.fid=a.rand()<p.fidget?1:0;
 };
 if(a.t>=a.dur)next();
 a.blend=Math.min(1,(a.blend??1)+dt*7.5);
 const u=Math.min(1,a.t/a.dur);
 if(a.state==='walk'||a.state==='hop'){
  const tg=a.target||a.home,dx=tg.x-a.x,dz=tg.z-a.z,dist=Math.hypot(dx,dz);
  const speed=(a.state==='hop'?1.6:.55)*p.tempo;if(dist>.02){const s=Math.min(dist,speed*dt);a.x+=dx/dist*s;a.z+=dz/dist*s;a.heading=Math.atan2(dx,dz);}
 }else if(a.state==='curious'){
  const tg=ctx.lookAt||a.target||a.home,dx=tg.x-a.x,dz=tg.z-a.z,dist=Math.hypot(dx,dz);
  if(dist>.05){const s=Math.min(dist,.28*p.tempo*dt);const nx=a.x+dx/dist*s,nz=a.z+dz/dist*s;if(Math.hypot(nx-a.home.x,nz-a.home.z)<=a.radius){a.x=nx;a.z=nz;}a.heading=Math.atan2(dx,dz);}
 }else if(a.state==='scared'){
  const tg=a.target||a.home,dx=tg.x-a.x,dz=tg.z-a.z,dist=Math.hypot(dx,dz);
  if(dist>.02){const s=Math.min(dist,.92*p.tempo*dt);a.x+=dx/dist*s;a.z+=dz/dist*s;a.heading=Math.atan2(-dx,-dz);}
 }else if(a.state==='zoomies'){
  const tg=a.target||a.home,dx=tg.x-a.x,dz=tg.z-a.z,dist=Math.hypot(dx,dz);
  if(dist<.12)pickTarget(a,1.25);
  else{
   const zig=Math.sin(a.t*14*p.tempo)*.35;
   const ang=Math.atan2(dx,dz)+zig;
   const s=1.95*p.tempo*dt;
   let nx=a.x+Math.sin(ang)*s,nz=a.z+Math.cos(ang)*s;
   const r=Math.hypot(nx-a.home.x,nz-a.home.z);
   if(r>a.radius){nx=a.home.x+(nx-a.home.x)*a.radius/r;nz=a.home.z+(nz-a.home.z)*a.radius/r;}
   a.x=nx;a.z=nz;a.heading=ang;
  }
 }
 if(a.state==='anticipate'){squash=1-.22*Math.sin(u*Math.PI/2);a.lift=0;}
 else if(a.state==='hop'){a.lift=Math.sin(u*Math.PI)*.55;squash=1+.26*Math.cos(u*Math.PI);}
 else if(a.state==='land'){a.lift=0;squash=1-.2*Math.sin(u*Math.PI);}
 else if(a.state==='walk'){const c=Math.abs(Math.sin(a.t*7*p.tempo));a.lift=c*.05;squash=1-.05*(1-c);}
 else if(a.state==='curious'){a.lift=0;squash=1+.06*Math.sin(u*Math.PI);}
 else if(a.state==='scared'){const scoot=Math.abs(Math.sin(a.t*12*p.tempo));a.lift=scoot*.03;squash=.86-.05*scoot;}
 else if(a.state==='zoomies'){const b=Math.abs(Math.sin(a.t*11*p.tempo));a.lift=b*.24;squash=1+.14*(b-.5);}
 else {a.lift=0;squash=1+.015*Math.sin(a.t*2.2);}
 spring(a.sq,squash,a.state==='land'||a.state==='anticipate'?260:a.state==='hop'||a.state==='zoomies'?200:90,a.state==='hop'?14:9,dt);
 const moving=a.state==='walk'||a.state==='hop'||a.state==='zoomies'||a.state==='scared'?1:0;
 return pose(a,moving,ctx);
}
function clampTarget(a,x,z){
 const r=Math.hypot(x-a.home.x,z-a.home.z);
 if(r>a.radius){x=a.home.x+(x-a.home.x)*a.radius/r;z=a.home.z+(z-a.home.z)*a.radius/r;}
 a.target={x,z};
}
function pickTarget(a,step){const ang=a.rand()*Math.PI*2,d=step*(.5+a.rand()*.5);clampTarget(a,a.x+Math.cos(ang)*d,a.z+Math.sin(ang)*d);}
function pose(a,moving,ctx){
 const dt=1/60;
 // Head turn: toward the camera/neighbour when idle or curious, else along travel.
 let want=0;if(ctx.lookAt&&(!moving||a.state==='curious')){const h=Math.atan2(ctx.lookAt.x-a.x,ctx.lookAt.z-a.z)-a.heading;want=Math.atan2(Math.sin(h),Math.cos(h))*Math.min(1,a.p.curiosity*(a.state==='curious'?1.7:1.4));want=Math.max(-.9,Math.min(.9,want));}
 if(a.fid&&!moving)want+=Math.sin(a.t*5)*.12;
 if(a.state==='curious')want+=Math.sin(a.t*3.2)*.14;
 spring(a.head,want,40,9,dt);
 const lv=a.state==='curious'?.24:a.state==='scared'?-.18:a.state==='zoomies'?.22:moving?(a.state==='hop'?.16:.08):0;
 spring(a.lean,lv,60,8,dt);
 // Overlap: tail and ears lag behind body motion (follow-through), plus joyful wag during zoomies.
 const zoomWag=a.state==='zoomies'?Math.sin(a.t*18)*.38:a.state==='curious'?Math.sin(a.t*6)*.12:0;
 const earTarget=a.state==='curious'?.26:a.state==='scared'?-.28:(1-a.sq.x)*1.8-a.lean.x;
 spring(a.tail,-a.lean.x*2.2+(a.sq.x-1)*1.5+zoomWag,30,4,dt);
 spring(a.ear,earTarget,55,5,dt);
 const sy=a.sq.x,sx=1/Math.sqrt(Math.max(.4,sy));
 const shadow=contactShadow({lift:a.lift,sy});
 const raw={x:a.x,z:a.z,lift:a.lift,sx,sy,heading:a.heading,head:a.head.x,lean:a.lean.x,tail:a.tail.x,ear:a.ear.x,state:a.state,prevState:a.prevState||a.state,blend:a.blend??1,shadowScale:shadow.scale,shadowOpacity:shadow.opacity,grounded:shadow.grounded};
 const out=a.lastPose&&a.blend<1?blendPose(a.lastPose,raw,a.blend):raw;
 a.lastPose=raw;
 return out;
}
