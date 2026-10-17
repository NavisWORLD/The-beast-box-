/** Surface engineering for every living-core creature (Cory's spec):
 *  - chaos: a per-creature Lorenz attractor, integrated over time and nudged by the 12D CST channels, feeds the
 *    surface displacement and the fur/fuzz texture offsets, so the texture is decoupled from the mesh and never repeats;
 *  - fluid: a curl-noise flow field drives fur + fuzz; its speed and amplitude follow a low-frequency heartbeat,
 *    plus the mic level (only when the user turned the sensor on), chat lines and taps;
 *  - jiggle: a damped spring for secondary motion and a ~0.3 s high-frequency contact shimmer when a hop lands.
 *  All GPU-side: a handful of uniforms per creature, no per-vertex CPU work (iPhone-safe). */
import {createCSTState,stepCSTState} from '../physics/cst-integrator.mjs';
type T=typeof import('three');

// One shared, page-wide excitation bus (chat, taps, mic). Mic events only exist when the user enabled the sensor.
const bus={excite:0,mic:0,bound:false};
function bindBus(){if(bus.bound||typeof window==='undefined')return;bus.bound=true;
 window.addEventListener('beastbox:beast-chat',()=>{bus.excite=Math.min(1.5,bus.excite+.6);});
 window.addEventListener('pointerdown',()=>{bus.excite=Math.min(1.5,bus.excite+.35);},{passive:true});
 window.addEventListener('beastbox:local-sensor-level',(e:any)=>{const l=Number(e?.detail?.level)||0;bus.mic=Math.max(bus.mic,Math.min(1,l));});}

export {LORENZ,lorenzStep,heartbeat,springStep} from './surface-math.mjs';
import {lorenzStep,heartbeat,springStep} from './surface-math.mjs';
import {getBeastAudio} from '../companion/beast-audio-engine.mjs';
const GLSL_FLOW=`uniform float uSLt;uniform vec3 uChaos;uniform float uFlowA;uniform float uJig;uniform float uShim;
vec3 slCurl(vec3 p){p+=uChaos*1.7;float t=uSLt;
 return vec3(sin(p.y*3.1+t)*cos(p.z*2.3-t*.7),sin(p.z*2.7-t*.8)*cos(p.x*3.3+t*.5),sin(p.x*2.9+t*.6)*cos(p.y*2.1-t*.9));}`;
export function attachSurfaceLife(THREE:T,LC:any,seed:string,low:boolean){
 bindBus();
 const U={uSLt:{value:0},uChaos:{value:new THREE.Vector3()},uFlowA:{value:0},uJig:{value:0},uShim:{value:0}};
 const disp=low?.014:.018;// reads at normal Cage zoom, still soft
 // body + lit parts: chaotic curl displacement, spring jiggle, contact shimmer; fur normals offset by the decoupled field
 const done:any[]=[];LC.group.traverse((o:any)=>{const m=o.material;if(!o.isMesh||!m||m.isShaderMaterial||done.includes(m))return;if(!(m.isMeshStandardMaterial||m.isMeshPhysicalMaterial))return;
  const prev=m.onBeforeCompile;m.onBeforeCompile=(sh:any,r:any)=>{prev?.call(m,sh,r);Object.assign(sh.uniforms,U);
   if(!sh.vertexShader.includes('#include <begin_vertex>'))return;
   sh.vertexShader=GLSL_FLOW+'\nvarying vec3 vSLp;\n'+sh.vertexShader.replace('#include <begin_vertex>',`#include <begin_vertex>
 vSLp=position;{vec3 cf=slCurl(position*4.);transformed+=normal*(dot(cf,vec3(.34))*${disp.toFixed(4)}*uFlowA+uJig*.02*max(0.,position.y+.2)+sin(position.y*60.+uSLt*230.)*.0035*uShim);transformed.xz+=cf.xz*${(disp*.5).toFixed(4)}*uFlowA;}`);
   if(sh.fragmentShader.includes('#include <normal_fragment_maps>'))sh.fragmentShader=GLSL_FLOW+'\nvarying vec3 vSLp;\n'+sh.fragmentShader.replace('#include <normal_fragment_maps>','#include <normal_fragment_maps>\n{vec3 cf=slCurl(vSLp*26.);normal=normalize(normal+cf*.32*(.5+uFlowA));}');};
  const key=m.customProgramCacheKey?.bind(m);m.customProgramCacheKey=()=>(key?key():m.uuid)+':lcsurf';m.needsUpdate=true;done.push(m);});
 // fuzz particles (birth/morph points): ride the same flow
 const pm=LC.pmat;if(pm?.isShaderMaterial&&!pm.userData.lcsurf){pm.userData.lcsurf=1;Object.assign(pm.uniforms,U);
  pm.vertexShader=GLSL_FLOW+'\n'+pm.vertexShader.replace('vec4 mv=modelViewMatrix*vec4(position,1.);','vec3 slP=position+slCurl(position*3.)*.03*(.4+uFlowA);vec4 mv=modelViewMatrix*vec4(slP,1.);');pm.needsUpdate=true;}
 // per-creature chaos state
 let h=0;for(const c of seed)h=(h*31+c.charCodeAt(0))>>>0;
 const L=[1+(h%97)/97,1+((h>>7)%89)/89,20+((h>>13)%83)/20];const S:any=createCSTState(seed+':surface');
 const spring={x:0,v:0};let t=(h%1000)/100,shim=0,landIn=-1,acc=0;
 const ohop=LC.hop;if(typeof ohop==='function'&&!LC.__surfHop){LC.__surfHop=1;LC.hop=(...a:any[])=>{landIn=.5;spring.v-=1.2;return ohop.apply(LC,a);};}
 const api={U,
  impulse(a=1){spring.v-=1.4*a;shim=.3;},
  step(dt:number){if(!(dt>0))return;dt=Math.min(dt,.05);t+=dt;
   (stepCSTState as any)(S,dt,{arousal:.3+bus.excite*.3});const ch:any=S.ch||{};const nudge=Math.tanh(Number(ch.chaos??ch.arousal??0)||0);
   acc+=dt;while(acc>1/240){lorenzStep(L,1/240,nudge);acc-=1/240;}// attractor stays bounded with small steps
   U.uChaos.value.set(L[0]/12,L[1]/16,(L[2]-25)/14);
   const beat=heartbeat(t,1+.35*Math.min(1,bus.excite));let music=0;try{music=(getBeastAudio() as any).level?.()||0;}catch{}// site music, only while sound is on (engine returns 0 when muted)
   const lvl=.3+beat*.55+bus.mic*.8+music*.9+bus.excite*.6;
   U.uSLt.value+=dt*(.35+lvl*1.1);U.uFlowA.value+=(Math.min(1.8,lvl)-U.uFlowA.value)*Math.min(1,dt*8);
   if(landIn>0){landIn-=dt;if(landIn<=0){shim=.3;spring.v-=1.6;}}
   U.uJig.value=springStep(spring,dt);shim=Math.max(0,shim-dt);U.uShim.value=shim/.3;
   bus.excite*=Math.exp(-dt*.6);bus.mic*=Math.exp(-dt*3);}};
 return api;
}
