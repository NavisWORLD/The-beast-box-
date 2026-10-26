// Visual Life Pass B5: ONE hero-colour palette function, read by the orbit globe and the first-person ground (the same renderer, the same uniforms).
// Source: Cosmo's look pack (vislife.json HERO, sha256 in vislife-look-data.mjs). SEEDED look, never a measurement; the inputs are the engine's own planet numbers
// (atmosphere, temperature_k, water, and the host star's hue). Pure: no clock, no Math.random. Rule: one hero colour per planet, supports serve the hero (hero share >= hero_floor).
import {VL_HERO} from './vislife-look-data.mjs';
const H=VL_HERO,C=H.const_block,ROLES=H.function.roles;
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
const s2l=v=>v<=0.04045?v/12.92:Math.pow((v+0.055)/1.055,2.4);
const h2l=h=>[1,3,5].map(i=>s2l(parseInt(h.slice(i,i+2),16)/255));
const hueRot=(c,deg)=>{const a=deg*Math.PI/180,ca=Math.cos(a),sa=Math.sin(a),k=1/Math.sqrt(3),d=k*(c[0]+c[1]+c[2]);const cr=[k*(c[2]-c[1]),k*(c[0]-c[2]),k*(c[1]-c[0])];return [0,1,2].map(i=>c[i]*ca+cr[i]*sa+k*d*(1-ca));};
/** The type rule (const_block.type_rule), the same order as the recorded planet assignments. */
export function planetType({atmosphere,temperature_k,water}){const a=+atmosphere,T=+temperature_k,w=+water;if(a<0.05)return 'moon';if(T>=700)return 'volcanic';if(T<=150)return 'ice';if(T<=350)return w>=0.15?'temperate':'ice';return 'desert';}
/** palette({atmosphere,temperature_k,water,hue}) -> {type,class,hero_role,hero,colours{role:[r,g,b]|null} (linear),weights,tilt,waterRamp|null}. Same output for orbit and first person by construction. */
export function palette(p){
 const ty=planetType(p),row=H.table[ty],tc=C.temperature_tilt,hr=C.hue_rotation;
 const T=+p.temperature_k;const tilt=clamp(Math.log10(T/tc.ref_k)/tc.span_log10,-1,1);const tgt=h2l(tilt>0?tc.warm_hex:tc.cool_hex);
 const hue=Number.isFinite(+p.hue)?+p.hue:hr.host_star_hue_ref;const deg=(hue-hr.host_star_hue_ref)*2;
 const colours={};
 for(const r of ROLES){if(!row[r]){colours[r]=null;continue;}const isH=r===row.hero_role;let c=row[r].linear;const m=(isH?tc.max_mix_hero:tc.max_mix_supports)*Math.abs(tilt);c=c.map((x,i)=>x+(tgt[i]-x)*m);c=hueRot(c,deg*(isH?hr.max_deg_hero:hr.max_deg_supports));colours[r]=c.map(v=>clamp(v,0,1));}
 const W=H.function.weights_table[ty];let w={};for(const r of ROLES)w[r]=Math.max(0,W.base[r]+(W.k_water[r]||0)*(+p.water-W.water_ref));
 let s=ROLES.reduce((a,r)=>a+w[r],0);for(const r of ROLES)w[r]/=s;
 if(w[row.hero_role]<C.hero_floor){const rest=ROLES.reduce((a,r)=>a+(r===row.hero_role?0:w[r]),0);for(const r of ROLES)w[r]=r===row.hero_role?C.hero_floor:w[r]*(1-C.hero_floor)/rest;}
 let waterRamp=null;if(colours.water){const wc=colours.water,lo=[0.62,0.86,0.90],dp=[0.02,0.08,0.28];waterRamp={shallow:wc.map((x,i)=>x+(lo[i]-x)*0.38),mid:wc,deep:wc.map((x,i)=>(x+(dp[i]-x)*0.45)*0.55)};}
 return {type:ty,class:row.class,hero_role:row.hero_role,hero:colours[row.hero_role],colours,weights:w,tilt,waterRamp};
}
/** sRGB hex colour for a biome on a planet type: the pack's biome hero (muted rock and grass, water takes the type water). null when the pack has none (e.g. water biomes on a moon). */
export function biomeHero(type,biomeId){const b=H.biome_table[biomeId];const c=b&&b.hero_by_type[type];return c?c.hex:null;}
/** The legend for the shader: for each biome id in `biomes` ([{id,rgb}]) the pack hero hex for this planet type, or the biome's own rgb when the pack has none. */
export function heroLegend(type,biomes){return biomes.map(b=>biomeHero(type,b.id)||b.rgb);}
