import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createPocketSky,orbitPosition} from '../lib/pocket-sky.mjs';
const read=path=>readFileSync(new URL(path,import.meta.url),'utf8');

test('the existing Spark Beast renders in FRONT of a background-only dimensional world',()=>{
 const portal=read('../components/beast-cage-portal.tsx');
 const css=read('../app/globals.css');
 const pocket=read('../components/cage-pocket-dimension.tsx');
 assert.match(portal,/SparkBeastArena profile=\{creature\}/);
 assert.match(portal,/CagePocketDimension/);
 assert.match(portal,/qbeastId=\{sameSpark\?session\.beast\.qbeast\.profile\.id:null\}/);
 assert.match(portal,/seed=\{sameSpark\?session\.beast\.genome\?\.seed\|\|session\.beast\.seed:null\}/);
 assert.match(portal,/href="\/sol-game"/);
 assert.match(css,/\.cage-pocket-active \[data-beast-arena="true"\]\{z-index:2\}/);
 assert.doesNotMatch(css,/\.cage-pocket-active \[data-beast-arena="true"\] \[data-spark-beast="true"\]\{opacity:0/);
 assert.doesNotMatch(pocket,/renderBeast\(|createCreatureRig\(|new THREE\.Sprite\(/);
 assert.doesNotMatch(pocket,/data-pocket-settings|World settings|Render quality|3D pocket enabled/);
});

test('two old CodePens provide reproducible spatial world, not a new model or measurements',()=>{
 const pocket=read('../components/cage-pocket-dimension.tsx');
 assert.match(pocket,/new THREE\.WebGLRenderer/);
 assert.match(pocket,/new THREE\.BoxGeometry\(9\.2,5\.2,9\.2\)/);
 assert.match(pocket,/createPocketSky\(key/);
 assert.match(pocket,/orbitPosition\(body,elapsed/);
 assert.match(pocket,/new THREE\.FogExp2/);
 assert.match(pocket,/beastbox:spark-chirp/);
 assert.match(pocket,/beastbox:spark-mute/);
 assert.match(pocket,/data-pocket-webgl="true"/);
 assert.match(pocket,/pointerdown/);
 assert.match(pocket,/pointermove/);
 assert.match(pocket,/keydown/);
 assert.match(pocket,/wheel/);
 assert.match(pocket,/role="status"/);
 assert.doesNotMatch(pocket,/getUserMedia|\/api\/quantum|SamplerV2|fetch\(|localStorage/);
});

test('cosmetic celestial generator reproduces its orbits exactly from the same seed',()=>{
 const x=createPocketSky('recorded-genome-seed-1',{quality:'auto'});
 const y=createPocketSky('recorded-genome-seed-1',{quality:'auto'});
 assert.deepEqual(x,y);
 assert.equal(x.bodies.length,4);
 assert.equal(createPocketSky('recorded-genome-seed-1',{quality:'low'}).bodies.length,2);
 assert.notDeepEqual(x,createPocketSky('different-seed',{quality:'auto'}));
 assert.deepEqual(orbitPosition(x.bodies[0],13),orbitPosition(y.bodies[0],13));
 assert.notDeepEqual(orbitPosition(x.bodies[0],0),orbitPosition(x.bodies[0],13));
});

test('iPhone WebGL fallback retains the original sprite, audio hit targets and circle',()=>{
 const css=read('../app/globals.css');
 const moduleCSS=read('../components/cage-pocket-dimension.module.css');
 assert.match(css,/\.cage-habitat-visual\.cage-pocket-active/);
 assert.match(css,/\[class\*="hit"\]\{touch-action:none\}/);
 assert.match(moduleCSS,/pointer-events:none/);
 assert.doesNotMatch(moduleCSS,/\.settings|\.panel|\.actions button/);
 assert.match(read('../components/spark-beast-arena.tsx'),/Make the beast attack/);
});
