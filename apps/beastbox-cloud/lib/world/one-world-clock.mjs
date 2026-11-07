// ONE world, ONE clock (Nov 7 2026, Cory's screenshots: Storms 20 vs 19, two different planets).
// Before this, TinyUniverseView and LivingWorld each ran their own grow() loop from genesis, so every page
// was a separate universe. This is the single owner: one state, one interval, one writer of `lw:universe`.
// Growth stays SIMULATED (grow() from lib/universe/tiny-universe.mjs, untouched); genesis stays RECORDED.
// Deterministic: grow() is seeded; no unseeded randomness here. The instance lives on globalThis so route changes,
// remounts and duplicate module copies all share it.
export const ONE_WORLD_KEY='lw:universe';
export const ONE_WORLD_TICK_MS=2000; // LivingWorld's existing TICK_S=2
export const ONE_WORLD_TICK_CAP=4000; // LivingWorld's existing cap
const G=globalThis;
/** Total world clocks ever created in this page (the test/diagnostic receipt: must stay 1). */
export function worldClockCount(){return G.__bbWorldClocks||0;}
export function createWorldClock({genesis,grow,storage=null,tickMs=ONE_WORLD_TICK_MS,cap=ONE_WORLD_TICK_CAP,setTimer=(f,ms)=>setInterval(f,ms),clearTimer=id=>clearInterval(id)}){
 if(!genesis||!grow)throw new Error('genesis and grow are required');
 G.__bbWorldClocks=(G.__bbWorldClocks||0)+1;
 let u=genesis;try{const s=JSON.parse(storage?.getItem(ONE_WORLD_KEY)||'null');if(s&&s.seed===genesis.seed&&s.schema===genesis.schema)u=s;}catch{}
 const subs=new Set();let timer=null;let paused=false;
 const emit=(prev)=>{for(const f of [...subs])try{f(u,prev);}catch{}};
 const step=()=>{if(paused||!u||u.tick>=cap)return;const prev=u;u=grow(u,1);try{storage?.setItem(ONE_WORLD_KEY,JSON.stringify(u));}catch{}emit(prev);};
 const clock={
  seed:genesis.seed,
  get:()=>u,
  subscribe(f){subs.add(f);return()=>subs.delete(f);},
  start(){if(timer==null)timer=setTimer(step,tickMs);return clock;},
  stop(){if(timer!=null){clearTimer(timer);timer=null;}},
  running:()=>timer!=null,
  setPaused(p){paused=!!p;},
  paused:()=>paused,
  step,
 };
 return clock;
}
/** The page-wide singleton. A second call returns the same clock (never a second universe). */
export function oneWorldClock(opts){
 if(G.__bbOneWorld)return G.__bbOneWorld;
 if(!opts)return null;
 G.__bbOneWorld=createWorldClock(opts).start();return G.__bbOneWorld;
}
export function currentWorldClock(){return G.__bbOneWorld||null;}
/** Resolve the shared clock, waiting for the root provider to create it. */
export function whenWorldClock(){const c=currentWorldClock();if(c)return Promise.resolve(c);return new Promise(res=>{const on=()=>{const k=currentWorldClock();if(k){G.removeEventListener?.('beastbox:one-world',on);res(k);}};G.addEventListener?.('beastbox:one-world',on);});}
