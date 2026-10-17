/** Pure surface-life math (plain JS so node --test runs it directly). */
export const LORENZ={sigma:10,rho:28,beta:8/3};
/** Lorenz step (RK2), with a small CST nudge on rho; exported for tests. */
export function lorenzStep(s,dt,nudge=0){const {sigma,beta}=LORENZ,rho=LORENZ.rho+nudge*4;
 const f=(x,y,z)=>[sigma*(y-x),x*(rho-z)-y,x*y-beta*z];
 const k1=f(s[0],s[1],s[2]);const m=[s[0]+k1[0]*dt/2,s[1]+k1[1]*dt/2,s[2]+k1[2]*dt/2];const k2=f(m[0],m[1],m[2]);
 s[0]+=k2[0]*dt;s[1]+=k2[1]*dt;s[2]+=k2[2]*dt;return s;}
/** Low-frequency heartbeat (lub-dub), 0..1. */
export const heartbeat=(t,hz=1.05)=>{const p=(t*hz)%1;const lub=Math.exp(-Math.pow((p-.08)/.035,2)),dub=.6*Math.exp(-Math.pow((p-.28)/.04,2));return Math.min(1,lub+dub);};
/** Damped spring (critically-ish damped, ~0.6 s settle). */
export function springStep(sp,dt,k=90,c=9){sp.v+=(-k*sp.x-c*sp.v)*dt;sp.x+=sp.v*dt;return sp.x;}

