'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {ArrowUpRight,AudioLines,BrainCircuit,Eye,LockKeyhole,Music2,Settings2,Sparkles,VolumeX} from 'lucide-react';
import UniverseRoomNav from './universe-room-nav';
import PixelBeast from './pixel-beast';
import {useBeastAudio} from './use-beast-audio';
import {useBeastSession} from './beast-session';
import {useUniverseMotion} from './use-universe-motion';
import {beastIdentity,shownName} from '../lib/companion/session.mjs';
import {DEFAULT_POCKET_3D,POCKET_3D_EVENT,POCKET_3D_KEY,readPocket3D,savePocket3D} from '../lib/companion/pocket-3d-settings.mjs';
import {publicBrainProvider} from '../lib/companion/public-brain-bay.mjs';
import styles from './universe-settings.module.css';

export default function UniverseSettings(){
 const {audio,state}=useBeastAudio();
 const {session}=useBeastSession();
 const motion=useUniverseMotion(),beast=session?.beast;
 const [notice,setNotice]=useState('');
 const [pocket3d,setPocket3d]=useState({...DEFAULT_POCKET_3D});
 useEffect(()=>{
  const sync=()=>{try{setPocket3d(readPocket3D(window.localStorage));}catch{setPocket3d({...DEFAULT_POCKET_3D});}};
  const changed=(event:StorageEvent)=>{if(event.key===POCKET_3D_KEY)sync();};
  sync();window.addEventListener('storage',changed);
  return()=>window.removeEventListener('storage',changed);
 },[]);
 function changePocket3D(next:{enabled:boolean;quality:string}){
  try{
   const saved=savePocket3D(window.localStorage,next);
   setPocket3d(saved);window.dispatchEvent(new Event(POCKET_3D_EVENT));
   setNotice('3D scenery preference saved on this device. Your Beast and game saves are unchanged.');
  }catch{setNotice('3D preference could not be saved; no creature or game state was changed.');}
 }
 const volume=Math.round(state.volume*100);
 function mute(){
  if(state.sparkMuted){audio.sparkUnmute();audio.unlock();window.dispatchEvent(new Event('beastbox:spark-unmute'));}
  else{audio.sparkMute();window.dispatchEvent(new Event('beastbox:spark-mute'));}
 }
 function setMotion(){
  const saved=motion.save(!motion.preference);
  setNotice(saved?'Motion preference saved on this device.':'Motion changed for this visit. This browser could not save the preference.');
 }
 return <main className={styles.room} data-reduced-motion={motion.reduced}>
  <UniverseRoomNav current="/settings"/>
  <section className={styles.intro}>
   <p className={styles.eyebrow}><Settings2 size={14} aria-hidden="true"/> MAKE THE UNIVERSE YOURS</p>
   <h1>A little quieter.<br/><em>A little calmer.</em></h1>
   <p>Simple controls for the whole website. Your Beast keeps its identity and story.</p>
  </section>
  <div className={styles.layout}>
   <div className={styles.controls}>
    <section className={styles.panel} aria-labelledby="sound-title">
     <div className={styles.sectionLabel}><span>01 / SOUND</span><AudioLines size={20} aria-hidden="true"/></div>
     <h2 id="sound-title">Set the atmosphere.</h2>
     <div className={styles.settingRow}><div className={styles.icon}><VolumeX size={19} aria-hidden="true"/></div><div><h3 id="mute-label">Mute website sound</h3><p>Music, creature sounds and website effects.</p></div><button type="button" role="switch" aria-checked={state.sparkMuted} aria-labelledby="mute-label" className={styles.toggle} onClick={mute}><span/></button></div>
     <div className={styles.settingRow}><div className={styles.icon}><Music2 size={19} aria-hidden="true"/></div><div><h3 id="music-label">Background music</h3><p>Keep the soundtrack on when sound is enabled.</p></div><button type="button" role="switch" aria-checked={state.musicOn} aria-labelledby="music-label" className={styles.toggle} onClick={()=>audio.setMusic(!state.musicOn)}><span/></button></div>
     <div className={styles.volume}><label htmlFor="website-volume">Website volume <output htmlFor="website-volume">{volume}%</output></label><input id="website-volume" type="range" min={0} max={100} step={1} value={volume} onChange={event=>audio.setVolume(Number(event.target.value)/100)}/><div aria-hidden="true"><span>SOFT</span><span>FULL</span></div></div>
     <p className={styles.hint}>Sound begins after your tap. The native Game Boy cartridge has its own sound switch.</p>
    </section>
    <section className={styles.panel} aria-labelledby="motion-title">
     <div className={styles.sectionLabel}><span>02 / MOTION</span><Sparkles size={20} aria-hidden="true"/></div>
     <h2 id="motion-title">Let things settle.</h2>
     <div className={styles.settingRow}><div className={styles.icon}><Eye size={19} aria-hidden="true"/></div><div><h3 id="motion-label">Reduce motion</h3><p>{motion.systemReduced?'Your operating system requests reduced motion.':'Keep the creature and room effects still.'}</p></div><button type="button" role="switch" aria-checked={motion.reduced} aria-labelledby="motion-label" className={styles.toggle} onClick={setMotion} disabled={motion.systemReduced}><span/></button></div>
     <p className={styles.hint}>Your operating system preference is always respected. This setting is saved on this device.</p>
     {notice&&<p className={styles.status} role="status">{notice}</p>}
    </section>
    <section className={styles.panel} aria-labelledby="pocket-3d-title">
     <div className={styles.sectionLabel}><span>03 / 3D WORLD</span><Eye size={20} aria-hidden="true"/></div>
     <h2 id="pocket-3d-title">Dimensional scenery.</h2>
     <div className={styles.settingRow}>
      <div className={styles.icon}><Sparkles size={19} aria-hidden="true"/></div>
      <div><h3 id="pocket-3d-label">Three.js pocket scenery</h3><p>Turn the 3D background on or off. Your original creature sprite, care, audio and native cartridge remain intact.</p></div>
      <button type="button" role="switch" aria-checked={pocket3d.enabled} aria-labelledby="pocket-3d-label" className={styles.toggle} onClick={()=>changePocket3D({...pocket3d,enabled:!pocket3d.enabled})}><span/></button>
     </div>
     <div className={styles.volume}>
      <label htmlFor="pocket-3d-quality">3D rendering quality</label>
      <select id="pocket-3d-quality" className={styles.qualitySelect} value={pocket3d.quality} onChange={event=>changePocket3D({...pocket3d,quality:event.target.value})} disabled={!pocket3d.enabled}>
       <option value="auto">Auto · adapts on mobile</option>
       <option value="low">Low · fewer effects</option>
       <option value="high">High · detailed scenery</option>
      </select>
     </div>
     <p className={styles.hint}>Your system reduced-motion choice always takes priority. These are local visual settings, not quantum or model settings, and they do not modify the native Game Boy ROM.</p>
     <div className={styles.advancedLinks}><Link href="/beast-cage#habitat"><Eye size={18} aria-hidden="true"/><span><strong>Open 3D Beast Cage</strong><small>Drag, pinch or use the arrow keys to orbit the existing world.</small></span><ArrowUpRight size={16} aria-hidden="true"/></Link><Link href="/beast-cage/turntable"><Sparkles size={18} aria-hidden="true"/><span><strong>Open original 3D turntable</strong><small>The existing Cursor-era character mesh and camera presets.</small></span><ArrowUpRight size={16} aria-hidden="true"/></Link></div>
    </section>
    <details className={styles.advanced}>
     <summary>Advanced rooms <span>OPEN WHEN YOU NEED THEM</span></summary>
     <div className={styles.advancedLinks}>
      <Link href="/brain-bay"><BrainCircuit size={20} aria-hidden="true"/><span><strong>Brain Bay</strong><small>Choose pattern, guest or explicit local Ollama.</small></span><ArrowUpRight size={16} aria-hidden="true"/></Link>
      <Link href="/beast-cage/talk"><Eye size={20} aria-hidden="true"/><span><strong>Sensors &amp; conversation</strong><small>Open the explicit camera and microphone controls.</small></span><ArrowUpRight size={16} aria-hidden="true"/></Link>
      <Link href="/workspace#settings"><LockKeyhole size={20} aria-hidden="true"/><span><strong>Owner workstation</strong><small>Existing credentials, provider and device controls.</small></span><ArrowUpRight size={16} aria-hidden="true"/></Link>
     </div>
    </details>
   </div>
   <aside className={styles.side}>
    <section className={styles.beastCard} aria-label="The same Beast">
     <div className={styles.sectionLabel}><span>YOUR COMPANION</span><span className={styles.localTag}>LOCAL</span></div>
     <div className={styles.portrait} data-motion={motion.reduced?'reduced':'full'}>{beast?.genome?<PixelBeast genome={beast.genome} publicSpark={Boolean(beast.qbeast)} stage={beast.qbeast?beast.nativeStage||1:beast.stage||1} reduced={motion.reduced} label={`${shownName(beast)}, your selected Beast`}/>:<Sparkles size={70} strokeWidth={1} aria-hidden="true"/>}</div>
     <h2>{beast?shownName(beast):'Your Beast belongs here'}</h2>
     {beast?<><code title={beastIdentity(beast)||''}>{beastIdentity(beast)}</code><p>One shared local session across your rooms.</p><span className={styles.provider}>Brain choice · {publicBrainProvider(session)==='local-mind'?'On-device pattern':publicBrainProvider(session)==='guest-rawrphos'?'RAWRPHØS guest':'Local Ollama'}</span></>:<><p>Labeled preview · no Beast selected.</p><a href="/spark/index.html" className={styles.meet}>Meet a Beast <ArrowUpRight size={14} aria-hidden="true"/></a></>}
    </section>
    <section className={styles.notes}>
     <span>YOUR SPACE, YOUR CHOICE</span>
     <p>These controls change sound and motion. Camera, microphone and model connections require their own explicit action.</p>
     <p>Your local Beast history stays in this browser. Owner credentials stay in the owner workstation.</p>
     <Link href="/research">Read the research receipts <ArrowUpRight size={14} aria-hidden="true"/></Link>
    </section>
   </aside>
  </div>
 </main>;
}
