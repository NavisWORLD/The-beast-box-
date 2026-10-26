// ONE list of every creation that lives in the pocket universe (Cory, Oct 25 2026): the active beast, every beast saved to this
// device's bestiary, and the artist-drawn residents. The pocket world, its "Who lives here" legend and the Zeref/nebula panel all
// read this list, so a creation never shows in one place and is missing from another. Pure: no DOM, no network.
import {ARTIST_RESIDENTS} from './artist-residents.mjs';
import {beastDisplayName,prettyBeastName} from './beast-name.mjs';
/** Saved beasts the pocket draws as roaming pixel sprites (phones and software GL draw fewer, never zero). */
export const MAX_SAVED_ROAMERS=8;
const nm=(v)=>typeof v==='string'&&v.trim()?prettyBeastName(v.trim().slice(0,32)):null;
/** @returns {{id:string,name:string,kind:'active'|'saved'|'beast'|'trainer',genome:any|null,seed:string|null,origin:string,look:string|null,art:string|null}[]} */
export function listCreations(session){
 const out=[];const seen=new Set();
 const add=(c)=>{if(seen.has(c.id))return;seen.add(c.id);out.push(c);};
 const beast=session&&session.beast;const bestiary=Array.isArray(session&&session.bestiary)?session.bestiary:[];
 if(beast&&beast.seed){const g=beast.genome||bestiary.find(b=>b&&b.seed===beast.seed)?.genome||null;
  add({id:'seed:'+beast.seed,name:beastDisplayName(beast)||'Your beast',kind:'active',genome:g,seed:String(beast.seed),origin:'Your beast · SEEDED',look:null,art:null});}
 for(const b of bestiary){if(!b||!b.seed)continue;
  add({id:'seed:'+b.seed,name:nm(b.name)||nm(b.genome&&b.genome.names&&b.genome.names['1'])||'Saved beast',kind:'saved',genome:b.genome||null,seed:String(b.seed),origin:'Saved Spark Beast · SEEDED',look:b.body?(b.body+(b.island?' · '+b.island:'')):null,art:null});}
 for(const r of ARTIST_RESIDENTS)add({id:r.id,name:r.name,kind:r.kind,genome:null,seed:null,origin:r.origin,look:r.look,art:r.views.front});
 return out;
}
/** The saved beasts that need their own roaming sprite in the pocket (not the active beast, which already stands in front). */
export function savedRoamers(session,max=MAX_SAVED_ROAMERS){return listCreations(session).filter(c=>c.kind==='saved'&&c.genome).slice(0,Math.max(0,max));}
/** Empty-state line for the legend when nothing has moved in yet. */
export function homeLabel(name){return (name&&String(name).trim()?String(name).trim():'Your beast')+'\u2019s home';}
/** Depth treatment for a flat sprite with no new art: it dims and cools with distance from the lens, shrinks a little and its contact
 * shadow softens, so a pixel creature reads as standing in the world, not pasted on it. 0 (near) .. 1 (far). */
export function depthFar(dist,near=2.5,far=9){return Number.isFinite(dist)?Math.min(1,Math.max(0,(dist-near)/(far-near))):0;}
