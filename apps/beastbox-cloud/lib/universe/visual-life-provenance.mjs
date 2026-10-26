// Visual Life Pass B7: provenance. ONE pure function that turns the view's own snapshot (window.__lwVisualLife) into an honest list:
// what is drawn, what drives it (a named engine channel), and its label. Nothing is invented here: a row appears as "on" only when the snapshot carries that piece,
// the labels come from visual-life-labels (SIMULATED stepped by the world loop, SEEDED designed look or placement), and the pack row quotes the pack's own version and sha256.
// RECORDED appears once, for the genesis seed behind the pack, and nowhere else. No clock, no Math.random, no network.
import {VL_PACK} from './vislife-look.mjs';
import {VL_OUTPUT_LABELS} from './visual-life-labels.mjs';
/** Authored rows. `text` is at most 44 characters; `driver` names the engine channel the piece reads. */
export const PROVENANCE_ROWS=Object.freeze([
 {key:'foam',out:'foam',text:'Foam on the water',driver:'world tick, sea wave field, wind'},
 {key:'caustics',out:'caustics',text:'Light on the shallow floor',driver:'sea wave field, sun direction'},
 {key:'haze',out:'haze_fog',text:'Haze in the air',driver:'atmosphere amount, sky horizon, storm tension'},
 {key:'fog',out:'haze_fog',text:'Fog in wet air',driver:'moisture of your cell, storm tension'},
 {key:'boom',out:'boom',text:'Boom light and ring',driver:'boom phase, distance (1/d^2 sky term)'},
 {key:'palette',out:'palette',text:'Hero colour of this world',driver:'atmosphere, temperature, water, star hue'},
 {key:'sound',out:'storm',text:'Event sounds (off until you turn them on)',driver:'storm tension, mean growth, boom phase (see Boom row)'},
]);
const present=(key,s)=>{
 switch(key){
  case 'foam':return !!s.foam;
  case 'caustics':return !!(s.caustics&&s.caustics.on);
  case 'haze':return !!s.haze;
  case 'fog':return !!(s.haze&&s.haze.mul>1.05);
  case 'boom':return !!s.boom;
  case 'palette':return !!s.palette;
  case 'sound':return !!(s.sound&&s.sound.on);
  default:return false;
 }
};
/** provenance(snapshot) -> {pack:{version,sha256,label}, seed:{text,label}, rows:[{key,text,driver,label,on}]} */
export function provenance(snapshot){
 const s=snapshot||{};
 const rows=PROVENANCE_ROWS.map(r=>{
  // the boom carries its own engine label when the snapshot has one; everything else uses the authored output label
  const label=r.key==='boom'&&s.boom&&s.boom.label?String(s.boom.label):VL_OUTPUT_LABELS[r.out];
  return {key:r.key,text:r.text,driver:r.driver,label,on:present(r.key,s)};
 });
 return {pack:{version:VL_PACK.version,sha256:VL_PACK.sha256,label:'SEEDED'},seed:{text:'Genesis seed behind the pack (jitter only)',label:'RECORDED'},rows};
}
