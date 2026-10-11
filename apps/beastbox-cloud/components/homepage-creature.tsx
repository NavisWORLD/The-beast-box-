'use client';
import {useState} from 'react';
import Link from 'next/link';
import CosmicCompanion3D from './cosmic-companion-3d';
import ZerefMoonwraith from './zeref-moonwraith';
import {useCompanion} from './companion-provider';
import {useBeastSession} from './beast-session';
import {shownName} from '../lib/companion/session.mjs';
import {visualStateFromBeast} from '../lib/companion/creature-visual-state.mjs';
import {ZEREF_PROFILE,ZEREF_RECORDED_SOURCE} from '../lib/zeref/zeref-mind.mjs';
import styles from './homepage-creature.module.css';

type View='zeref'|'model';

/**
 * The workshop guide is a preview, not a second QBEAST. Once a player has a
 * verified QBEAST the actual saved genome/ID/mood replace that preview.
 * Without one, the guide is ZEREF the Moonwraith (live vector rig); the
 * original procedural 3D guide stays one tap away under "3D model".
 */
export default function HomepageCreature(){
 const {profile}=useCompanion();
 const {session}=useBeastSession();
 const savedBeast=session?.beast?.qbeast?.profile?.id?session.beast:null;
 const genome=savedBeast?.genome?.seed?savedBeast.genome:null;
 const [spin,setSpin]=useState(false),[angle,setAngle]=useState<number|null>(null);
 const [waved,setWaved]=useState(false),[greet,setGreet]=useState(0);
 const [view,setView]=useState<View>('zeref');
 const [savedView,setSavedView]=useState<'mine'|'zeref'>('mine');
 const [line,setLine]=useState(''),[zMood,setZMood]=useState('content');
 const activeName=savedBeast?shownName(savedBeast):'';
 const waveMood=waved?'observing':'idle';
 const showZeref=genome?savedView==='zeref':view==='zeref';
 const zerefStats=ZEREF_PROFILE.stats;
 return <div className="cosmos-home-hero" aria-label="Interactive cosmic companion observatory" data-home-view={showZeref?'zeref':genome?'my-beast':'3d-model'}>
  {showZeref?<ZerefMoonwraith greet={greet} showCaption={false} onMood={mood=>{setLine(mood.line);setZMood(mood.mood);}}/>:
  <CosmicCompanion3D quality="low" profile={profile}
   preferSprite={Boolean(genome)} spriteGenome={genome}
   spriteStage={savedBeast?.nativeStage||savedBeast?.stage||1}
   spriteName={activeName}
   state={genome?visualStateFromBeast(savedBeast):waveMood}
   spriteId={savedBeast?.qbeast?.profile?.id||''}
   look={profile?.baseLook??'nebula'}
   label={genome?activeName+' · QBEAST '+savedBeast.qbeast.profile.id:'Original procedural cosmic dragon workshop guide'}
   turntable={spin} turntableAngle={angle}/>}
  <div className={styles.bubble} role="status" aria-live="polite">
   {genome?<><strong>✦ YOUR BEAST IS HERE</strong>
    <p>{activeName} · the same QBEAST you saved on this device.</p>
    <small>QBEAST {savedBeast.qbeast.profile.id}</small>
    <p className={styles.stats}>XP {Number(savedBeast.xp)||0} · Bond {Number(savedBeast.bond)||0} · Energy {Number(savedBeast.energy)||0}</p>
    <Link href="/beast-cage#habitat">Visit {activeName} →</Link>
    {showZeref?<small>Showing Zeref, the site guide. Your Beast&apos;s identity is unchanged.</small>:null}
   </>:showZeref?<><strong>✦ ZEREF · MOONWRAITH · <span data-zeref-mood>{zMood.toUpperCase()}</span></strong>
    <p>{line||'*soft moon-purr* I\u2019m right here.'}</p>
    <div className={styles.actions}>
     <button type="button" aria-pressed={waved} onClick={()=>{setWaved(value=>!value);setGreet(value=>value+1);}}>{waved?'Wave again ✦':'Wave hello ✦'}</button>
     <a href="/spark/index.html">Meet your Beast →</a>
    </div>
    <p className={styles.stats+' '+styles.zerefStats}>Zeref&apos;s profile · QBEAST {ZEREF_PROFILE.id} · Energy {zerefStats.energy} · Signal {zerefStats.signal} · Memory {zerefStats.memory} · Resonance {zerefStats.resonance}</p>
    <small>Tap to play, hold to pet. Moods: recorded IBM {ZEREF_RECORDED_SOURCE.backend} counts (job {ZEREF_RECORDED_SOURCE.job_id.slice(0,8)}…) + Zeref&apos;s stats + your taps, not a live quantum link. Guide reaction is visual only.</small>
   </>:<><strong>✦ HELLO FROM THE WORKSHOP</strong>
    <p>{waved?'Oh! A visitor waved. Want to meet a creature of your own?':'That little dragon noticed you. Curious what lives in here?'}</p>
    <div className={styles.actions}>
     <button type="button" aria-pressed={waved} onClick={()=>setWaved(value=>!value)}>{waved?'Wave again ✦':'Wave hello ✦'}</button>
     <a href="/spark/index.html">Meet your Beast →</a>
    </div>
    <small>Guide reaction is visual only. Your own Beast begins when you create one.</small>
   </>}
  </div>
  <div className="cosmos-home-controls" aria-label={genome?'Choose who appears in the observatory':'Guide view and real 3D rotation controls'}>
   {genome?<>
    <button type="button" aria-pressed={savedView==='mine'} onClick={()=>setSavedView('mine')}>My Beast</button>
    <button type="button" aria-pressed={savedView==='zeref'} onClick={()=>setSavedView('zeref')}>Zeref</button>
   </>:<>
    <button type="button" aria-pressed={view==='zeref'} onClick={()=>{setView('zeref');setSpin(false);}}>Zeref</button>
    <button type="button" aria-pressed={view==='model'} onClick={()=>setView('model')}>3D model</button>
    {view==='model'?<>
     <button type="button" aria-pressed={spin} onClick={()=>{setSpin(x=>!x);setAngle(null);}}>Rotate 360°</button>
     <button type="button" onClick={()=>{setSpin(false);setAngle(0);}}>Front</button>
     <button type="button" onClick={()=>{setSpin(false);setAngle(90);}}>Side</button>
     <button type="button" onClick={()=>{setSpin(false);setAngle(180);}}>Back</button>
    </>:null}
   </>}
  </div>
 </div>;
}
