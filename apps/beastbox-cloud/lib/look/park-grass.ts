// Park look PK3: an instanced meadow of wind-swayed blades. Presentation only.
// Placement is seeded (sha256 per chunk, then a small integer stream inside the chunk). No unseeded draws.
// Wind is the Genesis wind phase (seed + one world clock), applied in the vertex shader to the upper part of each blade.
// Reduced motion and LOW hold the blades still. Nothing here reads or writes beast, traveler, clock or signal state.
import {stream01} from './seed.ts';
import {PK_OUT,PK_SAT,type RGB} from './park-palette.ts';

export type GrassTier='LOW'|'MED'|'HIGH'|'GOD';
type GrassBudget={blades:number;radius:number;sway:boolean;costMs:number};
/** Blade counts and reach per tier, from the Park spec (K2): LOW 2k still, MED 8k (phone default), HIGH 25k, GOD 60k. */
export const PARK_GRASS_BUDGET:Readonly<Record<GrassTier,GrassBudget>>=Object.freeze({
 LOW:{blades:2000,radius:26,sway:false,costMs:.4},
 MED:{blades:8000,radius:36,sway:true,costMs:.8},
 HIGH:{blades:25000,radius:50,sway:true,costMs:1.4},
 GOD:{blades:60000,radius:66,sway:true,costMs:2.0},
});
export const PARK_GRASS_LABEL='Grass sway · SIMULATED';
const CHUNKS=16;

export function grassBudget(tier:string):GrassBudget{
 return (PARK_GRASS_BUDGET as Record<string,GrassBudget>)[tier]||PARK_GRASS_BUDGET.MED;
}

/** Integer stream seeded from one sha256 draw. Same key, same sequence. */
export function seededStream(key:string){
 let a=Math.floor(stream01(key)*4294967296)>>>0;
 return ()=>{
  a=(a+0x6D2B79F5)>>>0;
  let t=a;
  t=Math.imul(t^(t>>>15),t|1);
  t^=t+Math.imul(t^(t>>>7),t|61);
  return ((t^(t>>>14))>>>0)/4294967296;
 };
}

/**
 * Seeded blade layout on the dry ground. Returns offsets (x,y,z) and params (yaw, height, width, tint).
 * Blades are denser near the eye and thin out toward the reach, where the shader fades them into the meadow colour.
 */
/** Clump field 0..1 (pure, deterministic): patches a few metres across. */
export function clumpAt(x:number,z:number){const a=Math.sin(x*.83+z*.31)*Math.sin(z*.77-x*.27+1.3),b=Math.sin(x*2.3+1.7)*Math.sin(z*2.1+.4);const v=.5+.38*a+.12*b;return Math.min(1,Math.max(0,v));}
export function layoutGrass(o:{seed:string;tier:string;heightAt:(x:number,z:number)=>number;wetAt?:(x:number,z:number)=>boolean;wornAt?:(x:number,z:number)=>number}){
 const b=grassBudget(o.tier);
 const offsets=new Float32Array(b.blades*3),params=new Float32Array(b.blades*4);
 let n=0;
 const per=Math.ceil(b.blades/CHUNKS);
 for(let c=0;c<CHUNKS&&n<b.blades;c++){
  const r01=seededStream(o.seed+':park-grass:'+c);
  const a0=c/CHUNKS*Math.PI*2,a1=(c+1)/CHUNKS*Math.PI*2;
  let made=0,tries=0;
  while(made<per&&n<b.blades&&tries<per*3){
   tries++;
   const a=a0+(a1-a0)*r01();
   const r=.9+(b.radius-.9)*Math.pow(r01(),.8);
   const x=Math.cos(a)*r,z=Math.sin(a)*r;
   const yaw=r01()*Math.PI,h=.24+r01()*.26,w=.035+r01()*.03,tint=r01();
   if(o.wetAt?.(x,z))continue;
   /* Nov 12 (Cory: 'clumpy and patchy, no uniform carpet'): a deterministic clump field makes tall lush tufts and short dry patches, with matching tint; the valley path wears the blades short or bare */
   const cl=clumpAt(x,z);const worn=o.wornAt?o.wornAt(x,z):0;if(worn>.8&&tint<.85)continue;
   offsets[n*3]=x;offsets[n*3+1]=o.heightAt(x,z);offsets[n*3+2]=z;
   params[n*4]=yaw;params[n*4+1]=h*(.55+.85*cl)*(1-.75*worn);params[n*4+2]=w;params[n*4+3]=tint*.45+cl*.55;
   n++;made++;
  }
 }
 return {count:n,offsets:offsets.subarray(0,n*3),params:params.subarray(0,n*4),radius:b.radius,sway:b.sway};
}

const VERT=`attribute vec3 aOffset;attribute vec4 aParams;
uniform float uPhase,uAmp,uSway,uRadius;uniform vec3 uEye;
varying float vT,vTint,vFade,vGust;
void main(){
 float t=position.y;
 float h=aParams.y,w=aParams.z;
 float d=length(aOffset.xz-uEye.xz);
 float fade=1.0-smoothstep(uRadius*.6,uRadius,d);
 vec3 p=vec3(position.x*w*(1.0-t*.85),t*h*mix(.2,1.0,fade),0.0);
 float cs=cos(aParams.x),sn=sin(aParams.x);
 p=vec3(p.x*cs,p.y,-p.x*sn);
 float wave=sin(uPhase+aOffset.x*.21+aOffset.z*.17)+.45*sin(uPhase*1.7+aOffset.x*.53-aOffset.z*.41);
 /* visible gust waves (pallet-town-3d foliageWind idea, MIT): bright packets roll across the meadow along one wind direction */float gust=pow(.5+.5*sin(dot(aOffset.xz,vec2(.31,.17))-uPhase*1.3),5.0)*(.65+.35*sin(dot(aOffset.xz,vec2(-.07,.13))+uPhase*.21));vGust=gust;
 float lean=(wave*uAmp*uSway*1.7+(aParams.w-.5)*.22+gust*.55*step(1e-5,uAmp)*uSway)*t*t;
 p.x+=lean*h;p.z+=lean*h*.35;p.y-=abs(lean)*h*.3;
 vT=t;vTint=aParams.w;vFade=fade;
 gl_Position=projectionMatrix*modelViewMatrix*vec4(aOffset+p,1.0);
}`;
const FRAG=`uniform vec3 uRoot,uTip,uGround;uniform float uDay;
varying float vT,vTint,vFade,vGust;
${PK_SAT}void main(){
 vec3 c=mix(uRoot,uTip,smoothstep(.0,.65,vT));
 c*=.8+.4*vTint;c=mix(c,c*vec3(1.16,1.14,.98),vGust*smoothstep(.3,1.0,vT)); /* clump tint, and gust sheen on the bent tips */
 c=mix(uGround,c,smoothstep(.0,.3,vT)*.7+.3);
 c=mix(uGround,c,vFade);
 c*=mix(.85,1.0,clamp(uDay,0.0,1.0));
 gl_FragColor=vec4(pkLin(pkSat(c,1.2)),1.0);
${PK_OUT}}`;

/** Build the meadow mesh. One draw call: a 5-vertex blade instanced over the seeded layout. */
export function buildParkGrass(THREE:typeof import('three'),o:{seed:string;tier:string;heightAt:(x:number,z:number)=>number;wetAt?:(x:number,z:number)=>boolean;wornAt?:(x:number,z:number)=>number}){
 const L=layoutGrass(o);
 const g=new THREE.InstancedBufferGeometry();
 g.setAttribute('position',new THREE.Float32BufferAttribute([-1,0,0, 1,0,0, -.75,.5,0, .75,.5,0, 0,1,0],3));
 g.setIndex([0,1,2, 1,3,2, 2,3,4]);
 g.setAttribute('aOffset',new THREE.InstancedBufferAttribute(new Float32Array(L.offsets),3));
 g.setAttribute('aParams',new THREE.InstancedBufferAttribute(new Float32Array(L.params),4));
 g.instanceCount=L.count;
 const uniforms={
  uPhase:{value:0},uAmp:{value:0},uSway:{value:L.sway?1:0},uRadius:{value:L.radius},
  uEye:{value:new THREE.Vector3()},
  uRoot:{value:new THREE.Color()},uTip:{value:new THREE.Color()},uGround:{value:new THREE.Color()},uDay:{value:1},
 };
 const mat=new THREE.ShaderMaterial({uniforms,vertexShader:VERT,fragmentShader:FRAG,side:THREE.DoubleSide,fog:false});
 mat.name='park:grass';
 const mesh=new THREE.Mesh(g,mat);
 mesh.name='park-grass';mesh.frustumCulled=false;mesh.renderOrder=1;
 mesh.userData={label:PARK_GRASS_LABEL,count:L.count,tier:o.tier,seed:o.seed};
 return {mesh,uniforms,count:L.count};
}

function setC(c:{setRGB:(r:number,g:number,b:number)=>void},v:RGB){c.setRGB(v[0],v[1],v[2]);}
/** Per-frame: wind from the Genesis wind uniforms (read only), colours from the Park grade. */
export function syncParkGrass(u:ReturnType<typeof buildParkGrass>['uniforms'],w:{phase:number;amp:number;reduced?:boolean},grade:{grassRoot:RGB;grassTip:RGB;meadow:RGB;nightGround:RGB;day:number},eye?:{x:number;y:number;z:number}){
 u.uPhase.value=w.phase;u.uAmp.value=w.reduced?0:w.amp;
 setC(u.uRoot.value,grade.grassRoot);setC(u.uTip.value,grade.grassTip);
 const d=grade.day;
 setC(u.uGround.value,[grade.nightGround[0]+(grade.meadow[0]-grade.nightGround[0])*d,grade.nightGround[1]+(grade.meadow[1]-grade.nightGround[1])*d,grade.nightGround[2]+(grade.meadow[2]-grade.nightGround[2])*d]);
 u.uDay.value=d;
 if(eye)u.uEye.value.set(eye.x,eye.y,eye.z);
}
