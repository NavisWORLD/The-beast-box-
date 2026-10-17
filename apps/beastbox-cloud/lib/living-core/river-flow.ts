// CI rerun marker: river-flow layer for the Cage universe.
/** "Every atom flows like a river": a GPU-only stream layer for the Cage universe.
 *  Capped particle count (phones / software GL 900, else 2400). All motion runs in the vertex shader (no per-frame CPU loop).
 *  Streams follow sine-wave river paths bent by a curl-like flow field whose phases come from the 12 CST channels.
 *  ~12% of particles are faint glyphs (code / CST symbols). Palette = the existing cage purples + cyan. */
import {createCSTState,stepCSTState} from '../physics/cst-integrator.mjs';
type T=typeof import('three');
const GLYPHS='01φψΣ∞<>{}λ∂Ω12D';
export function addRiverFlow(THREE:T,parent:import('three').Object3D,{low,seed='cage',floorY=-.05}:{low:boolean;seed?:string;floorY?:number}){
 const N=low?900:2400,STREAMS=6;
 const f=(x:number)=>{const v=Math.sin(x)*43758.5453;return v-Math.floor(v);};
 const a=new Float32Array(N*4),pos=new Float32Array(N*3);
 for(let i=0;i<N;i++){a[i*4]=f(i*1.17+seed.length);a[i*4+1]=f(i*2.31+.7);a[i*4+2]=Math.floor(f(i*3.7+1.3)*STREAMS);a[i*4+3]=f(i*5.3+2.1)<.12?Math.floor(f(i*7.1)*GLYPHS.length)+1:0;}
 const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(pos,3));g.setAttribute('aSeed',new THREE.BufferAttribute(a,4));
 g.boundingSphere=new THREE.Sphere(new THREE.Vector3(),12);
 const cv=document.createElement('canvas');cv.width=512;cv.height=32;const cx=cv.getContext('2d')!;cx.fillStyle='#fff';cx.font='26px monospace';cx.textAlign='center';cx.textBaseline='middle';
 [...GLYPHS].forEach((ch,i)=>cx.fillText(ch,i*32+16,17));const tex=new THREE.CanvasTexture(cv);
 const cst=new Float32Array(12);const U={uTime:{value:0},uCst:{value:cst},uAtlas:{value:tex},uFloor:{value:floorY},uExcite:{value:0}};
 const vs=`attribute vec4 aSeed;uniform float uTime;uniform float uCst[12];uniform float uFloor;uniform float uExcite;varying float vG;varying float vA;varying float vS;
 float cs(int i){float v=0.;for(int k=0;k<12;k++){if(k==i)v=uCst[k];}return v;}
 void main(){float s=aSeed.z;int si=int(s+.5);float c=cs(si),c2=cs(si+6);
  float sp=(.035+.02*s)*(mod(s,2.)<.5?1.:-1.)*(1.+uExcite*.8);
  float th=aSeed.x*6.2832+uTime*sp;
  float R=1.2+s*1.05+sin(th*3.+uTime*.25+c*2.)*.35+(aSeed.y-.5)*.45;
  vec3 p=vec3(cos(th)*R,uFloor+.18+s*.42+sin(th*2.+uTime*.4+c2*2.)*.28+(aSeed.y-.5)*.25,sin(th)*R*.92);
  p+=vec3(sin(p.z*1.6+uTime*.6+c)*cos(p.y*1.1),sin(p.x*1.2-uTime*.45+c2)*.5,-cos(p.x*1.7+uTime*.5)*sin(p.y*1.3+c))*.16;
  vec4 mv=modelViewMatrix*vec4(p,1.);vG=aSeed.w;vS=s/5.;
  vA=(.35+.4*aSeed.y)*smoothstep(11.,6.,length(p.xz));
  gl_PointSize=(vG>0.?9.:2.4+aSeed.y*2.2)*clamp(6./-mv.z,.5,2.);gl_Position=projectionMatrix*mv;}`;
 const fs=`uniform sampler2D uAtlas;varying float vG;varying float vA;varying float vS;
 void main(){vec3 col=mix(vec3(.62,.48,1.),vec3(.45,.85,1.),vS);float a;
  if(vG>0.){vec2 uv=vec2((vG-1.+gl_PointCoord.x)/16.,1.-gl_PointCoord.y);a=texture2D(uAtlas,uv).a*.38;}
  else{a=smoothstep(.5,0.,length(gl_PointCoord-.5));}
  gl_FragColor=vec4(col,a*vA);}`;
 const m=new THREE.ShaderMaterial({uniforms:U as any,vertexShader:vs,fragmentShader:fs,transparent:true,depthWrite:false,blending:THREE.AdditiveBlending});
 const pts=new THREE.Points(g,m);pts.name='lc-river';pts.frustumCulled=false;parent.add(pts);
 const S:any=createCSTState(seed+':river');
 return {points:pts,count:N,
  kick(x=.5){U.uExcite.value=Math.min(1.5,U.uExcite.value+x);},
  step(dt:number){if(!(dt>0))return;U.uTime.value+=dt;(stepCSTState as any)(S,Math.min(dt,1/30),{arousal:.3});
   const v:any[]=Object.values(S.ch||{});for(let i=0;i<12;i++){const x=(Number(v[i%Math.max(1,v.length)])||0)*(1+i*.13);cst[i]+=(Math.tanh(x)-cst[i])*Math.min(1,dt*.5);}U.uExcite.value*=Math.exp(-dt*.5);},
  dispose(){parent.remove(pts);g.dispose();m.dispose();tex.dispose();}};
}

/** Stars drift in a slow river swirl (same colour/size/opacity). */
export function flowStars(m:import('three').Material,U:{uTime:{value:number}}){m.onBeforeCompile=(sh:any)=>{sh.uniforms.uTime=U.uTime;
 sh.vertexShader='uniform float uTime;\n'+sh.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\n{float r=length(transformed.xz);float an=uTime*.012*(1.+.5*sin(r*.35))+sin(uTime*.05+r*.2)*.02;float c=cos(an),s=sin(an);transformed.xz=mat2(c,-s,s,c)*transformed.xz;transformed.y+=sin(uTime*.18+transformed.x*.3+transformed.z*.2)*.06;}');};
 m.customProgramCacheKey=()=>'lc-flow-stars';m.needsUpdate=true;}
/** Grid glow: a soft brightness current travels across the existing lines (opacity/palette untouched otherwise). */
export function flowGrid(m:import('three').Material,U:{uTime:{value:number}}){m.onBeforeCompile=(sh:any)=>{sh.uniforms.uTime=U.uTime;
 sh.vertexShader='varying vec3 vFlowP;\n'+sh.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nvFlowP=position;');
 sh.fragmentShader='uniform float uTime;varying vec3 vFlowP;\n'+sh.fragmentShader.replace('#include <opaque_fragment>','outgoingLight*=.8+.9*smoothstep(.55,1.,.5+.5*sin(vFlowP.x*.8+vFlowP.z*.55+sin(vFlowP.z*.4+uTime*.2)*1.2-uTime*.5));\n#include <opaque_fragment>');};
 m.customProgramCacheKey=()=>'lc-flow-grid';m.needsUpdate=true;}
