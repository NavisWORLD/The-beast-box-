// Visual Life Pass, B3: ATMOSPHERE look. Haze toward the sky horizon, the limb rim seen from orbit, and fog density from moisture and storm.
// Numbers are Cosmo's pack (SEEDED look-hints, fpdepth.json by sha256); the engine's values WIN: the engine atmosphere value picks the class and the limb thickness, skyAt keeps the sky colour,
// F.moist (the cell under the camera) and F.storm (storm tension) set the fog multiplier. Airless worlds (atmosphere < 0.05) have no haze, no rim, no fog.
// Pure: no DOM, no clock, no Math.random. Label: SIMULATED where the world loop drives it (fog from moisture and storm), SEEDED for the look constants.
import {VL_ATMOSPHERE as A,pairTable,arrTable} from './vislife-look.mjs';
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
const smooth=(a,b,x)=>{const u=clamp((x-a)/(b-a),0,1);return u*u*(3-2*u);};
const lerp=(a,b,t)=>a+(b-a)*t;
/** thin / mid / thick from the engine atmosphere value: the nearest of the three reference amounts (moon 0, desert .55, temperate .85; sky-state knots). Airless (< 0.05) is always thin. */
export function atmoClass(atmo){const a=clamp(+atmo||0,0,1);if(a<0.05)return 'thin';return a<0.7?'mid':'thick';}
/** Limb rim for the orbit view: {enabled, thicknessFrac (of planet radius), gain}. */
export function limbRim(atmo){const c=atmoClass(atmo),r=A.limb_rim[c];if(!r.enabled)return {enabled:false,thicknessFrac:0,gain:0,cls:c};
 return {enabled:true,cls:c,thicknessFrac:pairTable(r.thickness_frac_radius_by_atmo,clamp(+atmo||0,0,1)),gain:r.gain};}
/** Rim alpha and colour at a lit limb point: cosL = dot(limb normal, sun direction) (sunward limb only). Linear RGB. */
export function limbAt(atmo,cosL){const c=atmoClass(atmo),r=A.limb_rim[c];if(!r.enabled)return {alpha:0,colour:[0,0,0]};
 const alpha=pairTable(r.alpha_by_sun_limb_cos,cosL)*r.gain,g=pairTable(r.golden_hour_mix_by_sun_elev_sin,clamp(cosL,0,1)),day=r.rim_colour.day.linear,gold=r.golden_hour_rim_colour.linear;
 return {alpha,colour:[0,1,2].map(i=>lerp(day[i],gold[i],g))};}
/** Fog density multiplier from the engine's moisture (0..1) and storm tension (0..1): bilinear on the pack grid. Airless = 1 (and fog stays off). */
export function fogMul(atmo,moisture,storm){const c=atmoClass(atmo),g=A.fog_density_mul_grid[c];if(!g.enabled)return 1;
 const m=clamp(+moisture||0,0,1),s=clamp(+storm||0,0,1),xs=g.moisture_axis,ys=g.storm_axis;const row=(i)=>arrTable(ys,g.mul[i],s);return arrTable(xs,xs.map((_,i)=>row(i)),m);}
/** Storm haze colour mix (0..mixMax): slate on temperate worlds, dust brown on mid worlds. */
export function stormHaze(atmo,storm){const c=atmoClass(atmo),g=A.fog_density_mul_grid[c];if(!g.enabled)return {mix:0,colour:[0,0,0]};return {mix:pairTable(g.storm_haze_mix_by_storm,clamp(+storm||0,0,1)),colour:g.storm_haze_colour.linear};}
/** Haze for the ground view: colour, per-metre exp2 density (x fog multiplier), the far mix cap. Time of day from the ENGINE: nightFactor and the sun's elevation (sin). */
export function hazeFor({atmo,sunElevSin,nightFactor,moisture=0,storm=0}){const c=atmoClass(atmo),H=A.haze_by_class[c];if(!H.day.enabled)return {enabled:false,cls:c,colour:[0,0,0],density:0,cap:0,mul:1,stormMix:0,stormColour:[0,0,0]};
 const nf=clamp(+nightFactor||0,0,1),wD=(1-nf)*smooth(0.05,0.35,+sunElevSin||0),wN=nf,wU=Math.max(0,1-wD-wN),mix3=(f)=>[0,1,2].map(i=>wD*f(H.day)[i]+wU*f(H.dusk)[i]+wN*f(H.night)[i]);
 const colour=mix3(t=>t.haze_colour.linear),density=wD*H.day.exp2_density+wU*H.dusk.exp2_density+wN*H.night.exp2_density,mul=fogMul(atmo,moisture,storm),sh=stormHaze(atmo,storm);
 return {enabled:true,cls:c,colour,density:density*mul,cap:A.const_block.far_mix_cap,mul,stormMix:sh.mix,stormColour:sh.colour};}
/** Haze mix 0..cap at a distance (metres): the pack's curve f(d) = min(cap, 1 - exp(-(d x density)^2)). */
export function hazeMixAt(h,distM){return h.enabled?Math.min(h.cap,1-Math.exp(-Math.pow(Math.max(0,distM)*h.density,2))):0;}
