// ONE WORLD (Cory, Oct 25 2026): the home pocket universe holds the whole universe, and every section of the site is a
// puzzle piece of it. This is the single source for that map: friendly names (no raw ids), each piece's job in the
// world, its neighbours, and which routes belong to which piece. Pure data + functions, no clock, no random.
/** Journey order is also the order of the prev/next arrows: from the whole sky, zooming in, then out to play and build. */
export const PIECES=Object.freeze([
 {key:'home',name:'Pocket universe',short:'Universe home',icon:'✦',href:'/',role:'The whole sky in one pocket: every other piece is a place inside it.',neighbors:['universe','cage','workshop']},
 {key:'universe',name:'Tiny Universe',short:'Tiny Universe',icon:'🌌',href:'/universe',role:'Zoom out: the planets and landscapes, seeded from the recorded run.',neighbors:['home','tiny']},
 {key:'tiny',name:'Tiny world',short:'Tiny world',icon:'🌍',href:'/beast-cage/world',role:'Zoom in: land on one planet and live there with your beast.',neighbors:['universe','cage']},
 {key:'cage',name:'Beast Cage',short:'Habitat',icon:'🏰',href:'/beast-cage',role:'Your beast’s home base: care, talk, look closer, its diary.',neighbors:['tiny','home','field']},
 {key:'field',name:'Lost COSMOS Field',short:'Field',icon:'📷',href:'/beast-cage/field',role:'The field piece: step outside and look through the camera, on your terms.',neighbors:['cage','game']},
 {key:'game',name:'Lost COSMOS',short:'Game',icon:'🎮',href:'/sol-game',role:'The adventure piece: take your beast out to play.',neighbors:['field','workshop']},
 {key:'workshop',name:'Workshop',short:'Workshop',icon:'🛠️',href:'/workspace',role:'Behind the scenes: brains, research, settings and the tools that build the world.',neighbors:['game','home']}
]);
const BY=Object.fromEntries(PIECES.map(p=>[p.key,p]));
/** Longest-prefix route table. Sub-pages belong to the piece they open from, so every page highlights somewhere on the map. */
const ROUTES=[
 ['/beast-cage/world','tiny','Tiny world'],['/beast-cage/field','field',null],['/beast-cage/go','universe','Star field'],
 ['/beast-cage/guest','game','Catch a Star'],['/beast-cage/play','cage','Adventure walk'],['/beast-cage/look','cage','Look Closer'],
 ['/beast-cage/turntable','cage','3D model'],['/beast-cage/talk','cage','Talk'],['/beast-cage','cage',null],
 ['/universe','universe',null],['/sol-game','game',null],['/workspace','workshop',null],
 ['/brain-bay','workshop','Brain Bay'],['/research','workshop','Research Lab'],['/settings','workshop','Settings'],
 ['/account','workshop','Account'],['/connect','workshop','Connect'],['/privacy','workshop','Privacy and info'],['/next','workshop','Coming soon'],
 ['/try','game','Guest model'],['/beach-two','tiny','Beach']
];
export function pieceForPath(path){
 const p=String(path||'/').split(/[?#]/)[0].replace(/\/+$/,'')||'/';
 if(p==='/')return {piece:BY.home,sub:null};
 let best=null;
 for(const [prefix,key,sub] of ROUTES){if((p===prefix||p.startsWith(prefix+'/'))&&(!best||prefix.length>best[0].length))best=[prefix,key,sub];}
 return best?{piece:BY[best[1]],sub:best[2]}:null;
}
export function pieceIndex(key){return PIECES.findIndex(p=>p.key===key);}
export function neighborsOf(key){return (BY[key]?.neighbors||[]).map(k=>BY[k]);}
/** prev/next in journey order, wrapping, so the arrows never dead-end. */
export function journeyStep(key,dir){const n=PIECES.length,i=pieceIndex(key);if(i<0)return null;return PIECES[(i+(dir<0?-1:1)+n)%n];}
export function worldHere(path){const m=pieceForPath(path);if(!m)return null;const i=pieceIndex(m.piece.key);
 return {piece:m.piece,sub:m.sub,index:i+1,total:PIECES.length,prev:journeyStep(m.piece.key,-1),next:journeyStep(m.piece.key,1),neighbors:neighborsOf(m.piece.key)};}
export const WORLD_LABELS=Object.freeze({
 title:'One world',
 line:'Every page is one puzzle piece of the same universe. Your beast, its seed and its diary travel with you between pieces.',
 honesty:'Landscapes are SEEDED from the recorded run, growth is SIMULATED, IBM seeds are RECORDED.'
});
