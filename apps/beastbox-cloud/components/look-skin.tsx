'use client';
import {useEffect} from 'react';
import {currentLook,LOOK_EVENT,LOOK_KEY} from '../lib/look/look-mode';
/** Keeps html[data-look] in step with the saved look, so the Park site skin (app/park-skin.css) follows Settings and the in-world Look button. Presentation only. */
export default function LookSkin(){
 useEffect(()=>{
  const sync=()=>{try{document.documentElement.setAttribute('data-look',currentLook());}catch{}};
  const onStore=(e:StorageEvent)=>{if(e.key===null||e.key===LOOK_KEY)sync();};
  sync();window.addEventListener(LOOK_EVENT,sync);window.addEventListener('storage',onStore);
  return()=>{window.removeEventListener(LOOK_EVENT,sync);window.removeEventListener('storage',onStore);};
 },[]);
 return null;
}
