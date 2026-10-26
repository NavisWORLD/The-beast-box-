/**
 * Pocket sand & fluid layer. Physics adapted from Cory Davis's MIT "Genesis Engine" CodePen
 * (codepen.io/cory-davis-the-builder/pen/bNpXqmm): per-particle velocity integration, pull
 * toward the nearest attractor, 0.99 drag and (1-0.1·dt) damping, plus the Particlizer's
 * spring back to an original position. Added here: creature disturbance (repulsion + swirl).
 * SIMULATED WORLD SEEDED FROM RECORDED MEASUREMENTS: the seed is the Beast's recorded seed; when
 * the Beast has its own validated Azure simulator receipt, its 4 recorded counts weight the wells.
 * Nothing is measured live and no receipt is invented.
 */
export const SAND_LABEL='IBM seed RECORDED on IBM hardware · Rigetti growth SIMULATED · where the world places things is SEEDED';
import {seededRng,clampDt,genesisDrag} from './physics/cst-integrator.mjs';
/** Seeded PRNG: the shared CST integrator one (bit-identical to the previous local copy). */
export const rngFrom=seededRng;
/** Adaptive particle budget: phones and reduced-motion get far fewer. */
export function sandBudget({width=1024,low=false,reduced=false,cores=4}={}){
 if(reduced)return 260;if(low||width<600)return 700;return cores>=8&&width>=1200?2400:1500;
}
const COUNT_KEYS=['00','01','10','11'];
/** Well weights from a validated receipt's counts (or even weights with no receipt). */
export function wellWeights(counts){
 if(!counts)return [1,1,1,1];const total=COUNT_KEYS.reduce((a,k)=>a+(Number(counts[k])||0),0);
 return total>0?COUNT_KEYS.map(k=>4*(Number(counts[k])||0)/total):[1,1,1,1];
}
export function createSandField({seed,count,half=4.3,counts=null}){
 const rnd=rngFrom('sand:'+(seed||'beastbox-visual-preview'));
 const pos=new Float32Array(count*3),vel=new Float32Array(count*3),home=new Float32Array(count*3),kind=new Uint8Array(count);
 const wells=COUNT_KEYS.map((_,i)=>{const a=i*Math.PI/2+rnd()*.8;const r=1.6+rnd()*1.9;return {x:Math.cos(a)*r,y:.05,z:Math.sin(a)*r,w:1};});
 const field={pos,vel,home,kind,wells,count,half,receipt:false,environment:false,envMult:null,counts:null,
  setCounts(c){field.counts=c||null;const w=field.envMult?field.envMult:wellWeights(c);wells.forEach((well,i)=>well.w=w[i]);field.receipt=Boolean(c);},
  /** Consent-based environment tilt (numbers only): weights = the receipt weights x the measured tilt. null restores the receipt weights. */
  setEnvironment(weights){field.envMult=Array.isArray(weights)&&weights.length===4&&weights.every(Number.isFinite)?weights:null;const w=field.envMult||wellWeights(field.counts);wells.forEach((well,i)=>well.w=w[i]);field.environment=Boolean(field.envMult);},
  step(dt,disturbers=[]){
   const d=clampDt(dt),k=genesisDrag(d);
   for(let i=0;i<count;i++){
    const j=i*3;let x=pos[j],y=pos[j+1],z=pos[j+2],vx=vel[j],vy=vel[j+1],vz=vel[j+2];
    // nearest attractor pull (Genesis Engine gravity-to-nearest), weighted by recorded counts
    let best=wells[0],bd=1e9;for(const w of wells){const q=(w.x-x)**2+(w.z-z)**2;if(q<bd){bd=q;best=w;}}
    const inv=1/Math.sqrt(bd+.25),g=(kind[i]?.35:.18)*best.w;
    vx+=(best.x-x)*inv*g*d;vz+=(best.z-z)*inv*g*d;
    // swirl around the well: fluid particles circulate, sand settles
    if(kind[i]){vx+=-(best.z-z)*inv*.22*d;vz+=(best.x-x)*inv*.22*d;}
    // spring to original position (Particlizer originalPos) + gravity to the floor for sand
    vx+=(home[j]-x)*.35*d;vz+=(home[j+2]-z)*.35*d;vy+=(home[j+1]-y)*(kind[i]?.9:1.6)*d-(kind[i]?0:.6)*d;
    // creatures disturb the field
    for(const c of disturbers){const dx=x-c.x,dz=z-c.z,q=dx*dx+dz*dz,R=c.r*c.r;if(q<R&&q>1e-6){const f=(1-q/R)*c.s*d/Math.sqrt(q);vx+=dx*f;vz+=dz*f;vy+=f*.6;}}
    vx*=k;vy*=k;vz*=k;x+=vx*d;y+=vy*d;z+=vz*d;
    if(y<0){y=0;vy=Math.abs(vy)*.2;}
    if(x<-half||x>half){vx=-vx*.5;x=Math.max(-half,Math.min(half,x));}
    if(z<-half||z>half){vz=-vz*.5;z=Math.max(-half,Math.min(half,z));}
    pos[j]=x;pos[j+1]=y;pos[j+2]=z;vel[j]=vx;vel[j+1]=vy;vel[j+2]=vz;
   }
  }};
 for(let i=0;i<count;i++){const j=i*3;kind[i]=rnd()<.42?1:0;
  const x=(rnd()-.5)*2*half*.94,z=(rnd()-.5)*2*half*.94,y=kind[i]?.15+rnd()*.9:rnd()*.05;
  home[j]=pos[j]=x;home[j+1]=pos[j+1]=y;home[j+2]=pos[j+2]=z;}
 if(counts)field.setCounts(counts);
 return field;
}
/** Only a Beast's OWN mapped receipt counts; the generic fallback receipt is not attributed to it. */
export function ownReceiptPath(path){return typeof path==='string'&&path.startsWith('/spark/azure-')&&path!=='/spark/azure-rigetti-qvm-20261009.json'?path:null;}
