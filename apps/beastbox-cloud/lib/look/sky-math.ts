// Painted sky for a ground viewer. Rayleigh and Henyey-Greenstein are the Genesis Engine
// phase functions, scaled so the horizon reads as colour rather than a physical integral.
// A sine veil drifts with the presentation clock. Reduced motion holds the veil still.
// The sky is DERIVED from the one sun. No unseeded draws.

export const SKY_LABEL='Sky · DERIVED';

const PI=Math.PI;
const clamp=(v:number,a:number,b:number)=>Math.min(b,Math.max(a,v));
const mix=(a:number,b:number,t:number)=>a+(b-a)*t;

export function smoothstep(edge0:number,edge1:number,x:number){
 const t=clamp((x-edge0)/(edge1-edge0),0,1);
 return t*t*(3-2*t);
}

export function rayleighPhase(mu:number){
 return 3/(16*PI)*(1+mu*mu);
}

export function hgPhase(mu:number,g:number){
 const g2=g*g;
 const denom=Math.pow(1+g2-2*g*mu,1.5);
 return (1-g2)/(4*PI*Math.max(1e-6,denom));
}

function veil(dir:number[],drift:number,motion:number){
 if(!(motion>0))return 0;
 return Math.sin(dir[0]*1.7+dir[2]*1.3+drift)*0.5
  +Math.sin(dir[0]*3.1-dir[1]*2.2+drift*1.3)*0.25
  +Math.sin(dir[2]*4.0+dir[1]*2.6-drift*0.8)*0.125;
}

const WARM=[1,0.62,0.32];

function norm3(v:number[]){
 const l=Math.hypot(v[0],v[1],v[2])||1;
 return [v[0]/l,v[1]/l,v[2]/l];
}

/** Sun core, wide glow, and a soft corona. Added after the air colour so a low sun is not painted out. */
function addDisc(c:number[],mu:number,dayK:number,tint:number[],drift:number,motion:number){
 const disc=smoothstep(0.9976,0.99945,mu)*dayK;
 const glow=Math.pow(Math.max(mu,0),28)*0.7*dayK;
 const pulse=motion>0?0.65+0.35*Math.sin(drift*1.7):0.75;
 const corona=Math.pow(Math.max(mu,0),8)*pulse*0.35*dayK;
 return c.map((v,i)=>v+tint[i]*(disc*3.6+glow*0.55)+WARM[i]*corona*0.25);
}

/** Air only. The terrain fades toward this, so it has no sun disc to blow the hills out. */
export function skyAir(dir:number[],sun:number[],horizon:number[],zenith:number[],drift=0,day=1,motion=1){
 const d=norm3(dir),s=norm3(sun);
 const e=d[1];
 const mu=clamp(d[0]*s[0]+d[1]*s[1]+d[2]*s[2],-1,1);
 const elev=clamp(e+veil(d,drift,motion)*0.08,-1,1);
 const t=Math.pow(clamp(elev,0,1),0.45);
 const h=horizon?.length===3?horizon:[.62,.78,.9];
 const z=zenith?.length===3?zenith:[.18,.4,.7];
 let c=[0,1,2].map(i=>h[i]+(z[i]-h[i])*t);
 const toward=clamp(hgPhase(Math.max(mu,0),0.76)*0.35*Math.pow(1-Math.abs(e),0.65),0,1);
 const dayK=clamp(day,0,1);
 c=c.map((v,i)=>v+WARM[i]*toward*0.18*dayK);
 if(e<0){
  const k=smoothstep(0,-0.25,e);
  c=c.map((v,i)=>mix(h[i]*0.55,h[i]*0.22,k));
 }
 return c;
}

/** Stylised sky colour along a view. The disc sits on the sun direction. The veil does not move the disc. */
export function skyColour(dir:number[],sun:number[],horizon:number[],zenith:number[],drift=0,day=1,motion=1,body:number[]=[1,.93,.78]){
 const d=norm3(dir),s=norm3(sun);
 const mu=clamp(d[0]*s[0]+d[1]*s[1]+d[2]*s[2],-1,1);
 const tint=body?.length===3?body:[1,.93,.78];
 return addDisc(skyAir(dir,sun,horizon,zenith,drift,day,motion),mu,clamp(day,0,1),tint,drift,motion);
}

/**
 * Orbit sky. A dark blue gradient and a sun disc, never the ground meadow colour.
 * Directions are still Y-up in the dome. The nadir stays space, not a flat fill.
 */
export function spaceSkyColour(dir:number[],sun:number[],drift=0,day=1,motion=1,body:number[]=[1,.95,.82]){
 const d=norm3(dir),s=norm3(sun);
 const e=d[1];
 const mu=clamp(d[0]*s[0]+d[1]*s[1]+d[2]*s[2],-1,1);
 const nadir=[0.045,0.055,0.18];
 const limb=[0.14,0.18,0.46];
 const zen=[0.06,0.08,0.24];
 const g=smoothstep(-0.55,0.65,e);
 const lift=smoothstep(-0.15,0.85,e);
 let c=nadir.map((v,i)=>mix(v,mix(limb[i],zen[i],lift),g));
 const warm=Math.pow(Math.max(mu,0),4)*0.06*clamp(day,0,1);
 c=c.map((v,i)=>v+[0.22,0.1,0.04][i]*warm);
 const tint=body?.length===3?body:[1,.95,.82];
 return addDisc(c,mu,clamp(day,0,1),tint,drift,motion);
}

/** Same painting as skyColour, for the dome and the terrain. Keep the constants aligned with the function above. */
export const SKY_COL_GLSL=`float skyVeil(vec3 d,float drift,float motion){
 float v=sin(d.x*1.7+d.z*1.3+drift)*0.5+sin(d.x*3.1-d.y*2.2+drift*1.3)*0.25+sin(d.z*4.0+d.y*2.6-drift*0.8)*0.125;
 return motion>0.0?v:0.0;
}
float rayleighPhase(float mu){return 3.0/(16.0*3.14159265)*(1.0+mu*mu);}
float hgPhase(float mu,float g){
 float g2=g*g;float denom=pow(1.0+g2-2.0*g*mu,1.5);
 return (1.0-g2)/(4.0*3.14159265*max(denom,1.0e-6));
}
vec3 addDisc(vec3 c,float mu,float dayK,vec3 body,float drift,float motion){
 float disc=smoothstep(0.9976,0.99945,mu)*dayK;
 float glow=pow(max(mu,0.0),28.0)*0.7*dayK;
 float pulse=motion>0.0?0.65+0.35*sin(drift*1.7):0.75;
 float corona=pow(max(mu,0.0),8.0)*pulse*0.35*dayK;
 vec3 warm=vec3(1.0,0.62,0.32);
 return c+body*(disc*3.6+glow*0.55)+warm*corona*0.25;
}
vec3 skyAir(vec3 dir,vec3 hor,vec3 zen,vec3 sun,float day,float drift,float motion){
 vec3 d=normalize(dir);vec3 s=normalize(sun);
 float e=d.y;float mu=clamp(dot(d,s),-1.0,1.0);
 float elev=clamp(e+skyVeil(d,drift,motion)*0.08,-1.0,1.0);
 float t=pow(clamp(elev,0.0,1.0),0.45);
 vec3 c=mix(hor,zen,t);
 float pm=hgPhase(max(mu,0.0),0.76);
 float toward=clamp(pm*0.35*pow(1.0-abs(e),0.65),0.0,1.0);
 float dayK=clamp(day,0.0,1.0);
 c+=vec3(1.0,0.62,0.32)*toward*0.18*dayK;
 if(e<0.0){float k=smoothstep(0.0,-0.25,e);c=mix(hor*0.55,hor*0.22,k);}
 return c;
}
vec3 skyCol(vec3 dir,vec3 hor,vec3 zen,vec3 body,vec3 sun,float day,float drift,float motion){
 vec3 s=normalize(sun);float mu=clamp(dot(normalize(dir),s),-1.0,1.0);
 return addDisc(skyAir(dir,hor,zen,sun,day,drift,motion),mu,clamp(day,0.0,1.0),body,drift,motion);
}
vec3 spaceAir(vec3 d){
 float e=d.y;
 vec3 nadir=vec3(0.045,0.055,0.18);
 vec3 limb=vec3(0.14,0.18,0.46);
 vec3 zen=vec3(0.06,0.08,0.24);
 float g=smoothstep(-0.55,0.65,e);
 return mix(nadir,mix(limb,zen,smoothstep(-0.15,0.85,e)),g);
}
vec3 spaceStars(vec3 d,float drift,float motion){
 vec3 g=d*140.0;vec3 cell=floor(g);
 float h=fract(sin(dot(cell,vec3(12.9898,78.233,37.719)))*43758.5453);
 float on=step(0.9965,h);
 float dd=length(g-(cell+vec3(0.5)));
 float core=smoothstep(0.16,0.0,dd);
 float tw=motion>0.0?0.75+0.25*sin(drift*2.0+h*6.0):1.0;
 return vec3(0.72,0.82,1.0)*on*core*tw*0.55;
}
vec3 spaceSky(vec3 dir,vec3 body,vec3 sun,float day,float drift,float motion){
 vec3 d=normalize(dir);vec3 s=normalize(sun);
 float mu=clamp(dot(d,s),-1.0,1.0);
 vec3 c=spaceAir(d);
 c+=vec3(0.22,0.10,0.04)*pow(max(mu,0.0),4.0)*0.08*clamp(day,0.0,1.0);
 c+=spaceStars(d,drift,motion)*(1.0-smoothstep(0.92,0.995,mu));
 return addDisc(c,mu,clamp(day,0.0,1.0),body,drift,motion);
}`;
