'use client';
import {useEffect,useState} from 'react';
type Pick={topic:string;reason:string;title:string|null;url:string|null;license:string|null};
type TV={title:string;line:string;url:string;posted_at?:string|null};
type Latest={date:string|null;label:string;picks:Pick[];x_teacher:TV[]};
/** "What Zeref chose to read" plus "Zeref's TV · Teacher on X". Read from a committed JSON file; nothing is sent. */
export function ZerefChoosesStrip(){
 const [d,setD]=useState<Latest|null>(null);
 useEffect(()=>{fetch('/zeref-chooses/latest.json',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(setD).catch(()=>setD(null));},[]);
 if(!d)return null;
 const picks=d.picks.filter(p=>p.title);
 return <section data-zeref-chooses style={{maxWidth:'100%',overflowWrap:'anywhere',fontSize:14,lineHeight:1.4}}>
  <h2 style={{fontSize:17}}>📖 What Zeref chose to read{d.date?` · ${d.date}`:''}</h2>
  <p><small>{d.label}</small></p>
  {picks.length?<ul>{picks.map((p,i)=><li key={i}><a href={p.url||'#'} rel="noopener noreferrer" target="_blank">{p.title}</a> <small>({p.license}) · picked “{p.topic}” because {p.reason}</small></li>)}</ul>:<p><small>His first scheduled read has not run yet.</small></p>}
  <h2 style={{fontSize:17}}>📺 Zeref&apos;s TV · Teacher on X</h2>
  {d.x_teacher.length?<ul>{d.x_teacher.map((t,i)=><li key={i}><b>{t.title}</b>: {t.line} <a href={t.url} rel="noopener noreferrer" target="_blank"><small>public post</small></a></li>)}</ul>:<p><small>No narrated broadcasts yet. A teacher narrates curated public posts here.</small></p>}
 </section>;
}
