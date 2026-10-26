// Visual Life Pass B4: event staging. The boom as ONE ring shell + lit water + an orbit bloom, all PURE functions of the engine's own boom state.
// HONESTY: the boom is boom.mjs's SEEDED (stepped test universe) event; this module only STAGES it. Phase, u, intensity, shellFrac, shellRadiusAu, colorRGB and the 1/d^2 sky term are boom.mjs numbers and WIN.
// The look numbers are Cosmo's SEEDED look-hints (vislife.json EVENTS, sha256 in vislife-look-data.mjs). No Date, no Math.random, no stored state: a replay of history reproduces it.
// NOT staged (no engine channel): a storm-cell bearing on the horizon or in orbit (the engine has storm tension F.storm, not a cell position), wet earth ahead of a cell (land-state wetness already follows moisture), moons at night.
import {boomState,boomSkyTerm,BOOM} from './boom.mjs';
import {VL_EVENTS} from './vislife-look-data.mjs';
import {pairTable,arrTable} from './vislife-look.mjs';
export const PHASES=Object.freeze(['flash','shell','fade','remnant']);
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
const mix3=(a,b,t)=>[0,1,2].map(i=>a[i]+(b[i]-a[i])*t);
const lin=o=>o.linear;
/** Local 0..1 position inside a phase (edges are boom.mjs's own BOOM.flashEnd/shellEnd/fadeEnd). */
export function phaseT(phase,u){const E=[0,BOOM.flashEnd,BOOM.shellEnd,BOOM.fadeEnd,1];const i=PHASES.indexOf(phase);if(i<0)return 0;return clamp((u-E[i])/(E[i+1]-E[i]),0,1);}
function rampColour(ramp,t){const xs=ramp.stops_t,cs=(ramp.colours||ramp.light_colour).map(lin);return [0,1,2].map(k=>arrTable(xs,cs.map(c=>c[k]),t));}
/** The staging for one boom at `tick`. sunUp 0..1 pales it by day exactly as boomSkyTerm does. Returns null before the event / for a star that cannot explode. */
export function boomStage(star,eventTick,tick,distanceAu,sunUp=0){
 const st=boomState(star,eventTick,tick);if(st.phase==='none')return null;
 const E=VL_EVENTS,sky=E.fp_sky.ramps[st.phase],orb=E.orbit_globe_flash.ramps[st.phase],M=E.mood_31;
 const t=phaseT(st.phase,st.u),term=boomSkyTerm(star,eventTick,tick,distanceAu,sunUp);
 const eng=st.colorRGB,engN=eng.map(c=>c/Math.max(1e-6,Math.max(...eng)));
 const ramp=rampColour(sky,t),rampIn=rampColour(sky,Math.max(0,t-0.3));
 const outer=mix3(mix3(ramp,lin(M.shell_radial.outer_edge_colour),0.5),engN,0.25);
 const inner=mix3(mix3(rampIn,lin(M.shell_radial.inner_edge_colour),0.5),engN,0.25);
 const shadow=lin(M.shell_radial.shadow_colour);
 const ringAlpha=clamp(arrTable(sky.stops_t,sky.alpha_hint,t)*term,0,1);
 // the ring's angular radius is the engine's own shell radius (AU) seen from the planet's distance, clamped to a readable sky size
 const angDeg=clamp(Math.atan2(st.shellRadiusAu,Math.max(0.05,distanceAu))*180/Math.PI,0,40);
 const lit=clamp(pairTable(M.lights_surfaces.water_lit_mix_by_boom_intensity,term),0,1);
 const bloomT=orb;const gain=arrTable(bloomT.stops_t,bloomT.light_gain,t);
 const bloom={radiusFrac:M.orbit_inset_bloom.bloom_radius_frac_of_globe_by_phase[st.phase],colour:rampColour({stops_t:bloomT.stops_t,light_colour:bloomT.light_colour},t),gain:gain*boomSkyTerm(star,eventTick,tick,distanceAu,0),halo:lin(M.orbit_inset_bloom.halo_colour)};
 return {phase:st.phase,u:st.u,t,intensity:st.intensity,skyTerm:term,shellFrac:st.shellFrac,shellRadiusAu:st.shellRadiusAu,
  ring:{angDeg,alpha:ringAlpha,outer,inner,shadow},waterLit:{mix:lit,colour:lin(M.lights_surfaces.shore_water_lit),underMax:M.lights_surfaces.under_water_lit_mix_max},bloom,label:st.label};
}
/** The strongest boom among the home sky's booms ([{star,eventTick,distance,dir}] from skyBooms), or null. */
export function stageBooms(list,tick,sunUp=0){let best=null;for(const b of list||[]){const s=boomStage(b.star,b.eventTick,tick,b.distance,sunUp);if(s&&(!best||s.skyTerm>best.stage.skyTerm))best={stage:s,dir:b.dir||null,star:b.star};}return best;}
/** Orbit bloom centre: the point of the globe's limb nearest the boom bearing, seen from `camDir` (both unit vectors). */
export function limbPoint(bearing,camDir){const d=bearing[0]*camDir[0]+bearing[1]*camDir[1]+bearing[2]*camDir[2];const p=[bearing[0]-camDir[0]*d,bearing[1]-camDir[1]*d,bearing[2]-camDir[2]*d];const l=Math.hypot(...p);return l<1e-6?null:p.map(x=>x/l);}
