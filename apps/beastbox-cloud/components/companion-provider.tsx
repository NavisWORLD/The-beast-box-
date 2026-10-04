'use client';
import {
 createContext,useCallback,useContext,useEffect,useMemo,useRef,useState,
 type ReactNode
} from 'react';
import {usePathname} from 'next/navigation';
import {Pause,Play,Eye,EyeOff,Volume2,VolumeX} from 'lucide-react';
import SparkBeastCompanion from './spark-beast-companion';
import LostCosmosDock from './lost-cosmos-dock';
import {BeastSessionProvider} from './beast-session';
import {
 pickAmbientAction,validCreature,type CreatureProfile,type AmbientAction
} from '../lib/creature-profile';
import {selectSafeRoamSpot,type Rect,type Spot} from '../lib/companion-roaming';
import {DRAGON_RUN_KEY,DRAGON_TRAITS} from '../lib/companion/pet-dragon.mjs';
import styles from './companion-provider.module.css';

type CompanionContextValue={
 profile:CreatureProfile|null;
 selectProfile:(candidate:CreatureProfile)=>void;
 clearProfile:()=>void;
};
const Context=createContext<CompanionContextValue|undefined>(undefined);
const ACTIVE_PROFILE_KEY='beastbox-active-creature-v1';
export function useCompanion(){
 const value=useContext(Context);
 if(!value)throw new Error('Companion context is unavailable');
 return value;
}
function editingText(){
 const active=document.activeElement;
 return active instanceof HTMLElement&&(
  active.matches('input,textarea,[contenteditable="true"]')||
  active.getAttribute('role')==='textbox'
 );
}
/**
 * Public GAME companion. Owns no sensors, memory, inference, execution, or
 * model authority or raw sensor media. Actual owner telemetry remains in the
 * existing owner dock. Its persistent React shell preserves only a validated
 * browser-local game profile and bounded roaming state across navigation.
 */
export default function CompanionProvider({children}:{children:ReactNode}){
 const pathname=usePathname();
 const [profile,setProfile]=useState<CreatureProfile|null>(null);
 const [action,setAction]=useState<AmbientAction>('hover');
 const [paused,setPaused]=useState(false),[hidden,setHidden]=useState(false);
 const [halted,setHalted]=useState(false),[typing,setTyping]=useState(false);
 const [soundEnabled,setSoundEnabled]=useState(false);
 const [reduced,setReduced]=useState(false),[spot,setSpot]=useState<Spot|null>(null);
 const [tick,setTick]=useState(0),tickRef=useRef(0);
 const [pageVisible,setPageVisible]=useState(true);
 const onProfile=useCallback((candidate:CreatureProfile)=>{
  if(!validCreature(candidate))return;
  setProfile(candidate);tickRef.current=0;setTick(0);
  setAction('hover');
  try{window.localStorage.setItem(ACTIVE_PROFILE_KEY,JSON.stringify(candidate));}catch{/* optional browser-only game profile */}
 },[]);
 useEffect(()=>{
  try{
   const raw=window.localStorage.getItem(ACTIVE_PROFILE_KEY);
   if(!raw)return;
   const candidate=JSON.parse(raw) as unknown;
   if(validCreature(candidate)){setProfile(candidate);setAction('hover');}
  }catch{/* private browsing or invalid local game profile: continue without persistence */}
 },[]);
 useEffect(()=>{
  const onSelected=(event:Event)=>{
   if(event instanceof CustomEvent)onProfile(event.detail);
  };
  const onAmbient=(event:Event)=>{
   if(!(event instanceof CustomEvent))return;
   const next=event.detail;
   if(next==='hover'||next==='orbit'||next==='perch'||next==='rest')setAction(next);
  };
  const onStop=()=>{setHalted(true);setPaused(true);setSoundEnabled(false);setAction('rest');};
  const onFocus=()=>setTyping(editingText());
  const onVisibility=()=>setPageVisible(!document.hidden);
  const motion=window.matchMedia('(prefers-reduced-motion: reduce)');
  const onMotion=()=>setReduced(motion.matches);
  onMotion();onVisibility();
  window.addEventListener('beastbox:genesis-selected',onSelected);
  window.addEventListener('beastbox:ambient-action',onAmbient);
  window.addEventListener('beastbox:master-privacy-stop',onStop);
  document.addEventListener('focusin',onFocus);
  document.addEventListener('focusout',onFocus);
  document.addEventListener('visibilitychange',onVisibility);
  motion.addEventListener('change',onMotion);
  return()=>{
   window.removeEventListener('beastbox:genesis-selected',onSelected);
   window.removeEventListener('beastbox:ambient-action',onAmbient);
   window.removeEventListener('beastbox:master-privacy-stop',onStop);
   document.removeEventListener('focusin',onFocus);
   document.removeEventListener('focusout',onFocus);
   document.removeEventListener('visibilitychange',onVisibility);
   motion.removeEventListener('change',onMotion);
  };
 },[onProfile]);
 const showPublic=pathname==='/'||pathname==='/beast-cage';
 useEffect(()=>{
  if(!showPublic||paused||halted||hidden||!pageVisible)return;
  const fallback:AmbientAction[]=['hover','orbit','perch','rest'];
  const clock=window.setInterval(()=>{
   const next=++tickRef.current;
   setTick(next);
   if(reduced)return;
   const nextAction=profile?pickAmbientAction(profile,next):fallback[next%fallback.length];
   setAction(nextAction);
   if(soundEnabled&&next%2===1){
    window.dispatchEvent(new CustomEvent('beastbox:spark-chirp',{
     detail:{channel:'roamer',intensity:nextAction==='orbit'?.9:.58}
    }));
   }
  },1600);
  return()=>window.clearInterval(clock);
 },[profile,showPublic,paused,halted,hidden,reduced,pageVisible,soundEnabled]);
 useEffect(()=>{
  if(!showPublic||hidden||typing||!pageVisible||reduced){setSpot(null);return;}
  let animation=0;
  const calculate=()=>{
   animation=0;
   if(editingText()){setSpot(null);return;}
   const viewport=window.visualViewport;
   const width=viewport?.width||window.innerWidth;
   const height=viewport?.height||window.innerHeight;
   // If the on-screen keyboard is consuming the viewport, park the avatar.
   if(height<window.innerHeight*.72){setSpot(null);return;}
   const avoid:Rect[]=[];
   const targets=document.querySelectorAll<HTMLElement>(
    'main h1, main h2, main h3, main p, main button, main a, main input, main textarea, [role="dialog"], [data-critical-control], aside[data-cosmos-mode="mini"], aside[data-cosmos-mode="full"]'
   );
   for(const element of targets){
    if(avoid.length>=160)break;
    if(element.closest('[data-companion-overlay]'))continue;
    const rect=element.getBoundingClientRect();
    if(rect.width<1||rect.height<1||rect.bottom<0||rect.top>height)continue;
    // The roaming Beast toolbar sits above and can be wider than the sprite.
    // Give the persistent cartridge dock a padded exclusion footprint so its
    // poster/actions never cover the Beast sound/pause/hide controls on mobile.
    if(element.matches('aside[data-cosmos-mode="mini"],aside[data-cosmos-mode="full"]')){
     const padX=width<680?84:54,padTop=width<680?64:44;
     const left=Math.max(0,rect.left-padX),top=Math.max(0,rect.top-padTop);
     avoid.push({left,top,width:Math.min(width-left,rect.width+padX),height:rect.height+padTop});
    }else{
     avoid.push({left:rect.left,top:rect.top,width:rect.width,height:rect.height});
    }
   }
   setSpot(selectSafeRoamSpot(width,height,avoid,tick));
  };
  const schedule=()=>{
   if(!animation)animation=window.requestAnimationFrame(calculate);
  };
  schedule();
  window.addEventListener('resize',schedule);
  window.addEventListener('scroll',schedule,{passive:true});
  window.visualViewport?.addEventListener('resize',schedule);
  return()=>{
   if(animation)window.cancelAnimationFrame(animation);
   window.removeEventListener('resize',schedule);
   window.removeEventListener('scroll',schedule);
   window.visualViewport?.removeEventListener('resize',schedule);
  };
 },[showPublic,hidden,typing,pageVisible,reduced,tick,pathname,profile]);
 const state=halted?'halted' as const:
  action==='rest'?'sleeping' as const:action==='orbit'?'celebrating' as const:
  action==='perch'?'observing' as const:'idle' as const;
 const clearProfile=useCallback(()=>{setProfile(null);setAction('hover');tickRef.current=0;setTick(0);try{window.localStorage.removeItem(ACTIVE_PROFILE_KEY);}catch{/* optional browser-only game profile */}},[]);
 const context=useMemo(()=>({profile,selectProfile:onProfile,clearProfile}),[profile,onProfile,clearProfile]);
 const toggleSound=()=>{
  setSoundEnabled(current=>{
   const next=!current;
   if(next){
    window.dispatchEvent(new CustomEvent('beastbox:spark-chirp',{detail:{channel:'roamer',intensity:.62}}));
   }
   return next;
  });
 };
 const canShow=showPublic&&!hidden&&!typing&&pageVisible&&!reduced&&spot!==null;
 const parked=halted||paused||!canShow;
 return <Context.Provider value={context}>
  <BeastSessionProvider>
  {children}
  <LostCosmosDock creature={profile} />
  </BeastSessionProvider>
  {showPublic?<aside data-companion-overlay="true" data-pet-dragon="true" className={styles.shell+(!canShow?' '+styles.parked:'')}
    aria-label="Pet dragon game habitat" data-companion-state={state}
    data-roaming={canShow&&!parked?'active':'parked'}
    style={canShow&&spot?{left:spot.left,top:spot.top,width:spot.width}:undefined}>
    <div className={styles.toolbar}>
     <button type="button" className={styles.control}
       onClick={()=>setHidden(x=>!x)} aria-label={hidden?'Show roaming companion':'Hide roaming companion'}>
      {hidden?<Eye size={15}/>:<EyeOff size={15}/>}
     </button>
     {!hidden?<button type="button" className={styles.control}
       onClick={()=>{
        if(halted){setHalted(false);setPaused(false);return;}
        setPaused(x=>!x);
       }}
       aria-label={halted?'Resume decorative companion only':paused?'Resume companion animation':'Pause companion animation'}>
      {parked?<Play size={15}/>:<Pause size={15}/>}
     </button>:null}
     {!hidden?<button type="button" className={styles.control} onClick={toggleSound}
       aria-pressed={soundEnabled}
       aria-label={soundEnabled?'Mute creature sounds':'Enable creature sounds'}>
      {soundEnabled?<Volume2 size={15}/>:<VolumeX size={15}/>}
     </button>:null}
    </div>
    {canShow?<div className={styles.figure} aria-hidden="true">
      <SparkBeastCompanion profile={profile} fallbackLook={profile?.baseLook??'nebula'}
       state={state} compact paused={parked||reduced} audioChannel="roamer"
       seedRunKey={DRAGON_RUN_KEY} seedTraits={DRAGON_TRAITS}
       label="Roaming pet dragon Spark Beast"/>
     </div>:null}
    <span className={styles.sr} aria-live="polite">
      {halted?'Decorative character stopped; backend permissions unchanged':
        'Classical seeded companion movement; not measured intelligence or live sensory input'}
    </span>
   </aside>:null}
 </Context.Provider>;
}
