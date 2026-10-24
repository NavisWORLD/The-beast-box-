// "The engine carries the sky", PR 3: the sea as an ENGINE OUTPUT. ONE wave field: waveHeightAt(sea, dir, t) is a pure function, mirrored in GLSL (SEA_GLSL, below); a test runs the
// GLSL text through a tiny evaluator and requires it to agree with the CPU function. The renderer asks the engine; it never invents weather.
//  - `sea` is DERIVED each step from engine channels: the CST wind (motionParams(F.S).wind) -> direction and speed; storm tension (F.storm) -> amplitude and whitecap coverage.
//  - Layers: 2 swell + 2 chop, Gerstner-lite (crest-sharpened sine on a sphere direction). Constants live in ONE block (SEA) and only where the engine has no number of its own.
//  - Camera, floating props and wading creatures sample the SAME field at 3 points (rideAt), so everything rides it.
//  - The existing tide band is untouched: shoreFoam is an ADDED layer over it.
// Pure: no DOM, no clock (t is engine time in seconds: world ticks / 4), no Math.random. Derived visuals only: nothing here is stored in the engine JSON.
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
const mix=(a,b,t)=>a+(b-a)*t;
export const SEA=Object.freeze({
 windRef:0.6,                 // |wind| (x,z) from motionParams peaks well under 0.5 in a 2000-tick run; 0.6 maps it to 0..1
 ampBase:0.012,ampStorm:0.05, // swell amplitude in planet-radius units (about 0.3 m .. 1.7 m at the 27 m world): ampBase + ampStorm * storm, scaled by (0.35 + 0.65 * wind)
 whitecapStorm:1.1,whitecapWind:0.12,
 foamLifeS:2,                 // crest foam forms and dissolves over ~2 s of ENGINE time
 shoreAmp:0.35,shoreSwellHz:0.11,
 // layers: [wavelength (radians on the unit sphere), amplitude share, speed (rad/s), direction offset from the wind (rad), phase seed]
 layers:Object.freeze([[0.9,1.0,0.16,0.0,0.3],[0.55,0.6,0.13,0.6,1.7],[0.21,0.22,0.34,-0.5,2.9],[0.12,0.12,0.42,1.1,4.1]]),
});
/** Derive the sea from the world field (or from {wind:{x,z}, storm}). Pure. */
export function seaFrom(F){
 const w=F?.mp?.wind||{x:0,z:0},storm=clamp(+F?.storm||0,0,1);const speed=Math.hypot(w.x,w.z);const windN=clamp(speed/SEA.windRef,0,1);
 const dir=speed>1e-6?Math.atan2(w.z,w.x):0;
 return {dir,wind:windN,storm,amp:(SEA.ampBase+SEA.ampStorm*storm)*(0.35+0.65*windN),chop:clamp(0.25+0.75*storm,0,1),whitecap:clamp(SEA.whitecapStorm*storm+SEA.whitecapWind*windN,0,1)};
}
const L=SEA.layers;
/** The layer's travel direction as a unit vector on the tangent plane's x/z axes plus a lift so every layer varies over the whole sphere. */
const layerDir=(sea,k)=>{const a=sea.dir+L[k][3];return [Math.cos(a),0.37*Math.sin(L[k][4]+k),Math.sin(a)];};
/** Sea surface height (radius units) at unit direction `d` and engine time t (seconds). Swell layers 0,1 carry the amplitude; chop layers 2,3 scale with sea.chop. */
export function waveHeightAt(sea,d,t){
 let h=0;
 for(let k=0;k<4;k++){const [wx,wy,wz]=layerDir(sea,k);const w=Math.PI*2/L[k][0];const p=w*(d[0]*wx+d[1]*wy+d[2]*wz)-L[k][2]*w*t+L[k][4];
  const q=0.5+0.5*Math.sin(p);const crest=2*q*q-1;const share=L[k][1]*(k<2?1:sea.chop);h+=sea.amp*share*crest;}
 return h;
}
/** GLSL ES 1.00 mirror of waveHeightAt. Uniforms/params are scalars so the text can be checked against the CPU function by tests/sea-state.test.mjs. */
export const SEA_GLSL=`float seaWaveHeight(float dx,float dy,float dz,float t,float dir,float amp,float chop){
 float h=0.0;float a;float w;float p;float q;
${L.map((l,k)=>` a=dir+(${l[3].toFixed(6)});w=${(Math.PI*2/l[0]).toFixed(9)};p=w*(dx*cos(a)+dy*(${(0.37*Math.sin(l[4]+k)).toFixed(9)})+dz*sin(a))-${(l[2]).toFixed(6)}*w*t+${l[4].toFixed(6)};q=0.5+0.5*sin(p);h+=amp*${(l[1]).toFixed(6)}*${k<2?'1.0':'chop'}*(2.0*q*q-1.0);`).join('\n')}
 return h;
}`;
/** Crest foam 0..1 at (dir, t): a crest (height near its layer maximum) leaves foam that dissolves over foamLifeS of engine time; gated by whitecap coverage and a seeded hash so the pattern is not uniform. */
export function crestFoam(sea,d,t){
 const a=Math.max(1e-9,sea.amp);let f=0;const steps=4,dt=SEA.foamLifeS/steps;
 for(let i=0;i<=steps;i++){const age=i*dt;const c=clamp((waveHeightAt(sea,d,t-age)/a-0.55)*2.2,0,1);f=Math.max(f,c*(1-age/SEA.foamLifeS));}
 const s=Math.sin(d[0]*127.1+d[1]*311.7+d[2]*74.7)*43758.5453;const gate=s-Math.floor(s)<sea.whitecap?1:0;
 return clamp(f*gate,0,1);
}
/** Shore foam over the existing tide band: waterline offset swings with the swell (advance/retreat), foam sits at the edge, wet sand above the line follows cell moisture. dist = signed metres inland from the still waterline (negative = water). */
export function shoreFoam(sea,dist,t,moisture=0.5){
 const swell=Math.sin(Math.PI*2*SEA.shoreSwellHz*t+0.7);const edge=SEA.shoreAmp*(0.4+sea.amp/Math.max(1e-9,SEA.ampBase+SEA.ampStorm))*swell; // metres the waterline advances (+) or retreats (-)
 const x=dist-edge;const foam=clamp(1-Math.abs(x)/0.35,0,1)*(0.45+0.55*sea.whitecap);const wet=x>0?clamp(1-x/2.2,0,1)*clamp(0.35+0.65*moisture,0,1):0;
 return {foam,wetSand:wet,edge};
}
/** Sun glitter: tight and white at a high sun, wide and gold at a low sun; chop widens it. Engine sun elevation (sunDir.y), star colour from starVisual. Returns {intensity, width, color}. */
export function sunGlitter(sunElev,sea,starRGB=[1,1,1]){
 const e=clamp(sunElev,0,1);const width=clamp(0.04+0.22*(1-e)+0.18*sea.chop,0.03,0.6);const gold=[1.0,0.78,0.42];const k=Math.pow(1-e,1.5);
 return {intensity:sunElev>0?clamp(0.35+0.65*e,0,1):0,width,color:starRGB.map((c,i)=>mix(c,gold[i],k))};
}
/** Schlick fresnel: deep water colour -> the sky it reflects (the sky is passed in so water and sky read the same engine sky). */
export function fresnelMix(cosView,deepRGB,skyRGB){const f=Math.pow(1-clamp(cosView,0,1),5);const r=0.02+0.98*f;return deepRGB.map((c,i)=>mix(c,skyRGB[i],r));}
/** Deep water colour from the planet's engine temperature (cold = darker teal, hot = warmer green). */
export function waterDeep(planet){const T=+(planet?.temperature_k??planet?.temp_k??planet?.temperature??288);const tn=clamp(((Number.isFinite(T)?T:288)-230)/120,0,1);return [mix(0.02,0.05,tn),mix(0.11,0.20,tn),mix(0.2,0.24,tn)];}
/** Ride: sample the field at 3 points around (dir) and return heave (height), pitch and roll in radians. `fwd` and `right` are unit tangent-ish vectors; `half` is the half-length in unit-sphere radians. */
export function rideAt(sea,d,fwd,right,t,half=0.01){
 const at=(a,b,s)=>{const v=[d[0]+a[0]*s*half,d[1]+a[1]*s*half,d[2]+a[2]*s*half];const l=Math.hypot(...v)||1;return waveHeightAt(sea,[v[0]/l,v[1]/l,v[2]/l],t);};
 const hc=waveHeightAt(sea,d,t),hf=at(fwd,fwd,1),hb=at(fwd,fwd,-1),hr=at(right,right,1),hl=at(right,right,-1);
 return {heave:hc,pitch:Math.atan2(hf-hb,2*half),roll:Math.atan2(hr-hl,2*half)};
}
