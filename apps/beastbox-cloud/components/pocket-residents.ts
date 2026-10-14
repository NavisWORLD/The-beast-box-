import {ARTIST_RESIDENTS,residentView} from '../lib/companion/artist-residents.mjs';
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
     return {r,sprite,shadow,h,phase:i*1.37+seedRandom()*2,radius:r.kind==='trainer'?2.2:2.7+seedRandom()*1.1,speed:(r.kind==='trainer'?.05:.09+seedRandom()*.06)*(i%2?1:-1),src:r.views.front,x:0,z:0};
    });
    const stepResidents=(t:number,theta:number)=>{
     for(const a of residents){
      const ang=a.phase+t*a.speed,x=Math.cos(ang)*a.radius+Math.sin(t*.31+a.phase)*.35,z=Math.sin(ang)*a.radius*.85;
      const heading=Math.atan2(x-a.x,z-a.z);a.x=x;a.z=z;
      const bob=reduced?0:Math.abs(Math.sin(t*3+a.phase))*.06;
      a.sprite.position.set(x,a.h/2+bob,z);a.shadow.position.set(x,-.03,z);
      const view=residentView(a.r,heading,theta);const m=a.sprite.material;
      if(view.src!==a.src){m.map=tex(view.src);m.needsUpdate=true;a.src=view.src;}
      a.sprite.scale.x=Math.abs(a.sprite.scale.x)*(view.flip?-1:1);
     }
    };
    const disturbers=()=>residents.map(a=>({x:a.x,z:a.z,r:.75*a.r.scale,s:2.4}));
    return {stepResidents,texCache,disturbers};
}
