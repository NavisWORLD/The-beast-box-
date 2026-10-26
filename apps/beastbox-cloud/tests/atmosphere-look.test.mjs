// Visual Life Pass, B3: atmosphere look. Class from the engine atmosphere, airless = nothing, fog grid = pack formula, haze curve = pack table, GLSL table text = CPU, deterministic, no clock.
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {atmoClass,limbRim,limbAt,fogMul,stormHaze,hazeFor,hazeMixAt} from '../lib/universe/atmosphere-look.mjs';
import {VL_ATMOSPHERE as A,pairTable,pairTableGLSL} from '../lib/universe/vislife-look.mjs';
const mixJs=(a,b,t)=>a+(b-a)*t;
const evalTable=(name,t)=>new Function('mix',pairTableGLSL(name,t).replace(new RegExp('float '+name+'\\(float s\\)\\{'),'return function(s){').replace(/float /g,'let '))(mixJs);
test('class comes from the engine atmosphere value; airless has no rim, no haze, no fog, no storm haze',()=>{
 assert.equal(atmoClass(0),'thin');assert.equal(atmoClass(0.049),'thin');assert.equal(atmoClass(0.55),'mid');assert.equal(atmoClass(0.85),'thick');
 assert.equal(limbRim(0).enabled,false);assert.equal(limbAt(0,1).alpha,0);assert.equal(fogMul(0,1,1),1);assert.equal(stormHaze(0,1).mix,0);
 const h=hazeFor({atmo:0,sunElevSin:.5,nightFactor:0,moisture:1,storm:1});assert.equal(h.enabled,false);assert.equal(hazeMixAt(h,1000),0);
});
test('limb thickness is the pack fraction of the planet radius and grows with atmosphere; rim is brightest at the sunward limb and goes golden when the sun is low',()=>{
 const a=limbRim(.3),b=limbRim(.85);assert.ok(b.thicknessFrac>a.thicknessFrac&&a.thicknessFrac>0);assert.equal(b.thicknessFrac,pairTable(A.limb_rim.thick.thickness_frac_radius_by_atmo,.85));
 assert.ok(limbAt(.85,1).alpha>limbAt(.85,0).alpha&&limbAt(.85,0).alpha>limbAt(.85,-1).alpha);
 const hi=limbAt(.85,.9),lo=limbAt(.85,.05);assert.ok(lo.colour[0]>lo.colour[2]*1.2,'golden low sun');assert.ok(hi.colour[2]>hi.colour[0],'blue high sun');
 assert.ok(limbAt(.55,.5).alpha<=limbAt(.85,.5).alpha,'mid gain 0.8');
});
test('fog multiplier equals the pack rule 1 + a*moisture + b*storm + c*moisture*storm at the grid points, rises with moisture and storm',()=>{
 for(const [atmo,k] of [[.85,'thick'],[.55,'mid']]){const m=A.const_block.fog_density_mul[k];
  for(const x of [0,.25,.5,.75,1])for(const s of [0,.25,.5,.75,1])assert.ok(Math.abs(fogMul(atmo,x,s)-(1+m.moisture*x+m.storm*s+m.cross*x*s))<1e-3,k+x+s);}
 assert.equal(fogMul(.85,0,0),1);assert.ok(fogMul(.85,.6,.2)>fogMul(.85,.3,.2));assert.ok(fogMul(.85,.3,.8)>fogMul(.85,.3,.2));
 assert.ok(stormHaze(.85,1).mix>stormHaze(.85,.3).mix);assert.equal(stormHaze(.85,0).mix,0);assert.ok(stormHaze(.85,1).mix<=A.const_block.storm_haze_mix_max+1e-9);
});
test('haze mix follows the pack curve at its distance stops; far mix is capped; night is denser than day',()=>{
 const day=hazeFor({atmo:.85,sunElevSin:.8,nightFactor:0});
 for(const [d,m] of A.haze_by_class.thick.day.mix_by_distance)assert.ok(Math.abs(hazeMixAt(day,d)-m)<0.003,'d='+d+' '+hazeMixAt(day,d)+' vs '+m);
 assert.ok(hazeMixAt(day,5000)<=A.const_block.far_mix_cap+1e-12);
 const night=hazeFor({atmo:.85,sunElevSin:-.5,nightFactor:1});assert.ok(night.density>day.density);
 const wet=hazeFor({atmo:.85,sunElevSin:.8,nightFactor:0,moisture:1,storm:1});assert.ok(wet.density>day.density*3.9);
});
test('GLSL table text (rim alpha, golden mix) equals the CPU tables',()=>{
 const r=A.limb_rim.thick;const a=evalTable('rimAlpha',r.alpha_by_sun_limb_cos),g=evalTable('rimGold',r.golden_hour_mix_by_sun_elev_sin);
 for(const s of [-1,-.5,-.2,0,.1,.3,.45,.8,1,2]){assert.ok(Math.abs(a(s)-pairTable(r.alpha_by_sun_limb_cos,s))<1e-9);assert.ok(Math.abs(g(s)-pairTable(r.golden_hour_mix_by_sun_elev_sin,s))<1e-9);}
});
test('same inputs twice = same atmosphere; no clock, no Math.random',()=>{
 const i={atmo:.85,sunElevSin:.1,nightFactor:.2,moisture:.4,storm:.3};assert.deepEqual(hazeFor(i),hazeFor({...i}));
 const src=readFileSync(new URL('../lib/universe/atmosphere-look.mjs',import.meta.url),'utf8').split('\n').filter(l=>!l.trim().startsWith('//')).join('\n');assert.ok(!/Math\.random|Date\.now|performance\.now|new Date/.test(src));
});
