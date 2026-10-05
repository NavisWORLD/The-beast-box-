'use client';
import {Bluetooth,BluetoothOff,BatteryMedium} from 'lucide-react';
import {BANDS,MUSE_LABEL} from '../lib/companion/muse-pair.mjs';
import {useMusePair} from './use-muse-pair';
import css from './muse-pair-panel.module.css';

const BAND_LABEL:Record<string,string>={delta:'Delta',theta:'Theta',alpha:'Alpha',beta:'Beta',gamma:'Gamma'};
const MOOD_TEXT:Record<string,string>={idle:'settling',calm:'calm',focused:'focused',sparky:'sparky',drowsy:'drowsy'};

/** Pair Muse: Web Bluetooth link to a Muse 2 / Muse S. Soft consumer EEG for play only. */
export default function MusePairPanel({id,title='Pair Muse'}:{id?:string;title?:string}){
 const {muse,state}=useMusePair();
 const connected=state.status==='connected';
 const busy=state.status==='connecting';
 const bands=state.bands as Record<string,number>;
 return <section className={css.panel} id={id} aria-label="Pair a Muse headband" data-muse-pair={state.status}>
  <header className={css.head}>
   {connected?<Bluetooth size={16} aria-hidden="true"/>:<BluetoothOff size={16} aria-hidden="true"/>}
   <strong>{title}</strong>
   <span className={css.status} role="status">{state.status==='unsupported'?'Not supported here':state.status==='checking'?'Checking':connected?`Connected · ${state.deviceName}`:busy?'Connecting…':'Not paired'}</span>
   {connected&&state.battery!==null?<span className={css.battery}><BatteryMedium size={14} aria-hidden="true"/> {state.battery}%</span>:null}
  </header>
  <p className={css.note}>{state.message}</p>
  {connected?<div className={css.bands} role="group" aria-label="Soft live band levels">
   {BANDS.map(name=><div key={name} className={css.band}>
    <span>{BAND_LABEL[name]}</span>
    <span className={css.bar} role="meter" aria-label={`${BAND_LABEL[name]} relative level`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round((bands[name]||0)*100)}><i style={{width:`${Math.round(Math.min(1,(bands[name]||0)*2.2)*100)}%`}}/></span>
    <small>{Math.round((bands[name]||0)*100)}%</small>
   </div>)}
   <p className={css.mood}>{state.influence.active?`Beast mood ${MOOD_TEXT[state.influence.mood]||'settling'} · energy ${Math.round(state.influence.energy*100)}% · music intensity ${Math.round(state.influence.intensity*100)}%`:'Reading the first second of signal…'}</p>
  </div>:null}
  <div className={css.actions}>
   {connected?<button type="button" className={css.off} onClick={()=>void muse.disconnect()}>Disconnect Muse</button>:
    <button type="button" className={css.pair} disabled={!state.supported||busy} onClick={()=>void muse.connect()}>{busy?'Connecting…':'Pair Muse'}</button>}
  </div>
  <p className={css.fine}>{MUSE_LABEL} Muse 2 and Muse S use Bluetooth service 0xfe8d.</p>
 </section>;
}
