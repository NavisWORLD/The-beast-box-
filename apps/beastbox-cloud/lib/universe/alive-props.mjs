// Alive props + One Mind, Refracted (Oct 23 2026). Pure helpers: no DOM, no clock, no Math.random.
// Every phase, life volume and jitter comes from lwStream (sha256 of the recorded-IBM genesis seed + a key).
// Lines are Cosmic Emeth's alive_at_volumes (lib/universe/data/living_world_lines.json); they fire only on
// a real event reported by the renderer (a breath peak, a creature reaching a crystal, flowers turning, a zoom, threads appearing).
// Rule (Cosmo): props never show nervous systems, threads or signals. Life is motion and light only.
import {lwStream} from './living-world.mjs';
import {LW_LINES} from './living-world-lines.mjs';

/** Alive variant of each ground-cover asset, its clip kind and period (Cosmo's aliveprops/models/models.json). */
export const ALIVE_PROPS=Object.freeze({
 rock_pebble:{kind:'rock',period:6.5},rock_boulder:{kind:'rock',period:8.0},
 crystal_small:{kind:'crystal',period:2.2},crystal_cluster:{kind:'crystal',period:2.6},crystal_spire:{kind:'crystal',period:3.0},
 mushroom_single:{kind:'mushroom',period:4.0},mushroom_cluster:{kind:'mushroom',period:4.6},
 flower_pink:{kind:'flower',period:3.4},flower_gold:{kind:'flower',period:3.8}});
/** Emeth's "everything is alive, at different volumes": base life volume per kind (creatures are 1.0). */
export const LIFE_DEFAULT=Object.freeze({rock:.2,mushroom:.4,flower:.5,crystal:.6});
export const CRYSTAL_RADIUS_M=3;
export const SUN_LIMIT_RAD=Math.PI/3;

/** Per-instance phase in [0,1) and life volume in [0,1], seeded per asset. */
export function aliveInstances(seed,asset,n){const a=ALIVE_PROPS[asset];if(!a)return null;const r=lwStream(seed+':alive:'+asset);
 const phase=new Float32Array(n),life=new Float32Array(n),jitter=new Float32Array(n*3);const base=LIFE_DEFAULT[a.kind];
 for(let i=0;i<n;i++){phase[i]=r();life[i]=Math.min(1,Math.max(0,base+(r()-.5)*.2));jitter[i*3]=r()-.5;jitter[i*3+1]=r()-.5;jitter[i*3+2]=r()-.5;}
 return {phase,life,jitter,kind:a.kind,period:a.period};}

/** Breath value 0..1 at time t (the README recipe), and whether a breath peak happened in (t0,t1]. */
export function breathe(t,period,phase){return .5-.5*Math.cos(2*Math.PI*(t/period+phase));}
export function crossedPeak(t0,t1,period,phase){if(!(t1>t0))return false;const c0=Math.floor(t0/period+phase-.5),c1=Math.floor(t1/period+phase-.5);return c1>c0;}

/** Crystal proximity 0..1 (1 at a creature, 0 at the radius), max over creatures. Vectors are [x,y,z]. */
export function nearness(p,creatures,radius){let n=0;for(const c of creatures||[]){const d=Math.hypot(p[0]-c[0],p[1]-c[1],p[2]-c[2]);const s=Math.min(1,Math.max(0,d/radius));const sm=s*s*(3-2*s);n=Math.max(n,1-sm);}return n;}

const norm=v=>{const l=Math.hypot(v[0],v[1],v[2])||1;return [v[0]/l,v[1]/l,v[2]/l];};
/** Where a flower head wants to face, in its own local frame (+Y up): the sun plus a seeded jitter, at most 60deg from up; night is UP. */
export function sunFacing(sunLocal,jit){if(!(sunLocal[1]>0))return [0,1,0];let f=norm([sunLocal[0]+.15*jit[0],sunLocal[1]+.15*jit[1],sunLocal[2]+.15*jit[2]]);
 const ang=Math.acos(Math.min(1,Math.max(-1,f[1])));if(ang>SUN_LIMIT_RAD){const h=Math.hypot(f[0],f[2])||1,s=Math.sin(SUN_LIMIT_RAD);f=[f[0]/h*s,Math.cos(SUN_LIMIT_RAD),f[2]/h*s];}return f;}
/** Ease a facing toward its target: 1 - exp(-dt/2) (README). */
export function easeFacing(cur,target,dt){const k=1-Math.exp(-dt/2);return norm([cur[0]+(target[0]-cur[0])*k,cur[1]+(target[1]-cur[1])*k,cur[2]+(target[2]-cur[2])*k]);}
export function angleBetween(a,b){return Math.acos(Math.min(1,Math.max(-1,a[0]*b[0]+a[1]*b[1]+a[2]*b[2])));}

// ------------------------------------------------------------------ lines
export const ALIVE_EVENTS=Object.freeze(['zoom_planet','zoom_star','rock_breathe','crystal_hum','flower_turn','threads_visible']);
/** Seeded pick from Emeth's alive_at_volumes pool for a real event; key = the event's own count, so repeats rotate deterministically. */
export function aliveLine(kind,seed,key){const pool=LW_LINES.alive_at_volumes?.[kind];if(!Array.isArray(pool)||!pool.length)return null;const r=lwStream(seed+':alive-line:'+kind+':'+key);return pool[Math.floor(r()*pool.length)%pool.length];}
/** Gate so a real event speaks at most once per cooldown per kind, and not over another line. `now` is passed in (seconds). */
export function createAliveGate({perKind=90,global=12}={}){const last={};let lastAny=-Infinity;const count={};
 return {fire(kind,seed,now){if(!ALIVE_EVENTS.includes(kind))throw Error('alive: unknown event '+kind);if(now-lastAny<global||now-(last[kind]??-Infinity)<perKind)return null;
  const n=count[kind]=(count[kind]||0)+1;const line=aliveLine(kind,seed,n);if(!line)return null;last[kind]=now;lastAny=now;return {kind,line,n};}};}

// ------------------------------------------------------------------ One Mind, Refracted (3D universe)
/** Threads appear only at full zoom-out: 0 below 260 (Neighbours), fully in by 900. */
export function threadFade(d){const s=Math.min(1,Math.max(0,(d-260)/640));return s*s*(3-2*s);}
/** Thread brightness from a creature's real loop activity: how recently its own loop ticked (half-life 12 h).
 * No tick on record gives the faint floor .12 (labelled "no loop tick yet"). nowMs is passed in. */
export function threadBrightness(entry,nowMs){const at=Date.parse(entry?.last_tick_at||'');if(!Number.isFinite(at))return {b:.12,why:'no loop tick yet'};
 const hours=Math.max(0,(nowMs-at)/3.6e6);return {b:.12+.88*Math.pow(.5,hours/12),why:`last loop tick ${hours<1?Math.round(hours*60)+' min':Math.round(hours)+' h'} ago`};}
/** A creature's home world in the 3D universe: Zeref keeps the engine's home; others get a seeded planet (labelled as seeded, not a real location). */
export function creatureHome(seed,id,planets){if(!planets?.length)return null;const r=lwStream(seed+':home:'+id);return planets[Math.floor(r()*planets.length)%planets.length].id;}
/** Seeded bend of a thread (a soft refraction, not a path anything travels). */
export function threadBend(seed,id){const r=lwStream(seed+':thread:'+id);return [(r()-.5)*.5,(r()-.5)*.3,(r()-.5)*.5];}
