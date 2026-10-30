// GENESIS X P2 sky (first person): clouds, moon, star fade, aurora, storm darkening, rain. Pure and deterministic.
// Inputs are ONLY the engine signals: the one sun (240 s day: elevation + day weight), spark ticks (SIMULATED) and the storm state.
// It never owns a clock or a sun. No random calls. A designed look (SEEDED constants), not a measurement and not real weather data.
export const P2SKY=Object.freeze({label:'SEEDED',cloudBase:.38,cloudStorm:.62,darkMax:.45,rainFrom:.35,auroraMax:.8,moonCloudDim:.8,starCloudDim:.85,sparkPulseTicks:6});
const cl=x=>Math.min(1,Math.max(0,+x||0));
const ss=(a,b,x)=>{const t=cl((x-a)/(b-a));return t*t*(3-2*t);};
/** state for one frame: {elevDeg, day (0..1, one sun), storm (0..1), rain (0..1), sparkTick (engine tick, SIMULATED)} */
export function p2SkyAt({elevDeg=0,day=0,storm=0,rain=0,sparkTick=0}={}){
  const s=cl(storm),d=cl(day);
  const cover=cl(P2SKY.cloudBase+P2SKY.cloudStorm*s);
  const darken=P2SKY.darkMax*s;
  const rainA=cl(Math.max(cl(rain),ss(P2SKY.rainFrom,1,s)));
  const night=1-ss(-12,-2,+elevDeg||0);
  // spark energy: a soft pulse each spark tick, decaying over sparkPulseTicks (integer tick -> deterministic)
  const k=((Math.floor(+sparkTick||0)%P2SKY.sparkPulseTicks)+P2SKY.sparkPulseTicks)%P2SKY.sparkPulseTicks;const spark=Math.exp(-k/2);
  const aurora=P2SKY.auroraMax*night*(1-cover*.7)*(.55+.45*spark);
  const starFade=1-P2SKY.starCloudDim*cover;
  const moonA=1-P2SKY.moonCloudDim*cover*(.5+.5*s);
  const cloudLit=d*(1-s*.6);
  return Object.freeze({label:'SIMULATED',cover,darken,rain:rainA,aurora,starFade,moonA,cloudLit,night,spark});
}
