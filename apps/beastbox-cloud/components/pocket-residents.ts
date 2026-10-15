import {ARTIST_RESIDENTS,residentView} from '../lib/companion/artist-residents.mjs';
import {loadResident3D} from './resident-3d';
import {motionPersona,createActor,stepActor} from '../lib/companion/film-motion.mjs';
type Three=typeof import('three');
/** Cory's artist-drawn residents (no quantum seed). They are separate creatures and never the
 * player's active Beast, which stays rendered by the Cage arena in front of the pocket. */
export function addPocketResidents(THREE:Three,scene:import('three').Scene,seedRandom:()=>number,reduced:boolean){
    const loader=new THREE.TextureLoader(),texCache=new Map<string,import('three').Texture>();
    const tex=(src:string)=>{let t=texCache.get(src);if(!t){t=loader.load(src);t.colorSpace=THREE.SRGBColorSpace;texCache.set(src,t);}return t;};
    const residents=ARTIST_RESIDENTS.map((r,i)=>{
     const mat=new THREE.SpriteMaterial({map:tex(r.views.front),transparent:true,depthWrite:false});
     const sprite=new THREE.Sprite(mat);const h=.95*r.scale;sprite.scale.set(h,h,1);sprite.name=r.id;
     const shadow=new THREE.Mesh(new THREE.CircleGeometry(.32*r.scale,20),new THREE.MeshBasicMaterial({color:0x000000,transparent:true,opacity:.32,depthWrite:false}));
     shadow.rotation.x=-Math.PI/2;shadow.position.y=-.03;scene.add(sprite);scene.add(shadow);
     // Film motion: artist-drawn → no quantum seed, so the persona comes from the resident's own id only.
     const home=(i/ARTIST_RESIDENTS.length)*Math.PI*2+.6,hr=r.kind==='trainer'?2.2:2.8;
     const actor=createActor(motionPersona({id:r.id}),{x:Math.cos(home)*hr,z:Math.sin(home)*hr*.85,radius:.9,seed:r.id});
     const slot:{mesh:import('three').Mesh|null}={mesh:null};
     // Frostmitt/Nyxbean: swap the flat sprite for the true-3D visual-hull model once it loads.
     void loadResident3D(THREE,r.id).then(m=>{if(!m)return;slot.mesh=m;scene.add(m);sprite.visible=false;});
     return {r,sprite,shadow,h,actor,slot,phase:i*1.37+seedRandom()*2,radius:r.kind==='trainer'?2.2:2.7+seedRandom()*1.1,speed:(r.kind==='trainer'?.05:.09+seedRandom()*.06)*(i%2?1:-1),src:r.views.front,x:0,z:0};
    });
    let lastT=0;
    const stepResidents=(t:number,theta:number,cam?:{x:number;z:number})=>{
     const dt=Math.max(0,Math.min(.05,t-lastT));lastT=t;
     residents.forEach((a,i)=>{
      // Curious ones turn to the camera; the others turn toward the creature at the habitat centre.
      const look=i%2===0&&cam?cam:{x:0,z:0};
      const p=stepActor(a.actor,reduced?0:dt,{lookAt:look,reduced});a.x=p.x;a.z=p.z;
      const hy=a.h*p.sy;a.sprite.position.set(p.x,hy/2+p.lift,p.z);a.shadow.position.set(p.x,-.03,p.z);
      a.shadow.scale.setScalar(1-Math.min(.5,p.lift*.9));
      const view=residentView(a.r,p.heading+p.head,theta);const m=a.sprite.material;
      if(view.src!==a.src){m.map=tex(view.src);m.needsUpdate=true;a.src=view.src;}
      a.sprite.scale.set(a.h*p.sx*(view.flip?-1:1),hy,1);m.rotation=-p.lean*(view.flip?-1:1);
      const mesh=a.slot.mesh;if(mesh){mesh.position.set(p.x,p.lift,p.z);mesh.scale.set(a.h*1.15*p.sx,a.h*1.15*p.sy,a.h*1.15*p.sx);mesh.rotation.set(p.lean,p.heading+p.head,0,'YXZ');}
     });
    };
    const disturbers=()=>residents.map(a=>({x:a.x,z:a.z,r:.75*a.r.scale,s:2.4}));
    return {stepResidents,texCache,disturbers};
}
