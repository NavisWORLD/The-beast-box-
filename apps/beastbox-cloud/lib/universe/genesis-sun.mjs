// Sun, light and gravity ported from Cory's own CodePens, not re-invented.
//  - "Genesis Engine: The Definitive Core" (codepen azdBZzX, source sha256 67a1c104...): blackBodyToRGB, createStarCorona,
//    createStar (PointLight at the star), createAtmosphere (scatter shell lit by lightDir), updateInterSystemPhysics (G*m1*m2/r^2),
//    createPlanet orbitSpeed = sqrt(G*M/r).
//  - "GENESIS X v19.5 / NIGHT OPS" (codepen bNpXqmm, sha256 cdbdd829...): sun position drives day/night (nightFactor smoothstep).
// Local copies: lastforge/living-cosmos/physics/a.html and physics/z/untitled/src/index.html (hashes above are verified).
// Pure maths here (no three) so node tests can run it. Everything is deterministic: seeded phase, fixed time step.
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
// verbatim: Definitive Core blackBodyToRGB(temp) -> r,g,b in 0..1
export function blackBodyToRGB(temp){
  temp/=100;let r,g,b;
  if(temp<=66){r=255;g=99.47*Math.log(temp)-161.12;}else{r=329.7*Math.pow(temp-60,-0.133);}
  if(temp<=66){g=99.47*Math.log(temp)-161.12;b=temp<=19?0:138.52*Math.log(temp-10)-305.04;}else{g=288.12*Math.pow(temp-60,-0.0755);b=255;}
  return [clamp(r,0,255)/255,clamp(g,0,255)/255,clamp(b,0,255)/255];
}
// corona uniforms exactly as createStarCorona: tNorm=(temp-2000)/18000
export function coronaParams(temp){const tNorm=clamp((temp-2000)/18000,0,1);return{intensity:0.6+0.8*tNorm,noiseScale:1.5+2.5*tNorm};}
// Universe scale: stars and planets sit at orbitR(pl)=4+5*sqrt(orbit_au). The pens use G=5000 at their own scale; here G is set
// so a 1 solar-mass star holds its 1 AU planet (R=9) on the same 0.05 rad/s the universe view already used (Kepler's 3rd law then
// spaces every other orbit). Star mass follows the pens (size*1000) with size = mass_solar.
export const STAR_MASS_PER_SOLAR=1000;
export const G_UNIVERSE=(0.05*0.05)*Math.pow(9,3)/STAR_MASS_PER_SOLAR;
export const orbitR=(au)=>4+5*Math.sqrt(au);
export const starMass=(st)=>st.mass_solar*STAR_MASS_PER_SOLAR;
// real mass ratio, not the pens' arbitrary size*100: an Earth is ~3e-6 of a Sun and mass grows steeply with radius
export const planetMass=(pl)=>0.003*Math.pow(pl.radius_earth,3);
// orbitSpeed = sqrt(G*M/distance), as in createPlanet
export const orbitSpeed=(G,M,d)=>Math.sqrt(G*M/d);
// point light: the pens use PointLight(color,2,20000,2): inverse-square decay. Calibrated so a planet at 1 AU (R=9) gets 2.2 like before;
// recorded luminosity (solar units) is exposure-compressed (log) because a raw 3000x star would white-out its inner worlds.
export function sunIntensity(lum){return 2.2*81*clamp(0.5+0.25*Math.log10(1+Math.max(0,lum)),0.5,2);}
// GENESIS X v19.5: nightFactor = smoothstep(.1,-.2,sunY) on the ground; the globe in living-world uses 1-smoothstep(-.1,.25,dot(n,sun)).
export const nightFactor=(dotNSun)=>{const x=clamp((dotNSun+0.1)/0.35,0,1);return 1-x*x*(3-2*x);};
// bodies of one star system: star {m}, planets [{id,m,p:[x,y,z],v:[vx,vy,vz]}] ; centred on the star at the origin
export function initSystem(star,planets){
  const M=starMass(star);
  return{M,planets:planets.map(pl=>{const R=orbitR(pl.orbit_au),a=pl.phase*Math.PI*2,sp=orbitSpeed(G_UNIVERSE,M,R);
    return{id:pl.id,m:planetMass(pl),p:[Math.cos(a)*R,0,Math.sin(a)*R],v:[-Math.sin(a)*sp,0,Math.cos(a)*sp]};})};
}
// updateInterSystemPhysics: a = sum G*m_other/d^2 toward each other body (the pen's force/m), then v+=a*dt, p+=v*dt.
// Star is fixed at the origin (it is ~1000x heavier; the pens let it drift). Semi-implicit Euler like the pens, fixed dt.
export function stepSystem(sys,dt){
  const ps=sys.planets,acc=ps.map(()=>[0,0,0]);
  for(let i=0;i<ps.length;i++){const a=acc[i];
    {const d=Math.hypot(...ps[i].p),d2=d*d;if(d2>1){const f=G_UNIVERSE*sys.M/d2/d;a[0]-=ps[i].p[0]*f;a[1]-=ps[i].p[1]*f;a[2]-=ps[i].p[2]*f;}}
    for(let j=0;j<ps.length;j++){if(i===j)continue;const dx=ps[j].p[0]-ps[i].p[0],dy=ps[j].p[1]-ps[i].p[1],dz=ps[j].p[2]-ps[i].p[2],d2=dx*dx+dy*dy+dz*dz;
      if(d2>1){const f=G_UNIVERSE*ps[j].m/d2/Math.sqrt(d2);a[0]+=dx*f;a[1]+=dy*f;a[2]+=dz*f;}}}
  for(let i=0;i<ps.length;i++){for(let k=0;k<3;k++)ps[i].v[k]+=acc[i][k]*dt;for(let k=0;k<3;k++)ps[i].p[k]+=ps[i].v[k]*dt;}
}
export const FIXED_DT=1/120;
// advance to simulated time t using fixed steps; returns steps taken (capped so a long tab sleep cannot stall a frame)
export function advanceTo(sys,state,t,maxSteps=240){
  let n=0;while(state.t+FIXED_DT<=t&&n<maxSteps){stepSystem(sys,FIXED_DT);state.t+=FIXED_DT;n++;}
  if(n===maxSteps)state.t=t;return n;
}

// ---- ENGINE-OWNED SUN (Oct 24 2026, "the engine carries the sky"). Additive: nothing above changes.
// One day = DAY_LENGTH_TICKS engine ticks. world-field stepped at 4 Hz, so 960 ticks = the 240 s day the living-world view has always used.
// sunDirAt(angle) is the SAME geometry the view has used (x=cos a, y=.35 sin(a/2+1), z=sin a, normalised) so the engine value can be proven equal
// to the view's path by test before any view reads it. sunFromElevation is a verbatim port of Cory's pen "updateSunPosition" (three.js
// setFromSphericalCoords(1, phi, theta); source: /workspace/specs/sky/pen_b.html sha256 54f58cbedb0d002c5cc62d908a810446ee0142c303a443a80e2aaab135ced694).
export const DAY_LENGTH_TICKS=960;
export function sunDirAt(angle){const x=Math.cos(angle),y=0.35*Math.sin(angle*0.5+1),z=Math.sin(angle);const l=Math.hypot(x,y,z)||1;return [x/l,y/l,z/l];}
export function sunFromElevation(elevDeg,azimuthDeg=180){const phi=(90-elevDeg)*Math.PI/180,theta=azimuthDeg*Math.PI/180;const sp=Math.sin(phi);return [sp*Math.sin(theta),Math.cos(phi),sp*Math.cos(theta)];}
