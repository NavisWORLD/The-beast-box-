// Seeded moons. The recorded genesis file has planets but NO moons, so these are procedural: derived only from the universe seed and the
// planet's recorded properties (no Math.random). They are labeled SEEDED everywhere they are shown; nothing here claims a measurement.
export const MOONS_LABEL='Moons: SEEDED (procedural from the universe seed, not recorded). The recorded genesis has planets but no moons.';
export const MOON_SEED_TAG='seeded';
// small deterministic stream (same LCG as universe-3d's rand)
export function rng(seed){let h=0;for(const c of seed)h=(h*31+c.charCodeAt(0))>>>0;return()=>{h=(h*1664525+1013904223)>>>0;return h/2**32;};}
// 0..3 moons, more for bigger planets; gas-giant-sized worlds can hold more, tiny ones usually none.
export function seedMoons(universeSeed,planets){
  const out=[];
  for(const p of planets){
    const r=rng(`${universeSeed}:moons:${p.id}`);
    const cap=Math.min(3,Math.round(0.6+0.55*Math.log2(1+Math.max(0,p.radius_earth??1))));
    const n=Math.min(cap,Math.floor(r()*(cap+1)));
    let a=2.7+r()*0.6; // orbit radius in planet radii, inside the (inner) Hill sphere
    for(let i=0;i<n;i++){
      const q=rng(`${universeSeed}:moon:${p.id}:${i}`);
      const radiusFrac=0.14+q()*0.2;                 // moon radius as a fraction of its planet's drawn radius
      const period=14*Math.pow(a/2.7,1.5)*(0.85+0.3*q()); // seconds per orbit: Kepler's a^1.5 law, scaled to be watchable
      out.push({id:`${p.id}-m${i}`,planet:p.id,seeded:true,tag:MOON_SEED_TAG,index:i,radiusFrac,aPlanetR:a,periodS:period,
        phase:q()*Math.PI*2,incl:(q()-0.5)*0.35,lonDeg:q()*360});
      a+=1.8+q()*1.2;
    }
  }
  return out;
}
// position relative to the planet centre, in planet radii (circular orbit, small inclination); angle also drives the tidal-lock spin
export function moonOffset(m,t){const th=m.phase+2*Math.PI*t/m.periodS;const c=Math.cos(th),s=Math.sin(th);
  return{x:m.aPlanetR*c,y:m.aPlanetR*s*Math.sin(m.incl),z:-m.aPlanetR*s*Math.cos(m.incl),theta:th};}
// the occluder (moon or planet) closest to the sun line through p; the shader draws one analytic shadow sphere
export function pickOccluder(p,sunDir,cands){let best=null,bd=1e30;for(const c of cands){const ox=c.x-p.x,oy=c.y-p.y,oz=c.z-p.z;const t=ox*sunDir.x+oy*sunDir.y+oz*sunDir.z;if(t<=0)continue;
  const px=ox-sunDir.x*t,py=oy-sunDir.y*t,pz=oz-sunDir.z*t;const d=Math.sqrt(px*px+py*py+pz*pz)-c.r;if(d<bd){bd=d;best=c;}}return best;}
