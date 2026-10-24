// "The engine carries the sky", PR 2a: each engine star's derived VISUAL state. A pure function of (star, engine channels): the orbit view and a planet's night sky read the same numbers.
// Reuses the Definitive Core ports in genesis-sun.mjs (blackBodyToRGB, coronaParams); nothing is re-ported. Visuals are outputs: nothing here is state and nothing is written into the engine JSON.
// Constants live in ONE block (STAR_VISUAL) and only where the engine has no number of its own.
import {blackBodyToRGB,coronaParams} from './genesis-sun.mjs';
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
export const STAR_VISUAL=Object.freeze({
 pulseAmp:0.04,            // brightness breathes +/- 4% around 1 with the world CST coherence channel (spec: "+/- few %")
 shimmerPhaseRate:0.07,    // corona noise phase advance per engine tick, scaled by (0.5 + chaos)
 sizeBase:0.5,             // apparent size = sizeBase * log10(1 + luminosity) / (1 + distance)
 sizeMin:0.02,sizeMax:1.5,
 remnantGlow:0.15,         // a neutron-star remnant keeps a small, hot, pulsing point
});
/** The two world CST channels a star reads, from a world field (F.S.ch.chaos / F.S.ch.coherence) and its tick. Pure read; defaults when no field exists yet. */
export function engineChannels(F){const ch=F?.S?.ch||{};return {chaos:clamp(+ch.chaos||0,0,1),coherence:clamp(Number.isFinite(+ch.coherence)?+ch.coherence:0.5,0,1),tick:F?.tick||0};}
/** starVisual(star, engineState, distance): {colorRGB, corona:{intensity,noiseScale,shimmer,phase}, pulse, brightness, apparentSize, remnant}. engineState = {chaos, coherence, tick}. */
export function starVisual(star,engineState={},distance=1){
 const {chaos=0,coherence=0.5,tick=0}=engineState;const K=STAR_VISUAL;
 const lum=Math.max(0,+star.luminosity||0);const remnant=star.remnant||null;
 const pulse=1+K.pulseAmp*(coherence*2-1);
 const base=coronaParams(+star.temperature_k||5800);
 const corona={intensity:base.intensity,noiseScale:base.noiseScale,shimmer:clamp(chaos,0,1),phase:tick*K.shimmerPhaseRate*(0.5+clamp(chaos,0,1))};
 const size=clamp(K.sizeBase*Math.log10(1+lum)/(1+Math.max(0,distance)),0,K.sizeMax);
 // a remnant's luminosity is 0 in the engine: a neutron star keeps a small pulsing point, a black hole none (the seeded black hole renders it)
 const glow=remnant==='neutron_star'?K.remnantGlow*pulse:0;
 return {colorRGB:blackBodyToRGB(+star.temperature_k||5800),corona,pulse,brightness:lum>0?pulse:glow,apparentSize:lum>0?Math.max(K.sizeMin,size):(remnant==='neutron_star'?K.sizeMin:0),remnant};
}
