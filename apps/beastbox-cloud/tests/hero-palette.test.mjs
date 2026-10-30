import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {palette,planetType,biomeHero,heroLegend} from '../lib/universe/hero-palette.mjs';
import {VL_HERO} from '../lib/universe/vislife-look-data.mjs';
const l2s=v=>v<=0.0031308?12.92*v:1.055*Math.pow(v,1/2.4)-0.055;
const byte=v=>Math.round(255*l2s(Math.max(0,Math.min(1,v))));
const hexOf=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16));
const PL=Object.entries(VL_HERO.palette_by_planet);
test('palette(planet) reproduces the pack for all 17 recorded planets (colours within 2 levels, weights within 0.003)',()=>{
 assert.equal(PL.length,17);
 for(const [id,pj] of PL){const i=pj.inputs,p=palette({atmosphere:i.atmosphere,temperature_k:i.temperature_k,water:i.water,hue:i.host_star_hue});
  assert.equal(p.type,pj.type,id);assert.equal(p.hero_role,pj.hero_role,id);
  for(const r of Object.keys(p.colours)){if(!p.colours[r]){assert.equal(pj.colours[r],null,id+r);continue;}const want=hexOf(pj.colours[r].hex);p.colours[r].forEach((v,k)=>assert.ok(Math.abs(byte(v)-want[k])<=2,id+' '+r));}
  for(const r of Object.keys(p.weights))assert.ok(Math.abs(p.weights[r]-pj.weights[r])<=0.003,id+' w '+r);}
});
test('one hero: its share never falls under hero_floor and the weights sum to 1',()=>{
 for(const [id,pj] of PL){const i=pj.inputs,p=palette({atmosphere:i.atmosphere,temperature_k:i.temperature_k,water:i.water,hue:i.host_star_hue});
  assert.ok(p.weights[p.hero_role]>=VL_HERO.const_block.hero_floor-1e-9,id);assert.ok(Math.abs(Object.values(p.weights).reduce((a,b)=>a+b,0)-1)<1e-9);}
 for(const [a,T,w] of [[0.5,300,1],[0.5,300,0],[0.9,500,0.5],[0.02,100,0.5],[0.5,800,0.9]]){const p=palette({atmosphere:a,temperature_k:T,water:w,hue:0.3});assert.ok(p.weights[p.hero_role]>=0.34-1e-9);}
});
test('temperate worlds put the water colour first, near the pack turquoise',()=>{const p=palette({atmosphere:0.6,temperature_k:290,water:0.7,hue:0.5});assert.equal(p.type,'temperate');assert.equal(p.hero_role,'water');const h=p.hero.map(byte);assert.ok(Math.abs(h[0]-0x1A)<=8&&Math.abs(h[1]-0xA0)<=8&&Math.abs(h[2]-0xB8)<=8,h.join());});
test('type rule matches the pack order',()=>{assert.equal(planetType({atmosphere:0.01,temperature_k:300,water:1}),'moon');assert.equal(planetType({atmosphere:0.5,temperature_k:700,water:0}),'volcanic');assert.equal(planetType({atmosphere:0.5,temperature_k:150,water:1}),'ice');assert.equal(planetType({atmosphere:0.5,temperature_k:300,water:0.1}),'ice');assert.equal(planetType({atmosphere:0.5,temperature_k:400,water:1}),'desert');});
test('same input, same output: the orbit and first-person calls are one function (deterministic, no mutation)',()=>{
 const p={atmosphere:0.4,temperature_k:310,water:0.6,hue:0.7};const s=JSON.stringify(p);const orbit=palette(p),fp=palette({...p});assert.deepEqual(orbit,fp);assert.equal(JSON.stringify(p),s);assert.deepEqual(palette(p),palette(p));
});
test('no Math.random / Date, and biome legend falls back to the biome rgb when the pack has none',()=>{
 const src=fs.readFileSync(new URL('../lib/universe/hero-palette.mjs',import.meta.url),'utf8').replace(/^\s*\/\/.*$/gm,'');assert.ok(!/Math\.random|Date\.|performance\.now|requestAnimationFrame/.test(src));
 assert.equal(biomeHero('temperate','grassland'),VL_HERO.biome_table.grassland.hero_by_type.temperate.hex);assert.equal(biomeHero('moon','deep_ocean'),null);
 const lg=heroLegend('moon',[{id:'deep_ocean',rgb:'#1B2F7A'},{id:'beach',rgb:'#F0D9A0'}]);assert.equal(lg[0],'#1B2F7A');assert.equal(lg[1],VL_HERO.biome_table.beach.hero_by_type.moon.hex);
});
