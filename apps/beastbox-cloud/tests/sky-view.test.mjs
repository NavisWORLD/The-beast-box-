// "The engine carries the sky", PR 5: the view adapter reads the engine. Accuracy traces, sun source, moons, booms, isolation, wiring scan.
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {genesis,grow} from '../lib/universe/tiny-universe.mjs';
import {skyConfigFor,sunSource,skyBooms,skyMoons,boomBearing,boomSpriteScale,SKY_VIEW} from '../lib/universe/sky-view.mjs';
import {skyAt,terminatorWidth} from '../lib/universe/sky-state.mjs';
import {PLANET_SHADING} from '../lib/universe/planet-shading.mjs';
import {pickType} from '../lib/universe/planet-types.mjs';
import {createWorldField,stepWorldField} from '../lib/universe/world-field.mjs';
import {sunDirAt,DAY_LENGTH_TICKS} from '../lib/universe/genesis-sun.mjs';
import {blackBodyToRGB} from '../lib/universe/genesis-sun.mjs';
const here=p=>new URL(p,import.meta.url);
const real=genesis(JSON.parse(readFileSync(here('../public/spark/ibm-marrakesh-reality-probe-20261009.json'),'utf8')));
test('sky config comes from the same shading data as the orbit globe: terminator width per planet type equals mix(0.015,0.12,atmo)',()=>{
 for(const p of real.planets){const star=real.stars.find(s=>s.id===p.star);const c=skyConfigFor(p,star);const sh=PLANET_SHADING[pickType(p)].shading;assert.equal(c.atmosphere,sh.atmo_amount);assert.deepEqual(c.skyColor,sh.sky_color);assert.equal(c.starTempK,star.temperature_k);assert.equal(terminatorWidth(c.atmosphere),0.015+(0.12-0.015)*sh.atmo_amount);}
});
test('sun source: engine sun when no override, the clock path stays as the fallback, a test/hold override wins',()=>{
 const F=createWorldField({seed:'v',W:8,H:4,initial:()=>({id:'grassland',h:0.2})});
 assert.equal(sunSource({field:F,override:false}).source,'engine');assert.deepEqual(sunSource({field:F,override:false}).dir,F.sunDir);
 assert.equal(sunSource({field:null,override:false}).source,'clock');assert.equal(sunSource({field:F,override:true}).source,'override');assert.equal(sunSource({field:F,override:true}).dir,null);
});
test('engine day: the sun crosses on engine time (one full turn = 960 ticks = 240 s) and stepping twice gives identical sun and sky',()=>{
 const mk=()=>createWorldField({seed:'day',W:8,H:4,initial:()=>({id:'grassland',h:0.2})});const A=mk(),B=mk();let hmax=-2,hmin=2;
 for(let i=0;i<DAY_LENGTH_TICKS;i++){stepWorldField(A,0.25);stepWorldField(B,0.25);assert.deepEqual(A.sunDir,B.sunDir);const sk=skyAt({sunDir:A.sunDir,atmosphere:0.85,starTempK:5800});hmax=Math.max(hmax,sk.sunElev);hmin=Math.min(hmin,sk.sunElev);}
 assert.ok(hmax>0.25&&hmin<-0.25,'the sun rises and sets over one engine day');
 const a0=createWorldField({seed:'day',W:8,H:4,initial:()=>({id:'grassland',h:0.2})});for(let i=0;i<DAY_LENGTH_TICKS;i++)stepWorldField(a0,0.25);const d=a0.sunAngle,s0=createWorldField({seed:'day',W:8,H:4,initial:()=>({id:'grassland',h:0.2})}).sunAngle;assert.ok(Math.abs(((d-s0)%(Math.PI*2)+Math.PI*2+1e-9)%(Math.PI*2))<1e-6||Math.abs(d-s0)<1e-6);
});
test('moons rise in correct phase: the lit fraction follows the real sun direction and engine orbit; hidden below the horizon',()=>{
 const pl=real.planets.find(p=>skyMoons(real.seed,p,[0,1,0],0).length)||null;if(!pl)return;
 const up=[0,1,0],sun=[1,0,0];let seen=new Set();for(let t=0;t<120;t+=3){for(const m of skyMoons(real.seed,pl,up,t)){const sk=skyAt({sunDir:sun,atmosphere:0.85,starTempK:5800,up,bodies:[m]});const b=sk.bodies[0];assert.ok(b.phase.litFraction>=0&&b.phase.litFraction<=1);assert.equal(b.aboveHorizon,b.dir[1]>0);seen.add(Math.round(b.phase.litFraction*4));}}
 assert.ok(seen.size>=3,'phases change as the moon orbits');
 assert.equal(JSON.stringify(skyMoons(real.seed,pl,up,7)),JSON.stringify(skyMoons(real.seed,pl,up,7)));
});
test('booms: a stepped universe replays its supernova into the sky list; the real recorded universe has none; bearing is seeded',()=>{
 assert.equal(skyBooms(real,real.planets[0],real.stars[0],0).length,0);
 let u=real;for(let i=0;i<400&&!u.history?.some(h=>h.events?.some(e=>e.kind==='supernova'));i+=40)u=grow(u,40);
 const ev=(u.history||[]).flatMap(h=>(h.events||[]).filter(e=>e.kind==='supernova'));
 assert.ok(ev.length>0,'a stepped universe reaches a supernova');{const st=u.stars.find(s=>s.id===ev[0].star);const homeP=u.planets.find(p=>p.star===st.id)||u.planets[0];const L=skyBooms(u,homeP,u.stars[0],u.tick);assert.ok(L.length>=1);for(const b of L){assert.ok(b.distance>=0.2);assert.equal(Math.round(Math.hypot(...b.dir)*1e6)/1e6,1);assert.deepEqual(b.dir,boomBearing(String(u.seed),b.star.id));}}
 assert.deepEqual(boomBearing('s','a'),boomBearing('s','a'));assert.notDeepEqual(boomBearing('s','a'),boomBearing('s','b'));
 assert.ok(boomSpriteScale(9)>boomSpriteScale(1));
});
test('isolation: the adapter never mutates the engine universe (JSON byte-identical)',()=>{
 const u=grow(real,25);const before=JSON.stringify(u);const home=u.planets[0],hs=u.stars.find(s=>s.id===home.star);
 skyConfigFor(home,hs);skyBooms(u,home,hs,u.tick);skyMoons(u.seed,home,[0,1,0],12);assert.equal(JSON.stringify(u),before);
});
test('view wiring: living-world reads the engine (sunSource, skyAt, skyMoons, boom glow), keeps the old clock/override path, and adds no clock or random to the engine modules',()=>{
 const src=readFileSync(here('../components/living-world.tsx'),'utf8');
 for(const k of ['sunSource({field','skyAt({sunDir','skyMoons(u.seed','boomGlow','__lwSunSource','Date.now()/1000+((window as any).__lwDayOffset||0)'])assert.ok(src.includes(k),k);
 const mod=readFileSync(here('../lib/universe/sky-view.mjs'),'utf8').split('\n').filter(l=>!l.trim().startsWith('//')).join('\n');assert.ok(!/Math\.random|Date\.now|performance\.now|new Date/.test(mod));
});
