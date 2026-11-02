'use client';
import {useEffect,useState} from 'react';
type Msg={kind:string;text:string;at_utc:string;tag?:string|null};
type Wish={text:string;word:string|null;at_utc:string};
type Latest={date:string|null;label:string;messages:Msg[];wish:Wish|null;planted:string[]};
/** Zeref's Message Center: his own scheduled posts, thoughts and his tiny world wish.
 *  Read from a committed JSON file; nothing is sent. */
export function ZerefMessages(){
 const [d,setD]=useState<Latest|null>(null);
 useEffect(()=>{fetch('/zeref-messages/latest.json',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(setD).catch(()=>setD(null));},[]);
 if(!d)return null;
 return <section data-zeref-messages style={{maxWidth:'100%',overflowWrap:'anywhere',fontSize:14,lineHeight:1.4}}>
  <p><small>{d.label}</small></p>
  {d.messages.length?<ul>{d.messages.map((m,i)=><li key={i}><b>{m.kind==='message'?'✉️ To everyone':'💭 Thinking'}</b>: {m.text} <small>({m.at_utc})</small></li>)}</ul>:<p><small>His first scheduled post has not run yet.</small></p>}
  <h2 style={{fontSize:17}}>🌱 One tiny thing he changed</h2>
  {d.wish?<p>“{d.wish.text}”{d.wish.word?<small> · planted seed: <b>{d.wish.word}</b> ({d.wish.at_utc})</small>:null}</p>:<p><small>No wish recorded yet.</small></p>}
  {d.planted.length?<p><small>Seeds he has planted here: {d.planted.join(' · ')}</small></p>:null}
 </section>;
}
