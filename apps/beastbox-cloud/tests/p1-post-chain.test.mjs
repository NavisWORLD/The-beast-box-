import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {P1POST} from '../lib/universe/data/p1post.mjs';
import {TIERS,autoTier,activeTier,readTierOverride,writeTierOverride,nextTier,tierSettings,qualityLabel,bloomThresholdPreExposure,QUALITY_KEY} from '../lib/universe/post-tiers.mjs';
import {sunVisible,grainSeed,createGraphicsState,stepGraphicsState,GRAPHICS_STATE_KEYS} from '../lib/universe/graphics-state.mjs';
import {GOD_RAYS_FRAG,OPTICS_FRAG} from '../lib/universe/post-shaders.mjs';
import {lightRigFor} from '../lib/universe/sky-view.mjs';
import {oneSunAt} from '../lib/universe/one-sun.mjs';
import {worldLightFrom} from '../lib/cosmos/sight.mjs';
const src=f=>fs.readFileSync(new URL('../'+f,import.meta.url),'utf8');
const mem=()=>{const m=new Map();return {getItem:k=>m.has(k)?m.get(k):null,setItem:(k,v)=>m.set(k,String(v)),removeItem:k=>m.delete(k)};};

test('the pack module matches Cosmo\'s p1post.json values (never hand-tuned)',()=>{
 assert.equal(P1POST.pack,'p1post');assert.equal(P1POST.label,'SEEDED');
 for(const t of TIERS){assert.ok(P1POST.tiers[t],t);assert.equal(tierSettings(t).optics.exposure,0.85);assert.equal(tierSettings(t).optics.tone_mapping,'ACESFilmic');}
 assert.equal(tierSettings('MED').god_rays.samples,12);assert.equal(tierSettings('GOD').god_rays.samples,32);
 assert.equal(tierSettings('LOW').bloom.enabled,false);
});
test('tiers: cost never drops LOW->GOD, bloom threshold never rises, MED is the default',()=>{
 for(let i=1;i<TIERS.length;i++){const a=tierSettings(TIERS[i-1]),b=tierSettings(TIERS[i]);
  assert.ok(b.god_rays.samples>=a.god_rays.samples);assert.ok(b.bloom.strength>=a.bloom.strength);assert.ok(b.bloom.threshold<=a.bloom.threshold);assert.ok(b.budget.max_dpr>=a.budget.max_dpr);}
 assert.equal(tierSettings('nonsense'),tierSettings('MED'));
});
test('auto-detect plus a remembered manual override, and the Quality chip label',()=>{
 assert.equal(autoTier({phone:true,cores:8,memoryGB:6}),'MED');assert.equal(autoTier({phone:true,cores:4,memoryGB:2}),'LOW');
 assert.equal(autoTier({cores:12,memoryGB:16}),'GOD');assert.equal(autoTier({softGL:true,cores:16,memoryGB:32}),'LOW');assert.equal(autoTier({cores:6,memoryGB:4}),'HIGH');
 const s=mem();assert.equal(readTierOverride(s),null);assert.equal(activeTier(s,{phone:true,cores:8,memoryGB:8}),'MED');
 writeTierOverride(s,'GOD');assert.equal(s.getItem(QUALITY_KEY),'GOD');assert.equal(activeTier(s,{phone:true}),'GOD');
 writeTierOverride(s,'bogus');assert.equal(readTierOverride(s),null);
 assert.deepEqual(TIERS.map(nextTier),['MED','HIGH','GOD','LOW']);
 for(const t of TIERS)assert.equal(qualityLabel(t),`Quality: ${t}`);
});
test('GRASS-BRIGHTNESS GATE: the brightest lit grass tip stays under every tier\'s bloom threshold (bloom only ships if this passes)',()=>{
 const lin=h=>[0,2,4].map(i=>{const c=parseInt(h.slice(1+i,3+i),16)/255;return c<=.04045?c/12.92:((c+.055)/1.055)**2.4;});
 const a=lin('#8B9B55'),b=lin('#B5A45A');const tip=a.map((v,i)=>v+(b[i]-v)*.4);const Y=c=>.2126*c[0]+.7152*c[1]+.0722*c[2];
 // worst case: noon, sun straight onto the blade, the one-sun rig (lightRigFor) at full day, white sun (brighter than the real warm sun)
 const noon=oneSunAt(60);const rig=lightRigFor({...noon,day:1},0.85);
 const lit=tip.map((v,i)=>v*(rig.sunIntensity+rig.hemiIntensity*rig.hemiColor[i]));const worst=Y(lit)*rig.exposure;
 const measured=Math.max(worst,P1POST.glare_budget.grass_tip_scene_lum_worst);
 for(const t of TIERS){const th=tierSettings(t).bloom.threshold;
  assert.ok(th>=1.25*measured-1e-4,`${t}: threshold ${th} must be >= 1.25 x grass tip ${measured.toFixed(4)}`);
  assert.ok(th>P1POST.glare_budget.sky_horizon_lum,`${t}: above the sky horizon`);
  assert.ok(Math.abs(bloomThresholdPreExposure(t)*0.85-th)<1e-9);}
});
test('sun gate: smoothstep(-2,6,elev) x on_screen x (1 - occluded); off below the horizon and off screen',()=>{
 assert.equal(sunVisible(-5,[0,0]),0);assert.equal(sunVisible(30,[0,0]),1);assert.equal(sunVisible(30,[1.5,0]),0);
 assert.equal(sunVisible(30,[0,0],1),0);assert.equal(sunVisible(30,null),0);assert.ok(sunVisible(2,[0,0])>0&&sunVisible(2,[0,0])<1);
});
test('god rays only ADD to the frame (never GENESIS X\'s whole-frame multiply) and gate on brightness',()=>{
 const g=GOD_RAYS_FRAG(12);assert.match(g,/base\.rgb\+rays\*uExposure\*uSunVisible/);assert.doesNotMatch(g,/color\s*\*\s*uExposure/);
 assert.match(g,/smoothstep\(uGate\.x,uGate\.y,l\)/);assert.match(g,/i<12;/);
});
test('grain is seeded from a hashed frame counter, deterministic, and nothing ported uses Math.random',()=>{
 assert.equal(grainSeed(7),grainSeed(7));assert.notEqual(grainSeed(7),grainSeed(8));for(let f=0;f<50;f++){const g=grainSeed(f);assert.ok(g>=0&&g<1);}
 assert.match(OPTICS_FRAG,/uGrainSeed/);
 for(const f of ['lib/universe/post-tiers.mjs','lib/universe/graphics-state.mjs','lib/universe/post-shaders.mjs','lib/universe/post-chain-three.ts','lib/universe/data/p1post.mjs','lib/world/view-mode.mjs'])
  assert.doesNotMatch(src(f).replace(/never Math\.random|not from a random call|no Math\.random[^\n]*/gi,''),/Math\.random/,f);
});
test('shared graphics state: GENESIS_UNIFORMS keys, fed by the one sun, never owning the clock',()=>{
 const g=createGraphicsState();for(const k of GRAPHICS_STATE_KEYS)assert.ok(k in g,k);
 const s=stepGraphicsState(g,{time:12,frame:3,sunDir:[0,1,0],sunElevDeg:40,sunNdc:[0,0],playerPos:[1,2,3]});
 assert.equal(s.uSunVisible,1);assert.deepEqual(s.uPlayerPos,[1,2,3]);assert.equal(s.uTime,12);
 assert.doesNotMatch(src('lib/universe/graphics-state.mjs'),/Date\.now|performance\.now/);
});
test('the post chain upgrades the one-sun rig: order render, god rays, bloom, optics, output; ACES at pack exposure',()=>{
 const c=src('lib/universe/post-chain-three.ts');
 const order=['new RenderPass(scene','GOD_RAYS_FRAG(s.','new UnrealBloomPass(new','fragmentShader:OPTICS_FRAG','new OutputPass()'].map(k=>c.indexOf(k));
 assert.ok(order.every(i=>i>0));assert.deepEqual([...order].sort((a,b)=>a-b),order);
 assert.match(c,/ACESFilmicToneMapping/);assert.match(c,/toneMappingExposure=o\.exposure/);
 const lw=src('components/living-world.tsx');assert.match(lw,/createPostChain/);assert.match(lw,/post\.render\(sunDisc\.position/);
 assert.doesNotMatch(c,/COMPANION|compDisc/,'the companion disc never casts rays');
 assert.doesNotMatch(c+src('lib/universe/post-shaders.mjs'),/AI CONSCIOUSNESS|real physics/i);
});
test('lightRigFor reads the one sun only (sun 3.03 x day, hemi .6 x day + .15)',()=>{
 const r=lightRigFor({day:.5,elevationDeg:10,sky:{zenith:[0,0,0],horizon:[1,1,1]}});
 assert.equal(r.label,'DERIVED');assert.ok(Math.abs(r.sunIntensity-1.515)<1e-9);assert.ok(Math.abs(r.hemiIntensity-.45)<1e-9);assert.deepEqual(r.hemiColor,[.5,.5,.5]);
 assert.equal(lightRigFor({day:0}).sunIntensity,0);
});
const SIGHT_SNAPSHOT=[{"brightness":0.81,"band":"bright","trend":"rising","feeling":"joy","event":"the lights getting bright","hue_family":"blue","sun_elev":0.28,"day_weight":1},{"brightness":0.81,"band":"bright","trend":"rising","feeling":"joy","event":"the lights getting bright","hue_family":"blue","sun_elev":0.32,"day_weight":1},{"brightness":0.81,"band":"bright","trend":"rising","feeling":"joy","event":"the lights getting bright","hue_family":"blue","sun_elev":0.33,"day_weight":1},{"brightness":0.81,"band":"bright","trend":"steady","feeling":"calm","event":null,"hue_family":"blue","sun_elev":0.32,"day_weight":1},{"brightness":0.81,"band":"bright","trend":"steady","feeling":"calm","event":null,"hue_family":"blue","sun_elev":0.3,"day_weight":1},{"brightness":0.82,"band":"bright","trend":"steady","feeling":"calm","event":null,"hue_family":"blue","sun_elev":0.25,"day_weight":1},{"brightness":0.82,"band":"bright","trend":"steady","feeling":"calm","event":null,"hue_family":"blue","sun_elev":0.19,"day_weight":1},{"brightness":0.79,"band":"bright","trend":"falling","feeling":"calm","event":null,"hue_family":"blue","sun_elev":0.11,"day_weight":0.87},{"brightness":0.69,"band":"bright","trend":"falling","feeling":"calm","event":null,"hue_family":"orange","sun_elev":0.02,"day_weight":0.42},{"brightness":0.51,"band":"soft","trend":"falling","feeling":"fear","event":"the lights going dark","hue_family":"orange","sun_elev":-0.07,"day_weight":0.03},{"brightness":0.34,"band":"dim","trend":"falling","feeling":"fear","event":"the lights going dark","hue_family":"orange","sun_elev":-0.16,"day_weight":0},{"brightness":0.22,"band":"dim","trend":"falling","feeling":"fear","event":"the lights going dark","hue_family":"rose","sun_elev":-0.23,"day_weight":0}];
test('SIGHT-SAME-SKY: sight\'s DERIVED world light still comes from the engine skyAt(), unchanged by the post chain',()=>{
 const s=src('lib/cosmos/sight.mjs');assert.match(s,/import \{skyAt\} from '\.\.\/universe\/sky-state\.mjs'/);
 for(const f of ['lib/universe/post-chain-three.ts','lib/universe/post-tiers.mjs','lib/universe/graphics-state.mjs'])assert.doesNotMatch(src(f),/sky-state|sight\.mjs/,f);
 const out=[];for(let p=0;p<240;p+=20)out.push(worldLightFrom({links:{liveTick:{state:'UP'}},at_ms:p*1000},p*1000));
 assert.deepEqual(out,SIGHT_SNAPSHOT);
});
