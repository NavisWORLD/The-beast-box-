/**
 * POCKET GRID ENVIRONMENT — the Cage pocket as a discrete, step-by-step world
 * so a key-press policy (hand-coded or neural) can act in it.
 *
 * Same seeded layout as the site: points of interest and void rifts come from
 * createPocket()/riftCells() on the pocket's 8x5 learner grid, and moves are
 * scored with the pocket learner's own enterCell()/learn(). One step = one key:
 * UP / DOWN / LEFT / RIGHT move one cell, WAIT rests. Leaving the grid is a
 * visible wall bump; entering a rift fails and is remembered (the beast only
 * learns where rifts are by bumping into them, exactly like the live pocket).
 *
 * What a policy may see (observe): its own cell, grid edges, which neighbour
 * cells it has visited and how often, which neighbours it has LEARNED are rifts,
 * and point-of-interest kinds. It never sees unlearned rift positions.
 *
 * Every step emits a canonical zeref-experience/v1 record (origin
 * deterministic_pocket_simulation). Pure; no DOM, storage, clock or network.
 */
import {createPocket} from './zeref-pocket.mjs';
import {GRID,GOALS,cellCenter,cellOf,chooseGoal,createLearner,enterCell,learn,restoreLearner} from './pocket-learner.mjs';
import {makeRecord} from './experience-record.mjs';

export const GRID_ENV_SCHEMA='zeref-pocket-grid/v1';
export const MOVES=Object.freeze(['UP','DOWN','LEFT','RIGHT']);
export const KEYS=Object.freeze([...MOVES,'WAIT']);
export const REWARD_RULE='grid-v1: new cell +1, revisit -0.05, rift bump -1, wall bump -1, WAIT 0';
const D={UP:[-1,0],DOWN:[1,0],LEFT:[0,-1],RIGHT:[0,1]};
const rc=i=>[Math.floor(i/GRID.cols),i%GRID.cols];
const idx=(r,c)=>r*GRID.cols+c;
const inGrid=(r,c)=>r>=0&&r<GRID.rows&&c>=0&&c<GRID.cols;
function hash32(t){let h=0x811c9dc5;for(let i=0;i<t.length;i++){h^=t.charCodeAt(i);h=Math.imul(h,0x01000193);}return h>>>0;}
function rnd(s){s.rng=(s.rng+0x6D2B79F5)|0;let t=s.rng;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return((t^(t>>>14))>>>0)/4294967296;}

export function createGridEnv({digest,key,qbeast_id,maxSteps=40,traits={curiosity:.5,playfulness:.5,sleepiness:.3},energy=65,origin='deterministic_pocket_simulation'}){
 const p=createPocket({digest,key});
 const poiAt={};for(const o of p.pois)poiAt[cellOf(o.x,o.y)]=o.kind;
 const start=cellOf(0,.15);
 const L=createLearner();L.cells[start]=1;
 return {schema:GRID_ENV_SCHEMA,digest,key,qbeast_id,origin,maxSteps,traits,energy,
  rifts:[...p.rifts],pois:p.pois.map(o=>({...o,cell:cellOf(o.x,o.y)})),poiAt,cell:start,start,t:0,
  learner:L,bumps:{rift:0,wall:0},poiKinds:[],actions:{UP:0,DOWN:0,LEFT:0,RIGHT:0,WAIT:0},
  policyState:{rng:hash32('grid-policy|'+key)|0,goal:null,target:null,rest:0},prevHash:null,done:false};
}

/** Serialise / restore (memory + save/reload integrity checks use this). */
export function snapshotEnv(e){return JSON.parse(JSON.stringify(e));}
export function restoreEnv(raw){
 if(!raw||raw.schema!==GRID_ENV_SCHEMA)throw Error('grid env: unknown snapshot');
 const e=JSON.parse(JSON.stringify(raw));e.learner=restoreLearner(raw.learner);return e;
}

/** What the beast can perceive. Hidden rifts are never included. */
export function observe(e){
 const [r,c]=rc(e.cell);const L=e.learner;
 const n={};
 for(const k of MOVES){const [dr,dc]=D[k],rr=r+dr,cc=c+dc;
  if(!inGrid(rr,cc)){n[k]={kind:'wall'};continue;}
  const i=idx(rr,cc);
  n[k]=L.known_blocked.includes(i)?{kind:'rift-known'}:{kind:'open',visits:L.cells[i],poi:e.poiAt[i]||null};
 }
 return {row:r,col:c,visits_here:L.cells[e.cell],poi_here:e.poiAt[e.cell]||null,neighbors:n,
  cells_visited:L.cells.filter(v=>v>0).length,known_rifts:L.known_blocked.length,step:e.t,steps_left:e.maxSteps-e.t,energy:e.energy};
}

/** Apply one key. Returns {obs, outcome, reward, done, record}. */
export function stepEnv(e,key,{policy='unknown',labels=[]}={}){
 if(e.done)throw Error('grid env: episode finished');
 if(!KEYS.includes(key))throw Error('grid env: illegal key '+key);
 const before=observe(e);
 let outcome,reward;
 e.actions[key]++;
 if(key==='WAIT'){outcome={kind:'rested'};reward=0;}
 else{
  const [r,c]=rc(e.cell),[dr,dc]=D[key],rr=r+dr,cc=c+dc;
  if(!inGrid(rr,cc)){e.bumps.wall++;e.learner.moves.blocked++;outcome={kind:'wall'};reward=-1;}
  else{
   const to=idx(rr,cc),res=enterCell(e.learner,to,e.rifts);
   if(res.outcome==='blocked'){e.bumps.rift++;learn(e.learner,'explore',-.5,null);outcome={kind:'rift',cell:to};reward=-1;}
   else{e.cell=to;outcome={kind:res.fresh?'new_cell':'revisit',cell:to};reward=res.fresh?1:-.05;
    if(res.fresh)learn(e.learner,'explore',.6,null);
    const poi=e.poiAt[to];if(poi&&!e.poiKinds.includes(poi))e.poiKinds.push(poi);}
  }
 }
 e.t++;e.done=e.t>=e.maxSteps;
 const record=makeRecord({qbeast_id:e.qbeast_id,origin:e.origin,episode:e.key,step:e.t,
  observation:before,decision:{policy},action:{key},outcome:{...outcome,observed:true},
  reward:{kind:'computed_reward',value:reward,rule:REWARD_RULE},
  memory:{cells_visited:e.learner.cells.filter(v=>v>0).length,known_rifts:[...e.learner.known_blocked].sort((a,b)=>a-b),moves:{...e.learner.moves}},
  labels:[{kind:'observed_outcome',value:outcome.kind,by:'pocket-grid-rules'},...labels],source:{ref:GRID_ENV_SCHEMA+' '+e.key},prev:e.prevHash});
 e.prevHash=record.hash;
 return {obs:observe(e),outcome,reward,done:e.done,record};
}

export function metrics(e){
 const n=Object.values(e.actions).reduce((a,b)=>a+b,0)||1;
 const ent=-Object.values(e.actions).filter(v=>v>0).reduce((s,v)=>s+(v/n)*Math.log2(v/n),0);
 return {steps:e.t,cells_visited:e.learner.cells.filter(v=>v>0).length,new_cells:e.learner.cells.filter(v=>v>0).length-1,
  rift_bumps:e.bumps.rift,wall_bumps:e.bumps.wall,blocked:e.bumps.rift+e.bumps.wall,moves_succeeded:e.learner.moves.succeeded,
  poi_kinds_reached:e.poiKinds.length,action_entropy_bits:Math.round(ent*1e4)/1e4,actions:{...e.actions}};
}

/* ----------------------------- baseline policies ----------------------------- */

/** Uniform random key among the four moves. */
export function randomPolicy(e){return MOVES[Math.floor(rnd(e.policyState)*4)];}

function stepToward(e,target){
 const [r,c]=rc(e.cell),[tr,tc]=rc(target);
 const opts=[];if(tr<r)opts.push('UP');if(tr>r)opts.push('DOWN');if(tc<c)opts.push('LEFT');if(tc>c)opts.push('RIGHT');
 const known=e.learner.known_blocked;
 const ok=opts.filter(k=>{const [dr,dc]=D[k];return !known.includes(idx(r+dr,c+dc));});
 const pick=ok.length?ok:opts;
 if(!pick.length)return null;
 // dominant axis first (what the continuous pocket's straight-line travel does)
 pick.sort((a,b)=>{const da=(a==='UP'||a==='DOWN')?Math.abs(tr-r):Math.abs(tc-c),db=(b==='UP'||b==='DOWN')?Math.abs(tr-r):Math.abs(tc-c);return db-da;});
 return pick[0];
}

/**
 * The site's own hand-coded pocket-learner policy, discretised: it picks a goal
 * with chooseGoal() (softmax over learned preferences, novelty, energy,
 * temperament), walks one cell per step toward the goal's target, rests for
 * rest goals, and re-plans on arrival or after a bump.
 */
export function pocketLearnerPolicy(e){
 const s=e.policyState;
 if(s.rest>0){s.rest--;return 'WAIT';}
 if(s.target==null||s.target===e.cell||s.bumped){
  s.bumped=false;
  const c=cellCenter(e.cell);
  const pv={x:c.x,y:c.y,pois:e.pois,lastTarget:s.lastId||null};
  const {goal,target}=chooseGoal(e.learner,pv,{energy:e.energy,traits:e.traits},()=>rnd(s),{});
  s.goal=goal;
  if(goal==='rest'||!target){s.rest=1;s.target=null;return 'WAIT';}
  s.lastId=target.id;s.target=cellOf(target.x,target.y);
  if(s.target===e.cell){s.target=null;return 'WAIT';}
 }
 return stepToward(e,s.target)||'WAIT';
}
export function notePolicyOutcome(e,outcome){if(outcome.kind==='rift'||outcome.kind==='wall')e.policyState.bumped=true;}

/** A stronger hand-coded baseline: nearest unvisited safe cell (BFS over known-safe cells). */
export function greedyFrontierPolicy(e){
 const o=observe(e);
 const fresh=MOVES.filter(k=>o.neighbors[k].kind==='open'&&o.neighbors[k].visits===0);
 if(fresh.length)return fresh[Math.floor(rnd(e.policyState)*fresh.length)];
 const L=e.learner,seen=new Set([e.cell]),q=[[e.cell,null]];
 while(q.length){const [i,first]=q.shift();const [r,c]=rc(i);
  for(const k of MOVES){const [dr,dc]=D[k],rr=r+dr,cc=c+dc;if(!inGrid(rr,cc))continue;const j=idx(rr,cc);
   if(seen.has(j)||L.known_blocked.includes(j))continue;seen.add(j);const f=first||k;
   if(L.cells[j]===0)return f;q.push([j,f]);}}
 const open=MOVES.filter(k=>o.neighbors[k].kind==='open');
 return open.length?open[Math.floor(rnd(e.policyState)*open.length)]:'WAIT';
}

export const BASELINES=Object.freeze({random:randomPolicy,'pocket-learner':pocketLearnerPolicy,'greedy-frontier':greedyFrontierPolicy});
export {GOALS};
