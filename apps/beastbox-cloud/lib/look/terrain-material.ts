// Height and slope biome blend for the Genesis terrain. Tone mapping stays on so ACES runs before dither.
// A real GPU fades far hills into the sky colour. Software GL keeps the lighter stacked haze.
import {HAZE_GLSL} from './haze.ts';
import {SKY_COL_GLSL} from './sky-math.ts';

const NOISE=`float h21(vec2 p){p=fract(p*vec2(127.1,311.7));p+=dot(p,p+19.19);return fract(p.x*p.y);}
float vn(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);
 return mix(mix(h21(i),h21(i+vec2(1.0,0.0)),f.x),mix(h21(i+vec2(0.0,1.0)),h21(i+vec2(1.0,1.0)),f.x),f.y);}`;

const VERT=`attribute float ao;attribute float noise;
varying float vH,vAo,vNoise,vD;varying vec3 vN,vW,vP;
void main(){
 vH=position.y;vAo=ao;vNoise=noise;vD=length(position.xz);vP=position;vN=normalize(normal);
 vec4 w=modelMatrix*vec4(position,1.0);vW=w.xyz;
 gl_Position=projectionMatrix*viewMatrix*w;
}`;

const FRAG_LITE=`uniform vec3 uSun,uHaze,uZen;uniform float uDay,uWater,uHazePhase,uMotion;
varying float vH,vAo,vNoise,vD;varying vec3 vN,vW,vP;
${NOISE}
${HAZE_GLSL}
void main(){
 float n=vNoise;
 float bh=vH+n*.12;
 vec3 sand=vec3(.72,.62,.42),meadow=vec3(.20,.46,.16),forest=vec3(.07,.20,.08),rock=vec3(.40,.38,.34),snow=vec3(.92,.94,.96);
 float slope=degrees(acos(clamp(normalize(vN).y,0.0,1.0)));
 float shoreY=uWater*smoothstep(12.0,70.0,vD);
 float above=bh-shoreY;
 float pad=1.0-smoothstep(6.0,14.0,vD);
 vec3 c=mix(sand,meadow,max(smoothstep(-.02,.22,above),pad));
 c=mix(c,forest,smoothstep(.55,1.7,above));
 c=mix(c,rock,smoothstep(32.0,38.0,slope+n*6.0));
 c=mix(c,snow,smoothstep(6.0,8.5,above)*smoothstep(48.0,28.0,vD)*(1.0-smoothstep(28.0,36.0,slope)));
 vec3 bn=abs(normalize(vN));float bs=bn.x+bn.y+bn.z;bn/=bs;
 float rockN=vn(vP.yz*2.4)*bn.x+vn(vP.xz*2.4)*bn.y+vn(vP.xy*2.4)*bn.z;
 c=mix(c,c*mix(.72,1.18,rockN),smoothstep(28.0,42.0,slope));
 float ndl=max(0.0,dot(normalize(vN),normalize(uSun)));
 float dayK=clamp(uDay,0.0,1.0);
 c*=(mix(0.46,0.28,dayK)+mix(0.35,0.72,dayK)*ndl)*vAo;
 float dist=distance(cameraPosition,vW);
 float h=max(vW.y,0.0);
 float drift=mix(1.0,.92+.08*sin(uHazePhase),uMotion);
 float near=hazeAmt(dist,h,.0045,1.15);
 float mid=hazeAmt(dist,h,.0012,.4);
 float far=hazeAmt(dist,h,.00035,.1);
 vec3 lowBand=mix(uHaze*.62,uHaze,.35);
 vec3 midBand=mix(uHaze,uZen,.45);
 vec3 band=mix(lowBand,midBand,clamp(mid,0.0,1.0));
 band=mix(band,uZen,clamp(far*.85+near*.08,0.0,1.0));
 c=mix(c,band,clamp((near*.4+mid*.35+far*.25)*drift,0.0,.55));
 gl_FragColor=vec4(c,1.0);
}`;

const FRAG=`uniform vec3 uSun,uHaze,uZen,uBody;uniform float uDay,uWater,uHazePhase,uMotion;
varying float vH,vAo,vNoise,vD;varying vec3 vN,vW,vP;
${NOISE}
${HAZE_GLSL}
${SKY_COL_GLSL}
void main(){
 float n=vNoise;
 float bh=vH+n*.12;
 vec3 sand=vec3(.72,.62,.42),meadow=vec3(.20,.46,.16),forest=vec3(.07,.20,.08),rock=vec3(.40,.38,.34),snow=vec3(.92,.94,.96);
 float slope=degrees(acos(clamp(normalize(vN).y,0.0,1.0)));
 float shoreY=uWater*smoothstep(12.0,70.0,vD);
 float above=bh-shoreY;
 float pad=1.0-smoothstep(6.0,14.0,vD);
 vec3 c=mix(sand,meadow,max(smoothstep(-.02,.22,above),pad));
 c=mix(c,forest,smoothstep(.55,1.7,above));
 c=mix(c,rock,smoothstep(32.0,38.0,slope+n*6.0));
 c=mix(c,snow,smoothstep(6.0,8.5,above)*smoothstep(48.0,28.0,vD)*(1.0-smoothstep(28.0,36.0,slope)));
 vec3 bn=abs(normalize(vN));float bs=bn.x+bn.y+bn.z;bn/=bs;
 float rockN=vn(vP.yz*2.4)*bn.x+vn(vP.xz*2.4)*bn.y+vn(vP.xy*2.4)*bn.z;
 c=mix(c,c*mix(.72,1.18,rockN),smoothstep(28.0,42.0,slope));
 float ndl=max(0.0,dot(normalize(vN),normalize(uSun)));
 float dayK=clamp(uDay,0.0,1.0);
 c*=(mix(0.46,0.28,dayK)+mix(0.35,0.72,dayK)*ndl)*vAo;
 float dist=distance(cameraPosition,vW);
 vec3 view=normalize(vW-cameraPosition);
 vec3 sky=skyAir(view,uHaze,uZen,uSun,uDay,uHazePhase,uMotion);
 float fade=aerialAmt(dist,max(vW.y,0.0));
 c=mix(c,sky,clamp(fade,0.0,0.28));
 gl_FragColor=vec4(c,1.0);
}`;

export function createTerrainMaterial(THREE:typeof import('three'),waterLevel:number,opts?:{lite?:boolean}){
 const lite=!!opts?.lite;
 const uniforms:Record<string,{value:unknown}>={
  uSun:{value:new THREE.Vector3(0,1,0)},
  uHaze:{value:new THREE.Color(.62,.74,.84)},
  uZen:{value:new THREE.Color(.16,.36,.64)},
  uDay:{value:1},
  uWater:{value:waterLevel},
  uHazePhase:{value:0},
  uMotion:{value:1},
 };
 if(!lite)uniforms.uBody={value:new THREE.Color(1,.93,.78)};
 const mat=new THREE.ShaderMaterial({uniforms,vertexShader:VERT,fragmentShader:lite?FRAG_LITE:FRAG,fog:false});
 return {material:mat,uniforms:uniforms as {
  uSun:{value:{copy:(v:unknown)=>void}};
  uHaze:{value:{copy:(v:unknown)=>void;setRGB:(r:number,g:number,b:number)=>void}};
  uZen:{value:{setRGB:(r:number,g:number,b:number)=>void}};
  uBody?:{value:{setRGB:(r:number,g:number,b:number)=>void}};
  uDay:{value:number};
  uWater:{value:number};
  uHazePhase:{value:number};
  uMotion:{value:number};
 }};
}
