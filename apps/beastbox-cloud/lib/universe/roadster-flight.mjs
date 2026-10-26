/**
 * Roadster flight · SIMULATED. Pure math for lifting the roadster off the Tiny World planet, climbing through its air into space,
 * exploring, and coming back. No clock, no Math.random, no DOM: time arrives as `dt`, input arrives as numbers.
 *
 * Honest scope, in plain words:
 *  - This is SCENE physics for the simulated tiny planet (radius PR = 8 world units). It is NOT a measurement and not Earth's numbers.
 *    The surface pull is a game-scale 6 u/s^2 so a climb takes seconds; gravity falls off as 1/r^2 like a real planet's.
 *  - The only limits are the physics of the scene: weight, thrust, and air drag that thins out with height (scale height ATMO.H).
 *    Nothing caps speed, distance or altitude. In vacuum there is no drag at all.
 *  - One continuous state: ground contact, climb, atmosphere and space are the same loop. There is no loading cut between them.
 */
export const FLIGHT_LABEL='Roadster flight · SIMULATED';
/** Scene constants (world units; 1 u is about 3.4 m of scene scale). */
export const FLIGHT=Object.freeze({
 R:8,                 // planet radius u (same as PR in living-world.tsx)
 g0:2,                // surface pull u/s^2 (scene-scale, falls as 1/r^2)
 thrust:4.8,          // max engine accel along the nose, u/s^2
 retro:3.2,            // max braking accel against velocity (airbrake + retro), u/s^2
 pitchRate:1.6, yawRate:1.4, rollRate:2.2, // rad/s at full input
 hullR:.12,           // contact radius of the hull above the ground, u
 landV:1.1,           // max touchdown speed that counts as a landing (u/s); faster is a skid, not damage
 maxStep:1/120,       // integrator sub-step (s)
});
/** Air: density 1 at the surface, falling exponentially. H is the scale height in u. Drag is 0 in vacuum. */
export const ATMO=Object.freeze({H:1.5,dragLin:.04,dragQuad:.03,levelRate:1.6});
const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]];const add=(a,b)=>[a[0]+b[0],a[1]+b[1],a[2]+b[2]];const mul=(a,k)=>[a[0]*k,a[1]*k,a[2]*k];
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
export const len=a=>Math.hypot(a[0],a[1],a[2]);
export const norm=a=>{const l=len(a);return l>1e-12?[a[0]/l,a[1]/l,a[2]/l]:[0,1,0];};
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
/** Rodrigues rotation of v about unit axis k by angle a. */
export function rot(v,k,a){const c=Math.cos(a),s=Math.sin(a),kv=dot(k,v);const kxv=cross(k,v);return [v[0]*c+kxv[0]*s+k[0]*kv*(1-c),v[1]*c+kxv[1]*s+k[1]*kv*(1-c),v[2]*c+kxv[2]*s+k[2]*kv*(1-c)];}
/** Re-orthonormalise a frame: fwd stays, up is made perpendicular to it. */
export function orthonormal(fwd,up){const f=norm(fwd);let u=sub(up,mul(f,dot(up,f)));if(len(u)<1e-9){u=Math.abs(f[1])<.9?[0,1,0]:[1,0,0];u=sub(u,mul(f,dot(u,f)));}return {fwd:f,up:norm(u)};}

/** Surface pull (u/s^2) at distance r from the centre: g0*(R/r)^2. */
export const gravityAt=(r,F=FLIGHT)=>F.g0*(F.R/Math.max(.05,r))**2;
/** Circular-orbit speed and escape speed at radius r: sqrt(mu/r) and sqrt(2 mu/r), mu = g0 R^2. */
export const circularSpeed=(r,F=FLIGHT)=>Math.sqrt(F.g0*F.R*F.R/Math.max(.05,r));
export const escapeSpeed=(r,F=FLIGHT)=>Math.sqrt(2*F.g0*F.R*F.R/Math.max(.05,r));
/** Air density (1 at the ground, ->0 with height). */
export const airDensity=(alt)=>alt<=0?1:Math.exp(-alt/ATMO.H);
/** Specific orbital energy (u^2/s^2). Negative = bound to the planet, >= 0 = escaping. */
export const orbitEnergy=(p,v,F=FLIGHT)=>.5*dot(v,v)-F.g0*F.R*F.R/Math.max(.05,len(p));
/** Fraction of the sky that is still "sky" (1 on the ground, 0 in space): drives background colour and star brightness. */
export const skyFade=(alt)=>clamp(airDensity(alt)*1.6-.05,0,1);

/**
 * Start a flight from the ground. p0 is the car's world position, n the surface normal, f its heading along the ground,
 * vGround the forward speed it already had (u/s). The nose lifts 35 degrees so the climb starts at once.
 */
export function liftOff(p0,n,f,vGround=0,F=FLIGHT){
 const up=norm(n);let fwd=norm(sub(f,mul(up,dot(f,up))));const lift=cross(fwd,up);// axis that tips the nose toward up
 const nose=rot(fwd,lift,.61);const fr=orthonormal(nose,up);
 return {p:[...p0],v:add(mul(fwd,Math.max(0,vGround)),mul(up,1.2)),fwd:fr.fwd,up:fr.up,t:0,landed:false,rolling:false,throttle:0};
}
/** Where the vehicle is relative to the planet: altitude over the hull-resting radius, speed, escape state. */
export function flightInfo(S,groundR=/** @type {number} */(FLIGHT.R),F=FLIGHT){
 const r=len(S.p),alt=r-groundR-F.hullR,sp=len(S.v),n=norm(S.p);const vr=dot(S.v,n);
 const E=orbitEnergy(S.p,S.v,F);
 return {r,alt,speed:sp,climb:vr,tangential:Math.sqrt(Math.max(0,sp*sp-vr*vr)),density:airDensity(alt),inSpace:airDensity(alt)<.05,energy:E,escaping:E>=0&&vr>0,
  circular:circularSpeed(r,F),escape:escapeSpeed(r,F),g:gravityAt(r,F)};
}
/**
 * Advance the flight by dt seconds. input: {thrust 0..1, brake 0..1, pitch -1..1 (+ = nose up), yaw -1..1 (+ = nose right), roll -1..1 (+ = bank right), level 0..1}.
 * groundAt(unitDir) -> ground radius in u at that direction (terrain height); defaults to the bare sphere.
 * Semi-implicit (leapfrog) sub-steps so a vacuum orbit keeps its energy. Mutates and returns S.
 */
export function stepFlight(S,input,dt,groundAt=/** @type {(n:number[])=>number} */(()=>FLIGHT.R),F=FLIGHT){
 let left=Math.max(0,Math.min(dt,.25));
 while(left>1e-9){const h=Math.min(left,F.maxStep);left-=h;one(S,input,h,groundAt,F);}
 return S;
}
function one(S,I,h,groundAt,F){
 const r=len(S.p),n=norm(S.p),gR=groundAt(n),alt=r-gR-F.hullR,rho=airDensity(alt);
 // attitude: pitch about the right axis, yaw about up, roll about the nose; the air gently levels the roll and the nose to the horizon
 const th=clamp(I.thrust||0,0,1),br=clamp(I.brake||0,0,1);S.throttle+=(th-S.throttle)*Math.min(1,h*6);
 let {fwd,up}=orthonormal(S.fwd,S.up);const tip=cross(fwd,up);// rotating about this tips the nose toward the roof
 const pi=clamp(I.pitch||0,-1,1)*F.pitchRate*h,yi=clamp(I.yaw||0,-1,1)*F.yawRate*h,ri=clamp(I.roll||0,-1,1)*F.rollRate*h;
 if(pi){fwd=rot(fwd,tip,pi);up=rot(up,tip,pi);}
 if(yi){fwd=rot(fwd,up,yi);}
 if(ri){up=rot(up,fwd,-ri);}
 const lvl=clamp(I.level??1,0,1)*ATMO.levelRate*rho*h;
 if(lvl>0){const want=orthonormal(fwd,n);const k=Math.min(1,lvl);up=norm(add(mul(up,1-k),mul(want.up,k)));}
 ({fwd,up}=orthonormal(fwd,up));S.fwd=fwd;S.up=up;
 // forces: pull toward the centre, engine along the nose, brake against velocity, drag only where there is air
 let a=mul(n,-gravityAt(r,F));
 a=add(a,mul(fwd,F.thrust*S.throttle));
 const sp=len(S.v);
 if(sp>1e-6&&br>0)a=add(a,mul(S.v,-br*Math.min(F.retro,sp/h*.5)/sp));
 if(rho>1e-4&&sp>1e-6)a=add(a,mul(S.v,-(ATMO.dragLin+ATMO.dragQuad*sp)*rho));
 // leapfrog: half kick, drift, half kick
 S.v=add(S.v,mul(a,h*.5));S.p=add(S.p,mul(S.v,h));
 const r2=len(S.p),n2=norm(S.p);let a2=mul(n2,-gravityAt(r2,F));a2=add(a2,mul(fwd,F.thrust*S.throttle));
 if(br>0&&sp>1e-6)a2=add(a2,mul(S.v,-br*Math.min(F.retro,len(S.v)/h*.5)/Math.max(1e-6,len(S.v))));
 const rho2=airDensity(r2-groundAt(n2)-F.hullR);const sp2=len(S.v);if(rho2>1e-4&&sp2>1e-6)a2=add(a2,mul(S.v,-(ATMO.dragLin+ATMO.dragQuad*sp2)*rho2));
 S.v=add(S.v,mul(a2,h*.5));S.t+=h;
 // ground contact: never inside the planet. A soft touchdown lands; a hard one skids (no damage, speed bleeds off)
 const g3=groundAt(n2),rest=g3+F.hullR;S.landed=false;
 if(r2<rest){S.p=mul(n2,rest);const vr=dot(S.v,n2);const vt=sub(S.v,mul(n2,vr));
  if(vr<0){S.touch=-vr;S.v=add(mul(n2,vr<-F.landV?-vr*.18:0),mul(vt,Math.max(0,1-4*h)));}else S.touch=0;
  S.landed=Math.abs(vr)<F.landV&&len(S.v)<F.landV*2.5;
 }
}
/** Autopilot for coming home ("Land"): returns an input for stepFlight. Burns retrograde to kill speed, then hovers down on a soft profile. */
export function landingAssist(S,groundR=/** @type {number} */(FLIGHT.R),F=FLIGHT){
 const n=norm(S.p),sp=len(S.v),alt=Math.max(0,len(S.p)-groundR-F.hullR),vr=dot(S.v,n);
 const aNet=Math.max(1,F.thrust*.85-gravityAt(len(S.p),F));
 const vSafe=Math.sqrt(2*aNet*Math.max(0,alt-.05))*.55+.5; // fastest descent we can still stop in time with margin
 const tangential=sub(S.v,mul(n,vr));const tsp=len(tangential);
 // desired nose: retrograde while moving fast, otherwise straight up so the engine holds us off the ground
 const wantRetro=(sp>2.5&&(alt>.4||tsp>1.2))||(tsp>1.2&&sp>.8)||(vr>.3&&alt>1.5);
 const want=wantRetro?norm(mul(S.v,-1)):n;
 const fwd=S.fwd,up=S.up,right=cross(up,fwd);
 const err=norm(want);const ep=dot(err,up),ey=dot(err,right),ef=dot(err,fwd);
 const pitch=clamp(ep*3,-1,1),yaw=ef<-.2&&Math.abs(ey)<.3?1:clamp(ey*3,-1,1);// dead behind us: pick a side and swing round
 const aligned=ef>.8;
 let thrust=0;
 if(aligned){
  if(wantRetro){ // burn when we are going faster than the profile allows, sideways, or still climbing away
   const over=(-vr)-vSafe;const E=orbitEnergy(S.p,S.v,F);
   thrust=Math.max(clamp(over/3,0,1),tsp>1.2?.8:0,vr>.3?1:0);
  }else{ // hover down: thrust cancels gravity, plus a little to follow the soft profile
   const hover=gravityAt(len(S.p),F)/F.thrust;thrust=clamp(hover+((-vr)-Math.min(vSafe,2))/4,0,1);
  }
 }
 return {thrust,brake:alt<.05?1:0,pitch,yaw,roll:0,level:1};
}

/** Orbit shape from the state: periapsis / apoapsis radii (u), Infinity apoapsis when the path is open. Pure. */
export function orbitElements(S,F=FLIGHT){
 const mu=F.g0*F.R*F.R,r=len(S.p),v2=dot(S.v,S.v);const E=.5*v2-mu/Math.max(.05,r);
 const h=cross(S.p,S.v),hh=len(h);const ev=sub(mul(cross(S.v,h),1/mu),mul(S.p,1/Math.max(.05,r)));const e=len(ev);
 if(hh<1e-9)return {e:1,peri:0,apo:r,bound:E<0};
 const a=E<0?-mu/(2*E):Infinity;
 return {e,peri:E<0?a*(1-e):hh*hh/(mu*(1+e)),apo:E<0?a*(1+e):Infinity,bound:E<0};
}
/** Autopilot for "Exit to orbit": a gravity turn. Phase 1 climbs and bends the nose to the horizon as the air thins until the high point (apoapsis) clears the air; the engine then cuts and the craft coasts up. Phase 2 burns along the flight path at the high point until the low point (periapsis) is also clear of the air: a bound orbit. Returns {thrust,brake,pitch,yaw,roll,level,done}. */
export function ascentAssist(S,groundR=/** @type {number} */(FLIGHT.R),F=FLIGHT){
 const r=len(S.p),n=norm(S.p),alt=Math.max(0,r-groundR-F.hullR);
 const vr=dot(S.v,n),tang=sub(S.v,mul(n,vr)),tsp=len(tang);
 const fwdT=norm(sub(S.fwd,mul(n,dot(S.fwd,n))));
 const heading=tsp>.4?norm(tang):fwdT;
 const el=orbitElements(S,F);
 const periGoal=groundR+ATMO.H*2.6,apoGoal=groundR+ATMO.H*3.2;
 const done=(el.bound&&el.peri>=periGoal&&r>groundR+ATMO.H*2)||(!el.bound&&alt>ATMO.H*3.5); // or already on a path out: you are free
 let want,burn=0;
 if(done){want=heading;}
 else if(!el.bound||el.apo<apoGoal){ // phase 1: climb and turn
  const th=(1-clamp(alt/(ATMO.H*3),0,1))*.95;want=norm(add(mul(heading,Math.cos(th)),mul(n,Math.sin(th))));burn=1;}
 else if(r>groundR+ATMO.H*2&&el.peri<periGoal){ // phase 2: circularise, prograde, at the high point
  want=norm(S.v);const nearApo=vr<.35*Math.max(.5,len(S.v))&&el.apo-r<ATMO.H*.8;burn=nearApo?1:0;if(!nearApo)want=norm(S.v);}
 else{want=norm(S.v);}
 const right=cross(S.up,S.fwd);const ep=dot(want,S.up),ey=dot(want,right),ef=dot(want,S.fwd);
 return {thrust:burn&&ef>.7?1:0,brake:0,pitch:clamp(ep*3,-1,1),yaw:ef<-.2&&Math.abs(ey)<.3?1:clamp(ey*3,-1,1),roll:0,level:1,done};
}
