// GENESIS X ringed planets (SEEDED look on SIMULATED planets) from Cosmo's ringedplanets pack. Rings are lit only by the one engine sun:
// seeded 64-band profiles, forward scatter when you look toward the sun through them, the planet's soft shadow on its rings and the rings'
// shadow on the planet (both analytic, no shadow map). The three fixed worlds (home, desert, volcano) never get rings. No random calls, no clock.
import {RINGED_PACK as P} from './ringed-planets-data.mjs';
export const RINGED_LABEL='SEEDED rings on SIMULATED planets, lit by the one sun';
export const NEVER_RINGS=Object.freeze([...P.rings.which.never_rings]);
const hash=(s)=>{let h=2166136261>>>0;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619)>>>0;}return h/4294967296;};
/** true for the three fixed worlds (ids world-home / world-desert / world-volcano, or the bare home / desert / volcano) */
export function isRinglessWorld(id){const s=String(id??'').toLowerCase();return NEVER_RINGS.includes(s)||NEVER_RINGS.includes('world-'+s);}
/** the pack ring preset for a planet: floor(hash(id + ':ringpreset') * 4) */
export function ringPresetFor(id){const ps=P.rings.presets;return ps[Math.min(ps.length-1,Math.floor(hash(String(id)+':ringpreset')*ps.length))];}
/** per-tier switches (unknown tier -> MED) */
export function ringTier(tier){return P.tiers[tier]||P.tiers.MED;}
export const RING_SCATTER_G=P.rings.forward_scatter.g;export const RING_PEN=P.rings.planet_shadow_on_ring.penumbra_pen;export const EARTHSHINE_CAP=P.lighting.earthshine.cap_linear;
/** CPU mirror of the planet-shadow-on-ring formula (for tests and probes). Q, C, sun are 3-vectors; sun is unit. */
export function planetShadowOnRing(Q,C,R,sun,pen=RING_PEN){const d=[Q[0]-C[0],Q[1]-C[1],Q[2]-C[2]];const tc=d[0]*sun[0]+d[1]*sun[1]+d[2]*sun[2];if(tc>=0)return 1;
 const p=[d[0]-sun[0]*tc,d[1]-sun[1]*tc,d[2]-sun[2]*tc];const perp=Math.hypot(...p);const a=R*(1-pen),b=R*(1+pen);const t=Math.min(1,Math.max(0,(perp-a)/(b-a)));return t*t*(3-2*t);}
/** CPU mirror of the ring-shadow-on-planet formula. Returns 1 (no shade) or 1 - opacity*band*0.85. */
export function ringShadowOnPlanet(Pp,C,nrm,sun,R,inner,outer,opacity,band=(u)=>1){const dn=sun[0]*nrm[0]+sun[1]*nrm[1]+sun[2]*nrm[2];if(Math.abs(dn)<1e-6)return 1;
 const t=((C[0]-Pp[0])*nrm[0]+(C[1]-Pp[1])*nrm[1]+(C[2]-Pp[2])*nrm[2])/dn;if(t<=0)return 1;const X=[Pp[0]+sun[0]*t-C[0],Pp[1]+sun[1]*t-C[1],Pp[2]+sun[2]*t-C[2]];const r=Math.hypot(...X)/R;
 return r>inner&&r<outer?1-opacity*band((r-inner)/(outer-inner))*.85:1;}
/** forward scatter gain: 1 + g * max(dot(-V, sun), 0)^8, V = view direction from eye to ring point */
export function forwardScatter(V,sun,g=RING_SCATTER_G){return 1+g*Math.pow(Math.max(0,-(V[0]*sun[0]+V[1]*sun[1]+V[2]*sun[2])),8);}
/** uniform values for one ring from its ringPlan entry and pack preset (plain numbers; the caller wraps them for three) */
export function ringLook(id,tier){const pr=ringPresetFor(id),t=ringTier(tier);return {preset:pr.id,tint:pr.tint.linear.slice(),opacity:pr.opacity,bands:pr.bands_1d.slice(),useBands:t.ring_bands?1:0,scatter:t.forward_scatter?RING_SCATTER_G:0,planetShadow:t.planet_shadow_on_ring?1:0,ringShadow:t.ring_shadow_on_planet?1:0};}
/** ring fragment shader (one sun only). Uniforms: uSun,uC,uTint,uR,uIn,uOut,uOp,uBands[64],uUseBands,uG,uPS. */
export const RING_FRAG=`uniform vec3 uSun,uC,uTint;uniform float uR,uIn,uOut,uOp,uUseBands,uG,uPS;uniform float uBands[64];varying vec3 vW;varying vec3 vNr;
float bandAt(float u){float x=clamp(u,0.0,1.0)*63.0;int i=int(floor(x));float f=fract(x);float a=0.0,b=0.0;for(int k=0;k<64;k++){if(k==i)a=uBands[k];if(k==i+1)b=uBands[k];}if(i>=63)b=a;return mix(a,b,f);}
void main(){float r=(distance(vW,uC)-uIn)/(uOut-uIn);float band=uUseBands>.5?bandAt(r):.55+.25*sin(r*41.0)+.2*sin(r*13.0+1.7);float edge=smoothstep(0.0,.06,r)*smoothstep(1.0,.9,r);
 vec3 oc=vW-uC;float tc=dot(oc,uSun);float perp=length(oc-uSun*tc);float sh=uPS>.5?(tc<0.0?mix(.12,1.0,smoothstep(uR*${(1-P.rings.planet_shadow_on_ring.penumbra_pen).toFixed(3)},uR*${(1+P.rings.planet_shadow_on_ring.penumbra_pen).toFixed(3)},perp)):1.0):((tc<0.0&&perp<uR)?.12:1.0);
 vec3 V=normalize(vW-cameraPosition);float fs=1.0+uG*pow(max(dot(-V,uSun),0.0),8.0);float lit=.25+.75*abs(dot(vNr,uSun));
 vec3 col=uTint*band*lit*fs*sh;gl_FragColor=vec4(col,uOp*edge*clamp(band*1.25,0.0,1.0));}`;
export const RING_VERT='varying vec3 vW;varying vec3 vNr;void main(){vW=(modelMatrix*vec4(position,1.0)).xyz;vNr=normalize(mat3(modelMatrix)*vec3(0.0,0.0,1.0));gl_Position=projectionMatrix*viewMatrix*vec4(vW,1.0);}';
/** GLSL to add to a planet fragment shader: the ring's shadow on the planet from the one sun (analytic ray-plane test). Needs uniforms uRsC,uRsN,uRsR,uRsIn,uRsOut,uRsOp,uRsOn and varying vW. */
export const RING_SHADOW_DECL='uniform vec3 uRsC,uRsN;uniform float uRsR,uRsIn,uRsOut,uRsOp,uRsOn;float ringShade(vec3 Pw,vec3 sd){if(uRsOn<.5)return 1.0;float dn=dot(sd,uRsN);if(abs(dn)<1e-4)return 1.0;float t=dot(uRsC-Pw,uRsN)/dn;if(t<=0.0)return 1.0;float r=length(Pw+sd*t-uRsC)/uRsR;return (r>uRsIn&&r<uRsOut)?1.0-uRsOp*.85*(.6+.4*sin((r-uRsIn)/(uRsOut-uRsIn)*40.0)):1.0;}';
/** patch a planet fragment shader that ends in gl_FragColor=vec4(c,1.0); so the rings' shadow darkens c. Returns the source unchanged when the marker is missing. */
export function withRingShadow(frag){const m='gl_FragColor=vec4(c,1.0);';const i=frag.lastIndexOf(m);if(i<0)return frag;const j=frag.indexOf('void main(){');if(j<0)return frag;
 return frag.slice(0,j)+RING_SHADOW_DECL+frag.slice(j,i)+'c*=ringShade(vW,normalize(uSun));'+frag.slice(i);}
export const RINGED_PACK_INFO=Object.freeze({label:P.label,honesty:P.honesty,seed:P.seed,version:P.version});
