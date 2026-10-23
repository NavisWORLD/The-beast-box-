// Living-world mechanics (ref: ASCII-CRAFT clip), pure + deterministic. Driven by the world field's CST state
// (cst-integrator Lorenz x/y/z + Hebbian strength) and IBM-seeded streams (lwStream). No unseeded randomness.
import {lwStream} from './living-world.mjs';
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
/** weather from the engine: Lorenz state (S.L), Hebbian (S.hebb or S.ch.hebb), field moisture + storm -> rain 0..1, cloud cover 0..1, wind */
export function weatherFrom(F,{moist=.5}={}){const L=F?.S?.L||{x:0,y:0,z:25};const hebb=+(F?.S?.hebb??F?.S?.ch?.hebb??.25)||0;const storm=+(F?.storm||0);
 const lz=clamp(Math.abs(L.z)/45);const cloud=clamp(.15+.55*moist+.35*lz+.4*storm-.15*hebb);const rain=clamp((cloud-.72)*3+storm*.6);
 return {cloud:+cloud.toFixed(3),rain:+rain.toFixed(3),wind:[clamp(L.x/20,-1,1),clamp(L.y/27,-1,1)],source:'cst-integrator Lorenz+Hebbian (SIMULATED)'};}
/** water flows downhill on the field grid: rain adds water, each cell passes water to its lowest neighbour (by surface height), seas fill low basins */
export function createWater(W,H,ground){const N=W*H;return {W,H,N,ground:Float32Array.from(ground),w:new Float32Array(N),steps:0};}
export function stepWater(Wt,{rain=0,dt=1,rate=.5,evap=.002}={}){const {W,H,N,ground,w}=Wt;const nw=Float32Array.from(w);
 for(let k=0;k<N;k++){nw[k]+=rain*.01*dt;}
 for(let j=0;j<H;j++)for(let i=0;i<W;i++){const k=j*W+i;if(nw[k]<=0)continue;const s=ground[k]+nw[k];let best=-1,bs=s;
  for(const [di,dj] of [[1,0],[-1,0],[0,1],[0,-1]]){const jj=j+dj;if(jj<0||jj>=H)continue;const ii=(i+di+W)%W;const kk=jj*W+ii;const ss=ground[kk]+nw[kk];if(ss<bs){bs=ss;best=kk;}}
  if(best>=0){const mv=Math.min(nw[k],(s-bs)*.5*rate);nw[k]-=mv;nw[best]+=mv;}}
 for(let k=0;k<N;k++)nw[k]=Math.max(0,nw[k]-evap*dt);Wt.w.set(nw);Wt.steps++;return Wt;}
export const waterTotal=Wt=>Wt.w.reduce((a,b)=>a+b,0);
/** first-person movement: walk / swim / fly weights blend smoothly; gravity pulls you back to solid ground when you stop flying */
export const MOVE=Object.freeze({g:9.8,flyLift:3.2,swimDepth:-.55,blend:4,maxFly:6});
export function createMover(){return {y:0,vy:0,fly:false,w:{walk:1,swim:0,fly:0}};}
export function stepMover(M,{dt,inWater=false,ground=0,mpu=1}){const g=MOVE.g*mpu;
 if(M.fly){M.vy+=(MOVE.flyLift*mpu-M.y)*dt*2-M.vy*dt*2;}else if(inWater){M.vy+=((MOVE.swimDepth*mpu)-M.y)*dt*3-M.vy*dt*3;}else M.vy-=g*dt;
 M.y+=M.vy*dt;M.y=Math.min(M.y,MOVE.maxFly*mpu);
 const floor=inWater?MOVE.swimDepth*mpu*1.3:ground;if(M.y<floor){M.y=floor;if(M.vy<0)M.vy=0;} // solid ground collision
 const want={walk:!M.fly&&!inWater?1:0,swim:!M.fly&&inWater?1:0,fly:M.fly?1:0};const a=Math.min(1,dt*MOVE.blend);
 for(const k of ['walk','swim','fly'])M.w[k]+=(want[k]-M.w[k])*a;return M;}
/** seeded layouts (cloud puffs, rain streaks, kelp, mountain profile) */
export function seededCloudPuffs(seed,n,unitFrom){const r=lwStream(seed+':clouds');return Array.from({length:n},()=>{const d=unitFrom(r);return {d,puffs:3+Math.floor(r()*4),size:.6+r()*.9,alt:.9+r()*.6,spin:r()*6.283};});}
export function mountainProfile(seed,n=256){const r=lwStream(seed+':mountains');const o=[...Array(5)].map(()=>[r()*6.283,1+Math.floor(r()*6)]);return Array.from({length:n},(_,i)=>{const a=i/n*6.283;let h=0;o.forEach(([p,f],j)=>{h+=Math.abs(Math.sin(a*f+p))/(j+1);});return +(h/2.3).toFixed(4);});}
