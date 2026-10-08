'use client';
import {useEffect,useState} from 'react';
import {usePathname} from 'next/navigation';
import {Music2,Volume2,VolumeX,X} from 'lucide-react';
import {useBeastAudio} from './use-beast-audio';
import styles from './site-sound-dock.module.css';

const ROOMS:Record<string,{seedKey:string;element:string;temperament:string}>={
 home:{seedKey:'cosmos-workshop',element:'starlight',temperament:'Curious'},
 cage:{seedKey:'cage-doorway',element:'nebula',temperament:'Calm'},
 game:{seedKey:'lost-cosmos-shell',element:'signal',temperament:'Focused'},
 lab:{seedKey:'cosmic-observatory',element:'aurora',temperament:'Calm'},
 workshop:{seedKey:'brain-workshop',element:'signal',temperament:'Curious'}
};
export default function SiteSoundDock(){
 const pathname=usePathname()||'/';
 const {audio,state}=useBeastAudio();
 const [open,setOpen]=useState(false);
 const soundOn=!state.sparkMuted;
 const audible=soundOn && state.contextState==='running' && state.unlocked;
 const room=pathname==='/'?'home':pathname.startsWith('/sol-game')?'game':pathname.startsWith('/beast-cage')?'cage':pathname.startsWith('/research')?'lab':'workshop';
 useEffect(()=>{
  if(state.sparkMuted)return;
  const scene=audio.getSnapshot().scene;
  // The actual habitat retains priority over generic website ambience.
  if(scene&&scene.id!=='cosmos-world-ambience')return;
  audio.setScene({id:'cosmos-world-ambience',...ROOMS[room],enabled:true});
  return()=>audio.clearScene('cosmos-world-ambience');
 },[audio,room,state.sparkMuted]);
 function testChirp(){
  // Keep unlock and the first oscillator in this same trusted tap for Safari.
  if(!soundOn)audio.sparkUnmute();
  audio.unlock();
  audio.sfx('confirm',{element:ROOMS[room].element,seedKey:ROOMS[room].seedKey});
 }
 function toggle(){
  if(soundOn&&!audible){testChirp();return;}
  if(soundOn){audio.sparkMute();window.dispatchEvent(new Event('beastbox:spark-mute'));}
  else{
   audio.sparkUnmute();
   audio.unlock(); // a synchronous trusted gesture on iPhone Safari
   audio.sfx('confirm',{element:ROOMS[room].element,seedKey:ROOMS[room].seedKey});
   window.dispatchEvent(new Event('beastbox:spark-unmute'));
  }
 }
 return <aside className={styles.dock+(pathname.startsWith("/workspace")?" "+styles.workspace:"")} aria-label="Cosmic sound controls" data-site-sound={soundOn?'on':'off'}>
  <div className={styles.compact}>
   <button type="button" className={styles.main} onClick={toggle} aria-pressed={soundOn}
    aria-label={!soundOn?'Enable sound throughout Beast Box':!audible?'Activate Beast Box sound with a test chirp':'Mute the entire Beast Box site'}>
    {soundOn?<Volume2 size={19}/>:<VolumeX size={19}/>}<span>{!soundOn?'SOUND OFF':audible?'SOUND ON':'TAP FOR SOUND'}</span>
   </button>
   <button type="button" className={styles.settings} onClick={()=>setOpen(value=>!value)}
    aria-label={open?'Close sound options':'Open sound options'} aria-expanded={open} aria-controls="cosmos-sound-options">
    {open?<X size={18}/>:<Music2 size={18}/>}
   </button>
  </div>
  {open?<section id="cosmos-sound-options" className={styles.panel} aria-label="Sound options">
   <strong>✦ COSMIC SOUND</strong>
   <button type="button" className={styles.music} aria-label="Mute site sound" disabled={!soundOn}
    onClick={()=>{audio.sparkMute();window.dispatchEvent(new Event('beastbox:spark-mute'));}}>🔇 MUTE SOUND</button>
   <p role="status">{!soundOn?'Sound muted':state.hidden?'Audio paused in the background':state.audioError||(!state.unlocked?'Tap Test Chirp to unlock Safari audio':!audible?'Audio context is '+state.contextState+' · tap Test Chirp':'AudioContext running · ready to play')}. Original sounds are synthesized locally after your tap.</p>
   <label htmlFor="cosmos-master-volume">Volume · {Math.round(state.volume*100)}%</label>
   <input type="range" id="cosmos-master-volume" min="0" max="100" step="5" value={Math.round(state.volume*100)}
    onChange={event=>audio.setVolume(Number(event.target.value)/100)} aria-label="Beast Box music, creature and effect volume"/>
   <button type="button" className={styles.music} onClick={testChirp} aria-label="Test Beast Box sound with a short chirp">▶ TEST CHIRP</button>
   <button type="button" className={styles.music} disabled={!soundOn} aria-pressed={soundOn&&state.musicOn}
    aria-label={state.musicOn?'Pause cosmic background music':'Play cosmic background music'}
    onClick={()=>{audio.unlock();audio.setMusic(!state.musicOn);}}>
    <Music2 size={15}/>{state.musicOn?'Pause music':'Play music'}
   </button>
   <p className={styles.hint}>If the test is silent on iPhone, check Silent Mode, media volume and the active Bluetooth/audio output. A visible ON switch is not proof a speaker played sound. The Game Boy has its own sound switch.</p>
  </section>:null}
 </aside>;
}
