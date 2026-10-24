/**
 * Growth nodes, VIEW math (pure, no DOM, no clock, no Math.random). Placement is SEEDED, growth speed rides the SIMULATED tick signal
 * (Rigetti Bell simulator, not hardware), genesis stays RECORDED. Nothing here claims live quantum or recorded growth.
 * Colour data is Cosmo's growth tint pack v1 (growth-tint-data.mjs): blend the asset's own base colour TOWARD the stage tint in linear
 * light (never multiply), with the kind's mix_scale. Scale, tint, fruit, shed and desaturation all read ONE growthCellAt() result, so
 * they can never disagree. The three.js side is lib/universe/surface-three.ts (instance attributes) and growth-three.ts (fruit, shed).
 */
import {GROWTH_TINT as P} from './growth-tint-data.mjs';
import {growthCellAt,GROWTH,NODE_STAGES} from './seeded-growth-nodes.mjs';
import {gaussianAffinity} from '../companion/spark/engine.mjs';
import {lwStream} from './living-world.mjs';

/** asset key -> growth layer (succession order: ring first, canopy last). Alive/dead props that should not grow (rocks, crystals, dead_ember) are absent. */
export const GROWTH_LAYER=Object.freeze({
 grass_tuft_a:'ring',grass_tuft_b:'ring',grass_tall_c:'ring',
 flower_pink:'patch',flower_gold:'patch',mushroom_single:'patch',mushroom_cluster:'patch',
 'tree:olive_meadow':'shrub','tree:crystal_leaf':'shrub',
 'tree:teal_round':'canopy','tree:teal_conifer':'canopy','tree:purple_glow':'canopy','tree:snow_conifer':'canopy','tree:giant_heartwood':'canopy',
});
export const TINT_BIOMES=Object.freeze([...P.biomes]);
/** Legend biomes the pack has no row for borrow the nearest pack biome (colour only). */
export const BIOME_ALIAS=Object.freeze({pine_forest:'heartwood_forest',savanna:'grassland',beach:'grassland',jelly_geyser:'paper_marsh',ember_fields:'grassland',mountain_rock:'grassland'});
export const tintBiome=b=>P.biomes.includes(b)?b:(BIOME_ALIAS[b]||'grassland');
/** The material names the tint touches: full strength, half strength (tips), never. */
export const TINT_STRENGTH=name=>P.apply_to_materials.includes(name)?1:P.apply_half_strength.includes(name)?.5:0;
export const FRUIT_LAYERS=Object.freeze([...P.fruit.applies_to_kinds]);
export const TAP_MS=600;
export const LEAN_MAX_DEG=4;// affinity lean at full affinity, a few degrees

const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const lerp=(a,b,t)=>a+(b-a)*t;
const smooth=t=>{t=clamp(t);return t*t*(3-2*t);};
export const srgbToLinear=c=>c<=0.04045?c/12.92:Math.pow((c+0.055)/1.055,2.4);
export const hexToLinear=h=>{const n=parseInt(h.slice(1),16);return [srgbToLinear((n>>16&255)/255),srgbToLinear((n>>8&255)/255),srgbToLinear((n&255)/255)];};
const mixRGB=(a,b,t)=>[lerp(a[0],b[0],t),lerp(a[1],b[1],t),lerp(a[2],b[2],t)];

/** Blend a base colour toward a tint in LINEAR light (the pack's rule; multiplying cannot turn teal into gold). */
export const blendLinear=(base,tint,m)=>mixRGB(base,tint,clamp(m));

/**
 * Tint for one cell: {rgb (linear), mix}. Inside the blend window of a stage the colour moves from the previous stage's colour to this one's
 * (smoothstep, windows of gold/shed move earlier with the node's gold start, as the pack describes for scarred nodes). scars>0 add the pack's
 * gold_bias toward the gold colour during full/bloom. mix = mix_by_stage (blended the same way) * the kind's mix_scale.
 */
export function tintFor(biome,layer,stage,x,{gold=GROWTH.goldAfter,scars=0}={}){
 const b=tintBiome(biome),i=NODE_STAGES.indexOf(stage);if(i<0||!P.resolved[b]?.[layer])return {rgb:[1,1,1],mix:0};
 const w=P.lerp.blend_by_stage[stage];const delta=(stage==='gold'||stage==='shed')?gold-GROWTH.goldAfter:0;
 const f=w.ease==='hold'||x==null?1:smooth((x-(w.x0+delta))/Math.max(1e-6,(w.x1-w.x0)));
 const to=hexToLinear(P.resolved[b][layer][stage]),prev=NODE_STAGES[Math.max(0,i-1)];
 const from=i>0?hexToLinear(P.resolved[b][layer][prev]):to;let rgb=mixRGB(from,to,f);
 let mix=lerp(P.mix_by_stage[prev],P.mix_by_stage[stage],f)*(P.kind_overrides[layer]?.mix_scale??1);
 if(scars>0&&(stage==='full'||stage==='bloom'))rgb=mixRGB(rgb,hexToLinear(P.resolved[b][layer].gold),P.desaturation.scarred.gold_bias);
 return {rgb,mix:clamp(mix)};
}
/** Desaturation 0..0.3: storm shiver (shrub + canopy only, 0 to 0.22 by tension) + scarred nodes (0.15), capped. */
export function desatAmount(layer,storm,scarred){
 const s=(layer==='shrub'||layer==='canopy')?P.desaturation.storm_shiver.max*clamp(storm):0;
 return Math.min(P.desaturation.total_cap,s+(scarred?P.desaturation.scarred.amount:0));
}
/** Linear emissive colour added to foliage for a stage (already scaled: stage * kind mul, +tap pulse, total <= max_total). */
/** Linear emissive tint colour for a stage (the shader multiplies it by the packed strength). */
export function emissiveTintLinear(stage){const c=P.emissive_boost_linear.emissive_tint_by_stage[stage];return c?hexToLinear(c):[0,0,0];}
export function emissiveAdd(layer,stage,tap=0){
 const e=P.emissive_boost_linear;const a=Math.min(e.max_total,(e.by_stage[stage]||0)*(e.by_kind_mul[layer]||1)+(tap>0?e.tap_pulse_add*clamp(tap):0));
 const c=e.emissive_tint_by_stage[stage];if(!c||a<=0)return [0,0,0];const l=hexToLinear(c);return [l[0]*a,l[1]*a,l[2]*a];
}
/** Fruit density 0..1 = kind * biome_mul * stage_mul; 0 outside shrub and canopy. Fades in across the bloom blend window. */
export function fruitDensity(biome,layer,stage,x=null,gold=GROWTH.goldAfter){
 const F=P.fruit;if(!F.applies_to_kinds.includes(layer))return 0;
 let sm=F.density_by_stage_mul[stage]||0;
 if(stage==='bloom'&&x!=null){const w=P.lerp.blend_by_stage.bloom;sm*=smooth((x-w.x0)/(w.x1-w.x0));}
 return clamp(F.density_by_kind[layer]*(F.density_by_biome_mul[tintBiome(biome)]||1)*sm);
}
/** Shed-leaf particle recipe for a layer (metres, m/s, s) plus the four golds as linear colours. */
export const shedRecipe=layer=>({...P.shed_particles.by_kind[layer],colors:P.shed_particles.colors.map(hexToLinear),emissive:P.shed_particles.emissive_linear,fadeOutLast:P.shed_particles.fade_out_last_fraction});
export const fruitPalette=()=>({colors:P.fruit.palette.map(hexToLinear),weights:[...P.fruit.palette_weights],sizeM:[...P.fruit.speck_size_m],emissive:P.fruit.emissive_linear});
export const CANOPY_SPILL=Object.freeze({...P.canopy_spill});

/**
 * ONE instance: scale multiplier (growthCellAt, per-layer lag), tint, mix, desat, emissive, fruit, stage. Identity outside every territory
 * (scale 1, mix 0), so instances away from a node are exactly what plantGround/plantTrees built.
 */
export function instanceGrowth(nodes,tick,dir,layer,biome,{cellRad=GROWTH.cellRad,storm=0,tap=0}={}){
 const c=growthCellAt(nodes,tick,dir,{layer,cellRad});
 if(!c.hit)return {hit:false,scale:1,rgb:[1,1,1],mix:0,desat:0,emissive:[0,0,0],fruit:0,stage:null,x:null,scarred:false,node:null};
 const stage=c.stage||'sprout',t=tintFor(biome,layer,stage,c.x,{gold:c.gold,scars:c.scars});
 return {hit:true,scale:c.scale,rgb:t.rgb,mix:c.x==null?0:t.mix,desat:desatAmount(layer,storm,c.scars>0),emissive:emissiveAdd(layer,stage,tap),fruit:fruitDensity(biome,layer,stage,c.x,c.gold),stage,x:c.x,scarred:c.scars>0,node:c.node};
}

/** Scale bounce on a tap, view state only: 1 + 0.18 * damped sine over TAP_MS; 0 under reduced motion. */
export function tapBounce(ageMs,reduced=false){if(reduced||ageMs<0||ageMs>=TAP_MS)return 0;const t=ageMs/TAP_MS;return .18*Math.sin(t*Math.PI*2.5)*(1-t)*(1-t)*1.6;}
/** 0..1 tap glow used for the emissive pulse (not motion, so it stays under reduced motion). */
export const tapGlow=ageMs=>ageMs<0||ageMs>=TAP_MS*1.5?0:1-ageMs/(TAP_MS*1.5);

/** Affinity lean in degrees: gaussianAffinity(distance in metres / R, 0) -- the engine's own kernel -- times LEAN_MAX_DEG, signed by the node's seeded lean. 0 when reduced. */
export function leanAffinity(distM,sigmaM=2.2){return gaussianAffinity([distM],[0],sigmaM);}

/** Tap key into Emeth's creature_notices (growth_tap_*): scarred wins, a canopy node that is full or later says canopy, tuft reads as sprout. */
export function tapNoticeKey(cell){
 if(!cell?.stage)return null;if(cell.scarred)return 'growth_tap_scarred';
 if(cell.node?.kind==='canopy'&&(cell.stage==='full'||cell.stage==='bloom'))return 'growth_tap_canopy';
 return 'growth_tap_'+(cell.stage==='tuft'?'sprout':cell.stage);
}
/** A tap on a node's territory: the closest node within its spread (radians via cellRad). Returns {node,cell} or null. */
export function tapNode(nodes,tick,dir,{cellRad=GROWTH.cellRad}={}){
 const c=growthCellAt(nodes,tick,dir,{cellRad,layer:'ring'});if(!c.hit||c.dc>c.node.spread)return null;
 return {node:c.node,cell:{stage:c.stage,scarred:c.scars>0,node:c.node,x:c.x}};
}

const unit=(lat,lon)=>{const a=lat*Math.PI/180,o=lon*Math.PI/180;return [Math.cos(a)*Math.cos(o),Math.sin(a),Math.cos(a)*Math.sin(o)];};
const fromUnit=v=>({lat:Math.asin(clamp(v[1],-1,1))*180/Math.PI,lon:Math.atan2(v[2],v[0])*180/Math.PI});
/**
 * The home planet's nodes live on the one Living World sphere. Where a SEEDED spot falls on water or bare ground, the VIEW moves it to the nearest
 * habitat the tint pack covers (deterministic ring search, no draws); the engine placement is untouched and the node keeps label SEEDED plus
 * view_snapped:true. Nothing is invented: if no habitat is within maxRad the node is dropped from the view.
 * @param {any[]} nodes @param {(dir:number[])=>boolean} habitat @param {{maxRad?:number}} [o]
 */
export function snapNodesToHabitat(nodes,habitat,{maxRad=1.3}={}){
 const out=[];
 for(const n of nodes){
  const c=unit(n.lat,n.lon);if(habitat(c)){out.push({...n,view_snapped:false});continue;}
  const e1=Math.hypot(c[0],c[2])>1e-6?[-c[2]/Math.hypot(c[0],c[2]),0,c[0]/Math.hypot(c[0],c[2])]:[1,0,0];
  const e2=[c[1]*e1[2]-c[2]*e1[1],c[2]*e1[0]-c[0]*e1[2],c[0]*e1[1]-c[1]*e1[0]];let hit=null;
  for(let r=0.04;r<=maxRad&&!hit;r+=0.04)for(let k=0;k<24&&!hit;k++){const a=k/24*Math.PI*2+r*7.1;
   const d=[0,1,2].map(i=>c[i]*Math.cos(r)+(e1[i]*Math.cos(a)+e2[i]*Math.sin(a))*Math.sin(r));if(habitat(d))hit=d;}
  if(hit){const p=fromUnit(hit);out.push({...n,lat:+p.lat.toFixed(4),lon:+p.lon.toFixed(4),view_snapped:true});}
 }
 return out;
}
/** Seeded fruit speck offsets (unit crown coordinates): per tree, `per` specks as [x,y,z,palette draw, threshold]. Fixed 5 draws per speck; stream lwStream(seed+':growth-fruit'). */
export function fruitOffsets(seed,trees,per=6){
 const r=lwStream(String(seed)+':growth-fruit');const out=new Float32Array(trees*per*5);
 for(let i=0;i<trees*per;i++){const th=r()*Math.PI*2,u=r()*2-1,ry=r(),pal=r(),thr=r();const s=Math.sqrt(1-u*u);
  out[i*5]=s*Math.cos(th);out[i*5+1]=0.55+0.35*ry;out[i*5+2]=s*Math.sin(th);out[i*5+3]=pal;out[i*5+4]=thr;}
 return out;
}
