'use client';
import {useEffect,useRef,useState} from 'react';
import {
 FAMILIES,STAT_NAMES,generateCreature,pickAmbientAction,validCreature,
 type AmbientAction,type CreatureProfile,type Family
} from '../lib/creature-profile';
import css from './genesis-forge.module.css';

const KEY='beastbox-genesis-v1-saved-game-characters';
const MAX_SAVES=8;
/**
 * Guest-safe game character generator. Saved browser characters are not a
 * model, server-side COSMOS identity, memory or permission grant.
 */
export default function GenesisForge({
 value,onChange,onAmbient
}:{
 value:CreatureProfile|null;
 onChange:(creature:CreatureProfile)=>void;
 onAmbient?:(action:AmbientAction)=>void;
}){
 const [seed,setSeed]=useState('cosmos-first-contact');
 const [family,setFamily]=useState<Family|'surprise'>('surprise');
 const [saved,setSaved]=useState<CreatureProfile[]>([]);
 const [action,setAction]=useState<AmbientAction>('hover');
 const [message,setMessage]=useState('');
 const [error,setError]=useState('');
 const tick=useRef(0);
 useEffect(()=>{
  if(value&&validCreature(value))window.dispatchEvent(new CustomEvent('beastbox:genesis-selected',{detail:value}));
 },[value]);
 useEffect(()=>{
  try{
   const item=JSON.parse(localStorage.getItem(KEY)??'[]');
   if(Array.isArray(item))setSaved(item.filter(validCreature).slice(0,MAX_SAVES));
  }catch{/* Private browsing: continue without local saved characters. */}
 },[]);
 function roll(input:string,choice:Family|'surprise'=family){
  try{
   const creature=generateCreature(input,choice==='surprise'?undefined:choice);
   onChange(creature);setError('');setMessage('Generated from a classical, reproducible seed.');
   setAction('hover');tick.current=0;
  }catch(e){setError(e instanceof Error?e.message:'Invalid seed.');}
 }
 function randomBirth(){
  const bytes=new Uint32Array(2);
  if(!globalThis.crypto?.getRandomValues){setError('Secure browser randomness is unavailable; enter a seed manually.');return;}
  globalThis.crypto.getRandomValues(bytes);
  const next=Array.from(bytes,x=>x.toString(16).padStart(8,'0')).join('');
  setSeed(next);roll(next);
 }
 function save(){
  if(!value||!validCreature(value)){setError('Generate a valid character first.');return;}
  const remaining=saved.filter(x=>x.id!==value.id);
  if(remaining.length>=MAX_SAVES){
   setError('Eight game characters are already saved here. Delete one explicitly before saving another.');
   return;
  }
  const next=[value,...remaining];
  try{
   localStorage.setItem(KEY,JSON.stringify(next));setSaved(next);
   setMessage('Saved this game-only character on this device. No COSMOS records were changed.');
  }catch{setError('Browser storage is unavailable. You can still export a game pack.');}
 }
 function remove(id:string){
  const next=saved.filter(x=>x.id!==id);
  try{localStorage.setItem(KEY,JSON.stringify(next));setSaved(next);setMessage('Local game character deleted.');}
  catch{setError('Could not update this browser’s storage.');}
 }
 function explore(){
  if(!value)return;
  const next=pickAmbientAction(value,tick.current++);
  setAction(next);onAmbient?.(next);
  window.dispatchEvent(new CustomEvent('beastbox:ambient-action',{detail:next}));
 }
 return <section className={css.forge} aria-label="Genesis Forge procedural character generator">
  <div className={css.heading}>
   <span className={css.overline}>✧ THE GENESIS FORGE · CLASSICAL PROCEDURAL GENERATION</span>
   <h2>Every little monster <em>gets its own stars.</em></h2>
   <p>Generate a reproducible game character with original cosmic styling, a
    personality and balanced GBA statistics. These are fictional gameplay
    attributes, not COSMOS memory or intelligence measurements.</p>
  </div>
  <div className={css.creator}>
   <label>Character seed
    <input value={seed} maxLength={64} aria-label="Character seed"
      onChange={e=>setSeed(e.target.value)} placeholder="Choose a seed" />
   </label>
   <label>Cosmic family
    <select value={family} aria-label="Cosmic family"
      onChange={e=>setFamily(e.target.value as Family|'surprise')}>
     <option value="surprise">Surprise me</option>
     {FAMILIES.map(item=><option key={item} value={item}>{item[0].toUpperCase()+item.slice(1)}</option>)}
    </select>
   </label>
   <button type="button" onClick={()=>roll(seed)} className={css.primary}>Generate from this seed</button>
   <button type="button" onClick={randomBirth} className={css.outline}>Random birth ✧</button>
  </div>
  {value&&<div className={css.profile} aria-label="Generated game character details">
   <div className={css.identity}>
    <span className={css.overline}>CREATURE // {value.id.toUpperCase()}</span>
    <h3>{value.name}</h3>
    <p>{value.family.toUpperCase()} · Level {value.game.level} · Game-only character</p>
    <fieldset className={css.appearance}><legend>Fine-tune this creature's original genome</legend>
     <label>Color shift <output>{value.appearance.hueShift}°</output>
      <input type="range" min={-127} max={127} step={1} value={value.appearance.hueShift}
       aria-label="Creature color shift"
       onChange={event=>onChange({...value,appearance:{...value.appearance,hueShift:Number(event.target.value)}})} />
     </label>
     <label>Galaxy glow <output>{value.appearance.glow}%</output>
      <input type="range" min={40} max={100} step={1} value={value.appearance.glow}
       aria-label="Creature glow"
       onChange={event=>onChange({...value,appearance:{...value.appearance,glow:Number(event.target.value)}})} />
     </label>
     <p>Cosmetic edits preserve the same generated fictional game stats.</p>
    </fieldset>
    <div className={css.chips}>
     <span>✧ Glow {value.appearance.glow}</span>
     <span>◈ Halo {value.appearance.haloPattern+1}</span>
     <span>◇ Cosmic variation {value.appearance.constellation}</span>
    </div>
    <button type="button" onClick={explore} className={css.outline}>Let it explore</button>
    <p className={css.ambient}>Ambient animation choice: {action}. Classical seeded
     behavior, not measured sensor activity.</p>
    <button type="button" onClick={save} className={css.outline}>Save game character on this device</button>
   </div>
   <div aria-label="Balanced fictional game stats" className={css.stats}>
    <strong>GBA · CHARACTER STATS <span>500 / 500 POINTS</span></strong>
    <dl>{STAT_NAMES.map(key=><div key={key} className={css.stat}>
      <dt>{key==='hp'?'HP':key.replace(/^\w/,c=>c.toUpperCase())}</dt>
      <dd>{value.game.stats[key]}</dd>
      <meter min="20" max="80" value={value.game.stats[key]} aria-label={key+' fictional points'}/>
     </div>)}</dl>
   </div>
  </div>}
  {saved.length>0&&<div className={css.collection} aria-label="Saved browser-only game characters">
   <strong>Your little constellation ({saved.length}/{MAX_SAVES})</strong>
   <div>{saved.map(item=><span key={item.id} className={css.saved}>
    <button type="button" onClick={()=>{setSeed(item.seed);setFamily(item.family);onChange(item);setMessage('Loaded a game-only browser save.');}}>
      Select {item.name}
    </button>
    <button type="button" onClick={()=>remove(item.id)} aria-label={'Delete browser save for '+item.name}>×</button>
   </span>)}</div>
  </div>}
  {error&&<p role="alert" className={css.error}>{error}</p>}
  {message&&<p role="status" className={css.notice}>{message}</p>}
  <small>No cloud inference, real sensors, quantum hardware or owner permissions are
   required. Optional save stays in this browser; use the ZIP to move your game character.</small>
 </section>;
}
