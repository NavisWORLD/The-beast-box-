// Visual Life Pass, B2: CAUSTICS, the bright net of light on a shallow sea floor. An engine output derived from the ONE wave function (waveHeightAt):
// light focuses where the surface is concave, so the pattern is the (negated) curvature of the same height field the sea phase uses, sampled at four offsets.
// Intensity follows Cosmo's pack rule (SEEDED look-hint; the engine's values win): I = exp(-depth/decay) x (1 - smoothstep(0.6 cutoff, cutoff, depth)) x sunGate(sin elevation), night = night_mul.
// Drivers: waveHeightAt phase (engine tick, t = ticks/4 s plus the engine clock's own fraction), sea.dir/amp/chop (wind, storm), sun elevation (engine sunDir.y), nightFactor, water depth (the height map). No private clock, no Math.random.
// Label: SIMULATED (stepped by the world loop). Below-waterline forms live in seabed-forms.mjs (SEEDED).
import {waveHeightAt} from './sea-state.mjs';
import {VL_WATER,pairTable} from './vislife-look.mjs';
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
const smooth=(a,b,x)=>{const u=clamp((x-a)/(b-a),0,1);return u*u*(3-2*u);};
const PK=VL_WATER.caustic.const_block;
export const CAUSTIC=Object.freeze({
 eps:0.02,        // radians on the unit sphere between the four curvature taps (a fifth of the shortest chop wavelength)
 gain:1.6,        // how hard curvature is pushed to bright lines
 decayM:PK.decay_m,cutoffM:PK.cutoff_m,nightMul:PK.night_mul,sunGate:PK.sun_elev_gate_sin,
});
/** Unit tangent basis at d (same fallback axis in the shader). */
export function tangents(d){const ax=Math.abs(d[1])>0.99?[1,0,0]:[0,1,0];let a=[d[1]*ax[2]-d[2]*ax[1],d[2]*ax[0]-d[0]*ax[2],d[0]*ax[1]-d[1]*ax[0]];const la=Math.hypot(...a);a=a.map(x=>x/la);const b=[d[1]*a[2]-d[2]*a[1],d[2]*a[0]-d[0]*a[2],d[0]*a[1]-d[1]*a[0]];return [a,b];}
/** The scalar half of the pattern (GLSL mirrored below): five heights -> 0..1 bright-line weight. Calm water gives soft light (the curvature is divided by amp then scaled by chop). */
export function causticFocus(h0,h1,h2,h3,h4,amp,chop){
 const q=(h1+h2+h3+h4-4*h0)/Math.max(1e-9,amp);const k=CAUSTIC.gain*(0.5+chop);
 const c=clamp(0.35-q*k*0.5,0,1);return c*c;
}
/** Caustic pattern 0..1 at unit direction d and engine time t (s). */
export function causticPattern(sea,d,t){
 const [a,b]=tangents(d),e=CAUSTIC.eps,at=(s,u)=>{const v=[d[0]+a[0]*s*e+b[0]*u*e,d[1]+a[1]*s*e+b[1]*u*e,d[2]+a[2]*s*e+b[2]*u*e];const l=Math.hypot(...v);return waveHeightAt(sea,[v[0]/l,v[1]/l,v[2]/l],t);};
 return causticFocus(waveHeightAt(sea,d,t),at(1,0),at(-1,0),at(0,1),at(0,-1),sea.amp,sea.chop);
}
/** Sun gate from the engine's sun elevation (sin) and the engine's night factor: 0 at night until the pack's night multiplier. */
export function causticSun(sunElevSin,night=0){return Math.max(pairTable(CAUSTIC.sunGate,sunElevSin),CAUSTIC.nightMul*clamp(night,0,1));}
/** Depth fall-off (metres in the pack's unit, see the view's depth note): 1 at the surface, 0 at the cutoff. */
export function causticDepth(depthM){const d=Math.max(0,depthM);return Math.exp(-d/CAUSTIC.decayM)*(1-smooth(0.6*CAUSTIC.cutoffM,CAUSTIC.cutoffM,d));}
/** Pack colour (linear RGB) at a depth for a sea type (default temperate). */
export function causticColour(depthM,seaType='temperate'){const r=(VL_WATER.caustic.by_sea_type[seaType]||VL_WATER.caustic.by_sea_type.temperate).ramp;const xs=r.map(s=>s.depth_m);
 return [0,1,2].map(i=>pairTable(r.map(s=>[s.depth_m,s.colour.linear[i]]),depthM)).map(v=>+v.toFixed(6));void xs;}
/** Full CPU intensity: pattern x depth fall-off x sun gate. */
export function causticAt(sea,d,t,depthM,sunElevSin,night=0){return causticPattern(sea,d,t)*causticDepth(depthM)*causticSun(sunElevSin,night);}
/** GLSL ES 1.00 mirror of causticFocus (scalar only so tests/caustics.test.mjs can run the text against the CPU function). The five heights come from seaWaveHeight (SEA_GLSL) at the same offsets. */
export const CAUSTIC_GLSL=`float causticFocus(float h0,float h1,float h2,float h3,float h4,float amp,float chop){
 float q=(h1+h2+h3+h4-4.0*h0)/max(1e-9,amp);float k=${CAUSTIC.gain.toFixed(6)}*(0.5+chop);float c=clamp(0.35-q*k*0.5,0.0,1.0);return c*c;
}`;
/** The shader piece that taps the sea field at five points and applies depth fall-off. Needs SEA_GLSL and CAUSTIC_GLSL before it. */
export const CAUSTIC_TAP_GLSL=`float causticAt(vec3 n,float t,float dir,float amp,float chop,float dm){
 vec3 ax=abs(n.y)>0.99?vec3(1.0,0.0,0.0):vec3(0.0,1.0,0.0);vec3 ta=normalize(cross(n,ax));vec3 tb=cross(n,ta);float e=${CAUSTIC.eps.toFixed(6)};
 vec3 n1=normalize(n+ta*e),n2=normalize(n-ta*e),n3=normalize(n+tb*e),n4=normalize(n-tb*e);
 float f=causticFocus(seaWaveHeight(n.x,n.y,n.z,t,dir,amp,chop),seaWaveHeight(n1.x,n1.y,n1.z,t,dir,amp,chop),seaWaveHeight(n2.x,n2.y,n2.z,t,dir,amp,chop),seaWaveHeight(n3.x,n3.y,n3.z,t,dir,amp,chop),seaWaveHeight(n4.x,n4.y,n4.z,t,dir,amp,chop),amp,chop);
 return f*exp(-dm/${CAUSTIC.decayM.toFixed(3)})*(1.0-smoothstep(${(0.6*CAUSTIC.cutoffM).toFixed(3)},${CAUSTIC.cutoffM.toFixed(3)},dm));
}`;
/** Light-mode caustics (phones and weaker devices, see heavyAllowed): ONE tap of the same wave function instead of five. Same drivers, softer net. */
export function causticLite(h,amp){const x=clamp(0.5-0.5*h/Math.max(1e-9,amp)*1.2,0,1);return x*x;}
export const CAUSTIC_LITE_GLSL=`float causticLite(float h,float amp){float x=clamp(0.5-0.5*h/max(1e-9,amp)*1.200000,0.0,1.0);return x*x;}`;
/** GLSL mirror of the sun gate table (built from the same pack stops, so the two cannot drift). Per fragment: s = dot(surface normal, sun direction). */
export const CAUSTIC_GATE_GLSL=(()=>{const t=CAUSTIC.sunGate;let g='float causticGate(float s){\n if(s<='+t[0][0].toFixed(6)+')return '+t[0][1].toFixed(6)+';\n';
 for(let i=1;i<t.length;i++)g+=' if(s<='+t[i][0].toFixed(6)+')return mix('+t[i-1][1].toFixed(6)+','+t[i][1].toFixed(6)+',(s-('+t[i-1][0].toFixed(6)+'))/'+(t[i][0]-t[i-1][0]).toFixed(6)+');\n';
 return g+' return '+t[t.length-1][1].toFixed(6)+';\n}';})();
