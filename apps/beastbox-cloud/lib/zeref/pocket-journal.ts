/**
 * Browser-local pocket journal: discovered combos, places reached and real
 * care (taps / attacks / visits) seen ON THIS DEVICE. Kept separate from the
 * server diary and from the Beast's save; clearing site data clears it.
 */
export type JournalCombo={key:string;name:string;at:string};
export type Journal={keys:string[];combos:JournalCombo[];comboCount:number;arrivals:number;places:Record<string,number>;care:{taps:number;visits:number};lastVisit:string|null;lastPlace?:string};
const KEY='beastbox-zeref-pocket-v1';
const EMPTY=():Journal=>({keys:[],combos:[],comboCount:0,arrivals:0,places:{},care:{taps:0,visits:0},lastVisit:null});
type Store=Record<string,Journal>;
function load():Store{try{const raw=window.localStorage.getItem(KEY);const v=raw?JSON.parse(raw):{};return v&&typeof v==='object'?v:{};}catch{return {};}}
function save(store:Store){try{window.localStorage.setItem(KEY,JSON.stringify(store));}catch{/* private mode: journal stays in memory for this view */}}
function update(id:string,fn:(j:Journal)=>void){
 const store=load();const j={...EMPTY(),...(store[id]||{})};fn(j);store[id]=j;save(store);
 window.dispatchEvent(new CustomEvent('beastbox:zeref-pocket',{detail:{id}}));
 return j;
}
export function readJournal(id:string):Journal{return {...EMPTY(),...(load()[id]||{})};}
/** Returns true when the combo is new on this device. */
export function recordCombo(id:string,c:{key:string;name:string}){
 let fresh=false;
 update(id,j=>{if(j.keys.includes(c.key))return;fresh=true;j.keys=[...j.keys,c.key].slice(-4000);j.comboCount++;j.combos=[{key:c.key,name:c.name,at:new Date().toISOString()},...j.combos].slice(0,60);});
 return fresh;
}
export function recordArrival(id:string,place:string){update(id,j=>{j.arrivals++;j.places[place]=(j.places[place]||0)+1;j.lastPlace=place;});}
export function recordCare(id:string,kind:'taps'|'visits'){update(id,j=>{j.care[kind]++;if(kind==='visits')j.lastVisit=new Date().toISOString();});}
