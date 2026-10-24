// Seeded growth nodes for the Tiny Universe land (Oct 24 2026). Food-forest style growth for the pocket world: a front spreads cell by cell
// from a node, layers come in order (grass ring, groundcover, berry shrub, canopy), then bloom, gold senescence, leaf shed, renewal.
// HONESTY, in plain words:
//   - PLACEMENT is SEEDED. Nodes are drawn from lwStream(seed+':growth-nodes:'+planet.id); the seed is the sha256 of the RECORDED IBM
//     ibm_marrakesh counts, but the recording itself holds no growth-node data. Every node carries label:'SEEDED'.
//   - GROWTH DRIVE stays SIMULATED. Speed rides the current tick's sim_E from the Rigetti-style Bell simulator (growth_label
//     "SIMULATED (Rigetti Bell simulator, not hardware)"). With no history it falls back to the RECORDED entanglement_E as a neutral drive.
//   - GENESIS stays RECORDED. Nothing here touches genesis, the tick sampler, pairs or life rules.
// Pure: state is a function of (seed, tick, planet). No Math.random, no clock, no stored state. Own streams only, so stars, planets,
// storms, life and pairs are byte-identical with nodes on or off. This is the universe's growth, not Zeref 009's model growth.
import {lwStream} from './living-world.mjs';

export const GROWTH_NODE_LABEL='SEEDED';
export const NODE_KINDS=Object.freeze(['ring','patch','shrub','canopy']);// grass front / groundcover fill / berry shrub / tree
export const NODE_STAGES=Object.freeze(['sprout','tuft','full','bloom','gold','shed']);// succession + senescence
export const GROWTH=Object.freeze({
 minHabitability:0.25,// no nodes on dead worlds
 frontCellsPerTick:0.5,// front advance speed before local modifiers
 goldAfter:0.78,// fraction of a node's life span where the gold phase begins
 scarGold:0.08,// each storm scar pulls gold this much earlier
 minGold:0.5,
 cellRad:0.04,// radians per ground cell (about 1 m on the ~27 m living world); callers can pass their own
 rim:1.12,// canopy overflow: the edge ring out to spread*rim keeps the mature overshoot
 unborn:0.04,// instance scale in a node's territory before the front has reached that cell
 spreadCells:[10,28],// territory radius in cells
 lifespan:[90,220],// ticks, before the kind multiplier
 kinds:Object.freeze({
  ring:{size:0.6,life:0.6},patch:{size:1.0,life:0.8},shrub:{size:1.4,life:1.1},canopy:{size:2.2,life:1.5},// size = base scale, life = lifespan multiplier (grass first, canopy last)
 }),
 fruitKinds:Object.freeze(['shrub','canopy']),
});
const KW={// [ring, patch, shrub, canopy] weights by home biome (view passes planet.biome when it has one)
 heartwood_forest:[.05,.1,.2,.65],rainforest:[.05,.1,.25,.6],sunflower_ring:[.35,.45,.1,.1],grassland:[.3,.45,.15,.1],
 crystal_moss:[.1,.2,.55,.15],paper_marsh:[.1,.2,.55,.15],_:[.25,.3,.25,.2],
};
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const f4=x=>+x.toFixed(4);

/** Placement only, tick-independent. @param {{seed?:any,planets?:any[]}} u */
export function seededGrowthNodes(u){
 const out=[];const seed=String(u?.seed??'tiny');
 for(const p of u?.planets||[]){
  const hab=+p.habitability||0;if(hab<GROWTH.minHabitability)continue;
  const r=lwStream(seed+':growth-nodes:'+p.id);
  const n=1+(r()<0.3+hab*0.5?1:0);
  const w=KW[p.biome]||KW._;
  for(let i=0;i<n;i++){
   const d=[r(),r(),r(),r(),r(),r(),r(),r(),r(),r()];// fixed 10 draws: kind, lat, lon, phase, vigor, hue, spread, goldShift, lifespan, lean
   let acc=0,k=3;for(let j=0;j<4;j++){acc+=w[j];if(d[0]<acc){k=j;break;}}
   const kind=NODE_KINDS[k];const [s0,s1]=GROWTH.spreadCells,[l0,l1]=GROWTH.lifespan;
   out.push({id:'growth-node-'+p.id+'-'+i,type:'growth_node',planet:p.id,kind,lat:f4((d[1]*2-1)*65),lon:f4((d[2]*2-1)*180),born:0,label:GROWTH_NODE_LABEL,
    phase:f4(d[3]),vigor:f4(d[4]),hue:f4(d[5]),spread:f4(s0+d[6]*(s1-s0)),goldShift:f4(d[7]),lifespan:Math.round((l0+d[8]*(l1-l0))*GROWTH.kinds[kind].life),lean:f4(d[9])});
  }
 }
 return out;
}

/** Drive from the CURRENT tick's SIMULATED sim_E (history entry for that tick, else the latest); empty history -> the recorded entanglement_E. */
export function growthDrive(u,tick){
 const h=u?.history||[];let e=null;
 for(let i=h.length-1;i>=0;i--){if(h[i].tick===tick&&typeof h[i].sim_E==='number'){e=h[i].sim_E;break;}}
 if(e==null){const last=h[h.length-1];e=last&&typeof last.sim_E==='number'?last.sim_E:+(u?.entanglement_E)||0;}
 return clamp(0.5+e,0.1,1.6);
}
const lifeX=(age,life)=>{const a=age/life;return a-Math.floor(a);};
const goldOf=(node,scars)=>clamp(GROWTH.goldAfter+(node.goldShift-0.5)*0.06-GROWTH.scarGold*scars,GROWTH.minGold,0.9);
const cuts=(gold)=>({sprout:0.12,tuft:0.35,full:Math.min(0.62,gold-0.04),gold,shed:0.93});
const easeOut=t=>1-(1-t)*(1-t);
const lerp=(a,b,t)=>a+(b-a)*t;
/** Stage name from life position x and the node's (scar-adjusted) gold point. */
export function stageAt(x,gold=GROWTH.goldAfter){const c=cuts(gold);return x<c.sprout?'sprout':x<c.tuft?'tuft':x<c.full?'full':x<gold?'bloom':x<c.shed?'gold':'shed';}
/** Normalized stage curve (no kind size): sprout->full ease-out, 1.0 at full/bloom, 1.06 at gold (the mature overshoot), leaf-drop shrink in shed. */
export function stageScale(x,gold=GROWTH.goldAfter){const c=cuts(gold);
 if(x<c.sprout)return 0.08+0.27*easeOut(x/c.sprout);
 if(x<c.tuft)return lerp(0.35,0.8,easeOut((x-c.sprout)/(c.tuft-c.sprout)));
 if(x<c.full)return lerp(0.8,1,easeOut((x-c.tuft)/(c.full-c.tuft)));
 if(x<gold)return 1;
 if(x<c.shed)return lerp(1,1.06,(x-gold)/(c.shed-gold));
 return lerp(1.06,0.7,(x-c.shed)/(1-c.shed));}
function scarsOf(node,u){
 const hist=u?.history||[];if(!hist.length)return 0;
 const storms=u?.storms||[];let n=0;
 for(const h of hist){
  const on=(Array.isArray(h.storms)&&h.storms.includes(node.planet))||storms.some(s=>s.planet===node.planet&&s.born<=h.tick&&h.tick<=s.born+s.lifetime);
  if(!on)continue;
  const x=lifeX(Math.max(0,h.tick-node.born),node.lifespan);const st=stageAt(x,GROWTH.goldAfter);
  if(st==='full'||st==='bloom')n++;
 }
 return n;
}
/** Pure state of one node at a tick. @returns {{stage:string,scale:number,norm:number,tint:number,fruit:boolean,lean:number,shed:number,x:number,generation:number,front:number,rate:number,drive:number,gold:number,scars:number,scarred:boolean}} */
export function growthNodeState(node,u,tick){
 const age=Math.max(0,tick-node.born);const drive=growthDrive(u,tick);
 const rate=GROWTH.frontCellsPerTick*(0.5+node.vigor)*drive;
 const scars=scarsOf(node,u);const gold=goldOf(node,scars);
 const generation=Math.floor(age/node.lifespan);const x=lifeX(age,node.lifespan);
 const stage=stageAt(x,gold);const c=cuts(gold);const norm=stageScale(x,gold);
 const kind=GROWTH.kinds[node.kind];
 const tint=stage==='shed'?1:stage==='gold'?clamp((x-gold)/(c.shed-gold)):0;// gold lerp factor; the renderer owns the colors
 const fruit=stage==='bloom'&&GROWTH.fruitKinds.includes(node.kind);
 const shed=stage==='shed'?f4(0.4+0.6*Math.sin(Math.PI*clamp((x-c.shed)/(1-c.shed)))):stage==='gold'&&tint>0.6?f4(0.15*(tint-0.6)/0.4):0;
 // rest lean (degrees) is seeded; bigger growth leans a little more. The view adds the affinity lean on top.
 const lean=f4((node.lean*2-1)*4*Math.min(1.06,norm));
 return {stage,scale:f4(norm*kind.size),norm:f4(norm),tint:f4(tint),fruit,lean,shed,x:f4(x),generation,front:f4(age*rate),rate:f4(rate),drive:f4(drive),gold:f4(gold),scars,scarred:scars>0};
}
/** Placement + state for every node at a tick. */
export function growthNodesAt(u,tick=u?.tick??0){return seededGrowthNodes(u).map(n=>({...n,tick,...growthNodeState(n,u,tick)}));}

const unit=(lat,lon)=>{const a=lat*Math.PI/180,o=lon*Math.PI/180;return [Math.cos(a)*Math.cos(o),Math.sin(a),Math.cos(a)*Math.sin(o)];};
/**
 * Stage multiplier for ONE ground direction (unit vector in the planet frame), from growthNodesAt() output; 1 where no node reaches (identity,
 * so existing planting is unchanged there). Inside a node's territory (spread cells) each cell has its own age: the front reached it
 * dc/rate ticks ago, so cells near the node are older (more grown) and the rim is still sprouting; cells the front has not reached sit at
 * GROWTH.unborn. The ring just past the edge keeps the mature overshoot (canopy spill), fading to 1 by spread*rim.
 * The view applies this at instance-build time; plantGround/plantTrees outputs are untouched. `tick` is kept for call-site symmetry:
 * the nodes already carry the state for their own tick.
 * @param {any[]} nodes @param {number} tick @param {number[]} dir @param {{cellRad?:number,planet?:string}} [o]
 */
export function growthScaleAt(nodes,tick,dir,o={}){
 const cellRad=o.cellRad||GROWTH.cellRad;let best=1,hit=false;
 for(const n of nodes||[]){
  if(o.planet&&n.planet!==o.planet)continue;
  const c=unit(n.lat,n.lon);const cos=clamp(c[0]*dir[0]+c[1]*dir[1]+c[2]*dir[2],-1,1);const dc=Math.acos(cos)/cellRad;
  if(dc>n.spread*GROWTH.rim)continue;
  let s;
  if(dc>n.spread){const m=Math.max(1,n.norm);s=lerp(m,1,(dc-n.spread)/(n.spread*(GROWTH.rim-1)));}
  else{const age=Math.max(0,tick-n.born)-dc/Math.max(1e-6,n.rate);
   s=age<0?GROWTH.unborn:stageScale(lifeX(age,n.lifespan),n.gold);}
  if(!hit||s>best){best=s;hit=true;}
 }
 return hit?f4(best):1;
}
