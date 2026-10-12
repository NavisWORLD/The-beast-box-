/**
 * POCKET LEARNER — "no leash": the beast picks its own goals in the Cage pocket
 * and learns from what happened. Pure and seeded (no DOM, storage or network),
 * shared by the browser rAF loop and the server diary replay.
 *
 * What it tracks (all measurable, all serialisable, persisted per beast):
 *  - a grid of pocket cells with visit counts (novelty = cells never visited)
 *  - move outcomes: succeeded vs blocked (seeded "void rift" cells block moves;
 *    the beast only learns where they are by bumping into them)
 *  - a value estimate per place, updated from the outcome of each visit
 *  - goal preferences (explore / visit / rest / play) that shift with reward
 * Goals are chosen by a softmax over utilities built from those estimates,
 * the beast's energy and temperament, and what it perceives (nearby objects,
 * other beasts if present, and — only when the user has switched the mic on —
 * a local sound-level number; nothing is recorded or uploaded).
 *
 * Honest boundary: this is learned behaviour from its own experience (simple
 * running averages over outcomes), not consciousness.
 */
export const LEARNER_SCHEMA='pocket-learner/v1';
export const GRID=Object.freeze({cols:8,rows:5,x0:-1,x1:1,y0:-.62,y1:.66});
export const GOALS=Object.freeze(['explore','visit','rest','play','come']);
const ALPHA=.18;
const clamp=(v,lo=0,hi=1)=>Math.min(hi,Math.max(lo,v));
function hash32(t){let h=0x811c9dc5;for(let i=0;i<t.length;i++){h^=t.charCodeAt(i);h=Math.imul(h,0x01000193);}return h>>>0;}

export function cellOf(x,y){
 const c=Math.floor((x-GRID.x0)/(GRID.x1-GRID.x0)*GRID.cols),r=Math.floor((y-GRID.y0)/(GRID.y1-GRID.y0)*GRID.rows);
 return clamp(r,0,GRID.rows-1)*GRID.cols+clamp(c,0,GRID.cols-1);
}
export function cellCenter(i){
 const c=i%GRID.cols,r=Math.floor(i/GRID.cols);
 return {x:+(GRID.x0+(c+.5)*(GRID.x1-GRID.x0)/GRID.cols).toFixed(3),y:+(GRID.y0+(r+.5)*(GRID.y1-GRID.y0)/GRID.rows).toFixed(3)};
}

/** Seeded rift cells for a pocket: never on a point of interest or the front-centre "call" spot. */
export function riftCells(pois,seedKey){
 const keep=new Set([...pois.map(p=>cellOf(p.x,p.y)),cellOf(0,.55),cellOf(0,.15)]);
 const out=[];let h=hash32('rifts|'+seedKey);
 for(let n=0;n<40&&out.length<3;n++){h=Math.imul(h^(h>>>15),0x2c1b3c6d)>>>0;const i=h%(GRID.cols*GRID.rows);if(!keep.has(i)&&!out.includes(i))out.push(i);}
 return out.sort((a,b)=>a-b);
}

export function createLearner(){
 return {schema:LEARNER_SCHEMA,cells:Array(GRID.cols*GRID.rows).fill(0),known_blocked:[],
  moves:{succeeded:0,blocked:0},value:{},prefs:{explore:.6,visit:.5,rest:.35,play:.4},goals:{explore:0,visit:0,rest:0,play:0,come:0},
  goal:null,decisions:0};
}
/** Accept a persisted learner, repairing anything malformed instead of trusting it. */
export function restoreLearner(raw){
 const L=createLearner();if(!raw||raw.schema!==LEARNER_SCHEMA)return L;
 if(Array.isArray(raw.cells)&&raw.cells.length===L.cells.length)L.cells=raw.cells.map(v=>Math.max(0,Math.floor(Number(v)||0)));
 if(Array.isArray(raw.known_blocked))L.known_blocked=raw.known_blocked.filter(i=>Number.isInteger(i)&&i>=0&&i<L.cells.length).slice(0,40);
 for(const k of ['succeeded','blocked'])L.moves[k]=Math.max(0,Math.floor(Number(raw.moves?.[k])||0));
 for(const [k,v] of Object.entries(raw.value||{}))if(/^[a-z-]+-\d+$/.test(k)&&Number.isFinite(v))L.value[k]=clamp(v,-1,1);
 for(const k of Object.keys(L.prefs))if(Number.isFinite(raw.prefs?.[k]))L.prefs[k]=clamp(raw.prefs[k],.05,1);
 for(const k of Object.keys(L.goals))L.goals[k]=Math.max(0,Math.floor(Number(raw.goals?.[k])||0));
 L.decisions=Math.max(0,Math.floor(Number(raw.decisions)||0));
 return L;
}

/** What the beast can perceive right now. */
export function perceive(p,{others=[],sound=null}={}){
 const near=p.pois.map(o=>({id:o.id,kind:o.kind,name:o.name,d:+Math.hypot(o.x-p.x,o.y-p.y).toFixed(3)})).sort((a,b)=>a.d-b.d).slice(0,3);
 const beasts=(others||[]).slice(0,6).map(b=>({id:String(b.id),d:+Math.hypot((b.x||0)-p.x,(b.y||0)-p.y).toFixed(3)}));
 const level=sound&&sound.active&&Number.isFinite(sound.level)?clamp(sound.level*4):null;
 return {near,beasts,sound:level};
}

/** Does the straight path cross a cell the beast already learned is blocked? */
function pathKnownBlocked(L,p,to){
 if(!L.known_blocked.length)return false;
 for(let s=1;s<=10;s++){const x=p.x+(to.x-p.x)*s/10,y=p.y+(to.y-p.y)*s/10;if(L.known_blocked.includes(cellOf(x,y)))return true;}
 return false;
}

/** The softmax utilities the beast decides with (exposed for tests / the UI). */
export function goalUtilities(L,p,m,sense={}){
 const e=clamp((m.energy??60)/100),T=m.traits||{};
 const unvisited=L.cells.filter((v,i)=>v===0&&!L.known_blocked.includes(i)).length/L.cells.length;
 const bestValue=Math.max(0,...p.pois.map(o=>L.value[o.id]??.3));
 const loud=sense.sound??0;
 return {
  explore:L.prefs.explore*(.25+unvisited*1.6)*(.5+(T.curiosity??.5))*(.4+e)+loud*.3,
  visit:L.prefs.visit*(.4+bestValue)*(.6+e*.4),
  rest:L.prefs.rest*(1.25-e)*(.6+(T.sleepiness??.3))-loud*.2,
  play:L.prefs.play*(.3+(T.playfulness??.5))*e+(sense.beasts?.length?.25:0)
 };
}

function softmax(u,r,temp=.35){
 const ks=Object.keys(u),w=ks.map(k=>Math.exp(u[k]/temp)),t=w.reduce((a,b)=>a+b,0);let x=r*t;
 for(let i=0;i<ks.length;i++){x-=w[i];if(x<=0)return ks[i];}return ks[ks.length-1];
}

/**
 * Choose the next goal and a concrete target. rand = the pocket's seeded rng.
 * Returns {goal, target:{id,kind,name,x,y}, utilities}.
 */
export function chooseGoal(L,p,m,rand,sense={}){
 const u=goalUtilities(L,p,m,sense);
 let goal=softmax(u,rand());
 let target=null;
 if(goal==='explore'){
  // frontier: least-visited reachable cells, nearer first; skip paths through known rifts
  const here=cellOf(p.x,p.y);
  const cand=L.cells.map((v,i)=>({i,v,c:cellCenter(i)})).filter(o=>o.i!==here&&!L.known_blocked.includes(o.i)&&!pathKnownBlocked(L,p,o.c))
   .map(o=>({...o,score:o.v*1.5+Math.hypot(o.c.x-p.x,o.c.y-p.y)*.6+rand()*.4})).sort((a,b)=>a.score-b.score);
  if(cand.length){const o=cand[0];target={id:'cell-'+o.i,kind:'cell',name:o.v?'a familiar patch':'an unexplored patch',...o.c};}
  else goal='visit';
 }
 if(goal==='visit'){
  const opts=p.pois.filter(o=>o.id!==p.lastTarget&&!pathKnownBlocked(L,p,o));
  const list=opts.length?opts:p.pois;
  const w=list.map(o=>Math.exp(((L.value[o.id]??.3)+(o.kind==='moon-pool'&&(m.energy??60)<50?.4:0))/.3));
  let x=rand()*w.reduce((a,b)=>a+b,0);target=list[list.length-1];
  for(let i=0;i<list.length;i++){x-=w[i];if(x<=0){target=list[i];break;}}
 }
 if(goal==='play'){
  const a=rand()*Math.PI*2,r=.18+rand()*.18;
  const to={x:clamp(p.x+Math.cos(a)*r,-.92,.92),y:clamp(p.y+Math.sin(a)*r*.7,-.55,.6)};
  target={id:'play-'+cellOf(to.x,to.y),kind:'play',name:'a spark to chase',...to};
 }
 L.goal=goal;L.goals[goal]=(L.goals[goal]||0)+1;L.decisions++;
 return {goal,target,utilities:u};
}

/** The user called or tapped: walk to the front-centre spot (the only time it comes over). */
export function callTarget(){return {id:'call',kind:'call',name:'you',x:0,y:.55};}

/** Record entering a cell. Returns 'blocked' (rift) or 'ok'; new=true when first visit ever. */
export function enterCell(L,cell,rifts){
 if(rifts.includes(cell)){L.moves.blocked++;if(!L.known_blocked.includes(cell))L.known_blocked.push(cell);return {outcome:'blocked',fresh:false};}
 const fresh=L.cells[cell]===0;L.cells[cell]++;L.moves.succeeded++;return {outcome:'ok',fresh};
}

/** Learn from how a goal ended. reward in [-1,1]. */
export function learn(L,goal,reward,placeId=null){
 const r=clamp(reward,-1,1);
 if(placeId&&/^[a-z-]+-\d+$/.test(placeId))L.value[placeId]=+(((L.value[placeId]??.3)+ALPHA*(r-(L.value[placeId]??.3)))).toFixed(4);
 if(L.prefs[goal]!=null)L.prefs[goal]=+clamp(L.prefs[goal]+ALPHA*.5*(r-.2),.05,1).toFixed(4);
}

/** Measurable learning summary for the diary and the UI. */
export function learningSummary(L,pois=[]){
 const visited=L.cells.filter(v=>v>0).length;
 const fav=Object.entries(L.value).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]))[0];
 const favPoi=fav?pois.find(o=>o.id===fav[0]):null;
 const total=L.moves.succeeded+L.moves.blocked;
 return {cells_visited:visited,cells_total:L.cells.length,known_rifts:L.known_blocked.length,moves_succeeded:L.moves.succeeded,moves_blocked:L.moves.blocked,
  blocked_rate:total?+(L.moves.blocked/total).toFixed(3):0,favorite_spot:favPoi?favPoi.name:null,favorite_value:fav?+fav[1].toFixed(3):null,
  prefs:{...L.prefs},decisions:L.decisions};
}
