'use client';
import Link from 'next/link';
import {useEffect,useState} from 'react';
import {useBeastSession} from './beast-session';
import {createTrail} from '../lib/companion/adventure.mjs';
import {environmentFor,PLACES,encourageCurrentBehavior} from '../lib/companion/behavior.mjs';
import {shownName} from '../lib/companion/session.mjs';
import styles from './creature-habitat.module.css';
const names:Record<string,string>={grove:'Starlit grove',nest:'Cozy nest',shore:'Quiet shore',observatory:'Observatory'};
export default function CreatureHabitat(){
 const {session,trail,change,setTrail,storageStatus}=useBeastSession(),beast=session?.beast,core=beast?.behavior;
 const [environment,setEnvironment]=useState(environmentFor()),[paused,setPaused]=useState(false),[note,setNote]=useState('');
 useEffect(()=>{setEnvironment(environmentFor({place:trail.place}));try{setPaused(localStorage.getItem('beastbox-behavior-paused-v1')==='true');}catch{}},[beast?.seed]);
 function stimulus(input:any){const next=environmentFor(input);setEnvironment(next);if(next.place!==trail.place)setTrail(createTrail(next.place));window.dispatchEvent(new CustomEvent('beastbox:environment',{detail:next}));}
 function toggle(){try{localStorage.setItem('beastbox-behavior-paused-v1',String(!paused));setPaused(!paused);setNote(paused?'Back to investigating.':'Taking a quiet pause. Your Beast stays saved.');}catch{setNote('The pause setting could not be saved.');}}
 async function encourage(){const saved=await change(draft=>{const result=encourageCurrentBehavior(draft);if(!result.ok)throw Error(result.reason);});setNote(saved.ok?'Encouragement remembered on this device.':saved.reason||'Encouragement could not be saved.');}
 if(!beast)return null;
 return <section className={styles.habitat} data-creature-habitat data-creature-id={beast.qbeast?.profile?.id||beast.seed} aria-labelledby="habitat-activity-title">
  <p className={styles.tag}>A LITTLE WORLD TO INVESTIGATE</p><h2 id="habitat-activity-title">What caught {shownName(beast)}’s eye?</h2>
  <p>Change the room. Their inherited traits, needs and remembered outcomes shape the next activity.</p>
  <div className={styles.places}>{PLACES.map(place=><button type="button" key={place} aria-pressed={environment.place===place} onClick={()=>stimulus({...environment,place})}>{names[place]}</button>)}</div>
  <div className={styles.tools}>
   <button type="button" aria-pressed={environment.toy>0} onClick={()=>stimulus({...environment,toy:environment.toy?0:1})}>{environment.toy?'Put star toy away':'Offer a floating star toy'}</button>
   <button type="button" aria-pressed={environment.sound>0} onClick={()=>stimulus({...environment,sound:environment.sound?0:.8})}>{environment.sound?'Quiet the room':'Try a simulated signal'}</button>
   <button type="button" aria-pressed={paused} onClick={toggle}>{paused?'Resume activity':'Pause activity'}</button>
   <button type="button" disabled={!core?.events?.length} onClick={()=>void encourage()}>Encourage {core?.lastAction||'activity'}</button>
  </div>
  <div className={styles.activity}><span><strong>{paused?'paused':core?.lastAction||'getting settled'}</strong>{core?` · Behavior energy ${Math.round(core.energy)} / 100`:''}</span>{core&&<meter min={0} max={100} value={core.energy} aria-label={`${shownName(beast)} behavior energy`}/>}<Link href="/research#god-core">Peek under the magic →</Link></div>
  <p className={styles.note} role="status">{note||storageStatus}. Room inputs are local simulations. No microphone is being used here.</p>
 </section>;
}
