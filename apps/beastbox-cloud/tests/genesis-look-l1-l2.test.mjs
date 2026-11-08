import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {sunTintFor,sunKelvinFromDeg,tintRig,SUN_LABEL} from '../lib/look/sun-tint.ts';
import {skyColour,spaceSkyColour,rayleighPhase,hgPhase,createSkyDome,syncSky,SKY_LABEL} from '../lib/look/sky-dome.ts';
import {aerialAmount,hazeColour} from '../lib/look/haze.ts';
import {skyAir} from '../lib/look/sky-math.ts';
import {exposureTarget,stepExposure,bloomFor,postPlan,POST_LABEL} from '../lib/look/post.ts';
import {attachGenesisLook} from '../lib/look/attach.ts';
import {buildFoliage,PLACEMENT_LABEL} from '../lib/look/foliage.ts';
import {lightRigFor} from '../lib/universe/sky-view.mjs';
import {oneSunAt} from '../lib/universe/one-sun.mjs';

const root=new URL('../',import.meta.url);
const read=p=>readFileSync(new URL(p,root),'utf8');
const lum=c=>0.2126*c[0]+0.7152*c[1]+0.0722*c[2];
const norm=v=>{const l=Math.hypot(...v)||1;return v.map(x=>x/l);};

test('sun tint is the seeded black-body of the one sun elevation',()=>{
 const noon=sunTintFor(64);
 const low=sunTintFor(2);
 assert.equal(noon.label,SUN_LABEL);
 assert.equal(SUN_LABEL,'Sun · SEEDED');
 assert.equal(sunKelvinFromDeg(64),6500);
 assert.ok(sunKelvinFromDeg(2)<2800);
 assert.ok(low.rgb[0]/Math.max(1e-4,low.rgb[2]) > noon.rgb[0]/Math.max(1e-4,noon.rgb[2]));
 const rig=Object.freeze(lightRigFor({day:1,elevationDeg:8,sky:{zenith:[.1,.2,.4],horizon:[.8,.5,.3]}}));
 const before=JSON.stringify(rig);
 const tinted=tintRig(rig,[1,0.875,0.7055]);
 assert.equal(JSON.stringify(rig),before);
 assert.ok(tinted.sunColor[0]>tinted.sunColor[2]);
 assert.ok(tinted.sunColor[2]<0.7055);
});

test('the animated sky puts the sun on the one-sun direction and brightens that horizon',()=>{
 let day=null;
 for(let s=0;s<240;s+=.5){const os=oneSunAt(s);if(os.elevationDeg>25)day=os;}
 assert.ok(day);
 const rig=lightRigFor(day);
 const sun=day.dir;
 const along=norm(sun);
 const side=norm([-sun[2],0.15,sun[0]]);
 const away=norm([-sun[0],0.02,-sun[2]]);
 const toward=norm([sun[0],0.02,sun[2]]);
 const body=[1,.93,.78];
 const hor=day.sky.horizon,zen=day.sky.zenith;
 const peak=skyColour(along,sun,hor,zen,0,day.day,1,body);
 const off=skyColour(side,sun,hor,zen,0,day.day,1,body);
 assert.ok(lum(peak)>lum(off)+0.2);
 const warm=skyColour(toward,sun,hor,zen,1.2,day.day,1,body);
 const cool=skyColour(away,sun,hor,zen,1.2,day.day,1,body);
 assert.ok(lum(warm)>lum(cool));
 const a=skyColour(side,sun,hor,zen,0.2,day.day,1,body);
 const b=skyColour(side,sun,hor,zen,2.4,day.day,1,body);
 assert.notDeepEqual(a.map(v=>+v.toFixed(4)),b.map(v=>+v.toFixed(4)));
 assert.deepEqual(skyColour(along,sun,hor,zen,0.4,day.day,0,body),skyColour(along,sun,hor,zen,0.4,day.day,0,body));
 assert.ok(rayleighPhase(1)>rayleighPhase(0));
 assert.ok(hgPhase(1,0.995)>hgPhase(0,0.995));
 assert.equal(SKY_LABEL,'Sky · DERIVED');
});

test('orbit space is a dark blue gradient and the sun disc is hotter than the air',()=>{
 const sun=[0.25,0.35,0.9];
 const up=spaceSkyColour([0,1,0],sun,0,1,1);
 const down=spaceSkyColour([0,-1,0],sun,0,1,1);
 assert.ok(lum(up)<0.25);
 assert.ok(lum(down)<lum(up));
 assert.ok(up[2]>up[1]&&down[2]>down[1]);
 assert.notDeepEqual(up.map(v=>+v.toFixed(3)),down.map(v=>+v.toFixed(3)));
 const disc=spaceSkyColour(norm(sun),sun,0,1,1);
 assert.ok(lum(disc)>lum(up)+1);
 const off=skyColour([0,0.2,1],sun,[.62,.78,.9],[.18,.4,.7],0,1,1);
 const on=skyColour(norm(sun),sun,[.62,.78,.9],[.18,.4,.7],0,1,1);
 assert.ok(lum(on)>lum(off)+1);
});

test('far hills fade into the sky colour and the fade thins with height',()=>{
 assert.ok(aerialAmount(400,0)>aerialAmount(12,0));
 assert.ok(aerialAmount(400,0)>aerialAmount(400,48));
 assert.ok(aerialAmount(400,0)>0.3&&aerialAmount(400,0)<0.55);
 assert.ok(aerialAmount(8,2)<0.15);
 const sun=[0.4,0.15,0.9];
 const hor=[0.62,0.74,0.86],zen=[0.12,0.32,0.7];
 const toward=skyAir(norm([sun[0],0.02,sun[2]]),sun,hor,zen,0,1,0);
 const away=skyAir(norm([-sun[0],0.02,-sun[2]]),sun,hor,zen,0,1,0);
 assert.ok(lum(toward)>lum(away));
 assert.ok(hazeColour([0,0.2,1],sun,hor,zen,0.2).every(v=>v>=0&&v<=1.2));
});

test('genesis post follows the sun, blooms only on HIGH and GOD, and skips the heavy chain on software GL',()=>{
 assert.equal(POST_LABEL,'Post · SIMULATED');
 assert.ok(exposureTarget(70)<exposureTarget(-25));
 assert.ok(exposureTarget(70)<0.8);
 assert.ok(exposureTarget(-25)>0.95);
 assert.equal(stepExposure(1,0.7,0),1);
 assert.ok(stepExposure(1,0.7,0.1)<1);
 assert.ok(stepExposure(1,0.7,0.1)>0.7);
 const night=bloomFor(postPlan('HIGH'),-20);
 const noon=bloomFor(postPlan('HIGH'),70);
 assert.ok(noon.strength<night.strength);
 assert.ok(noon.threshold>night.threshold);
 assert.equal(postPlan('LOW').bloom,false);
 assert.equal(postPlan('LOW').fxaa,false);
 assert.equal(postPlan('MED').bloom,false);
 assert.equal(postPlan('MED').fxaa,true);
 assert.equal(postPlan('HIGH').bloom,true);
 assert.equal(postPlan('HIGH').bloomScale,0.5);
 assert.equal(postPlan('GOD').bloomScale,1);
 assert.equal(postPlan('GOD',true).bloom,false);
 assert.equal(postPlan('HIGH',true).fxaa,false);
 assert.equal(postPlan('HIGH',true).heavy,false);
});

test('software GL keeps the light sky and a real GPU gets the scattering sky',async()=>{
 const THREE=await import('three');
 const opts={seed:'s',tier:'MED',heightAt:()=>0,getLook:()=>'genesis',reduced:()=>false,nowMs:()=>0,readTick:()=>2,
  getSun:()=>({dir:[0.2,0.8,0.3],day:1,elevationDeg:48,sky:{zenith:[.1,.3,.7],horizon:[.7,.8,.9],starAlpha:0}})};
 const lite=attachGenesisLook(THREE,{add(){},children:[]},{...opts,softGL:true});
 lite.sync();
 const liteSky=lite.group.getObjectByName('genesis-sky');
 assert.equal(liteSky.userData.label,SKY_LABEL);
 assert.equal(liteSky.userData.sun,SUN_LABEL);
 assert.doesNotMatch(liteSky.material.fragmentShader,/rayleighPhase/);
 lite.dispose();
 const heavy=attachGenesisLook(THREE,{add(){},children:[]},{...opts,softGL:false});
 heavy.sync();
 const sky=heavy.group.getObjectByName('genesis-sky');
 assert.match(sky.material.fragmentShader,/rayleighPhase/);
 assert.match(sky.material.fragmentShader,/hgPhase/);
 const rig=lightRigFor({day:1,elevationDeg:48,sky:opts.getSun().sky});
 const disc=syncSky(sky.material.uniforms,opts.getSun(),rig,{skyDrift:0.4,reduced:false,hazePhase:0,windPhase:0,windAmp:0,wavePhase:0,waveAmp:0,cloudPhase:0});
 assert.ok(Math.abs(disc.sunDir[1]-opts.getSun().dir[1]/Math.hypot(...opts.getSun().dir))<1e-6);
 assert.ok(sky.material.uniforms.uBody.value.r>0);
 heavy.dispose();
 const classic={visible:true};
 const orb=attachGenesisLook(THREE,{add(){},children:[]},{...opts,follow:()=>({position:new THREE.Vector3(),quaternion:new THREE.Quaternion(),visible:false}),classicRoots:()=>[classic]});
 orb.sync();
 assert.equal(classic.visible,false);
 assert.equal(orb.group.getObjectByName('genesis-terrain').visible,false);
 assert.equal(orb.group.getObjectByName('genesis-sky').material.uniforms.uSpace.value,1);
 assert.match(orb.group.getObjectByName('genesis-sky').material.fragmentShader,/spaceSky/);
 orb.dispose();
 const grown=buildFoliage(THREE,{heightAt:()=>1,shoreAt:()=>0,tier:'LOW',seed:'meadow'});
 assert.equal(grown.grass.userData.label,PLACEMENT_LABEL);
 assert.equal(PLACEMENT_LABEL,'Placement · SEEDED');
});

test('the living world keeps Classic post, labels the new look, and skips heavy genesis on software GL',()=>{
 const lw=read('components/living-world.tsx');
 assert.match(lw,/post\.render\(sunDisc\.position/);
 assert.match(lw,/sun\.color\.set\(ONE_SUN\.hex\)/);
 assert.match(lw,/lookRef\.current==='genesis'/);
 assert.match(lw,/sunTintFor\(/);
 assert.match(lw,/createGenesisPost\(/);
 assert.match(lw,/softGL/);
 assert.match(lw,/Sky · DERIVED/);
 assert.match(lw,/Sun · SEEDED/);
 assert.match(lw,/Placement · SEEDED/);
 assert.match(read('components/cage-pocket-dimension.tsx'),/soft\?null/);
 assert.match(lw,/Reads traveler, beast and world positions and writes the THREE camera/);
});
