// Park look (PK1: palette, sky and haze grade). Builds on the Genesis ground and grades it.
// Park never edits a Genesis material or writes a Genesis uniform. It draws Park twins that read the same
// Genesis uniforms (sun, day, clock) plus their own uPk* colours, and swaps them in only while Park is chosen.
// Classic and Genesis frames therefore stay exactly as they were. No new light, no second sun, no second clock.
import {usesGenesisBase,currentLook} from './look-mode.ts';
import {parkGrade,PK_OUT,PK_SAT,type ParkGrade,type RGB} from './park-palette.ts';
import {buildParkGrass,syncParkGrass,PARK_GRASS_LABEL} from './park-grass.ts';
import {shoreSurface} from './water.ts';
export {PK_OUT,PK_SAT};

export const PARK_LABEL='Park grade · SIMULATED';

type Edit=[string|RegExp,string];
type Variant={key:string;edits:Edit[];uniforms:(THREE:typeof import('three'))=>Record<string,{value:any}>;sync:(u:Record<string,{value:any}>,g:ParkGrade)=>void};

const col=(THREE:typeof import('three'))=>new THREE.Color(0,0,0);
/** Saturation lift. The page's ACES output flattens colour; Park pre-lifts it so the meadow and sky stay vivid. */
function setC(u:{value:{setRGB:(r:number,g:number,b:number)=>void}},c:RGB){u.value.setRGB(c[0],c[1],c[2]);}

/** Park twin of the Genesis sky: same dome, same disc, Park zenith and horizon. */
export const PARK_SKY:Variant={
 key:'genesis-sky',
 edits:[
  [/uniform vec3 uSun,uZen,uHor;/,'uniform vec3 uSun,uPkZen,uPkHor;\n#define uZen uPkZen\n#define uHor uPkHor\n'+PK_SAT],
  [/vec3 c=mix\(uHor,uZen,pow\(clamp\(e\+veil,0\.0,1\.0\),\.45\)\);/,'vec3 c=mix(uHor,uZen,pow(clamp(e+veil,0.0,1.0),.32));'],
  [/ gl_FragColor=vec4\(c,1\.0\);\n\}$/,' gl_FragColor=vec4(pkLin(pkSat(c,1.2)),1.0);\n'+PK_OUT+'}'],
 ],
 uniforms:THREE=>({uPkZen:{value:col(THREE)},uPkHor:{value:col(THREE)}}),
 sync:(u,g)=>{setC(u.uPkZen,g.zenith);setC(u.uPkHor,g.horizon);},
};
/** Park twin of the Genesis terrain: meadow, sand path and terracotta cutbank, wrapped light, cool shadow, Park haze. */
export const PARK_TERRAIN:Variant={
 key:'genesis-terrain',
 edits:[
  [/uniform vec3 uSun,uHaze,uZen;/,'uniform vec3 uSun,uPkHaze,uPkZen,uPkSand,uPkMeadow,uPkMeadowMid,uPkCliff,uPkCliffShade,uPkShadow,uPkKey,uPkNight;\n#define uHaze uPkHaze\n#define uZen uPkZen\n'+PK_SAT],
  [/vec3 c=mix\(sand,meadow,max\(smoothstep\(-\.02,\.22,above\),pad\)\);/,'vec3 c=mix(sand,meadow,max(smoothstep(-.14,.0,above),pad));'],
  [/vec3 sand=vec3\([^;]*snow=vec3\(\.92,\.94,\.96\);/,'vec3 sand=uPkSand,meadow=mix(uPkMeadow,uPkMeadowMid,vn(vP.xz*.08)*.5),forest=uPkMeadowMid,rock=mix(uPkCliff,uPkCliffShade,.3),snow=vec3(.92,.94,.96);'],
  [/ c\*=\(mix\(0\.46,0\.28,dayK\)\+mix\(0\.35,0\.72,dayK\)\*ndl\)\*vAo;/,` float wrap=clamp((dot(normalize(vN),normalize(uSun))+.45)/1.45,0.0,1.0);
 vec3 lightC=mix(mix(uPkShadow,vec3(1.0),.5),uPkKey,wrap)*mix(.84,1.0,vAo);
 vec3 nightC=uPkNight*(.45+.9*dot(c,vec3(.3,.59,.11)))*mix(.75,1.0,wrap);
 c=mix(nightC,c*lightC,dayK);`],
  [/c=mix\(c,band,clamp\(\(near\*\.55\+mid\*\.3\+far\*\.15\)\*drift,0\.0,\.92\)\);/,'c=mix(c,band,clamp((near*.1+mid*.32+far*.45)*drift,0.0,.9));'],
  [/ gl_FragColor=vec4\(c,1\.0\);\n\}$/,' gl_FragColor=vec4(pkLin(pkSat(c,1.2)),1.0);\n'+PK_OUT+'}'],
 ],
 uniforms:THREE=>Object.fromEntries(['uPkHaze','uPkZen','uPkSand','uPkMeadow','uPkMeadowMid','uPkCliff','uPkCliffShade','uPkShadow','uPkKey','uPkNight'].map(k=>[k,{value:col(THREE)}])),
 sync:(u,g)=>{setC(u.uPkHaze,g.haze);setC(u.uPkZen,g.zenith);setC(u.uPkSand,g.sand);setC(u.uPkMeadow,g.meadow);setC(u.uPkMeadowMid,g.meadowMid);setC(u.uPkCliff,g.cliff);setC(u.uPkCliffShade,g.cliffShade);setC(u.uPkShadow,g.shadow);setC(u.uPkKey,g.key);setC(u.uPkNight,g.nightGround);},
};
/** Park twin of the Genesis water: bright cyan shallows, Park deep, white foam. Waves stay SIMULATED. */
export const PARK_WATER:Variant={
 key:'genesis-water',
 edits:[
  [/uniform vec3 uSun,uSky,uDeep;/,'uniform vec3 uSun,uPkSky,uPkDeep,uPkShallow,uPkSand,uPkFoam;\n#define uSky uPkSky\n#define uDeep uPkDeep\n'+PK_SAT],
  [/vec3 sand=vec3\(\.62,\.56,\.38\);/,'vec3 sand=uPkSand;'],
  [/vec3 c=mix\(vec3\(\.08,\.55,\.52\),uDeep,t\);/,'vec3 c=mix(uPkShallow,uDeep,t);'],
  [/c=mix\(c,vec3\(\.9,\.95,\.96\),foam\*\.82\);/,'c=mix(c,uPkFoam,foam*.9);'],
  [/ c\*=a;\n gl_FragColor=vec4\(c,a\);\n\}$/,' c=pkLin(pkSat(c,1.15))*a;\n gl_FragColor=vec4(c,a);\n'+PK_OUT+'}'],
 ],
 uniforms:THREE=>Object.fromEntries(['uPkSky','uPkDeep','uPkShallow','uPkSand','uPkFoam'].map(k=>[k,{value:col(THREE)}])),
 sync:(u,g)=>{setC(u.uPkSky,g.horizon);setC(u.uPkDeep,g.deep);setC(u.uPkShallow,g.shallow);setC(u.uPkSand,g.sand);setC(u.uPkFoam,g.foam);},
};
/** Park twin of the Genesis grass: dark teal root to bright tip. */
export const PARK_GRASS:Variant={
 key:'genesis-grass',
 edits:[
  [/uniform float uDay;/,'uniform float uDay;uniform vec3 uPkRoot,uPkTip;\n'+PK_SAT],
  [/vec3 c=mix\(vec3\(\.10,\.24,\.07\),vec3\(\.34,\.52,\.16\),/,'vec3 c=mix(uPkRoot,uPkTip,'],
  [/c\*=mix\(\.2,1\.0,clamp\(uDay,0\.0,1\.0\)\);/,'c*=mix(.8,1.0,clamp(uDay,0.0,1.0));c=pkSat(c,1.2);'],
  [/ gl_FragColor=vec4\(c,1\.0\);\n\}$/,' gl_FragColor=vec4(pkLin(c),1.0);\n'+PK_OUT+'}'],
 ],
 uniforms:THREE=>({uPkRoot:{value:col(THREE)},uPkTip:{value:col(THREE)}}),
 sync:(u,g)=>{setC(u.uPkRoot,g.grassRoot);setC(u.uPkTip,g.grassTip);},
};
/** Park twin of the Genesis cone trees: Park canopy fill. Cory's own ball trees are not touched. */
export const PARK_TREES:Variant={
 key:'genesis-trees',
 edits:[
  [/uniform float uDay;/,'uniform float uDay;uniform vec3 uPkCanopy;\n'+PK_SAT],
  [/vec3 trunk=vec3\(\.28,\.16,\.08\),leaf=vec3\(\.08,\.26,\.1\);/,'vec3 trunk=vec3(.48,.32,.2),leaf=uPkCanopy*1.25;'],
  [/vec3 c=mix\(trunk,leaf,smoothstep\(\.35,1\.1,vY\)\);/,'vec3 c=mix(trunk,leaf,smoothstep(.06,.24,vY));'],
  [/gl_FragColor=vec4\(c\*mix\(\.18,1\.0,clamp\(uDay,0\.0,1\.0\)\),1\.0\);/,'gl_FragColor=vec4(pkLin(c*mix(.72,1.0,clamp(uDay,0.0,1.0))),1.0);\n'+PK_OUT],
 ],
 uniforms:THREE=>({uPkCanopy:{value:col(THREE)}}),
 sync:(u,g)=>{setC(u.uPkCanopy,g.canopy);},
};
export const PARK_VARIANTS=Object.freeze([PARK_SKY,PARK_TERRAIN,PARK_WATER,PARK_GRASS,PARK_TREES]);

/** Apply a variant's edits to a Genesis shader. Returns null when any edit does not match, so Park never ships half a shader. */
export function editShader(src:string,edits:Edit[]){
 let out=src;
 for(const [from,to] of edits){
  const next=out.replace(from,to);
  if(next===out)return null;
  out=next;
 }
 return out;
}

type Mat={fragmentShader:string;vertexShader:string;uniforms:Record<string,{value:any}>;side?:number;transparent?:boolean;depthWrite?:boolean;depthTest?:boolean;premultipliedAlpha?:boolean;dispose?:()=>void};

/** Park twin of one Genesis ShaderMaterial. It shares the Genesis uniform objects (read only) and adds uPk* colours. */
export function parkTwin(THREE:typeof import('three'),base:Mat,v:Variant){
 const frag=editShader(base.fragmentShader,v.edits);
 if(!frag)return null;
 const own=v.uniforms(THREE);
 const mat=new THREE.ShaderMaterial({
  uniforms:{...base.uniforms,...own},vertexShader:base.vertexShader,fragmentShader:frag,
  side:base.side as any,transparent:!!base.transparent,depthWrite:base.depthWrite!==false,depthTest:base.depthTest!==false,
  premultipliedAlpha:!!base.premultipliedAlpha,fog:false,
 });
 mat.name='park:'+v.key;
 return {material:mat,own};
}

type GenesisHandle={anchor:{onBeforeRender:(...a:any[])=>void};group:any;sync:()=>any;tier?:string};
type Opts={getLook?:()=>string;getSun?:()=>{elevationDeg?:number}|null;
 /** Extra page layers Park hides while it is on (for example the pale far-horizon shells). Restored exactly when Park is off. */
 conceal?:()=>any[];
 /** PK3 meadow: the same seeded height the Genesis ground uses, and the same seed. Without heightAt there is no Park grass. */
 heightAt?:(x:number,z:number)=>number;seed?:string;
 camera?:()=>{position:{x:number;y:number;z:number}}|null;
 tier?:()=>string};

/**
 * Mount Park on an attached Genesis look. Call once, right after attachGenesisLook.
 * The Genesis sync runs first every frame; Park then swaps in its twins (Park) or puts the Genesis materials back (anything else).
 */
export function attachParkLook(THREE:typeof import('three'),genesis:GenesisHandle,opts:Opts={}){
 const twins=new WeakMap<object,{material:any;own:Record<string,{value:any}>;variant:Variant}>();
 const originals=new WeakMap<object,any>();
 const byKey=new Map(PARK_VARIANTS.map(v=>[v.key,v]));
 let lastElev=NaN,rising=true,grade:ParkGrade|null=null,on=false,swapped=0;
 const look=()=>opts.getLook?opts.getLook():currentLook();
 let grass:ReturnType<typeof buildParkGrass>&{tier:string}|null=null;
 let shore:ReturnType<typeof shoreSurface>|null=null;
 const eye=new THREE.Vector3();
 function meadow(g:ParkGrade){
  if(!opts.heightAt)return;
  const tier=String(opts.tier?.()||genesis.tier||'MED');
  if(!grass||grass.mesh.parent!==genesis.group||grass.tier!==tier){
   if(grass){grass.mesh.parent?.remove(grass.mesh);grass.mesh.geometry.dispose();(grass.mesh.material as any).dispose();}
   const seed=opts.seed||'genesis',h=opts.heightAt;
   shore=shore||shoreSurface(h,seed);
   const s=shore; // the spawn pad (inside 14) is meadow in the Genesis terrain shader, so it is meadow here too
   grass={...buildParkGrass(THREE,{seed,tier,heightAt:h,wetAt:(x,z)=>Math.hypot(x,z)>14&&s.at(x,z)>h(x,z)-.02}),tier};
   genesis.group.add(grass.mesh);
  }
  grass.mesh.visible=true;
  const gg=genesis.group.children.find((o:any)=>o.name==='genesis-grass');
  const wu=gg?.material?.uniforms;
  const cam=opts.camera?.();
  if(cam){eye.set(cam.position.x,cam.position.y,cam.position.z);genesis.group.worldToLocal(eye);}
  syncParkGrass(grass.uniforms,{phase:Number(wu?.uPhase?.value??0),amp:Number(wu?.uAmp?.value??0)},g,cam?eye:undefined);
 }
 const hidden=new Map<any,boolean>();
 function hide(){
  for(const o of opts.conceal?.()||[]){
   if(!o)continue;
   if(!hidden.has(o))hidden.set(o,o.visible!==false);
   o.visible=false;
  }
 }
 function restore(){
  swapped=0;
  if(grass)grass.mesh.visible=false;
  for(const [o,v] of hidden)o.visible=v;
  hidden.clear();
  for(const o of genesis.group.children){
   const orig=originals.get(o.material);
   if(orig){o.material=orig;}
  }
 }
 function apply(){
  on=look()==='park';
  if(!on){restore();return null;}
  const sun=opts.getSun?.()||null;
  const elev=Number(sun?.elevationDeg??45);
  if(Number.isFinite(lastElev)&&Math.abs(elev-lastElev)>1e-4)rising=elev>lastElev;
  lastElev=elev;
  grade=parkGrade(elev,rising);
  swapped=0;
  if(genesis.group.visible)hide();else{for(const [o,v] of hidden)o.visible=v;hidden.clear();}
  for(const o of genesis.group.children){
   const v=byKey.get(o.name);
   if(!v||!o.material)continue;
   let cur=o.material;
   if(!originals.has(cur)){
    let t=twins.get(cur);
    if(!t){
     const made=parkTwin(THREE,cur,v);
     if(!made)continue;
     t={...made,variant:v};twins.set(cur,t);originals.set(made.material,cur);
    }
    o.material=t.material;cur=t.material;
   }
   const orig=originals.get(cur);
   const t=twins.get(orig);
   if(t){t.variant.sync(t.own,grade);swapped++;}
  }
  if(genesis.group.visible)meadow(grade);
  return grade;
 }
 const base=genesis.anchor.onBeforeRender;
 genesis.anchor.onBeforeRender=(...a:any[])=>{base(...a);apply();};
 return {
  apply,
  get on(){return on;},
  state(){return {on,stop:grade?.stop??null,day:grade?+grade.day.toFixed(3):null,swapped,label:PARK_LABEL,grass:grass?{count:grass.count,tier:grass.tier,visible:grass.mesh.visible,label:PARK_GRASS_LABEL}:null};},
  dispose(){genesis.anchor.onBeforeRender=base;restore();if(grass){grass.mesh.parent?.remove(grass.mesh);grass.mesh.geometry.dispose();(grass.mesh.material as any).dispose();grass=null;}},
 };
}

/** True when the Genesis ground should draw (Genesis or Park). */
export const drawsGenesisGround=usesGenesisBase;
