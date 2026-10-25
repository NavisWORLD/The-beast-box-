/**
 * CST INTEGRATOR: the one deterministic physics core for every moving thing in Beast Box.
 *
 * Ported from Cory Davis's 12-Dimensional Cosmic Synapse Theory engine
 * (NavisWORLD/Cosmic-synapse-the-living-universe-sim-engine-, CSTClosedLoop in
 * standalone/SIM_EARTH_7_08_REALITY_BODY.html and research/cst-closed-loop/sim.mjs):
 *  - Lorenz step  dx=σ(y−x), dy=x(ρ−z)−y, dz=xy−βz, ρ modulated by arousal (GAIN.lorenzRho)
 *    and x forced by quantum_entropy (GAIN.lorenzQ), explicit Euler like the original.
 *  - Coherence feedback from the previous Hebbian strength (GAIN.hebbCoh).
 *  - creatureMood(): joy / curiosity / fear / calm / mischief from the state.
 * "D" here means state-channel count (Cory's own docs say so), all channels clamped to [0,1].
 * These channels only shape cosmetic motion (stiffness, wind, damping, turbulence, phase).
 *
 * Pure: no DOM, clock or network. Same seed + same inputs → identical trajectories.
 */
import {psiNudge,PSI_GAIN} from './cst-psi.mjs';
export const PHI=(1+Math.sqrt(5))/2;
export const GOLDEN_ANGLE=Math.PI*2*(1-1/PHI);
/** Same coupling gains as CSTClosedLoop.GAIN. */
export const CST_GAIN=Object.freeze({lorenzRho:.30,lorenzQ:2.0,hebbCoh:.20,bio:.004,storm:.02,hebbBio:.5,bell:.01});
export const LORENZ=Object.freeze({sigma:10,rho:28,beta:8/3});
export const CST12=Object.freeze(['frequency_mass','geometric_phase','spectral_flatness','phase_velocity','entanglement',
 'valence','arousal','dominance','audio_psi','phi_harmonics','av_coherence','quantum_entropy']);
export const clamp=(x,a=0,b=1)=>x<a?a:x>b?b:x;
/** The dt clamp every Beast Box integrator already used (50 ms max, never negative). */
export const clampDt=(dt,max=.05)=>Math.min(max,Math.max(0,Number(dt)||0));

// ---------------------------------------------------------------- one shared PRNG
/** FNV-1a 32-bit hash (same bits as the old film-motion fnv / pocket-sand hash). */
export function fnv1a(str){let h=0x811c9dc5;for(const ch of String(str)){h^=ch.charCodeAt(0);h=Math.imul(h,0x01000193)>>>0;}return h>>>0;}
/** xorshift32 seeded by FNV-1a(seed). Bit-identical to the previous film-motion prng() and pocket-sand rngFrom(). */
export function seededRng(seed){let a=fnv1a(seed)||1;return()=>{a^=a<<13;a>>>=0;a^=a>>>17;a^=a<<5;a>>>=0;return a/4294967296;};}

// ---------------------------------------------------------------- fixed-step clock
/**
 * Fixed-step accumulator clock. tick(frameDt, step) calls step(h, t) n times with a constant h,
 * so motion is frame-rate independent and replayable. maxSubsteps guards against spirals.
 */
export function createCSTClock({seed='cst',hz=120,maxSubsteps=8,maxFrame=.1}={}){
 const h=1/hz;
 const c={seed:String(seed),h,t:0,steps:0,acc:0,rng:seededRng('clock:'+seed),alpha:0,
  tick(frameDt,step){
   c.acc+=clampDt(frameDt,maxFrame);let n=0;
   while(c.acc>=h&&n<maxSubsteps){step&&step(h,c.t);c.t+=h;c.acc-=h;c.steps++;n++;}
   if(n===maxSubsteps&&c.acc>h)c.acc=0;
   c.alpha=c.acc/h;return n;
  }};
 return c;
}

// ---------------------------------------------------------------- CST state + Lorenz
/** Lorenz step (CSTClosedLoop.lorenzStep port). L={x,y,z} mutated. */
export function lorenzStep(L,dt,{arousal=.5,qe=.5}={}){
 const {sigma,beta}=LORENZ,rho=LORENZ.rho*(1+CST_GAIN.lorenzRho*(clamp(arousal)-.5));
 const dx=sigma*(L.y-L.x)+CST_GAIN.lorenzQ*(clamp(qe)-.5),dy=L.x*(rho-L.z)-L.y,dz=L.x*L.y-beta*L.z;
 L.x+=dx*dt;L.y+=dy*dt;L.z+=dz*dt;
 // keep bounded (the attractor stays near |x|,|y|<25, z<50); NaN guard
 if(!Number.isFinite(L.x+L.y+L.z)){L.x=.1;L.y=.2;L.z=.3;}
 return L;
}
/** CSTClosedLoop.coherenceFeedback port. */
export const coherenceFeedback=(coh,hebbPrev)=>clamp(coh+CST_GAIN.hebbCoh*(clamp(hebbPrev)-.25));
/** CSTClosedLoop.creatureMood port, on a named-channel state. */
export function creatureMood(s){
 return {joy:clamp(s.resonance*.6+s.coherence*.4),curiosity:clamp(s.curiosity),fear:clamp(s.avoid),
  calm:clamp(1-s.instability),mischief:clamp(s.chaos*.6+s.curiosity*.4)};
}
/**
 * Build a creature's CST state from its seed + (optional) emotion {valence,arousal,...} and
 * (optional) own recorded counts. Without counts quantum_entropy is a seeded constant: never invented as "measured".
 */
export function createCSTState(seed,{emotion={},counts=null}={}){
 const r=seededRng('cst:'+seed);
 let qe=.3+r()*.4;
 if(counts&&typeof counts==='object'){const v=Object.values(counts).filter(n=>n>0),t=v.reduce((a,b)=>a+b,0);
  if(t&&v.length>1)qe=-v.reduce((s,n)=>s+(n/t)*Math.log2(n/t),0)/Math.log2(v.length);}
 return {seed:String(seed),L:{x:.1+r()*.2,y:.2+r()*.2,z:.3+r()*.2},hebb:.25+r()*.2,phase:r()*Math.PI*2,
  ch:{valence:clamp(emotion.valence??.6),arousal:clamp(emotion.arousal??.4),dominance:clamp(emotion.dominance??.5),
   quantum_entropy:clamp(qe),phi_harmonics:.6,coherence:.6,chaos:.2,instability:.2,curiosity:clamp(emotion.curiosity??.5),
   resonance:.5,avoid:clamp(emotion.fear??.1)}};
}
// ---------------------------------------------------------------- optional outer-product Hebbian rule (MODEL)
/**
 * Opt-in true outer-product Hebbian rule over 12 channels (the 11 named CST channels + Lorenz x, each in [0,1]):
 *    w_ij ← clamp( w_ij + dt·(η·pre_i·post_j − decay·w_ij), 0, wMax )
 * pre = the channel vector at the end of the previous step, post = the vector after this step. The fixed point is
 * w* = (η/decay)·pre·post, so with η=decay the weights track the running channel outer product and stay inside [0,wMax].
 * It is the "fire together, wire together" rule written as an actual matrix. The ORIGINAL rule (S.hebb relaxing toward
 * coherence·0.6+valence·0.2) is untouched and stays the default; with the flag on it still runs, and S.hebb is
 * additionally pulled toward mean(W) at rate `pull` per second (that pull is the only way W reaches the dynamics).
 * Rates are per model-second (dt is seconds). LABEL: MODEL: a hypothesis about how weights could form, not a measurement.
 */
export const HEBB_OUTER=Object.freeze({eta:.5,decay:.5,wMax:1,pull:.10});
export const HEBB12=Object.freeze(['valence','arousal','dominance','quantum_entropy','phi_harmonics','coherence','chaos','instability','curiosity','resonance','avoid','lorenz_x']);
/** The 12-vector the outer-product rule works on (all clamped to [0,1]). */
export function hebbVector(S){const c=S.ch,v=[];for(const k of HEBB12)v.push(k==='lorenz_x'?clamp(.5+S.L.x/40):clamp(c[k]));return v;}
/** Mean of W in [0,wMax]: the scalar the pull uses (and a readout for diagnostics). */
export function outerHebbStrength(S){if(!S.W)return 0;let t=0;for(let i=0;i<S.W.length;i++)t+=S.W[i];return t/S.W.length;}
function outerHebbUpdate(S,dt,o){
 const eta=Number.isFinite(o.eta)?o.eta:HEBB_OUTER.eta,decay=Number.isFinite(o.decay)?o.decay:HEBB_OUTER.decay,
  wMax=Number.isFinite(o.wMax)?o.wMax:HEBB_OUTER.wMax,pull=Number.isFinite(o.pull)?o.pull:HEBB_OUTER.pull,n=HEBB12.length;
 const post=hebbVector(S),pre=S.Wpre||post;
 if(!S.W)S.W=new Array(n*n).fill(0);
 for(let i=0;i<n;i++)for(let j=0;j<n;j++){const k=i*n+j,w=S.W[k]+dt*(eta*pre[i]*post[j]-decay*S.W[k]);S.W[k]=w<0?0:w>wMax?wMax:w;}
 S.Wpre=post;
 S.hebb=clamp(S.hebb+(clamp(outerHebbStrength(S)/(wMax||1))-S.hebb)*Math.min(1,dt*pull));
}
/**
 * Advance the state one fixed step: Lorenz, chaos/instability, coherence, Hebbian.
 *
 * DEFAULT (opts omitted/null) is the original behavior, bit for bit. Optional MODEL extensions, each off unless asked:
 *  - opts.outerHebb:true|{eta,decay,wMax,pull}  true outer-product Hebbian rule on 12 channels (see HEBB_OUTER below).
 *  - opts.psi:true|{gain}  CST ψ (cst-psi.mjs, MODEL) nudges the coherence AND Hebbian targets by gain·(ψn−½),
 *    gain default PSI_GAIN=0.10, so the shift is bounded to ±gain/2 (±0.05) before the usual clamp.
 *
 * Lorenz dt NOTE (documented honestly, not hidden): this port integrates the Lorenz system at dt·0.35 per call, while the
 * Sim Earth reference engine (standalone/SIM_EARTH_7_08_REALITY_BODY.html) uses dt·0.035: ten times slower. Both are
 * explicit Euler with the same σ, ρ, β. Beast Box runs at ≤50 ms steps, so 0.35 gives a livelier wind/turbulence for
 * cosmetic motion; the .35 is a visual-tempo choice made here, it is not a calibrated or measured match to Sim Earth.
 */
export function stepCSTState(S,dt,emotion=null,opts=null){
 const c=S.ch;
 if(emotion){for(const [k,src] of [['valence','valence'],['arousal','arousal'],['curiosity','curiosity'],['avoid','fear']])
  if(Number.isFinite(emotion[src]))c[k]+=(clamp(emotion[src])-c[k])*Math.min(1,dt*3);}
 lorenzStep(S.L,dt*.35,{arousal:c.arousal,qe:c.quantum_entropy});
 const lx=clamp(.5+S.L.x/40),ly=clamp(.5+S.L.y/50);
 c.chaos+=(clamp(Math.abs(lx-.5)*1.4+Math.abs(ly-.5)*.6)-c.chaos)*Math.min(1,dt*2);
 c.instability+=(clamp(c.chaos*.5+c.avoid*.4+c.arousal*.2)-c.instability)*Math.min(1,dt*2);
 const psiN=opts&&opts.psi?psiNudge(c,typeof opts.psi==='object'&&Number.isFinite(opts.psi.gain)?opts.psi.gain:PSI_GAIN):0; // MODEL, bounded, 0 by default
 let coh=coherenceFeedback(clamp((1-c.instability)*.5+c.valence*.3+c.phi_harmonics*.2),S.hebb);
 if(psiN)coh=clamp(coh+psiN);
 c.coherence+=(coh-c.coherence)*Math.min(1,dt*2);
 S.hebb+=(clamp(c.coherence*.6+c.valence*.2+psiN)-S.hebb)*dt*.05;
 c.resonance+=(clamp(c.coherence*.7+c.valence*.3)-c.resonance)*Math.min(1,dt);
 S.phase+=dt*(1+c.arousal);
 if(opts&&opts.outerHebb)outerHebbUpdate(S,dt,typeof opts.outerHebb==='object'?opts.outerHebb:{});
 return S;
}
/**
 * CST → motion parameters. The mapping Cory asked for:
 *  arousal → stiffness, Lorenz → wind, coherence → damping, chaos → turbulence, phi → phase.
 */
export function motionParams(S){
 const c=S.ch,s=Math.hypot(S.L.x,S.L.y,S.L.z)||1;
 return {
  stiffness:.6+c.arousal*1.2,            // spring k multiplier
  damping:.55+c.coherence*.9,            // damping multiplier: coherent = smooth
  turbulence:c.chaos*.9+c.instability*.3, // noise amplitude
  wind:{x:S.L.x/s*(.2+c.chaos),y:(S.L.z/s-.6)*.3,z:S.L.y/s*(.2+c.chaos)},
  phaseStep:GOLDEN_ANGLE*(.5+c.phi_harmonics*.5), // per-bone phase offset
  phase:S.phase,
  mood:creatureMood(c),
 };
}

// ---------------------------------------------------------------- solvers
/** Semi-implicit (symplectic) Euler damped spring on {x,v}. Same formula film-motion used. */
export function springStep(s,target,k,d,dt){const a=(target-s.x)*k-s.v*d;s.v+=a*dt;s.x+=s.v*dt;return s.x;}
/** Vector damped spring on Float arrays/objects with x,y,z. */
export function springStep3(p,v,target,k,d,dt){
 for(const ax of ['x','y','z']){const a=(target[ax]-p[ax])*k-v[ax]*d;v[ax]+=a*dt;p[ax]+=v[ax]*dt;}return p;
}
/** Per-step drag+damp factor used by pocket-sand (Genesis Engine: 0.99/frame drag, (1-0.1dt) damp). */
export const genesisDrag=d=>Math.pow(.99,d*60)*(1-.1*d);
/** Verlet point: {x,y,z,px,py,pz,w} (w = inverse mass, 0 = pinned). */
export function verletPoint(x=0,y=0,z=0,w=1){return {x,y,z,px:x,py:y,pz:z,w};}
/** Position Verlet with velocity damping and an acceleration vector. */
export function verletIntegrate(points,dt,{acc={x:0,y:0,z:0},damping=.02}={}){
 const keep=1-damping,dt2=dt*dt;
 for(const p of points){if(!p.w)continue;
  const vx=(p.x-p.px)*keep,vy=(p.y-p.py)*keep,vz=(p.z-p.pz)*keep;
  p.px=p.x;p.py=p.y;p.pz=p.z;p.x+=vx+acc.x*dt2;p.y+=vy+acc.y*dt2;p.z+=vz+acc.z*dt2;}
 return points;
}
/** Distance constraint, XPBD style (compliance 0 = rigid). lambda kept on the constraint. */
export function solveDistance(a,b,rest,{compliance=0,dt=1/120}={}){
 const dx=b.x-a.x,dy=b.y-a.y,dz=b.z-a.z,len=Math.hypot(dx,dy,dz);const w=a.w+b.w;
 if(len<1e-9||w<=0)return 0;
 const C=len-rest,alpha=compliance/(dt*dt),dl=-C/(w+alpha);
 const nx=dx/len,ny=dy/len,nz=dz/len;
 a.x-=nx*dl*a.w;a.y-=ny*dl*a.w;a.z-=nz*dl*a.w;b.x+=nx*dl*b.w;b.y+=ny*dl*b.w;b.z+=nz*dl*b.w;
 return C;
}
/** Keep a point outside a sphere collider {x,y,z,r}. */
export function solveSphereCollision(p,s){const dx=p.x-s.x,dy=p.y-s.y,dz=p.z-s.z,l=Math.hypot(dx,dy,dz);
 if(l<s.r&&l>1e-9){const k=s.r/l;p.x=s.x+dx*k;p.y=s.y+dy*k;p.z=s.z+dz*k;return true;}return false;}
/** Cheap deterministic 3D value-noise turbulence, seeded. */
export function turbulence3(x,y,z,t,seed=0){
 const s=(seed%997)*.013;
 return {x:Math.sin(y*1.7+t*1.3+s)+Math.sin(z*2.3-t*.7)*.5,
  y:Math.sin(z*1.9+t*1.1+s*2)+Math.sin(x*2.1+t*.5)*.5,
  z:Math.sin(x*1.5-t*1.2+s*3)+Math.sin(y*2.7+t*.9)*.5};
}
