// Realistic-cosmic space backdrop for the orbit view (Cory, Nov 12: "Realistic cosmic"). Presentation only.
// A seeded Milky Way band (dust lanes, warm core), faint blue/teal/magenta nebula clouds and soft round stars in three depth layers.
// Seeded sha256 only (stream01), no clock beyond the one world tick for twinkle, no second sun. A designed look, not a sky survey.
import {stream01} from './seed.ts';
import {PK_OUT} from './park-palette.ts';

export const COSMIC_SKY_LABEL='Space backdrop · SEEDED (designed, not a sky survey)';
/** Tier budget: LOW draws no backdrop (flat Park space blue stays), MED stars + band, HIGH/GOD add nebula detail octaves. */
export function cosmicSkyBudget(tier:string){return tier==='LOW'?{on:false,octaves:0}:tier==='MED'?{on:true,octaves:3}:{on:true,octaves:5};}

const VERT=`varying vec3 vD;void main(){vD=normalize(position);vec4 p=projectionMatrix*modelViewMatrix*vec4(position,1.0);gl_Position=p.xyww;}`;
function frag(oct:number){return `uniform vec3 uAx,uNeb;uniform float uT,uSeed,uA;varying vec3 vD;
float h31(vec3 p){p=fract(p*.1031+uSeed);p+=dot(p,p.yzx+33.33);return fract((p.x+p.y)*p.z);}
float n3(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(mix(h31(i),h31(i+vec3(1,0,0)),f.x),mix(h31(i+vec3(0,1,0)),h31(i+vec3(1,1,0)),f.x),f.y),mix(mix(h31(i+vec3(0,0,1)),h31(i+vec3(1,0,1)),f.x),mix(h31(i+vec3(0,1,1)),h31(i+vec3(1,1,1)),f.x),f.y),f.z);}
float fbm(vec3 p){float s=0.0,a=.5;for(int i=0;i<${Math.max(1,oct)};i++){s+=a*n3(p);p=p*2.03+7.1;a*=.5;}return s;}
vec3 stars(vec3 d,float sc,float th,float sz,float gain){vec3 g=d*sc;vec3 c=floor(g);float h=h31(c);if(h<th)return vec3(0.0);
 vec3 sp=c+.25+.5*vec3(h31(c+11.3),h31(c+27.1),h31(c+53.9));float dd=length(g-sp);float core=1.0-smoothstep(0.0,sz,dd);core*=core;
 float m=h31(c+91.7);float tw=.8+.2*sin(uT*(.6+m)+m*40.0);vec3 tint=mix(vec3(.72,.82,1.0),vec3(1.0,.88,.72),h31(c+5.5));return tint*core*gain*tw*(.45+.9*m);}
void main(){vec3 d=normalize(vD);
 float lat=dot(d,uAx);float band=exp(-pow(lat/.22,2.0));float core=exp(-pow(lat/.07,2.0));
 float n=fbm(d*3.0);float dust=smoothstep(.5,.72,fbm(d*6.5+3.0));
 vec3 mw=(vec3(.42,.5,.78)*band*(.55+.6*n)+vec3(1.0,.86,.66)*core*.55*n)*(1.0-.8*dust*band);
 float nb=smoothstep(.55,.85,fbm(d*1.7+uNeb*4.0));vec3 neb=mix(vec3(.05,.22,.42),vec3(.42,.12,.4),smoothstep(.3,.7,fbm(d*2.3+9.0)))*nb*.45;
 vec3 st=stars(d,420.0,.6,.28,.45)+stars(d,160.0,.78,.16,.9)*(1.0+band)+stars(d,55.0,.94,.06,1.7);
 vec3 c=vec3(.006,.018,.075)+mw*.32+neb*.6+st;
 gl_FragColor=vec4(c*uA,1.0);
${PK_OUT}}`;}

export function addCosmicSky(THREE:typeof import('three'),scene:{add:(o:any)=>void;remove:(o:any)=>void},opts:{seed:string;tier?:()=>string}){
 const s=opts.seed+':cosmic-sky';
 const ax=new THREE.Vector3(stream01(s+':ax:x')*2-1,stream01(s+':ax:y')*2-1,stream01(s+':ax:z')*2-1).normalize();
 const U:any={uAx:{value:ax},uNeb:{value:new THREE.Vector3(stream01(s+':n:x'),stream01(s+':n:y'),stream01(s+':n:z'))},uT:{value:0},uSeed:{value:stream01(s+':seed')},uA:{value:1}};
 let mesh:any=null,built='';
 function build(tier:string){
  if(mesh){scene.remove(mesh);mesh.geometry.dispose();mesh.material.dispose();mesh=null;}
  const B=cosmicSkyBudget(tier);built=tier;if(!B.on)return;
  const m=new THREE.ShaderMaterial({uniforms:U,vertexShader:VERT,fragmentShader:frag(B.octaves),side:THREE.BackSide,depthWrite:false,depthTest:true,fog:false});m.name='cosmic-sky';
  mesh=new THREE.Mesh(new THREE.SphereGeometry(300,48,24),m);mesh.name='cosmic-sky';mesh.renderOrder=-30;mesh.frustumCulled=false;scene.add(mesh);
 }
 return {
  /** show: true while the camera is out in orbit space. */
  update(show:boolean,cam:{x:number;y:number;z:number},t:number){
   const tier=String(opts.tier?opts.tier():'MED');if(tier!==built)build(tier);if(!mesh)return;mesh.visible=show;if(!show)return;mesh.position.set(cam.x,cam.y,cam.z);U.uT.value=t;},
  state(){return {on:!!mesh&&mesh.visible,tier:built,label:COSMIC_SKY_LABEL};},
  dispose(){if(mesh){scene.remove(mesh);mesh.geometry.dispose();mesh.material.dispose();}},
 };
}
