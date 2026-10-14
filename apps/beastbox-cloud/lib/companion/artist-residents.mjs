/**
 * Artist-drawn Pocket residents, from Cory Davis's own uploaded art (2026-10-14).
 * They are new, distinct creatures with their own art and ids. They have NO quantum
 * seed: no IBM counts, no Rigetti/QVM run and no genome. They never reuse
 * bb-7f9c2a03 (Moonwraith), bb-deada969 (RAWRPHØS) or any QBEAST identity.
 */
export const ARTIST_ORIGIN='ARTIST-DRAWN · NO QUANTUM SEED';
const v=(slug,views)=>Object.freeze(Object.fromEntries(views.map(k=>[k,`/companion/art/${slug}/${k}.webp`])));
export const ARTIST_RESIDENTS=Object.freeze([
 Object.freeze({id:'art-frostmitt',name:'Frostmitt',kind:'beast',look:'Frost cat in a purple beanie',views:v('frostmitt',['front','side','back']),scale:1.05}),
 Object.freeze({id:'art-nyxbean',name:'Nyxbean',kind:'beast',look:'Black cosmic kitten in a beanie',views:v('nyxbean',['front','side','back']),scale:.9}),
 Object.freeze({id:'art-velvetcoil',name:'Velvetcoil',kind:'beast',look:'Purple serpent dragon (pixel art)',views:v('velvetcoil',['front']),scale:1.25}),
 Object.freeze({id:'art-shardhowl',name:'Shardhowl',kind:'beast',look:'Crystal void wolf (pixel art)',views:v('shardhowl',['front']),scale:1.2}),
 Object.freeze({id:'art-kairo',name:'Kairo',kind:'trainer',look:'Horned hoodie kid · human trainer, not a beast',views:v('kairo',['front','side','back']),scale:1.35}),
].map(r=>Object.freeze({...r,origin:ARTIST_ORIGIN,quantumSeed:null,artist:'Cory Davis'})));
/** Pick a view from heading (radians, world) relative to camera azimuth. */
export function residentView(resident,heading,cameraTheta){
 const views=resident.views;if(!views.side)return {src:views.front,flip:false};
 let d=Math.atan2(Math.sin(heading-cameraTheta),Math.cos(heading-cameraTheta));
 const a=Math.abs(d);
 if(a<Math.PI/4)return {src:views.back,flip:false};
 if(a>Math.PI*3/4)return {src:views.front,flip:false};
 return {src:views.side,flip:d<0};
}
