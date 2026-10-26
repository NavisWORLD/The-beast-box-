'use client';
// The "Creature" switch (Cory, Oct 26 2026). Sits in the cage's Details row on the home page and on the Beast Cage page.
// ON (default) = the beast stands in the open scene. OFF = the universe alone; the beast is still there and still alive.
// Same saved choice and same words as the dock's "Show {beast}" row. Display only.
import {useActiveBeastName} from './use-active-beast-name';
import {useCreations} from './use-creations';
import {useCageCreature} from './use-cage-creature';
import {cageCreatureWords} from '../lib/world/cage-creature.mjs';
export default function CageCreatureSwitch({context}:{context:'home'|'cage'}){
 const name=useActiveBeastName();const short=((name||'').split(/\s+·\s+/)[0]||'').trim()||'Your beast';
 const [on,set]=useCageCreature();const neighbors=useCreations().filter(r=>r.kind!=='active').length;const w=cageCreatureWords(short);
 return <div className="cage-creature-switch" data-cage-creature-switch={context} data-on={on}>
  <button type="button" role="switch" aria-checked={on} aria-label={on?w.ariaOn:w.ariaOff} title={w.note} onClick={()=>set(!on)}>
   <span className="ccs-track" aria-hidden="true"><i/></span><span className="ccs-word">{w.switchLabel}</span></button>
  <span className="ccs-state" role="status">{on?w.stateOn:w.stateOff}</span>
  {neighbors>0?<span className="ccs-cap">{neighbors===1?'1 neighbor lives here.':neighbors+' neighbors live here.'}</span>:null}
 </div>;
}
