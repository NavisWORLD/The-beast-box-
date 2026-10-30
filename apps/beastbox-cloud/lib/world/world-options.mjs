// ONE shared source for the options that show up in more than one area (Cory, Oct 25 2026): the Living world / Pocket
// explorer / Classic pixel sprite view switch, Reset 3D camera, the Diary, the sensing pointer and the naming. Each
// page asks for its own CONTEXT (home frames the pocket universe, the cage frames the habitat); labels and the saved
// choice never diverge. Pure functions, storage is injected.
export const VIEW_STORAGE='beastbox-cage-view-v1';
export const VIEW_EVENT='beastbox:world-view';
export const VIEW_OPTIONS=Object.freeze([
 {id:'world',icon:'🌍',label:'Living world',needsBeast:true,hint:'The tiny world you and your beast live on.'},
 {id:'pocket',icon:'✦',label:'Pocket explorer',needsBeast:false,hint:'The 3D pocket dimension, with your beast roaming.'},
 {id:'classic',icon:'▦',label:'Classic pixel sprite',needsBeast:false,hint:'The original pixel sprite, shown only because you chose it.'}
]);
export const CONTEXTS=Object.freeze({
 cage:{key:'cage',menuLabel:'Habitat menu',title:'Habitat options',frame:'How you see your beast’s habitat.',diaryHref:'#zeref-diary',reset:'Reset 3D camera'},
 home:{key:'home',menuLabel:'Pocket universe menu',title:'Pocket universe options',frame:'How you see the whole pocket universe.',diaryHref:'/beast-cage#zeref-diary',reset:'Reset 3D camera'}
});
export const SHARED_LABELS=Object.freeze({
 reset:'Reset 3D camera',resetAria:'Reset 3D pocket camera',diary:name=>(name||'Your beast')+'’s Diary',
 senses:'Senses (camera & mic)',look:'Look Closer',sensesNote:'Camera and microphone start only when you tap them yourself, in the Workshop (Settings → Senses). Nothing here turns them on.'
});
export function viewOptionsFor({hasBeast}){return VIEW_OPTIONS.filter(o=>hasBeast||!o.needsBeast);}
/** A visitor without a saved beast has no living world: that choice falls back to the pocket explorer (never a blank view). */
export function normalizeView(v,{hasBeast}){
 if(v==='classic'||v==='pocket')return v;
 if(v==='world')return hasBeast?'world':'pocket';
 return hasBeast?'world':'pocket';
}
export function readView(storage,{hasBeast}){let raw=null;try{raw=storage?.getItem?.(VIEW_STORAGE)??null;}catch{}return normalizeView(raw,{hasBeast});}
export function writeView(storage,v){if(!VIEW_OPTIONS.some(o=>o.id===v))return false;try{storage?.setItem?.(VIEW_STORAGE,v);return true;}catch{return false;}}
/** The pixel-sprite flag the pocket scene already uses is derived from the view so the two switches can never disagree. */
export function pixelFlagForView(v){return v==='classic';}
export function viewForPixelFlag(on,current){if(on)return 'classic';return current==='classic'?'pocket':current;}
/** Which overlay the creature layer may draw. The 2D sprite is NEVER an overlay unless the visitor chose the classic view. */
export function overlayFor(view,{rigAvailable}){
 if(view==='classic')return 'sprite';
 if(view==='pocket'&&rigAvailable)return 'rig';
 return 'none';
}
/** Menu sections in order. `place` and `tools` are filled by the scene (portal hosts), the rest are plain. */
export const MENU_SECTIONS=Object.freeze(['view','place','tools','diary','senses','about']);
export function menuModel(ctxKey,{hasBeast,beastName}){
 const ctx=CONTEXTS[ctxKey]||CONTEXTS.cage;
 return {ctx,views:viewOptionsFor({hasBeast}),reset:{label:SHARED_LABELS.reset,aria:SHARED_LABELS.resetAria},
  diary:{label:SHARED_LABELS.diary(beastName),href:ctx.diaryHref},senses:{label:SHARED_LABELS.senses,note:SHARED_LABELS.sensesNote,href:'/workspace#senses'},look:{label:SHARED_LABELS.look,href:hasBeast?'/beast-cage/look':'/beast-cage/look?with=zeref'},sections:MENU_SECTIONS};
}
