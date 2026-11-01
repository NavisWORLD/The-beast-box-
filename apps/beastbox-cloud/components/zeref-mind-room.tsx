'use client';
import {useEffect,useState} from 'react';
type Item={title:string|null;line:string|null;url:string|null;license:string|null;label:'RECORDED'|'DERIVED'};
type Wonder={status:string;thought:string|null;topics:string[]|null;label:string;at_utc:string};
type Room={wonder?:Wonder|null;label:string;tvs:{id:string;name:string;item:Item|null}[]};
// Fixed glow per TV (no randomness), in the world's violet/cyan palette.
const GLOW:Record<string,string>={wikipedia:'#7dd3fc',gutenberg:'#fcd34d',kjv:'#fde68a',history:'#fca5a5',religions:'#c4b5fd','x-teacher':'#86efac',world:'#f0abfc'};
export function ZerefMindRoom(){
 const [r,setR]=useState<Room|null>(null);
 useEffect(()=>{fetch('/zeref-chooses/mind-room.json',{cache:'no-store'}).then(x=>x.ok?x.json():null).then(setR).catch(()=>setR(null));},[]);
 if(!r)return <p>Opening the Mind Room…</p>;
 return <section data-mind-room style={{background:'radial-gradient(ellipse at top,#2e1065,#0b0420 70%)',color:'#ede9fe',padding:12,borderRadius:16,maxWidth:'100%',boxSizing:'border-box'}}>
  <p style={{fontSize:12,opacity:.8,margin:'0 0 10px'}}>{r.label}</p>
  {r.wonder&&<div data-wonder style={{border:'2px dashed #f0abfc',borderRadius:12,padding:10,marginBottom:10,background:'#1e0b3a',overflowWrap:'anywhere'}}>
   <div style={{fontSize:12,color:'#f0abfc',fontWeight:700}}>💭 His latest wonder <span style={{fontSize:10,border:'1px solid #f0abfc',borderRadius:6,padding:'0 4px',whiteSpace:'nowrap'}}>{r.wonder.status}</span></div>
   {r.wonder.thought?<div style={{fontSize:14,margin:'4px 0'}}>“I want to learn about{r.wonder.thought}”</div>:null}
   <div style={{fontSize:11,opacity:.8}}>{r.wonder.label}{r.wonder.topics?.length?` · topics: ${r.wonder.topics.join(', ')}`:''}</div>
  </div>}
  <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(160px,1fr))',gap:10}}>
   {r.tvs.map(t=>{const g=GLOW[t.id]||'#a78bfa';return <article key={t.id} data-tv={t.id} style={{border:`2px solid ${g}`,borderRadius:12,padding:10,background:'#140a2e',boxShadow:`0 0 14px ${g}88, inset 0 0 18px ${g}22`,minWidth:0,overflowWrap:'anywhere'}}>
    <header style={{display:'flex',justifyContent:'space-between',gap:6,fontSize:12,color:g,fontWeight:700}}><span>📺 {t.name}</span>{t.item&&<span data-label style={{fontSize:10,border:`1px solid ${g}`,borderRadius:6,padding:'0 4px'}}>{t.item.label}</span>}</header>
    {t.item?<><div style={{fontWeight:700,fontSize:14,margin:'6px 0 2px'}}>{t.item.url?<a href={t.item.url} style={{color:'#fff'}} rel="noopener noreferrer" target="_blank">{t.item.title}</a>:t.item.title}</div>
     <div style={{fontSize:12,lineHeight:1.35,opacity:.9}}>{t.item.line}</div></>:<div style={{fontSize:12,opacity:.6,marginTop:6}}>Static: nothing on this channel yet.</div>}
   </article>;})}
  </div>
 </section>;
}
