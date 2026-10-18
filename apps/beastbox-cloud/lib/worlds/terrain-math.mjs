/** Home-world terrain (pure, no three.js): a large analytic heightfield that stays flat under the cage,
 * rolls into gentle hills where creatures roam (r 20..30) and swells into big hills/valleys out to the horizon.
 * Caves are carved hill mounds whose tunnel floors stay walkable so creatures can roam inside. */
export const TERRAIN=Object.freeze({flatR:19,roamR:30,size:280,chunks:8,segHigh:36,segLow:20,treesHigh:900,treesLow:260});
const h1=(x,z)=>Math.sin(x*.061+1.3)*Math.cos(z*.053-.7)+.5*Math.sin(x*.137-z*.11+2.1)+.25*Math.sin(x*.29+z*.31);
/** World-unit cave sites (entrance faces the centre; tunnel runs outward and down). */
export const CAVES=Object.freeze([
 {id:'cave-ember-hollow',label:'Ember hollow',a:.35,r:23.5,len:7,w:1.6,color:'#ff9a5a'},
 {id:'cave-whisper-deep',label:'Whisper deep',a:2.45,r:23,len:8,w:1.8,color:'#7af0ff'},
 {id:'cave-root-vault',label:'Root vault',a:4.4,r:24,len:6.5,w:1.5,color:'#9dff9a'},
]);
/** local cave coords: s along tunnel (0 = mouth), t across. */
export function caveLocal(c,x,z){const ux=Math.cos(c.a),uz=Math.sin(c.a),ox=ux*c.r,oz=uz*c.r;const dx=x-ox,dz=z-oz;return {s:dx*ux+dz*uz,t:-dx*uz+dz*ux};}
function hillRaw(x,z){const r=Math.hypot(x,z);if(r<=TERRAIN.flatR)return 0;const k=Math.min(1,(r-TERRAIN.flatR)/11),e=k*k*(3-2*k);
 const near=e*(.9+.6*h1(x,z));const far=Math.max(0,r-TERRAIN.roamR);return Math.max(0,near+far*far*.0042*(1.3+h1(x*.5,z*.5))+far*.06*h1(x*1.7,z*1.7));}
/** Cave tunnel floor depth (negative) inside a footprint, else null. */
export function caveFloor(x,z){for(const c of CAVES){const L=caveLocal(c,x,z);if(L.s>-.4&&L.s<c.len&&Math.abs(L.t)<c.w)return {cave:c,y:-.06-Math.max(0,L.s)*.05};}return null;}
/** Walkable ground height (cave floors override the mound above them). */
export function terrainHeight(x,z){const f=caveFloor(x,z);if(f)return f.y;return hillRaw(x,z)+caveMound(x,z);}
/** Visible hill height (mound included, used for the mesh). */
export function surfaceHeight(x,z){return hillRaw(x,z)+caveMound(x,z);}
export function caveMound(x,z){let m=0;for(const c of CAVES){const L=caveLocal(c,x,z);if(L.s<c.len&&L.s>-8&&Math.abs(L.t)<c.w*1.1)continue;// open approach + tunnel corridor (tube is the roof)
  const ds=Math.max(0,L.s<0?-L.s*1.6:L.s-c.len),dt=Math.max(0,Math.abs(L.t)-c.w*1.4);const d=Math.hypot(ds,dt);m=Math.max(m,4.2*Math.exp(-d*d*.08)*Math.min(1,(L.s+1.5)/1.5>0?1:0));}return m;}
/** World-space cave mouth/tip points (roam goals). */
export function caveSpots(){return CAVES.map(c=>({id:c.id,kind:'cave',label:c.label,x:Math.cos(c.a)*(c.r+c.len*.6),z:Math.sin(c.a)*(c.r+c.len*.6),mouth:{x:Math.cos(c.a)*c.r,z:Math.sin(c.a)*c.r},color:c.color}));}
export function rng(seed){let a=[...String(seed)].reduce((h,ch)=>Math.imul(h^ch.charCodeAt(0),16777619),2166136261)>>>0;return()=>{a=(a+0x6D2B79F5)>>>0;let t=a;t=Math.imul(t^t>>>15,t|1);t^=t+Math.imul(t^t>>>7,t|61);return((t^t>>>14)>>>0)/4294967296;};}
/** Forest placement: dense on hills, never on the cage/flat play floor, never blocking cave mouths. */
export function forest(n,seed='home-forest'){const r=rng(seed),out=[];let guard=0;while(out.length<n&&guard++<n*8){const a=r()*6.2832,d=21+Math.pow(r(),.7)*(TERRAIN.size*.45-21);const x=Math.cos(a)*d,z=Math.sin(a)*d;
 if(caveFloor(x,z))continue;let nearMouth=false;for(const c of CAVES){const L=caveLocal(c,x,z);if(L.s<1&&L.s>-5&&Math.abs(L.t)<3)nearMouth=true;}if(nearMouth)continue;
 const cl=.5+.5*Math.sin(x*.09)*Math.cos(z*.08);if(r()>.35+cl*.65)continue;out.push({x,z,y:surfaceHeight(x,z),s:2.2+r()*3.8+(d>40?r()*4:0),rot:r()*6.2832,k:r()});}return out;}
