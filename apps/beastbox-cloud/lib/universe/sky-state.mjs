// "The engine carries the sky", PR 4: the sky and light as a pure function of engine state.
// skyAt({sunDir, sunElev, atmosphere, starTempK, booms, bodies, ...}) -> gradient, nightFactor, twilight band, star visibility,
// boom glows and the lighting rig. Derived visuals only: nothing here is stored back into the engine's JSON.
// Engine numbers win. Constants (SKY) are only where the engine has no number (Cosmo's engine_sky_palette v1 stand-ins, SEEDED look values).
// PORTED, with sources:
//  - terminatorWeight / twilightBand / moonPhaseDiffuse: planet-glsl (generated from Cosmo's planets pack glsl/terminator.glsl and
//    glsl/phase_moon.glsl). The JS here is the same arithmetic, so orbit and first-person read ONE function. tests/sky-state.test.mjs
//    re-reads the generated planet-glsl.ts and fails if the GLSL text or the constants change.
//  - nightFactor: GENESIS X v19.5 / NIGHT OPS (codepen bNpXqmm, index.html sha256 cdbdd829261121544e7ab3bd9bae3707abc29daef7c84022f5d48dccd485e785)
//    `nightFactor = smoothstep(0.1,-0.2,sunY)`; on a planet the same smoothstep is taken at the per-planet terminator edges (-w, 1.6w).
import {blackBodyToRGB} from './genesis-sun.mjs';
import {starVisual} from './star-visual.mjs';
import {boomState,boomSkyTerm} from './boom.mjs';
export const NIGHT_OPS_SHA256='cdbdd829261121544e7ab3bd9bae3707abc29daef7c84022f5d48dccd485e785';
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
const ss=(a,b,x)=>{const t=clamp((x-a)/(b-a),0,1);return t*t*(3-2*t);};
const lerp=(a,b,t)=>a+(b-a)*t;
const mixv=(a,b,t)=>a.map((x,i)=>lerp(x,b[i],t));
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const norm=v=>{const l=Math.hypot(v[0],v[1],v[2])||1;return [v[0]/l,v[1]/l,v[2]/l];};
export const SKY=Object.freeze({
  // atmosphere amounts of the reference types in planet-shading (moon 0, desert .55, temperate .85) = thin / mid / thick
  knots:[0,0.55,0.85],
  nightZenith:[0.0085,0.0085,0.02],nightHorizonLift:[0,0.75,1],nightHorizonSkyK:0.018,
  dayZenithK:0.8,dayHorizonWhiteMix:0.38,duskGold:[1,0.62,0.25],duskGoldMix:0.45,duskZenithTwilightTint:0.08,
  starTintMix:0.35,refStarK:5800,
  starVis:{thin:[0,0],mid:[0.2,0.75],thick:[0.35,0.9]},brightnessLead:0.15,weber:0.02,
  moonLit:[0.84,0.82,0.88],moonDark:[0.027,0.024,0.036],earthshine:0.035,moonStarWhiteMix:0.35,
  boomGlowDeg:{flash:[9,7,5.5,4.5,3.5],shell:[3.2,3,2.6,2,1.5],fade:[1.4,1.2,1,0.8,0.6],remnant:[0.3,0.3,0.28,0.26,0.25]},
  boomDayHorizonPull:0.55,boomAmbientK:0.10,boomAmbientCap:0.25,boomGlowCap:1,
  nightAmbient:0.125,defaultSky:[0.3,0.52,1],defaultTwilight:[1,0.52,0.42],
});
/** piecewise-linear over the three atmosphere knots (thin, mid, thick); flat beyond the last. */
export function byAtmo(atmo,thin,mid,thick){const a=clamp(+atmo||0,0,1),k=SKY.knots;if(a<=k[1])return lerp(thin,mid,a/k[1]);if(a<=k[2])return lerp(mid,thick,(a-k[1])/(k[2]-k[1]));return thick;}
/** planet-glsl: width = mix(0.015, 0.12, uAtmo) */
export const terminatorWidth=(atmo)=>lerp(0.015,0.12,clamp(+atmo||0,0,1));
/** planet-glsl terminatorWeight(N,L,width) = smoothstep(-width, width*1.6, dot(N,L)); `elev` = dot(up, sunDir) = sin(sun elevation). */
export const terminatorWeight=(elev,width)=>ss(-width,width*1.6,elev);
/** nightFactor on a planet = 1 - terminatorWeight: the sky, the globe and the lamps share the terminator edges. 1 at/below -w, 0 at/above 1.6w. */
export const skyNightFactor=(elev,width)=>1-terminatorWeight(elev,width);
/** planet-glsl twilightBand(N,L,width,twilightColor,strength) = twilightColor * exp(-x*x) * strength, x = dot(N,L)/(width*1.4+1e-4). */
export function twilightBandAt(elev,width,color,strength){const x=elev/(width*1.4+1e-4);return color.map(c=>c*Math.exp(-x*x)*strength);}
/** the band weight alone (twilightBand with a white colour and strength 1) */
export const twilightWeight=(elev,width)=>{const x=elev/(width*1.4+1e-4);return Math.exp(-x*x);};
/** planet-glsl moonPhaseDiffuse (Lommel-Seeliger with opposition surge): N surface normal, L moon->sun, V moon->observer. */
export function moonPhaseDiffuse(N,L,V){
  const ndl=Math.max(dot(N,L),0),ndv=Math.max(dot(N,V),0);const ls=2*ndl/(ndl+ndv+1e-3);
  const cosA=clamp(dot(L,V),-1,1);const surge=1+0.45*Math.exp(-Math.acos(cosA)/0.10);return ls*surge*(ndl>0?1:0);
}
/** the ONE moon phase, used at orbit and in the first-person sky. sunDir = unit planet->sun; toMoon = unit observer->moon (far-sun approximation: L = sunDir).
 *  Returns the lit fraction of the disc, the phase angle and the mean disc brightness (moonPhaseDiffuse averaged over the visible hemisphere, 12x12 deterministic samples). */
export function moonPhase(sunDir,toMoon){
  const L=norm(sunDir),V=norm(toMoon).map(x=>-x);const cosA=clamp(dot(L,V),-1,1);
  // basis on the disc seen from the observer (view axis = V)
  const ref=Math.abs(V[1])<0.9?[0,1,0]:[1,0,0];const ex=norm([V[1]*ref[2]-V[2]*ref[1],V[2]*ref[0]-V[0]*ref[2],V[0]*ref[1]-V[1]*ref[0]]);const ey=[V[1]*ex[2]-V[2]*ex[1],V[2]*ex[0]-V[0]*ex[2],V[0]*ex[1]-V[1]*ex[0]];
  let sum=0,n=0;for(let i=0;i<12;i++)for(let j=0;j<12;j++){const x=(i+0.5)/6-1,y=(j+0.5)/6-1,r2=x*x+y*y;if(r2>1)continue;const z=Math.sqrt(1-r2);const N=[ex[0]*x+ey[0]*y+V[0]*z,ex[1]*x+ey[1]*y+V[1]*z,ex[2]*x+ey[2]*y+V[2]*z];sum+=moonPhaseDiffuse(N,L,V);n++;}
  return {litFraction:(1+cosA)/2,phaseAngle:Math.acos(cosA),brightness:n?sum/n:0};
}
/** star visibility alpha: the brightest stars come out first; airless worlds always see them. */
export function starAlpha(nf,brightness01,atmo){
  const lo=byAtmo(atmo,SKY.starVis.thin[0],SKY.starVis.mid[0],SKY.starVis.thick[0]),hi=byAtmo(atmo,SKY.starVis.thin[1],SKY.starVis.mid[1],SKY.starVis.thick[1]);
  if(hi===0&&lo===0||(+atmo||0)<=0.02)return 1;const lead=SKY.brightnessLead*clamp(brightness01,0,1);return ss(lo-lead,hi-lead,nf);
}
/** Weber hint: a star is drawn only if its linear peak is at least 2% of the sky luminance behind it. */
export const weberVisible=(starPeak,skyLum)=>starPeak>=SKY.weber*skyLum;
const lum=c=>0.2126*c[0]+0.7152*c[1]+0.0722*c[2];
const starNorm=T=>{const c=blackBodyToRGB(T||SKY.refStarK),r=blackBodyToRGB(SKY.refStarK);const m=c.map((x,i)=>x/Math.max(1e-6,r[i]));const mx=Math.max(...m);return m.map(x=>x/mx);};
const stops=(arr,t)=>{const f=clamp(t,0,1)*(arr.length-1),i=Math.min(arr.length-2,Math.floor(f));return lerp(arr[i],arr[i+1],f-i);};
const localT=(phase,u)=>{const e={flash:[0,0.02],shell:[0.02,0.45],fade:[0.45,0.80],remnant:[0.80,1]}[phase];return e?clamp((u-e[0])/(e[1]-e[0]),0,1):0;};
/** skyAt: everything the first-person sky and the lighting rig need, from engine state alone.
 *  in: {sunDir, sunElev?, up?=[0,1,0], atmosphere, starTempK, skyColor?, twilightColor?, star?, channels?, tick?, booms?:[{star,eventTick,distance,dir}], bodies?:[{id,kind:'moon'|'partner'|'neighbor'|'star',dir,star?,distance?,radius?}]}
 *  out: {width, sunElev, nightFactor, dayWeight, zenith, horizon, twilight:{weight,color}, starAlpha(b), booms[], boomAmbient, bodies[], rig} (all linear light) */
export function skyAt(inp){
  const atmo=clamp(+inp.atmosphere||0,0,1),up=inp.up||[0,1,0],sunDir=norm(inp.sunDir||[0,1,0]);
  const elev=Number.isFinite(inp.sunElev)?inp.sunElev:dot(up,sunDir);const w=terminatorWidth(atmo);
  const nf=skyNightFactor(elev,w),day=1-nf;const skyC=inp.skyColor||SKY.defaultSky,twC=inp.twilightColor||SKY.defaultTwilight;
  const sTint=starNorm(inp.starTempK);const tint=mixv([1,1,1],sTint,SKY.starTintMix);
  const lift=byAtmo(atmo,...SKY.nightHorizonLift);
  const nightH=SKY.nightZenith.map((c,i)=>c+skyC[i]*SKY.nightHorizonSkyK*lift);
  let dayZ=skyC.map((c,i)=>c*SKY.dayZenithK*tint[i]);let dayH=mixv(dayZ,[1,1,1],SKY.dayHorizonWhiteMix).map((c,i)=>c*(0.5+0.5*tint[i]));
  // airless: no scattering, the sky stays the night colour in daylight
  const sc=byAtmo(atmo,0,0.75,1);dayZ=mixv(SKY.nightZenith,dayZ,sc);dayH=mixv(SKY.nightZenith,dayH,sc);
  let zenith=mixv(SKY.nightZenith,dayZ,day),horizon=mixv(nightH,dayH,day);
  const tw=twilightWeight(elev,w)*atmo;const gold=SKY.duskGold.map((c,i)=>c*tint[i]);
  horizon=mixv(horizon,gold,SKY.duskGoldMix*tw);zenith=mixv(zenith,twC,SKY.duskZenithTwilightTint*tw);
  const twilight={weight:tw,color:twilightBandAt(elev,w,twC,atmo)};
  // booms: a glow at the bearing, pale by day, plus rig ambient for planets in range
  const booms=[];let amb=0;const ambC=[0,0,0];
  for(const b of inp.booms||[]){
    const st=boomState(b.star,b.eventTick,inp.tick||0);if(st.phase==='none')continue;
    const strength=Math.min(SKY.boomGlowCap,boomSkyTerm(b.star,b.eventTick,inp.tick||0,b.distance,day));
    if(!(strength>0))continue;
    const color=mixv(st.colorRGB,horizon.map(c=>c/Math.max(1e-6,Math.max(...horizon))),SKY.boomDayHorizonPull*day);
    const rad=stops(SKY.boomGlowDeg[st.phase],localT(st.phase,st.u));
    booms.push({star:b.star.id,dir:b.dir?norm(b.dir):null,phase:st.phase,strength,color,radiusDeg:rad,rays:st.phase==='flash'?{count:8,lengthMul:3,alpha:0.55}:null,label:st.label});
    const a=Math.min(SKY.boomAmbientCap,SKY.boomAmbientK*strength);for(let i=0;i<3;i++)ambC[i]+=color[i]*a;amb+=a;
  }
  const bodies=[];
  for(const b of inp.bodies||[]){
    const d=norm(b.dir),e=dot(up,d);const o={id:b.id,kind:b.kind,dir:d,elev:e,aboveHorizon:e>0};
    if(b.kind==='moon'){const p=moonPhase(sunDir,d);o.phase=p;const hr=byAtmo(atmo,0,0.75,1);o.horizonRedden=clamp(1-e/0.4,0,1)*hr;o.visible=o.aboveHorizon;
      o.lightMix=SKY.moonStarWhiteMix;o.halo=0.1*nf;}
    else if(b.kind==='partner'){o.visible=o.aboveHorizon;}
    else if(b.kind==='neighbor'||b.kind==='star'){const v=b.star?starVisual(b.star,inp.channels||{},b.distance):null;o.visual=v;
      const bright=v?clamp(v.brightness,0,1):0.5;o.alpha=b.kind==='star'?1:starAlpha(nf,bright,atmo);
      if(b.kind==='neighbor'&&v)o.alpha=weberVisible(bright*v.pulse*0.1,lum(horizon))?o.alpha:0;o.visible=o.aboveHorizon&&o.alpha>0;}
    bodies.push(o);
  }
  const sunWeight=terminatorWeight(elev,w);
  const rig={sunWeight,hemiSky:zenith,hemiGround:horizon.map(c=>c*0.35),
    ambient:SKY.nightAmbient+Math.min(SKY.nightAmbient,amb),boomAmbient:ambC};
  return {width:w,sunElev:elev,nightFactor:nf,dayWeight:day,zenith,horizon,twilight,starAlpha:(b01)=>starAlpha(nf,b01,atmo),booms,boomAmbient:ambC,bodies,rig};
}
