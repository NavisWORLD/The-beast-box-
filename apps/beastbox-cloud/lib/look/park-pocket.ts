// Park look for the pocket (the home window's software-GL fallback and the /beast-cage pocket explorer).
// Presentation only: a cheap day sky with painted clouds and a sun disc on the ONE sun, plus the Park grade for the
// pocket's own lights and fog. It never reads or writes world, beast, loop or signal state. No unseeded draws: cloud
// layout comes from the sha256 stream (lib/look/seed.ts). Cheap on purpose: vertex colours and a few sprites, so a
// CPU rasteriser draws it as easily as a phone.
import {stream01} from './seed.ts';
import {parkGrade,hexRgb,PARK_DAY,PARK_NIGHT,type ParkGrade,type RGB} from './park-palette.ts';

export const PARK_POCKET_LABEL='Park sky · SIMULATED clouds';
/** Clouds per tier. Low keeps a handful. */
export function pocketCloudCount(low:boolean){return low?7:14;}

const lin=(c:RGB):RGB=>[Math.pow(c[0],2.2),Math.pow(c[1],2.2),Math.pow(c[2],2.2)];

/** Sun elevation in degrees from a one-sun direction (y up). */
export function elevationOf(dir:ArrayLike<number>){const y=Number(dir[1]);return Math.asin(Math.max(-1,Math.min(1,Number.isFinite(y)?y:0)))*180/Math.PI;}

/** Seeded cloud layout: azimuth, height, scale. Same seed, same sky. */
export function cloudLayout(seed:string,n:number){
 const out:{az:number;el:number;s:number;w:number}[]=[];
 for(let i=0;i<n;i++){
  const k=seed+':park-pocket:cloud:'+i;
  out.push({az:stream01(k+':az')*Math.PI*2,el:.1+stream01(k+':el')*.38,s:.7+stream01(k+':s')*.9,w:1.6+stream01(k+':w')*1.2});
 }
 return out;
}

function cloudTexture(THREE:typeof import('three'),seed:string){
 if(typeof document==='undefined')return null;
 const c=document.createElement('canvas');c.width=256;c.height=128;
 const g=c.getContext('2d');
 if(g){
  // a painted cumulus: overlapping soft puffs, lit top, cool underside (Park cloud lit #E8FCFE, shade from the sky fill)
  for(let i=0;i<9;i++){
   const k=seed+':park-pocket:puff:'+i;
   const x=48+stream01(k+':x')*160,y=58+stream01(k+':y')*30-(i%3)*6,r=26+stream01(k+':r')*26;
   const grd=g.createRadialGradient(x,y-r*.35,r*.15,x,y,r);
   grd.addColorStop(0,'rgba(255,255,255,1)');grd.addColorStop(.55,'rgba(232,252,254,.95)');grd.addColorStop(.85,'rgba(190,225,240,.55)');grd.addColorStop(1,'rgba(190,225,240,0)');
   g.fillStyle=grd;g.beginPath();g.arc(x,y,r,0,Math.PI*2);g.fill();
  }
 }
 const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t;
}
function discTexture(THREE:typeof import('three')){
 if(typeof document==='undefined')return null;
 const c=document.createElement('canvas');c.width=c.height=128;
 const g=c.getContext('2d');
 if(g){const grd=g.createRadialGradient(64,64,0,64,64,64);grd.addColorStop(0,'rgba(255,255,250,1)');grd.addColorStop(.22,'rgba(255,248,220,1)');grd.addColorStop(.3,'rgba(255,231,168,.55)');grd.addColorStop(1,'rgba(255,231,168,0)');g.fillStyle=grd;g.fillRect(0,0,128,128);}
 const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t;
}

/** The fallback pocket keeps the one sun's direction but never grades below this elevation, so its sky stays Park blue (no lavender dusk band); the living world shows the full day cycle. */
export const POCKET_GRADE_FLOOR_DEG=20;
type Opts={seed:string;low:boolean;radius?:number;sunDir:()=>ArrayLike<number>};

/** Park sky dome + painted clouds + sun disc. Call update() once per frame; it returns the current grade. */
export function addParkPocketSky(THREE:typeof import('three'),scene:{add:(o:any)=>void;remove:(o:any)=>void},opts:Opts){
 const R=opts.radius??60;
 const group=new THREE.Group();group.name='park-pocket-sky';
 const geo=new THREE.SphereGeometry(R,opts.low?16:28,opts.low?10:16);
 const col=new Float32Array(geo.attributes.position.count*3);
 geo.setAttribute('color',new THREE.BufferAttribute(col,3));
 const dome=new THREE.Mesh(geo,new THREE.MeshBasicMaterial({vertexColors:true,side:THREE.BackSide,depthWrite:false,fog:false}));
 dome.name='park-pocket-dome';dome.renderOrder=-20;dome.frustumCulled=false;group.add(dome);
 const ctex=cloudTexture(THREE,opts.seed);
 const clouds=cloudLayout(opts.seed,pocketCloudCount(opts.low)).map(c=>{
  const m=new THREE.SpriteMaterial({map:ctex,transparent:true,depthWrite:false,fog:false,opacity:.95});
  const sp=new THREE.Sprite(m);
  const r=R*.82;
  sp.position.set(Math.cos(c.az)*Math.cos(c.el)*r,Math.sin(c.el)*r,Math.sin(c.az)*Math.cos(c.el)*r);
  sp.scale.set(R*.32*c.s*c.w/1.8,R*.16*c.s,1);sp.renderOrder=-19;sp.name='park-pocket-cloud';group.add(sp);
  return {sp,m,c};
 });
 const sun=new THREE.Sprite(new THREE.SpriteMaterial({map:discTexture(THREE),transparent:true,depthWrite:false,fog:false,blending:THREE.AdditiveBlending}));
 sun.scale.setScalar(R*.22);sun.renderOrder=-18;sun.name='park-pocket-sun';group.add(sun);
 scene.add(group);
 const P=geo.attributes.position as any;
 let lastElev=NaN,rising=true,grade:ParkGrade=parkGrade(45,true);
 const tmp=new THREE.Color(),cloudLit=lin(hexRgb(PARK_DAY.cloudLit)),cloudShade=lin(hexRgb(PARK_NIGHT.skyFill));
 function paint(g:ParkGrade){
  const z=lin(g.zenith),h=lin(g.horizon),hz=lin(g.haze),ground=lin(g.day>.5?hexRgb(PARK_DAY.meadowMid):hexRgb(PARK_NIGHT.grass));
  for(let i=0;i<P.count;i++){
   const y=P.getY(i)/R;
   let c:RGB;
   if(y>=0){const k=Math.pow(Math.min(1,y),.42);c=[h[0]+(z[0]-h[0])*k,h[1]+(z[1]-h[1])*k,h[2]+(z[2]-h[2])*k];}
   else{const k=Math.min(1,-y*4);c=[hz[0]+(ground[0]-hz[0])*k,hz[1]+(ground[1]-hz[1])*k,hz[2]+(ground[2]-hz[2])*k];}
   col[i*3]=c[0];col[i*3+1]=c[1];col[i*3+2]=c[2];
  }
  (geo.attributes.color as any).needsUpdate=true;
 }
 paint(grade);
 return {
  group,
  get grade(){return grade;},
  update(center?:{x:number;y:number;z:number}){
   const d=opts.sunDir();
   const elev=elevationOf(d);
   if(Number.isFinite(lastElev)&&Math.abs(elev-lastElev)>1e-4)rising=elev>lastElev;
   if(!Number.isFinite(lastElev)||Math.abs(elev-lastElev)>.05){grade=parkGrade(Math.max(elev,POCKET_GRADE_FLOOR_DEG),rising);paint(grade);lastElev=elev;}
   if(center)group.position.set(center.x,center.y,center.z);
   const L=Math.hypot(d[0],d[1],d[2])||1;
   sun.position.set(d[0]/L*R*.8,d[1]/L*R*.8,d[2]/L*R*.8);sun.visible=elev>-3;
   const day=grade.day;
   tmp.setRGB(cloudShade[0]+(cloudLit[0]-cloudShade[0])*day,cloudShade[1]+(cloudLit[1]-cloudShade[1])*day,cloudShade[2]+(cloudLit[2]-cloudShade[2])*day);
   for(const c of clouds){c.m.color.copy(tmp);c.m.opacity=.35+.6*day;}
   return grade;
  },
  dispose(){scene.remove(group);geo.dispose();(dome.material as any).dispose();ctex?.dispose();for(const c of clouds)c.m.dispose();sun.material.map?.dispose();sun.material.dispose();},
 };
}

/** Linear Park colours the pocket's lights and fog use for a grade. */
export function pocketLightColors(g:ParkGrade){
 const day=g.day;
 const mix=(a:RGB,b:RGB,t:number):RGB=>[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t];
 return {
  fog:lin(g.haze),
  skyFill:lin(mix(hexRgb('#2B4C8A'),hexRgb(PARK_NIGHT.skyFill),day)),
  groundFill:lin(mix(hexRgb(PARK_NIGHT.grass),hexRgb(PARK_DAY.meadowMid),day)),
  warm:lin(hexRgb(PARK_DAY.warmFill)),
  day,
 };
}
