// "The engine carries the sky", PR 5: the adapter the first-person view uses to read the engine's sky.
// Pure functions (no three, no DOM, no clock): the view passes in engine state and gets numbers back, so node tests can check the wiring.
import {lwStream,unitFrom} from './living-world.mjs';
import {PLANET_SHADING} from './planet-shading.mjs';
import {pickType} from './planet-types.mjs';
import {seedMoons,moonOffset} from './moons.mjs';
import {boomsAt,supernovaEvents} from './boom.mjs';
import {engineChannels} from './star-visual.mjs';
export const SKY_VIEW=Object.freeze({
  skyDist:150,               // where sky bodies sit from the world centre (units), matching the existing sun/moon sprites
  moonDist:70,               // existing moon distance
  auPerMapUnit:10,           // SEEDED view mapping: star x,y sit in a unit square; one unit = 10 AU for the boom's 1/d^2 term
  homeBoomMinAu:0.2,
  flatBackgroundMix:0.5,     // fallback only: the ground view draws a gradient dome (one-world-look addSkyDome)
      // scene.background is one colour: halfway between zenith and horizon
});
/** What the home planet's sky is made of, from the same shading data the orbit globe uses (so the terminator width is identical). */
export function skyConfigFor(planet,star){
  const type=pickType(planet||{});const sh=PLANET_SHADING[type]?.shading;
  return {type,atmosphere:sh?+sh.atmo_amount:0.5,skyColor:sh?.sky_color||null,twilightColor:sh?.twilight_color||null,starTempK:+star?.temperature_k||5800};
}
/** The sun the view should use. `override` means a test hook or a held/special view is in charge, so the old clock path stays. */
export function sunSource({field,override}){
  if(override)return {source:'override',dir:null};
  if(field&&field.sunDir)return {source:'engine',dir:field.sunDir};
  return {source:'clock',dir:null};
}
/** A bearing in the sky for a boom: seeded from the universe seed and the star id (the engine has positions in a plane, not a sky). */
export function boomBearing(seed,starId){const r=lwStream(seed+':boombearing:'+starId);const v=unitFrom(r);return [v[0],Math.abs(v[1])*0.7+0.1,v[2]].map((x,i,a)=>x/Math.hypot(...a));}
/** The booms the home planet's sky can see, replayed from engine history at `tick`: [{star, eventTick, distance(AU), dir}] */
export function skyBooms(u,homePlanet,homeStar,tick){
  if(!u||!homeStar)return [];const by=new Map((u.stars||[]).map(s=>[s.id,s]));const out=[];
  for(const b of boomsAt(u,tick)){const st=by.get(b.star);if(!st)continue;
    let d;if(st.id===homeStar.id)d=Math.max(SKY_VIEW.homeBoomMinAu,+homePlanet?.orbit_au||SKY_VIEW.homeBoomMinAu);else d=Math.max(0.5,Math.hypot((st.x||0)-(homeStar.x||0),(st.y||0)-(homeStar.y||0))*SKY_VIEW.auPerMapUnit);
    out.push({star:st,eventTick:b.eventTick,distance:d,dir:boomBearing(String(u.seed||'tiny'),st.id)});}
  return out;
}
/** The home planet's seeded moons as sky bodies at engine time t (seconds): direction from a surface observer standing at `up`. */
export function skyMoons(seed,planet,up,t){
  if(!planet)return [];const ms=seedMoons(String(seed||'tiny'),[planet]);
  return ms.map(m=>{const o=moonOffset(m,t);const v=[o.x-up[0],o.y-up[1],o.z-up[2]];const l=Math.hypot(...v)||1;return {id:m.id,kind:'moon',dir:v.map(x=>x/l),radius:m.radiusFrac,distance:l};});
}
/** boom glow sprite geometry: half-size in world units for a sprite at `dist`, so the profile's 3R halo fits. */
export const boomSpriteScale=(radiusDeg,dist=SKY_VIEW.skyDist)=>2*dist*Math.tan(Math.min(80,3*radiusDeg)*Math.PI/180);
export {engineChannels,supernovaEvents};
/** The ONE light rig (P1): everything the view's lights and post chain take from the one sun, in one place. DERIVED from oneSunAt()
 * output (`os`: {day, elevationDeg, sky}) and the pack tier exposure; FIX_NOTES_43c74d3 values (sun 3.03 x day once, hemi .6 x day + .15).
 * Never a second clock or night factor: `day` is the one-sun value the view already computed. */
export function lightRigFor(os,exposure=0.85){
  const day=Math.min(1,Math.max(0,+os?.day||0));const z=os?.sky?.zenith||[0,0,0],h=os?.sky?.horizon||[0,0,0];
  return {label:'DERIVED',sunIntensity:3.03*day,hemiIntensity:.6*day+.15,hemiColor:[0,1,2].map(i=>(z[i]+h[i])/2),exposure,sunElevationDeg:+os?.elevationDeg||0};
}
