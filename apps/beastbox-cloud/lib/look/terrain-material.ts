// Height and slope biome blend for the Genesis terrain. Tone mapping stays on so ACES runs before dither.
import {HAZE_GLSL} from './haze.ts';

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

const FRAG=`uniform vec3 uSun,uHaze,uZen;uniform float uDay,uWater,uHazePhase,uMotion;uniform vec3 uPath;
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
 c=mix(c,snow,smoothstep(3.4,4.8,above)*(1.0-smoothstep(28.0,36.0,slope)));
 if(uPath.z>.5){vec2 fw=vec2(cos(uPath.x),sin(uPath.x)),sd=vec2(-fw.y,fw.x);float f=dot(vP.xz,fw),x=dot(vP.xz,sd);float px=1.6*sin(f*.19+uPath.y*.01)*smoothstep(0.0,4.0,f);float w=.32+.018*f+.08*vn(vP.xz*1.7);float pm=(1.0-smoothstep(w*.55,w,abs(x-px)))*smoothstep(1.2,2.6,f)*(1.0-smoothstep(40.0,60.0,f));vec3 dirt=mix(vec3(.50,.40,.27),vec3(.62,.52,.36),vn(vP.xz*3.1));c=mix(c,dirt,pm*.92);c=mix(c,c*vec3(.92,.9,.78),(1.0-smoothstep(w,w*2.2,abs(x-px)))*smoothstep(1.2,2.6,f)*.6);} /* first person: a winding dirt path down the valley floor toward the bay, with worn edges (same curve as the terrain valley, SEEDED) */
 vec3 bn=abs(normalize(vN));float bs=bn.x+bn.y+bn.z;bn/=bs;
 float rockN=vn(vP.yz*2.4)*bn.x+vn(vP.xz*2.4)*bn.y+vn(vP.xy*2.4)*bn.z;
 c=mix(c,c*mix(.72,1.18,rockN),smoothstep(28.0,42.0,slope));
 float ndl=max(0.0,dot(normalize(vN),normalize(uSun)));
 float dayK=clamp(uDay,0.0,1.0);
 c*=(mix(0.46,0.28,dayK)+mix(0.35,0.72,dayK)*ndl)*vAo;
 float dist=distance(cameraPosition,vW);
 float h=max(vW.y,0.0);
 float drift=mix(1.0,.92+.08*sin(uHazePhase),uMotion);
 float near=hazeAmt(dist,h,.045,.8);
 float mid=hazeAmt(dist,h,.012,.35);
 float far=hazeAmt(dist,h,.004,.12);
 vec3 lowBand=mix(uHaze*.62,uHaze,.35);
 vec3 midBand=mix(uHaze,uZen,.45);
 vec3 band=mix(lowBand,midBand,clamp(mid,0.0,1.0));
 band=mix(band,uZen,clamp(far*.85+near*.08,0.0,1.0));
 c=mix(c,band,clamp((near*.55+mid*.3+far*.15)*drift,0.0,.92));
 gl_FragColor=vec4(c,1.0);
}`;

export function createTerrainMaterial(THREE:typeof import('three'),waterLevel:number,path?:{bearing:number;seed:number}|null){
 const uniforms={
  uSun:{value:new THREE.Vector3(0,1,0)},
  uHaze:{value:new THREE.Color(.62,.74,.84)},
  uZen:{value:new THREE.Color(.16,.36,.64)},
  uDay:{value:1},
  uWater:{value:waterLevel},
  uHazePhase:{value:0},
  uMotion:{value:1},
  uPath:{value:new THREE.Vector3(path?.bearing??0,path?.seed??0,path?1:0)},
 };
 const mat=new THREE.ShaderMaterial({uniforms,vertexShader:VERT,fragmentShader:FRAG,fog:false});
 return {material:mat,uniforms};
}
