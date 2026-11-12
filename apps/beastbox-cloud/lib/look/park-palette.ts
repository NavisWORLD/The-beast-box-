// Park look palette and cost tiers. Presentation only: these colours grade the Genesis ground; they never touch world state.
// Values come from the Park look spec (Cosmo, 2026-11-11). They are our own numbers for a shader grade, not copied art.

export type RGB=[number,number,number];

/** Day palette (sRGB hex). */
export const PARK_DAY=Object.freeze({
 skyZenith:'#1AA6FF',skyMid:'#2BACFF',skyHorizon:'#3BCBFD',cloudLit:'#E8FCFE',haze:'#90D4E8',
 meadowSun:'#79D389',meadowMid:'#4C9661',grassTip:'#8EE09A',grassRoot:'#2F5A43',canopy:'#3E8A55',
 sand:'#F5D7A0',cliffSun:'#E08A62',cliffShade:'#8A5A48',oceanShallow:'#4DD9FC',oceanDeep:'#2BA0D4',foam:'#F2FFFE',
 flowerYellow:'#F0D23A',flowerMagenta:'#E07AB0',warmFill:'#FFE7A8',
} as const);

/** Shadow and night palette (sRGB hex). */
export const PARK_NIGHT=Object.freeze({
 shadow:'#3A5A70',skyFill:'#7EC8E8',zenith:'#000444',mid:'#000E57',horizon:'#001B6D',
 grass:'#205B61',foliage:'#1A2F47',farHills:'#4174A3',moon:'#E8EEF8',warmAccent:'#F0B45A',
} as const);

/**
 * Rough GPU ms per frame at 390x844 for each Park technique and tier. Estimates from the spec, not device measurements.
 * null means off on that tier.
 */
export const PARK_COST=Object.freeze({
 K1_terrain:{LOW:.4,MED:.6,HIGH:.8,GOD:1.0},
 K2_grass:{LOW:.4,MED:.8,HIGH:1.4,GOD:2.0},
 K3_sky:{LOW:.2,MED:.4,HIGH:.5,GOD:.6},
 K4_clouds:{LOW:.2,MED:.4,HIGH:.6,GOD:.8},
 K5_haze:{LOW:.1,MED:.2,HIGH:.2,GOD:.3},
 K6_water:{LOW:.6,MED:.9,HIGH:2.0,GOD:2.5},
 K7_rim:{LOW:null,MED:.1,HIGH:.4,GOD:.5},
 K8_lut:{LOW:0,MED:0,HIGH:0,GOD:0},
 K11_planet:{LOW:.2,MED:.3,HIGH:.5,GOD:.7},
} as const);

/** Hex to sRGB triple in 0..1. Shader colours in lib/look are display values, so this does no colour-space conversion. */
export function hexRgb(hex:string):RGB{
 const h=String(hex).replace('#','');
 const n=parseInt(h.length===3?h.split('').map(c=>c+c).join(''):h,16);
 return [((n>>16)&255)/255,((n>>8)&255)/255,(n&255)/255];
}
export function mixRgb(a:RGB,b:RGB,t:number):RGB{
 const k=Math.max(0,Math.min(1,t));
 return [a[0]+(b[0]-a[0])*k,a[1]+(b[1]-a[1])*k,a[2]+(b[2]-a[2])*k];
}
function smooth(e0:number,e1:number,v:number){const t=Math.max(0,Math.min(1,(v-e0)/((e1-e0)||1)));return t*t*(3-2*t);}

/** Low-sun colours for the 4-stop LUT. Morning leans gold, dusk leans magenta-orange. */
const MORNING={zenith:hexRgb('#4FA8F0'),horizon:hexRgb('#FFD28A'),haze:hexRgb('#F4D8A8'),key:[1.08,.98,.86] as RGB};
const DUSK={zenith:hexRgb('#5A6BD8'),horizon:hexRgb('#FF9A7A'),haze:hexRgb('#E8A6B8'),key:[1.08,.9,.86] as RGB};

export type ParkGrade={
 stop:'night'|'morning'|'noon'|'dusk';
 day:number;
 zenith:RGB;horizon:RGB;haze:RGB;
 meadow:RGB;meadowMid:RGB;sand:RGB;cliff:RGB;cliffShade:RGB;
 grassTip:RGB;grassRoot:RGB;canopy:RGB;
 shallow:RGB;deep:RGB;foam:RGB;
 shadow:RGB;key:RGB;nightGround:RGB;
};

/**
 * Day/night LUT on the one sun. Intensity follows sun elevation; colour comes from four stops
 * (morning gold, noon cyan, dusk magenta-orange, night indigo). `rising` only picks morning vs dusk.
 * Pure function: same elevation in, same colours out.
 */
export function parkGrade(elevationDeg:number,rising=true):ParkGrade{
 const e=Number.isFinite(elevationDeg)?elevationDeg:45;
 const day=smooth(-8,6,e);
 const noonK=smooth(4,24,e);
 const low=rising?MORNING:DUSK;
 const dz=mixRgb(low.zenith,hexRgb(PARK_DAY.skyZenith),noonK);
 const dh=mixRgb(low.horizon,mixRgb(hexRgb(PARK_DAY.skyHorizon),hexRgb(PARK_DAY.cloudLit),.32),noonK);
 const dHaze=mixRgb(low.haze,hexRgb(PARK_DAY.haze),noonK);
 const dKey=mixRgb(low.key,[1.04,1.02,.97],noonK);
 const stop:ParkGrade['stop']=day<.5?'night':noonK>.5?'noon':rising?'morning':'dusk';
 return {
  stop,day,
  zenith:mixRgb(hexRgb(PARK_NIGHT.zenith),dz,day),
  horizon:mixRgb(hexRgb(PARK_NIGHT.horizon),dh,day),
  haze:mixRgb(hexRgb(PARK_NIGHT.farHills),dHaze,day),
  meadow:hexRgb(PARK_DAY.meadowSun),meadowMid:hexRgb(PARK_DAY.meadowMid),sand:hexRgb(PARK_DAY.sand),
  cliff:hexRgb(PARK_DAY.cliffSun),cliffShade:hexRgb(PARK_DAY.cliffShade),
  grassTip:mixRgb(hexRgb(PARK_NIGHT.grass),hexRgb(PARK_DAY.grassTip),day),
  grassRoot:mixRgb(hexRgb(PARK_NIGHT.foliage),hexRgb(PARK_DAY.grassRoot),day),
  canopy:mixRgb(hexRgb(PARK_NIGHT.foliage),hexRgb(PARK_DAY.canopy),day),
  shallow:mixRgb(hexRgb('#1F4E7A'),hexRgb(PARK_DAY.oceanShallow),day),
  deep:mixRgb(hexRgb('#0B2350'),hexRgb(PARK_DAY.oceanDeep),day),
  foam:mixRgb(hexRgb('#9FB8D8'),hexRgb(PARK_DAY.foam),day),
  shadow:hexRgb(PARK_NIGHT.shadow),
  key:dKey,
  nightGround:hexRgb(PARK_NIGHT.grass),
 };
}

/** Rec.709 saturation of an sRGB triple, 0 for grey. Used by tests to keep Park above Genesis. */
export function saturation(c:RGB){const mx=Math.max(...c),mn=Math.min(...c);return mx<=0?0:(mx-mn)/mx;}
