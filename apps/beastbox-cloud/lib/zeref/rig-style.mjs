/**
 * Rig skins: the high-quality ZEREF vector rig for every habitat beast.
 *
 * - The site's Zeref (or a saved beast named Zeref) wears Cory's canonical
 *   Moonwraith palette from the sprite atlas / character card.
 * - Any other Spark Beast gets a comparable rig variant tinted and featured
 *   from ITS OWN recorded-seed genome (island palette + hue/sat/val genes,
 *   wings, ears/horns, tail, glow). Purely visual: identity, stats and saves
 *   are untouched.
 */
import {paletteOf} from '../../public/spark/draw.mjs';
import {sha256Hex} from '../../public/spark/sha.mjs';
import {ZEREF_PROFILE} from './zeref-mind.mjs';

const hex=rgb=>'#'+rgb.map(c=>Math.max(0,Math.min(255,Math.round(c))).toString(16).padStart(2,'0')).join('');
const mix=(a,b,t)=>a.map((v,i)=>v+(b[i]-v)*t);
const dark=(rgb,k)=>rgb.map(v=>v*k);

export const ZEREF_SKIN=Object.freeze({
 canonical:true,fur:['#3a2a5e','#1d1430','#0b0714'],furSolid:'#160f24',lid:'#21163a',stroke:'#5b3b96',
 ear:['#d6b4ff','#7a46d8'],iris:['#f0e2ff','#c69bff','#7b3cf0','#2a0d5e'],wing:['#3c1d78','#8a4ff0','#8fe8ff'],
 moon:['#fbf6ff','#bfa0ff'],tail:['#0d0818','#24173f','#6b3fd0'],beans:'#b98aff',brow:'#7a5bb5',mouth:'#d6b8ff',
 accent:'#b57bff',glow:'#8fe8ff',
 features:Object.freeze({wings:true,moonHorns:true,crescent:true,horns:false,tailTip:'wisp'})
});

export function isZerefBeast({id,name}={}){
 return id===ZEREF_PROFILE.id||/\bzeref\b/i.test(String(name||''));
}

/** Genome -> rig skin. Returns ZEREF_SKIN for Zeref. */
export function skinFromGenome(gen,{id,name}={}){
 if(isZerefBeast({id,name})||!gen||!gen.island)return ZEREF_SKIN;
 let pal;try{pal=paletteOf(gen);}catch{return ZEREF_SKIN;}
 const b=pal.base,a=pal.alt,be=pal.belly,ac=pal.accent,gl=pal.glow;
 const deep=dark(b.sh,.55);
 const hornEars=['horns','crown','flame','crystal','antlers','bolts','antenna'].includes(gen.ears);
 return {
  canonical:false,
  fur:[hex(b.li),hex(b.mid),hex(deep)],furSolid:hex(dark(b.sh,.8)),lid:hex(dark(b.sh,.7)),stroke:hex(dark(a.sh,.8)),
  ear:[hex(be.li),hex(ac.mid)],iris:['#f6f2ff',hex(gl.li),hex(ac.mid),hex(dark(ac.sh,.45))],
  wing:[hex(dark(a.sh,.8)),hex(a.mid),hex(gl.li)],moon:['#fbfbff',hex(gl.mid)],
  tail:[hex(deep),hex(b.mid),hex(a.mid)],beans:hex(ac.li),brow:hex(mix(a.li,[255,255,255],.2)),mouth:hex(mix(be.li,[255,255,255],.4)),
  accent:hex(ac.mid),glow:hex(gl.li),
  features:{wings:gen.wings!=='none',moonHorns:hornEars,crescent:false,horns:hornEars,tailTip:gen.tail==='none'?'none':gen.tail==='flame'?'flame':'wisp'}
 };
}

/** The genome's own recorded-count features, in the shape createMind() accepts as `seed`. */
export function seedFromGenome(gen){
 if(!gen||!gen.seed)return null;
 const q=gen.quantum||{},m=Array.isArray(q.marginals)?q.marginals:[];
 const n=(v,d)=>Number.isFinite(Number(v))?Number(v):d;
 const z=n(m[0],.5),x=n(m[1],.5),ent=n(q.entropy_norm,.6);
 return {digest:sha256Hex(String(gen.seed)+'|'+String(q.counts_sha256||'')),runs:1,shots:0,backend:String(q.backend||''),job_id:String(q.job_id||''),
  features:{zzOdd:z,xxEven:x,lean:(z-.5)*2,noise:.08+(1-Math.min(1,ent))*.2}};
}
