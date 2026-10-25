'use client';
// One shared view state for Living world / Pocket explorer / Classic pixel sprite: the cage, the home pocket and the menu all read
// and write the same saved choice, and the pocket scene's own classic-pixel flag is kept in step (they can never disagree).
import {useCallback,useEffect,useState} from 'react';
import {VIEW_EVENT,readView,writeView,pixelFlagForView,viewForPixelFlag,normalizeView,type ViewId} from '../lib/world/world-options.mjs';
import {deviceClassicPixel,saveClassicPixel} from '../lib/companion/pocket-3d-settings.mjs';
export default function useWorldView(hasBeast:boolean,opts:{pixelSync?:boolean}={}){
 const pixelSync=opts.pixelSync!==false;
 const [view,setViewState]=useState<ViewId>(()=>normalizeView(null,{hasBeast}));
 useEffect(()=>{
  const sync=()=>{
   let v=readView(window.localStorage,{hasBeast});
   // the pocket's own ▦ toggle writes the pixel flag; honour it so both switches agree
   if(pixelSync&&deviceClassicPixel()&&v!=='classic')v='classic';
   setViewState(v);
  };
  sync();
  const onPixel=()=>{if(pixelSync)setViewState(cur=>viewForPixelFlag(deviceClassicPixel(),cur));};
  window.addEventListener(VIEW_EVENT,sync);window.addEventListener('beastbox:pixel-mode',onPixel);
  return()=>{window.removeEventListener(VIEW_EVENT,sync);window.removeEventListener('beastbox:pixel-mode',onPixel);};
 },[hasBeast,pixelSync]);
 const setView=useCallback((next:ViewId)=>{
  const v=normalizeView(next,{hasBeast});
  setViewState(v);writeView(window.localStorage,v);
  const px=pixelFlagForView(v);
  if(pixelSync&&deviceClassicPixel()!==px){saveClassicPixel(px);window.dispatchEvent(new Event('beastbox:pixel-mode'));}
  window.dispatchEvent(new Event(VIEW_EVENT));
 },[hasBeast,pixelSync]);
 return {view:normalizeView(view,{hasBeast}),setView};
}
