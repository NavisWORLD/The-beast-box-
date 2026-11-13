/**
 * First-person cumulus (Cory, Nov 12 2026: "real cumulus clouds with volume and shading").
 * Each cloud is a painted canvas card made from SEEDED overlapping puffs: a cool shaded underside, sunlit tops, a flat base.
 * Cards sit far out (250-600 units) a few degrees above the horizon in the first-person ground frame, drift slowly on the
 * caller's clock, darken with the one day value and pick up the sky haze with distance. No random calls, no lights. Tier-scaled.
 */
type T=typeof import('three');
export const CLOUDS_LABEL='First-person cumulus · SEEDED painted cards, drift on the world clock';
export function cloudBudget(tier:string){return tier==='GOD'?{cards:26,variants:8,size:256}:tier==='HIGH'?{cards:20,variants:6,size:256}:tier==='MED'?{cards:14,variants:5,size:192}:{cards:7,variants:3,size:128};}
function paint(doc:Document,r:()=>number,W:number){const H=W>>1;const c=doc.createElement('canvas');c.width=W;c.height=H;const x=c.getContext('2d');if(!x)return c;const k=W/256;
 const base=H*.78;const n=16+Math.floor(r()*12);const puffs:{x:number;y:number;r:number}[]=[];
 for(let i=0;i<n;i++){const u=r();const px=W*(.14+.72*(u*.5+r()*.5));const mid=1-Math.abs(px/W-.5)*2;const pr=(14+r()*22+30*mid*r())*k;const py=base-pr*.55-mid*(10+r()*26)*k;puffs.push({x:px,y:py,r:pr});}
 for(const p of puffs){const g=x.createRadialGradient(p.x,p.y+p.r*.15,p.r*.2,p.x,p.y,p.r);g.addColorStop(0,'rgba(150,166,190,0.95)');g.addColorStop(1,'rgba(150,166,190,0)');x.fillStyle=g;x.beginPath();x.arc(p.x,p.y,p.r,0,Math.PI*2);x.fill();}
 for(const p of puffs){const lx=p.x-p.r*.16,ly=p.y-p.r*.22,lr=p.r*.86;const g=x.createRadialGradient(lx-lr*.2,ly-lr*.25,lr*.1,lx,ly,lr);g.addColorStop(0,'rgba(255,255,255,1)');g.addColorStop(.55,'rgba(246,248,252,0.92)');g.addColorStop(1,'rgba(226,232,242,0)');x.fillStyle=g;x.beginPath();x.arc(lx,ly,lr,0,Math.PI*2);x.fill();}
 x.globalCompositeOperation='destination-out';const fb=x.createLinearGradient(0,base-4*k,0,base+8*k);fb.addColorStop(0,'rgba(0,0,0,0)');fb.addColorStop(1,'rgba(0,0,0,1)');x.fillStyle=fb;x.fillRect(0,base-4*k,W,H-base+4*k); /* flat base */
 x.globalCompositeOperation='source-over';return c;}
type Opts={rand:()=>number;tier:string;haze?:number[];plane?:number};
export function addFpClouds(THREE:T,parent:import('three').Object3D,o:Opts){
 const g=new THREE.Group();g.name='fp-clouds';parent.add(g);const B=cloudBudget(o.tier);const r=o.rand;const doc=typeof document!=='undefined'?document:null;
 const tex:any[]=[];if(doc)for(let i=0;i<B.variants;i++){const t=new THREE.CanvasTexture(paint(doc,r,B.size));t.colorSpace=THREE.SRGBColorSpace;tex.push(t);}
 const haze=new THREE.Color().setRGB(...((o.haze||[.74,.85,.96]) as [number,number,number]));const cards:{sp:any;a:number;d:number;el:number;w:number;k:number}[]=[];
 if(tex.length)for(let i=0;i<B.cards;i++){const a=r()*Math.PI*2,d=250+r()*350,el=(2.5+Math.pow(r(),1.6)*16)*Math.PI/180;const m=new THREE.SpriteMaterial({map:tex[i%tex.length],transparent:true,depthWrite:false,fog:false});
  const sp=new THREE.Sprite(m);const w=d*(.16+r()*.22);sp.scale.set(w,w*.5,1);sp.renderOrder=-9;g.add(sp);const k=Math.min(.5,(d-250)/700+.08);cards.push({sp,a,d,el,w:(r()<.5?-1:1)*(.0015+r()*.002),k});}
 const place=(t:number)=>{for(const c of cards){const a=c.a+c.w*t;c.sp.position.set(Math.cos(a)*c.d,Math.tan(c.el)*c.d+(o.plane??1.5),Math.sin(a)*c.d);}};place(0);
 (globalThis as any).__lwFpClouds={label:CLOUDS_LABEL,tier:o.tier,cards:cards.length};
 const col=new THREE.Color();
 return {group:g,update(t:number,day:number,hor?:number[]){place(t);const dk=Math.max(.18,Math.min(1,day));if(hor)haze.setRGB(hor[0],hor[1],hor[2]);for(const c of cards){col.setRGB(1,1,1).lerp(haze,c.k).multiplyScalar(dk);c.sp.material.color.copy(col);}},dispose(){parent.remove(g);for(const t of tex)t.dispose();}};
}
