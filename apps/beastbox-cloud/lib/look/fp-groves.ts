/**
 * First-person groves (Cory, Nov 12 2026: "a meadow needs trees to read as a world").
 * Places MORE of Cory's own eyed ball trees, bushes and flower drifts from the biome prop sheets (the same cutout art, unchanged)
 * on the first-person hills: clumped into seeded groves at near (~20 m), mid and far distance, kept off the winding valley floor
 * and out of the bay. Far ones take on the sky haze (aerial perspective). Each tree gets a soft round contact shadow on the ground.
 * SEEDED placement (the caller's sha256 stream), no random calls, no lights. Tier-scaled; LOW draws a few near groves only.
 */
type T=typeof import('three');
export type GroveFrame={rect:number[];height_m:number;kind:string};
export type GroveSheet={image:string;frames:Record<string,GroveFrame>};
export const GROVE_LABEL='First-person groves · SEEDED placement of the existing eyed-tree, bush and flower cutouts';
/** Tree / bush / flower counts by tier. LOW stays light but never empty. */
export function groveBudget(tier:string){return tier==='GOD'?{groves:22,trees:420,bushes:260,flowers:360,far:true}:tier==='HIGH'?{groves:18,trees:300,bushes:180,flowers:240,far:true}:tier==='MED'?{groves:14,trees:170,bushes:110,flowers:140,far:true}:{groves:8,trees:60,bushes:40,flowers:50,far:false};}
type Opts={rand:()=>number;tier:string;sheets:Record<string,GroveSheet>;bio:string;heightAt:(x:number,z:number)=>number;
 /** 0 on the valley floor / path, 1 up on the hills */ valley:(x:number,z:number)=>number;inBay:(x:number,z:number)=>boolean;
 /** the valley / view bearing: a few groves are placed to frame it, left and right */ frameBearing?:number;unitsPerMetre:number;haze?:number[]};
export function addFpGroves(THREE:T,parent:import('three').Object3D,o:Opts){
 const g=new THREE.Group();g.name='fp-groves';parent.add(g);const B=groveBudget(o.tier);const r=o.rand;const MU=o.unitsPerMetre;
 const tex=new Map<string,any>();const frameTex=(sheetId:string,f:GroveFrame)=>{const key=sheetId+':'+f.rect.join(',');if(tex.has(key))return tex.get(key);const sh=o.sheets[sheetId];
  const t=new THREE.TextureLoader().load(o.bio+sh.image,(tx:any)=>{const im=tx.image;const [x,y,w,h]=f.rect;tx.repeat.set(w/im.width,h/im.height);tx.offset.set(x/im.width,1-(y+h)/im.height);tx.needsUpdate=true;});
  t.colorSpace=THREE.SRGBColorSpace;tex.set(key,t);return t;};
 const pick=(kinds:string[])=>{const out:{sheet:string;f:GroveFrame}[]=[];for(const id of ['grassland','heartwood_forest']){const sh=o.sheets[id];if(!sh)continue;for(const f of Object.values(sh.frames))if(kinds.includes(f.kind))out.push({sheet:id,f});}return out;};
 const trees=pick(['round_tree']),bushes=pick(['bush']),flowers=pick(['flower']);
 /* soft round contact shadow (one shared canvas texture, radial falloff) */
 const sc=typeof document!=='undefined'?document.createElement('canvas'):null;let shadowTex:any=null;if(sc){sc.width=sc.height=64;const cx=sc.getContext('2d');if(cx){const gr=cx.createRadialGradient(32,32,2,32,32,31);gr.addColorStop(0,'rgba(0,0,0,0.55)');gr.addColorStop(.6,'rgba(0,0,0,0.22)');gr.addColorStop(1,'rgba(0,0,0,0)');cx.fillStyle=gr;cx.fillRect(0,0,64,64);}shadowTex=new THREE.CanvasTexture(sc);}
 const shadowMat=shadowTex?new THREE.MeshBasicMaterial({map:shadowTex,transparent:true,depthWrite:false,toneMapped:false,polygonOffset:true,polygonOffsetFactor:-2}):null;
 const shadowGeo=new THREE.PlaneGeometry(1,1).rotateX(-Math.PI/2);
 const haze=new THREE.Color().setRGB(...((o.haze||[.72,.84,.95]) as [number,number,number]));
 const centres:{x:number;z:number;s:number}[]=[];
 if(o.frameBearing!=null){for(const side of [-1,1])for(let k=0;k<(B.far?3:2);k++){const a=o.frameBearing+side*(.42+r()*.4+k*.12);const d=6.5+k*4+r()*4;const x=Math.cos(a)*d,z=Math.sin(a)*d;if(o.valley(x,z)<.5)continue;centres.push({x,z,s:1.6+r()*1.8});}} /* framing groves on the hills either side of the valley */
 for(let i=0;i<B.groves*6&&centres.length<B.groves;i++){const a=r()*Math.PI*2;const near=centres.length<Math.ceil(B.groves*.35);const d=near?6+r()*10:B.far?14+Math.pow(r(),1.3)*110:12+r()*20;const x=Math.cos(a)*d,z=Math.sin(a)*d;
  if(o.inBay(x,z)||o.valley(x,z)<.6)continue;centres.push({x,z,s:(near?1.4:2.6)+r()*(near?1.6:5)});}
 const placed:{x:number;z:number}[]=[];
 const put=(list:{sheet:string;f:GroveFrame}[],n:number,spread:number,minD:number,valleyMin:number,scaleR:[number,number],shadow:boolean)=>{
  let made=0;for(let i=0;i<n*4&&made<n&&centres.length;i++){const c=centres[Math.floor(r()*centres.length)];const a=r()*Math.PI*2,rr=Math.sqrt(r())*c.s*spread;const x=c.x+Math.cos(a)*rr,z=c.z+Math.sin(a)*rr;const d=Math.hypot(x,z);
   if(d<minD||o.inBay(x,z)||o.valley(x,z)<valleyMin)continue;const pk=list[Math.floor(r()*list.length)];if(!pk)break;const f=pk.f;
   const sc2=scaleR[0]+r()*(scaleR[1]-scaleR[0]);const hU=f.height_m*MU*sc2;const m=new THREE.SpriteMaterial({map:frameTex(pk.sheet,f),transparent:true,alphaTest:.4,depthWrite:true,fog:false});
   const k=Math.min(.55,Math.max(0,(d-12)/110));m.color.setRGB(1,1,1).lerp(haze,k); /* aerial perspective: far trees take on the sky haze */
   const sp=new THREE.Sprite(m);sp.center.set(.5,.02);sp.scale.set(hU*f.rect[2]/f.rect[3],hU,1);const y=o.heightAt(x,z);sp.position.set(x,y-hU*.01,z);g.add(sp);placed.push({x,z});
   if(shadow&&shadowMat&&d<40){const s=new THREE.Mesh(shadowGeo,shadowMat);const w=hU*f.rect[2]/f.rect[3]*.75;s.scale.set(w*1.5,1,w);s.position.set(x+w*.25,y+.01,z);s.renderOrder=-5;g.add(s);}
   made++;}return made;};
 const nT=put(trees,B.trees,1,5.5,.55,[.7,1.45],true);
 const nB=put(bushes,B.bushes,1.25,4.5,.4,[.7,1.4],true);
 const nF=put(flowers,B.flowers,1.6,4.0,.2,[.6,1.3],false);
 (globalThis as any).__lwFpGroves={label:GROVE_LABEL,tier:o.tier,groves:centres.length,trees:nT,bushes:nB,flowers:nF};
 return {group:g,count:()=>({trees:nT,bushes:nB,flowers:nF}),dispose(){parent.remove(g);for(const t of tex.values())t.dispose();shadowTex?.dispose();shadowGeo.dispose();}};
}
