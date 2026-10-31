'use client';
import {useState,type FormEvent} from 'react';
type Line={who:'you'|'zeref';text:string;meta?:string};
export default function GrowingChat(){
 const [lines,setLines]=useState<Line[]>([]);const [text,setText]=useState('');const [busy,setBusy]=useState(false);
 async function send(e:FormEvent){e.preventDefault();const t=text.trim();if(!t||busy)return;setBusy(true);setText('');setLines(l=>[...l,{who:'you',text:t}]);
  try{const res=await fetch('/api/guest-growing',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});
   const r=await res.json();
   setLines(l=>[...l,res.ok?{who:'zeref',text:r.reply,meta:`${r.label} · ${r.tag} · step ${r.step}`}:{who:'zeref',text:r.error||'Growing Zeref is unavailable right now.',meta:'Growing Zeref · not the pin'}]);
  }catch{setLines(l=>[...l,{who:'zeref',text:'Growing Zeref is unavailable right now.',meta:'Growing Zeref · not the pin'}]);}
  finally{setBusy(false);}}
 return <section data-growing-chat>
  {lines.map((l,i)=><p key={i}><b>{l.who==='you'?'You':'Growing Zeref'}:</b> {l.text}{l.meta?<><br/><small>{l.meta}</small></>:null}</p>)}
  <form onSubmit={send}><input value={text} onChange={e=>setText(e.target.value)} maxLength={1500} placeholder="Say something to Growing Zeref" style={{width:'75%'}}/> <button disabled={busy}>Send</button></form>
 </section>;
}
