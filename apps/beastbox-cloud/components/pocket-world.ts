/**
 * Pocket WORLD (Oct 15): the cage opens into a small planet-pocket around the habitat.
 *  - rolling terrain that falls away from the habitat to a shoreline
 *  - an ocean with Gerstner waves, shore foam, rain rings, sky reflection
 *  - a syrupy cosmic sky: domain-warped swirling nebulae, two parallax star layers, a black hole with an
 *    accretion disk + photon ring and gravitational lensing of the sky behind it
 *  - sun + moon on the day/night cycle with matching key light and fog colour
 * All driven by the shared CST state (night/rain/chaos/coherence) and seed-deterministic; mobile tiers via `low`.
 */
import {oneSunAt} from '@/lib/universe/one-sun.mjs';
import {seededRng} from '../lib/physics/cst-integrator.mjs';
type Three=typeof import('three');
const NOISE=`float h31(vec3 p){p=fract(p*.3183099+.1);p*=17.0;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}
float n3(vec3 x){vec3 i=floor(x),f=fract(x);f=f*f*(3.0-2.0*f);return mix(mix(mix(h31(i),h31(i+vec3(1,0,0)),f.x),mix(h31(i+vec3(0,1,0)),h31(i+vec3(1,1,0)),f.x),f.y),mix(mix(h31(i+vec3(0,0,1)),h31(i+vec3(1,0,1)),f.x),mix(h31(i+vec3(0,1,1)),h31(i+vec3(1,1,1)),f.x),f.y),f.z);}
float fbm(vec3 p){float a=.5,s=0.0;for(int i=0;i<5;i++){s+=a*n3(p);p=p*2.03+vec3(1.7,9.2,3.1);a*=.5;}return s;}
`;
export function addPocketWorld(THREE:Three,scene:import('three').Scene,{seed='pocket',low=false}:{seed?:string;low?:boolean}={}){
 const R=seededRng('world:'+seed);const group=new THREE.Group();group.name='pocket-world';scene.add(group);const keep:any[]=[];const k=<T,>(x:T)=>{keep.push(x);return x;};
 const U={uT:{value:0},uNight:{value:.6},uRain:{value:0},uChaos:{value:.2},uCoh:{value:.5},uSun:{value:new THREE.Vector3(0,1,0)},uMoon:{value:new THREE.Vector3(0,-1,0)},
  uBH:{value:new THREE.Vector3(-.45,.2,-.87).normalize()},uSeed:{value:new THREE.Vector3(R()*40,R()*40,R()*40)},uCam:{value:new THREE.Vector3()}};
 const SEA=-.55;
 // ---- terrain: a ring that rolls away from the habitat and dips under the sea
 const tg=k(new THREE.RingGeometry(4.0,13,low?72:160,low?24:56));
 const terr=new THREE.Mesh(tg,k(new THREE.ShaderMaterial({uniforms:{...U,fogColor:{value:new THREE.Color()},fogDensity:{value:.03}},fog:true,
  vertexShader:`${NOISE}uniform vec3 uSeed;varying vec3 vW;varying float vH;
   #include <fog_pars_vertex>
   void main(){vec3 p=position;float r=length(p.xy);float hills=fbm(vec3(p.xy*.28,0.0)+uSeed);float ridge=1.0-abs(n3(vec3(p.xy*.18,3.0)+uSeed)*2.0-1.0);float fall=smoothstep(6.5,10.5,r);
    float h=mix(-.06+(hills*1.9+ridge*ridge*1.6-.9)*smoothstep(4.1,6.0,r),${SEA.toFixed(2)}-1.4,fall);vH=h;vec4 w=modelMatrix*vec4(p.x,p.y,h,1.0);vW=w.xyz;
    vec4 mvPosition=viewMatrix*w;gl_Position=projectionMatrix*mvPosition;
    #include <fog_vertex>
   }`,
  fragmentShader:`${NOISE}uniform float uNight,uRain,uT;uniform vec3 uSun;varying vec3 vW;varying float vH;
   #include <fog_pars_fragment>
   void main(){vec3 n=normalize(cross(dFdx(vW),dFdy(vW)));if(n.y<0.0)n=-n;float sand=smoothstep(${(SEA+.35).toFixed(2)},${(SEA+.05).toFixed(2)},vH);
    vec3 grass=mix(vec3(.12,.34,.38),vec3(.32,.16,.58),fbm(vW*.5));grass=mix(grass,vec3(.42,.3,.7),smoothstep(.6,1.4,vH)*.5);vec3 c=mix(grass,vec3(.4,.32,.48),sand);c=mix(c,c*.55,uRain*.5);   // wet when raining
    float sunL=max(0.0,dot(n,normalize(uSun)))*(1.0-uNight);float moonL=max(0.0,n.y)*uNight*.35;
    float sky=.35+.25*n.y;c*=sky*.8+sunL*.9+moonL*1.0;float rim=pow(1.0-max(0.0,dot(n,normalize(cameraPosition-vW))),3.0);c+=mix(vec3(.5,.3,1.0),vec3(.2,.8,1.0),uNight)*rim*.05;gl_FragColor=vec4(c,1.0);
    #include <fog_fragment>
   }`})));
 terr.rotation.x=-Math.PI/2;group.add(terr);
 // ---- ocean: Gerstner waves (CST chaos = sea state), foam at the shore and on crests, rain rings
 const og=k(new THREE.PlaneGeometry(80,80,low?96:220,low?96:220));
 const oceanMat=k(new THREE.ShaderMaterial({transparent:false,uniforms:{...U,fogColor:{value:new THREE.Color()},fogDensity:{value:.03}},fog:true,
  vertexShader:`uniform float uT,uChaos;varying vec3 vW;varying vec3 vN;varying float vCrest;
   #include <fog_pars_vertex>
   vec3 gw(vec2 d,float A,float L,float Q,vec2 p,inout vec3 T,inout vec3 B){float kk=6.2831/L,c=sqrt(9.8/kk),f=kk*(dot(d,p)-c*uT);
    T+=vec3(-d.x*d.x*Q*sin(f),d.x*Q*cos(f),-d.x*d.y*Q*sin(f));B+=vec3(-d.x*d.y*Q*sin(f),d.y*Q*cos(f),-d.y*d.y*Q*sin(f));
    return vec3(d.x*A*cos(f),A*sin(f),d.y*A*cos(f));}
   void main(){vec2 p=(modelMatrix*vec4(position,1.0)).xz;float sea=.35+uChaos*1.3;vec3 T=vec3(1,0,0),B=vec3(0,0,1),o=vec3(0);
    o+=gw(normalize(vec2(1,.3)),.06*sea,6.0,.35,p,T,B);o+=gw(normalize(vec2(-.4,1)),.04*sea,3.3,.3,p,T,B);
    ${low?'':'o+=gw(normalize(vec2(.7,-.6)),.025*sea,1.7,.25,p,T,B);o+=gw(normalize(vec2(-.9,-.2)),.012*sea,.9,.2,p,T,B);'}
    float shore=smoothstep(6.0,9.0,length(p));o*=shore;vCrest=o.y/(.12*sea+.001);
    vec3 w=vec3(p.x,${SEA.toFixed(2)},p.y)+o;vW=w;vN=normalize(cross(B,T));vec4 mvPosition=viewMatrix*vec4(w,1.0);gl_Position=projectionMatrix*mvPosition;
    #include <fog_vertex>
   }`,
  fragmentShader:`${NOISE}uniform float uT,uNight,uRain;uniform vec3 uSun,uMoon,cameraPos;varying vec3 vW;varying vec3 vN;varying float vCrest;
   #include <fog_pars_fragment>
   void main(){vec3 n=normalize(vN);
    // rain rings: per-cell expanding ripples perturb the normal
    if(uRain>.02){vec2 g=vW.xz*2.2;vec2 id=floor(g);vec2 f=fract(g)-.5;float ph=fract(uT*.9+h31(vec3(id,1.0)));float rr=length(f-(vec2(h31(vec3(id,2.0)),h31(vec3(id,3.0)))-.5)*.5);
     float ring=sin((rr-ph*.45)*60.0)*smoothstep(.06,.0,abs(rr-ph*.45))*(1.0-ph)*uRain;n=normalize(n+vec3(f.x,0.0,f.y)*ring*2.0);}
    vec3 v=normalize(cameraPosition-vW);float fres=.02+.98*pow(1.0-max(0.0,dot(n,v)),5.0);
    vec3 deep=mix(vec3(.02,.12,.22),vec3(.01,.02,.08),uNight),shal=mix(vec3(.05,.45,.55),vec3(.06,.1,.25),uNight);
    float d=length(vW.xz);vec3 c=mix(shal,deep,smoothstep(7.0,14.0,d));
    vec3 sky=mix(vec3(.35,.4,.85),vec3(.12,.06,.3),uNight);c=mix(c,sky,fres);
    vec3 L=normalize(uNight>.5?uMoon:uSun);vec3 hh=normalize(L+v);c+=mix(vec3(1.0,.85,.6),vec3(.7,.8,1.0),uNight)*pow(max(0.0,dot(n,hh)),180.0)*(uNight>.5?1.2:3.0);
    float foam=smoothstep(.55,1.0,vCrest)*.6+smoothstep(6.4,7.3,d)*smoothstep(9.0,7.8,d)*(.6+.4*sin(d*9.0-uT*2.0))*.7;foam*=.6+.4*n3(vec3(vW.xz*3.0,uT*.3));c=mix(c,vec3(.85,.9,1.0)*(1.0-uNight*.6),clamp(foam,0.0,1.0));
    gl_FragColor=vec4(c,1.0);
    #include <fog_fragment>
   }`}));
 const ocean=new THREE.Mesh(og,oceanMat);ocean.rotation.x=-Math.PI/2;ocean.frustumCulled=false;group.add(ocean);
 // ---- cosmic sky: swirl nebula + parallax stars + black hole (disk, photon ring, lensing) + sun/moon discs
 const skyMat=k(new THREE.ShaderMaterial({side:THREE.BackSide,depthWrite:false,fog:false,uniforms:U,
  vertexShader:`varying vec3 vD;void main(){vD=normalize(position);vec4 p=projectionMatrix*viewMatrix*vec4(position+cameraPosition,1.0);gl_Position=p.xyww;}`,
  fragmentShader:`${NOISE}uniform float uT,uNight,uChaos,uCoh;uniform vec3 uSun,uMoon,uBH,uSeed,uCam;varying vec3 vD;
   vec3 stars(vec3 d,float s,float th){vec3 q=d*s;vec3 id=floor(q);float h=h31(id+uSeed);float st=step(th,h)*smoothstep(.45,.0,length(fract(q)-.5))*(.6+.4*sin(uT*2.0+h*50.0));return mix(vec3(.7,.8,1.0),vec3(1.0,.8,.9),h)*st;}
   void main(){vec3 d=normalize(vD);
    // gravitational lensing: bend view rays around the black hole
    float a=acos(clamp(dot(d,uBH),-1.0,1.0));float rs=.026;vec3 tang=normalize(d-uBH*dot(d,uBH)+1e-5);
    float bend=rs*rs*2.2/max(a,rs*.9);vec3 dl=normalize(d+tang*bend*1.0);
    // syrupy swirl nebula: domain warping that slowly rotates; chaos stirs it, coherence calms it
    vec3 p=dl*2.2+uSeed*.05;float tw=uT*.015*(1.0+uChaos*2.0);
    vec3 w=vec3(fbm(p+vec3(tw,0,0)),fbm(p+vec3(5.2,1.3,tw)),fbm(p+vec3(2.1,tw,7.7)));float nb=fbm(p+w*(1.6+uChaos)+vec3(0,0,tw));
    float nb2=fbm(p*1.7-w*1.2+3.0);
    vec3 neb=mix(vec3(.25,.05,.45),vec3(.05,.45,.75),nb2);neb=mix(neb,vec3(.95,.35,.7),smoothstep(.62,.85,nb)*.6);neb*=smoothstep(.35,.85,nb)*1.3;
    vec3 c=mix(vec3(.02,.01,.06),vec3(.10,.12,.35),smoothstep(-.2,.6,d.y)*(1.0-uNight))+neb*(.55+.45*uNight);
    vec3 par=uCam*.002;c+=(stars(dl+par,180.0,.985)+stars(dl+par*3.0,90.0,.993)*1.4)*(.25+.75*uNight);
    // black hole: shadow, photon ring, tilted accretion disk with doppler beaming
    float shadow=smoothstep(rs*1.0,rs*.85,a);vec3 up=normalize(cross(uBH,vec3(.2,1.0,.1)));vec3 rt=normalize(cross(up,uBH));
    vec2 q=vec2(dot(d-uBH,rt),dot(d-uBH,up));vec2 qd=vec2(q.x,q.y/.28);float rd=length(qd);
    float disk=smoothstep(rs*1.3,rs*1.7,rd)*smoothstep(rs*5.0,rs*2.0,rd);float ang=atan(qd.y,qd.x);
    float swirl=.6+.4*sin(ang*6.0-uT*1.5+rd*120.0);float dop=.55+.45*cos(ang);
    vec3 dc=mix(vec3(1.0,.45,.15),vec3(1.0,.9,.7),dop)*disk*swirl*(1.2+dop*1.6);
    if(q.y>0.0&&rd<rs*1.4)dc*=.0;  // the far side of the disk dips behind the shadow
    float ring=smoothstep(.006,.0,abs(a-rs*1.08))*1.6;c=c*(1.0-shadow)+dc+vec3(1.0,.85,.65)*ring;
    // sun + moon
    float sd=dot(d,normalize(uSun));c+=vec3(1.0,.8,.5)*(smoothstep(.9994,.9997,sd)*6.0+pow(max(0.0,sd),60.0)*.6)*(1.0-uNight*.9);
    float md=dot(d,normalize(uMoon));float moon=smoothstep(.9993,.9996,md);float crater=fbm(d*400.0);c=mix(c,vec3(.85,.88,1.0)*(.75+.25*crater),moon*uNight)+vec3(.5,.6,1.0)*pow(max(0.0,md),200.0)*.4*uNight;
    gl_FragColor=vec4(c,1.0);}`}));
 const sky=new THREE.Mesh(k(new THREE.SphereGeometry(500,low?32:64,low?16:32)),skyMat);sky.renderOrder=-10;sky.frustumCulled=false;group.add(sky);
 // ---- lights: sun / moon keys that follow the cycle
 const sunL=new THREE.DirectionalLight(0xffe2b8,0);const moonL=new THREE.DirectionalLight(0x9fb8ff,0);group.add(sunL,moonL);
 let dayPhase=R()*Math.PI*2;
 function update(dt:number,env:{night:number;rain:number},ch:{chaos:number;coherence:number},cam?:import('three').Vector3){
  U.uT.value+=dt;U.uNight.value=env.night;U.uRain.value=env.rain;U.uChaos.value=ch.chaos;U.uCoh.value=ch.coherence;if(cam)U.uCam.value.copy(cam);
  // the cycle angle follows the CST-driven night value (night=1 → sun below horizon, moon up)
  const ang=Math.acos(Math.max(-1,Math.min(1,1-2*env.night)));dayPhase+=dt*.01;
  {const os=oneSunAt(Date.now()/1000);U.uSun.value.set(os.dir[0],os.dir[1],os.dir[2]).normalize();void ang;} /* ONE SUN: same day clock as the living world (SEEDED) */U.uMoon.value.copy(U.uSun.value).multiplyScalar(-1).add(new THREE.Vector3(.2,0,.1)).normalize();
  sunL.position.copy(U.uSun.value).multiplyScalar(10);moonL.position.copy(U.uMoon.value).multiplyScalar(10);
  sunL.intensity=Math.max(0,U.uSun.value.y)*2.2*(1-env.rain*.6);moonL.intensity=Math.max(0,U.uMoon.value.y)*.7*env.night;
  const fog=scene.fog as any;if(fog){fog.color.setRGB(.05+(1-env.night)*.18,.04+(1-env.night)*.16,.12+(1-env.night)*.3);fog.color.lerp(new THREE.Color(.3,.32,.4),env.rain*.4);
   for(const m of [terr.material,oceanMat] as any[]){m.uniforms.fogColor.value.copy(fog.color);m.uniforms.fogDensity.value=fog.density??.03;}}
 }
 return {group,update,uniforms:U,dispose(){scene.remove(group);keep.forEach(x=>x.dispose?.());}};
}
