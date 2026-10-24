// Terrain texture helpers (pure, seedless: everything comes from the planet's recorded values).
/** snow/ice cap amount 0..1 from the planet's RECORDED temperature (K); ice worlds always carry caps, hot/airless worlds none. */
export function snowAmount(type,tempK){if(type==='moon'||type==='volcanic'||type==='desert')return 0;const t=Number.isFinite(tempK)?Math.max(0,Math.min(1,(290-tempK)/90)):(type==='ice'?1:0.15);return type==='ice'?Math.max(t,0.8):t;}
