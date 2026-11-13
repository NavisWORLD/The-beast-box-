/**
 * Rounded props (Cory, Nov 12 2026: "smooth or bevel the crystals, rocks and mushrooms"). PROPS ONLY: never creatures, Zeref or Cory's eyed trees.
 * soft: weld, two midpoint subdivisions, Taubin smoothing (volume-keeping, so pebbles and caps round off instead of shrinking), smooth normals.
 * gem:  the same with lighter smoothing (3 Taubin passes), so crystals keep their spire shape with rounded, soft edges.
 * Pure geometry maths, no random calls. The idea of rounding props comes from pallet-town-3d's Sculpt approach (MIT); this code is our own.
 */
type T=typeof import('three');
export const ROUND_SOFT=/^(rock|moss|cap|stalk)$/;export const ROUND_GEM=/^(crystal|crystal_teal)$/;
export function roundMode(materialName:string|undefined,url:string):'soft'|'gem'|null{if(!/aliveprops|groundcover/.test(url))return null;const n=materialName||'';return ROUND_SOFT.test(n)?'soft':ROUND_GEM.test(n)?'gem':null;}
/** Weld by position (rounded to 1e-4). Returns flat arrays. */
export function weld(pos:ArrayLike<number>,index:ArrayLike<number>|null){const key=new Map<string,number>();const P:number[]=[];const I:number[]=[];const n=index?index.length:pos.length/3;
 for(let k=0;k<n;k++){const i=index?index[k]:k;const x=pos[i*3],y=pos[i*3+1],z=pos[i*3+2];const s=Math.round(x*1e4)+','+Math.round(y*1e4)+','+Math.round(z*1e4);let j=key.get(s);if(j==null){j=P.length/3;P.push(x,y,z);key.set(s,j);}I.push(j);}
 const out:number[]=[];for(let k=0;k<I.length;k+=3){if(I[k]!==I[k+1]&&I[k+1]!==I[k+2]&&I[k]!==I[k+2])out.push(I[k],I[k+1],I[k+2]);}return {P,I:out};}
export function subdivide(P:number[],I:number[]){const P2=P.slice();const em=new Map<string,number>();const mid=(a:number,b:number)=>{const k=a<b?a+'_'+b:b+'_'+a;let m=em.get(k);if(m==null){m=P2.length/3;P2.push((P[a*3]+P[b*3])/2,(P[a*3+1]+P[b*3+1])/2,(P[a*3+2]+P[b*3+2])/2);em.set(k,m);}return m;};
 const I2:number[]=[];for(let k=0;k<I.length;k+=3){const a=I[k],b=I[k+1],c=I[k+2];const ab=mid(a,b),bc=mid(b,c),ca=mid(c,a);I2.push(a,ab,ca,ab,b,bc,ca,bc,c,ab,bc,ca);}return {P:P2,I:I2};}
export function taubin(P:number[],I:number[],iters=6,lam=.5,mu=-.53){const n=P.length/3;const nb:Set<number>[]=Array.from({length:n},()=>new Set());for(let k=0;k<I.length;k+=3){const a=I[k],b=I[k+1],c=I[k+2];nb[a].add(b).add(c);nb[b].add(a).add(c);nb[c].add(a).add(b);}
 let cur=P.slice();for(let it=0;it<iters*2;it++){const f=it%2?mu:lam;const nx=cur.slice();for(let i=0;i<n;i++){const s=nb[i];if(!s.size)continue;let x=0,y=0,z=0;for(const j of s){x+=cur[j*3];y+=cur[j*3+1];z+=cur[j*3+2];}x/=s.size;y/=s.size;z/=s.size;nx[i*3]+=f*(x-cur[i*3]);nx[i*3+1]+=f*(y-cur[i*3+1]);nx[i*3+2]+=f*(z-cur[i*3+2]);}cur=nx;}return cur;}
/** Round one prop geometry in place of the original (returns a new BufferGeometry; position + normal only). */
export function roundGeometry(THREE:T,geo:import('three').BufferGeometry,mode:'soft'|'gem'){
 const pa=geo.getAttribute('position');if(!pa)return geo;const idx=geo.index?Array.from(geo.index.array as ArrayLike<number>):null;let {P,I}=weld(pa.array as ArrayLike<number>,idx);
 if(P.length/3<4000){for(let s=0;s<2;s++)({P,I}=subdivide(P,I));P=taubin(P,I,mode==='gem'?3:6);} /* gem: lighter smoothing, so crystals become soft rounded gems but keep their spire shape */
 const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(P,3));g.setIndex(I);g.computeVertexNormals();g.computeBoundingSphere();return g;}
