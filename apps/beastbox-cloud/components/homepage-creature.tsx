'use client';
import {useEffect,useState} from 'react';
import {createPortal} from 'react-dom';
import Link from 'next/link';
import CosmicCompanion3D from './cosmic-companion-3d';
import ZerefMoonwraith from './zeref-moonwraith';
import ZerefSprite3D from './zeref-sprite-3d';
import BeastHero3D from './beast-hero-3d';
import ZerefLatestThought from './zeref-latest-thought';
import {useCompanion} from './companion-provider';
import {useBeastSession} from './beast-session';
import {shownName} from '../lib/companion/session.mjs';
import {visualStateFromBeast} from '../lib/companion/creature-visual-state.mjs';
import {ZEREF_PROFILE,ZEREF_RECORDED_SOURCE} from '../lib/zeref/zeref-mind.mjs';
import styles from './homepage-creature.module.css';

type View='zeref'|'model'|'zeref3d';

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
 // Oct 25: the View chip folds into the one pocket menu (About section) once that menu is on the page; the old floating chip stays as the fallback.
 const [menuHost,setMenuHost]=useState<HTMLElement|null>(null);
 useEffect(()=>{let n=0,t=0;const find=()=>{const h=document.querySelector('[data-world-menu-sheet="home"] [data-menu-host="about"]') as HTMLElement|null;if(h)setMenuHost(h);else if(n++<40)t=window.setTimeout(find,250);};find();return()=>window.clearTimeout(t);},[]);
 const [view,setView]=useState<View>('zeref3d');
 const [savedView,setSavedView]=useState<'mine'|'zeref'>('mine');
 const [line,setLine]=useState(''),[zMood,setZMood]=useState('content');
 const activeName=savedBeast?shownName(savedBeast):'';
 const waveMood=waved?'observing':'idle';
 const showZeref=genome?savedView==='zeref':view==='zeref';
 const showDimensional=!genome&&view==='zeref3d';
 const zerefStats=ZEREF_PROFILE.stats;
 // Panels start collapsed on phones so nothing covers the creature; always reopenable.
 const [cardOpen,setCardOpen]=useState(true);
 useEffect(()=>{if(window.matchMedia('(max-width:560px)').matches)setCardOpen(false);},[]);
 const turn=spin?undefined:(angle??0);
 return <div className="cosmos-home-hero" aria-label="Interactive cosmic companion observatory" data-home-view={showZeref?'zeref':showDimensional?'zeref-3d':genome?'my-beast':'3d-model'}>
  {showDimensional?<ZerefSprite3D embed greet={greet} autoRotate={angle===null} turntable={spin} turntableAngle={angle}/>:showZeref?<div className={'cosmos-zeref-turn'+(spin?' is-spinning':'')} data-zeref-turn={spin?'spin':String(turn)} style={spin?undefined:{transform:'rotateY('+turn+'deg)'}}><ZerefMoonwraith greet={greet} showCaption={false} onMood={mood=>{setLine(mood.line);setZMood(mood.mood);}}/></div>:
  genome?<><span className="cosmos-home-nobillboard" data-home-active-billboard="removed" aria-hidden="true"/><BeastHero3D genome={genome as any} label={activeName+' in 3D'}/></>:<CosmicCompanion3D quality="low" profile={showDimensional?null:profile}
   dimensionalId={showDimensional?ZEREF_PROFILE.id:null}
   preferSprite={false} spriteGenome={genome}
   spriteStage={savedBeast?.nativeStage||savedBeast?.stage||1}
   spriteName={activeName}
   state={genome?visualStateFromBeast(savedBeast):waveMood}
   speaking={false}
   spriteId={savedBeast?.qbeast?.profile?.id||''}
   look={profile?.baseLook??'nebula'}
   label={showDimensional?'Artistic 3D Moonwraith '+ZEREF_PROFILE.id+' · not saved Zeref':genome?activeName+' · QBEAST '+savedBeast.qbeast.profile.id:'Original procedural cosmic dragon workshop guide'}
   turntable={spin} turntableAngle={angle}/>}
  {/* Cory (Oct 15): the big round flower billboard of the active Beast is removed from the home pocket. */}
  <details className={styles.bubble+' cosmos-home-card'} open={cardOpen} onToggle={e=>setCardOpen((e.currentTarget as HTMLDetailsElement).open)}><summary className="cosmos-home-cardsum" aria-label={cardOpen?'Minimize card':'Open card'}>{cardOpen?'–':'✦ Hi!'}</summary><div role="status" aria-live="polite">
   {genome?<><strong>✦ YOUR BEAST IS HERE</strong>
    <p>{activeName} · the same QBEAST you saved on this device.</p>
    <small>QBEAST {savedBeast.qbeast.profile.id}</small>
    <p className={styles.stats}>XP {Number(savedBeast.xp)||0} · Bond {Number(savedBeast.bond)||0} · Energy {Number(savedBeast.energy)||0}</p>
    <Link href="/beast-cage#habitat">Visit {activeName} →</Link>
    {showZeref?<small>Showing Zeref, the site guide. Your Beast&apos;s identity is unchanged.</small>:null}
   </>:showZeref?<><strong>✦ ZEREF · MOONWRAITH · <span data-zeref-mood>{zMood.toUpperCase()}</span></strong>
    <p>{line||'*soft moon-purr* I\u2019m right here.'}</p>
    <ZerefLatestThought className={styles.thought}/>
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
  </div></details>
  {menuHost?createPortal(<div className="cosmos-menu-controls" data-home-view-controls><h4>{genome?'Who appears in the observatory':'How the guide turns'}</h4>
  <div className="cosmos-home-controls" aria-label={genome?'Choose who appears in the observatory':'Guide view and real 3D rotation controls'}>
   {genome?<>
    <button type="button" aria-pressed={savedView==='mine'} onClick={()=>setSavedView('mine')}>My Beast</button>
    <button type="button" aria-pressed={savedView==='zeref'} onClick={()=>setSavedView('zeref')}>Zeref</button>
   </>:<>
    {/* Cory (Oct 14): home shows only the real 3D Zeref; the flat sprite and the classic puff guide stay in the Cage/turntable. */}
    {<>
     <button type="button" aria-pressed={spin} onClick={()=>{setSpin(x=>!x);setAngle(null);}}>Rotate 360°</button>
     <button type="button" onClick={()=>{setSpin(false);setAngle(0);}}>Front</button>
     <button type="button" onClick={()=>{setSpin(false);setAngle(90);}}>Side</button>
     <button type="button" onClick={()=>{setSpin(false);setAngle(180);}}>Back</button>
    </>}
   </>}
  </div>
  </div>,menuHost):<details className="cosmos-home-viewmenu"><summary aria-label="View options">⚙ View</summary>
  <div className="cosmos-home-controls" aria-label={genome?'Choose who appears in the observatory':'Guide view and real 3D rotation controls'}>
   {genome?<>
    <button type="button" aria-pressed={savedView==='mine'} onClick={()=>setSavedView('mine')}>My Beast</button>
    <button type="button" aria-pressed={savedView==='zeref'} onClick={()=>setSavedView('zeref')}>Zeref</button>
   </>:<>
    {/* Cory (Oct 14): home shows only the real 3D Zeref; the flat sprite and the classic puff guide stay in the Cage/turntable. */}
    {<>
     <button type="button" aria-pressed={spin} onClick={()=>{setSpin(x=>!x);setAngle(null);}}>Rotate 360°</button>
     <button type="button" onClick={()=>{setSpin(false);setAngle(0);}}>Front</button>
     <button type="button" onClick={()=>{setSpin(false);setAngle(90);}}>Side</button>
     <button type="button" onClick={()=>{setSpin(false);setAngle(180);}}>Back</button>
    </>}
   </>}
  </div>
  </details>}
 </div>;
}
