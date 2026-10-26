// Visual Life Pass: helpers over Cosmo's look pack (SEEDED look-hints; the engine's values win). Pure table lookups, no clock, no Math.random.
export {VL_PACK,VL_CLASS,VL_HERO,VL_SAME_WORLD,VL_ATMOSPHERE,VL_WATER,VL_EVENTS} from './vislife-look-data.mjs';
/** Piecewise-linear lookup in a [[x,y],...] table (clamped at both ends). */
export function pairTable(t,x){if(x<=t[0][0])return t[0][1];for(let i=1;i<t.length;i++){if(x<=t[i][0]){const a=t[i-1],b=t[i],u=(x-a[0])/(b[0]-a[0]||1);return a[1]+(b[1]-a[1])*u;}}return t[t.length-1][1];}
/** Piecewise-linear lookup over parallel arrays xs / ys. */
export function arrTable(xs,ys,x){if(x<=xs[0])return ys[0];for(let i=1;i<xs.length;i++){if(x<=xs[i]){const u=(x-xs[i-1])/(xs[i]-xs[i-1]||1);return ys[i-1]+(ys[i]-ys[i-1])*u;}}return ys[ys.length-1];}
