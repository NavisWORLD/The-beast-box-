/**
 * Small classical 2D stable-fluids solver (Stam 1999 style: semi-Lagrangian advection,
 * Jacobi diffusion, pressure projection) on a coarse periodic grid. Purely cosmetic and
 * classical: it drives creature secondary motion and particles, nothing else.
 *
 * Inspiration only: Mello, Collura, Stoudenmire, Levy, "Magic of the Well: assessing quantum
 * resources of fluid dynamics data", arXiv:2512.03177 (shear flows whose complexity grows with
 * Reynolds number and shrinks with shear width). Nothing quantum runs here.
 *
 * Mapping: chaos (0..1) -> Reynolds number Re (low viscosity = more swirl);
 *          storm (0..1) -> thinner shear layer (sharper, more unstable flow).
 */
const clamp=(x,a,b)=>Math.min(b,Math.max(a,x));
export function flowParams({storm=0.3,chaos=0.3}={}){
 const s=clamp(+storm||0,0,1),c=clamp(+chaos||0,0,1);
 return {reynolds:Math.round(200+c*4800),shearWidth:+(0.18-0.13*s).toFixed(3),force:0.6+1.4*s};
}
export function createFluid(n=24,{storm=0.3,chaos=0.3,seed=1}={}){
 const N=n*n,f={n,u:new Float32Array(N),v:new Float32Array(N),u0:new Float32Array(N),v0:new Float32Array(N),p:new Float32Array(N),div:new Float32Array(N),t:0,seed,params:flowParams({storm,chaos})};
 // Kelvin-Helmholtz-like double shear layer with a small seeded perturbation.
 let r=(seed>>>0)||1;const rnd=()=>((r=(Math.imul(r,1664525)+1013904223)>>>0)/4294967296);
 const w=f.params.shearWidth;
 for(let j=0;j<n;j++)for(let i=0;i<n;i++){const y=j/n,k=i+j*n;
  f.u[k]=Math.tanh((y-.25)/w)-Math.tanh((y-.75)/w)-1;f.v[k]=.05*Math.sin(2*Math.PI*(i/n+rnd()*.1));}
 return f;
}
export function setFlow(f,{storm,chaos}){f.params=flowParams({storm,chaos});return f;}
const idx=(n,i,j)=>(((i%n)+n)%n)+(((j%n)+n)%n)*n;
function sample(n,a,x,y){const i=Math.floor(x),j=Math.floor(y),fx=x-i,fy=y-j;
 return (1-fx)*(1-fy)*a[idx(n,i,j)]+fx*(1-fy)*a[idx(n,i+1,j)]+(1-fx)*fy*a[idx(n,i,j+1)]+fx*fy*a[idx(n,i+1,j+1)];}
export function stepFluid(f,dt){
 const {n,u,v,u0,v0,p,div}=f;dt=clamp(dt||0,0,.05);f.t+=dt;
 const nu=1/f.params.reynolds*n, a=nu*dt*n; // grid-scaled viscosity
 // gentle forcing that keeps the shear alive
 const F=f.params.force*dt*.15,w=f.params.shearWidth;
 for(let j=0;j<n;j++){const y=j/n,tgt=Math.tanh((y-.25)/w)-Math.tanh((y-.75)/w)-1;for(let i=0;i<n;i++){const k=i+j*n;u[k]+=F*(tgt-u[k]);}}
 // advect (semi-Lagrangian)
 u0.set(u);v0.set(v);
 for(let j=0;j<n;j++)for(let i=0;i<n;i++){const k=i+j*n,x=i-dt*n*u0[k]*.25,y=j-dt*n*v0[k]*.25;u[k]=sample(n,u0,x,y);v[k]=sample(n,v0,x,y);}
 // diffuse (few Jacobi sweeps)
 if(a>0)for(let it=0;it<4;it++){u0.set(u);v0.set(v);
  for(let j=0;j<n;j++)for(let i=0;i<n;i++){const k=i+j*n;
   u[k]=(u0[k]+a*(u0[idx(n,i-1,j)]+u0[idx(n,i+1,j)]+u0[idx(n,i,j-1)]+u0[idx(n,i,j+1)]))/(1+4*a);
   v[k]=(v0[k]+a*(v0[idx(n,i-1,j)]+v0[idx(n,i+1,j)]+v0[idx(n,i,j-1)]+v0[idx(n,i,j+1)]))/(1+4*a);}}
 // project: make divergence-free
 for(let j=0;j<n;j++)for(let i=0;i<n;i++){const k=i+j*n;div[k]=-.5*(u[idx(n,i+1,j)]-u[idx(n,i-1,j)]+v[idx(n,i,j+1)]-v[idx(n,i,j-1)]);p[k]=0;}
 for(let it=0;it<12;it++)for(let j=0;j<n;j++)for(let i=0;i<n;i++){const k=i+j*n;p[k]=(div[k]+p[idx(n,i-1,j)]+p[idx(n,i+1,j)]+p[idx(n,i,j-1)]+p[idx(n,i,j+1)])/4;}
 for(let j=0;j<n;j++)for(let i=0;i<n;i++){const k=i+j*n;u[k]-=.5*(p[idx(n,i+1,j)]-p[idx(n,i-1,j)]);v[k]-=.5*(p[idx(n,i,j+1)]-p[idx(n,i,j-1)]);}
 return f;
}
/** Velocity at normalized (x,y) in [0,1). */
export function velocityAt(f,x,y){return {u:sample(f.n,f.u,x*f.n,y*f.n),v:sample(f.n,f.v,x*f.n,y*f.n)};}
export function divergence(f){let m=0;const {n,u,v}=f;for(let j=0;j<n;j++)for(let i=0;i<n;i++)m=Math.max(m,Math.abs(u[idx(n,i+1,j)]-u[idx(n,i-1,j)]+v[idx(n,i,j+1)]-v[idx(n,i,j-1)]));return m;}
/** storm/chaos from the creature's seed emotions plus the CHSH-game mood (all in 0..1). */
export function stormChaos(em,game){
 const tot=(em?.joy||0)+(em?.curiosity||0)+(em?.fear||0)+(em?.calm||0)+(em?.mischief||0)||1;
 let storm=((em?.fear||0)+(em?.mischief||0))/tot*1.6, chaos=(em?.curiosity||0)/tot*1.8;
 if(game&&Number.isFinite(game.stormDelta))storm+=game.stormDelta;
 return {storm:clamp(storm,0,1),chaos:clamp(chaos,0,1)};
}
