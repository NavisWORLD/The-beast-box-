import {motionPersona,createActor,stepActor} from '../lib/companion/film-motion.mjs';
import {UNIVERSE_R} from '../lib/living-core/roam-brain.mjs';
import {renderBeast,blit,SPRITE} from '../public/spark/draw.mjs';
import {depthFar,type Creation} from '../lib/companion/creations.mjs';
type Three=typeof import('three');
/** Every beast saved to this device's bestiary roams the pocket as its own pixel sprite (SEEDED: drawn from its saved genome).
 * They share the artist residents' film motion and ground. The active beast is not repeated here. */
export function addSavedBeastSprites(THREE:Three,scene:import('three').Scene,list:Creation[],reduced:boolean,groundAt:(x:number,z:number)=>number=()=>0){
 const mats:import('three').Material[]=[],texes:import('three').Texture[]=[];
 const items=list.map((c,i)=>{
  const cv=document.createElement('canvas');cv.width=cv.height=SPRITE*2;const ctx=cv.getContext('2d');
  if(ctx){try{blit(ctx,renderBeast(c.genome,Number(c.genome?.stage)||2,'open'),0,0,2);}catch{}}
  const tex=new THREE.CanvasTexture(cv);tex.colorSpace=THREE.SRGBColorSpace;tex.magFilter=THREE.NearestFilter;texes.push(tex);
  const mat=new THREE.SpriteMaterial({map:tex,transparent:true,depthWrite:false});mats.push(mat);
  const h=.8,sprite=new THREE.Sprite(mat);sprite.scale.set(h,h,1);sprite.name=c.id;scene.add(sprite);
  const smat=new THREE.MeshBasicMaterial({color:0x000000,transparent:true,opacity:.32,depthWrite:false});mats.push(smat);
  const shadow=new THREE.Mesh(new THREE.CircleGeometry(.3,20),smat);shadow.rotation.x=-Math.PI/2;scene.add(shadow);
  const home=(i/Math.max(1,list.length))*Math.PI*2+1.9,hr=3.2+(i%3)*.35;
  const actor=createActor(motionPersona({id:c.id,seed:c.seed}),{x:Math.cos(home)*hr,z:Math.sin(home)*hr*.85,radius:.9,seed:c.id,universe:UNIVERSE_R});
  return {c,sprite,shadow,smat,mat,h,actor,x:0,z:0};
 });
 let last=0;
 const step=(t:number,cam?:{x:number;z:number})=>{
  const dt=Math.max(0,Math.min(.05,t-last));last=t;
  for(const a of items){
   const p=stepActor(a.actor,reduced?0:dt,{lookAt:cam||{x:0,z:0},reduced});a.x=p.x;a.z=p.z;
   const far=cam?depthFar(Math.hypot(p.x-cam.x,p.z-cam.z)):0;
   const k=1-.14*far,hy=a.h*p.sy*k;const gy=groundAt(p.x,p.z);
   a.sprite.position.set(p.x,gy+hy/2+p.lift,p.z);a.shadow.position.set(p.x,gy+.005,p.z);
   a.shadow.scale.setScalar((1-Math.min(.5,p.lift*.9))*(1+.25*far));a.smat.opacity=.34-.14*far;
   a.sprite.scale.set(a.h*p.sx*k,hy,1);a.mat.rotation=-p.lean;
   // cool, dim tint with distance (atmospheric depth)
   (a.mat as any).color.setRGB(1-.34*far,1-.3*far,1-.1*far);
  }
 };
 return {step,disturbers:()=>items.map(a=>({x:a.x,z:a.z,r:.6,s:2,id:a.c.id})),pickables:()=>items.map(a=>({id:a.c.id,obj:a.sprite as import('three').Object3D})),
  dispose:()=>{for(const a of items){scene.remove(a.sprite);scene.remove(a.shadow);a.shadow.geometry.dispose();}mats.forEach(m=>m.dispose());texes.forEach(t=>t.dispose());}};
}
