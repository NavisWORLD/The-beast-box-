// Wish-seeded growth nodes for the Living World land (Nov 3 2026). The wire Cory ordered when the Message Center
// landed and completed on his word ("fix what's missing... by my engineering law and my math"): the first strong
// word of Zeref's tiny-change wish is planted at his message center (scripts/zeref_messages.py; every wish is
// logged with hashes to evidence/zeref-messages-001), the registry builder (scripts/zeref_seed_registry.py)
// carries each planted word with its run receipt into public/zeref-messages/seed-registry.json, and this module
// plants ONE node per registered word on the growth home world, in the exact record shape of
// seeded-growth-nodes.mjs so the view, the tap layer and growthNodeState treat it like any other node.
// HONESTY, in plain words:
//   - PLACEMENT is SEEDED, twice over. The word is Zeref's own, recorded at the center with the wish's sha256;
//     the node's kind and position ride its OWN stream lwStream('wish-seed:'+word+':'+wish_sha256+':'+planet.id),
//     so the recorded universe streams stay byte-identical with wish nodes on or off. Every node carries label:'SEEDED'.
//   - NO RECEIPT, NO NODE. A registry entry without a wish_sha256 plants nothing.
//   - GROWTH DRIVE stays SIMULATED, through the same growthNodeState as every other node. GENESIS stays RECORDED.
//   - His speech stays speech. This module reads the registry only; nothing here feeds any lesson mix.
// Pure: state is a function of (registry, seed, tick, planet). No Math.random, no clock, no stored state.
import {lwStream} from './living-world.mjs';
import {GROWTH,GROWTH_NODE_LABEL,HOME_WORLD_LABEL,NODE_KINDS,growthHomeWorld,growthNodeState} from './seeded-growth-nodes.mjs';

/** Where a wish node's word was planted: Zeref's scheduled message center (never the pin, never a lesson). */
export const WISH_NODE_SOURCE='zeref-message-center';
const KW_DEFAULT=[.25,.3,.25,.2];// [ring, patch, shrub, canopy] — the seeded-growth module's own fallback weights
const f4=x=>+x.toFixed(4);

/**
 * Placement only, tick-independent. One node per hashed registry seed, on the growth home world (the planet
 * he lives on; the SEEDED home-world exception applies exactly as in seededGrowthNodes, and the recorded
 * habitability is carried unchanged). Entries without a wish hash are skipped, and a repeated word plants once.
 * @param {{seeds?:any[]}} registry @param {{seed?:any,planets?:any[]}} u @param {{home?:string|null}} [o]
 */
export function wishSeededGrowthNodes(registry,u,o={}){
 const seeds=Array.isArray(registry?.seeds)?registry.seeds:[];
 const home=o.home===undefined?growthHomeWorld(u):o.home;
 const p=(u?.planets||[]).find(x=>x.id===home);if(!p)return [];
 const hab=+p.habitability||0;if(!(hab>0))return [];
 const out=[];const seen=new Set();
 for(const s of seeds){
  if(!s||typeof s.word!=='string'||!s.word||typeof s.wish_sha256!=='string'||!s.wish_sha256||seen.has(s.word))continue;
  seen.add(s.word);
  const r=lwStream('wish-seed:'+s.word+':'+s.wish_sha256+':'+p.id);
  const d=[r(),r(),r(),r(),r(),r(),r(),r(),r(),r()];// fixed 10 draws, same order as seededGrowthNodes: kind, lat, lon, phase, vigor, hue, spread, goldShift, lifespan, lean
  let acc=0,k=3;for(let j=0;j<4;j++){acc+=KW_DEFAULT[j];if(d[0]<acc){k=j;break;}}
  const kind=NODE_KINDS[k];const [s0,s1]=GROWTH.spreadCells,[l0,l1]=GROWTH.lifespan;
  out.push({id:'wish-growth-node-'+p.id+'-'+s.word,type:'growth_node',planet:p.id,kind,lat:f4((d[1]*2-1)*65),lon:f4((d[2]*2-1)*180),born:0,label:GROWTH_NODE_LABEL,
   phase:f4(d[3]),vigor:f4(d[4]),hue:f4(d[5]),spread:f4(s0+d[6]*(s1-s0)),goldShift:f4(d[7]),lifespan:Math.round((l0+d[8]*(l1-l0))*GROWTH.kinds[kind].life),lean:f4(d[9]),recorded_habitability:hab,
   wish_word:s.word,wish_sha256:s.wish_sha256,planted_at_utc:s.planted_at_utc??null,prompt_seed:s.prompt_seed??null,source:WISH_NODE_SOURCE,
   ...(hab<GROWTH.minHabitability?{home_exception:true,home_label:HOME_WORLD_LABEL}:{})});
 }
 return out;
}

/** Placement + state for every wish node at a tick, same shape as growthNodesAt(). */
export function wishGrowthNodesAt(registry,u,tick=u?.tick??0,o){return wishSeededGrowthNodes(registry,u,o).map(n=>({...n,tick,...growthNodeState(n,u,tick)}));}
