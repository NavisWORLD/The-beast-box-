'use client';
import {useEffect,useState} from 'react';
type Looked={title:string,provenance:string};
type Turn={from:string,text:string,at?:string,lookup?:Looked[]};
type Confused={active:boolean,why:string[],label:string}|null;
export default function ClassroomPanel(){
 const [owner,setOwner]=useState<boolean|null>(null);
 const [turns,setTurns]=useState<Turn[]>([]);
 const [text,setText]=useState('');const [topic,setTopic]=useState('');const [target,setTarget]=useState('');
 const [drill,setDrill]=useState<''|'hit'|'miss'>('');
 const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [confused,setConfused]=useState<Confused>(null);
 useEffect(()=>{fetch('/api/session',{cache:'no-store'}).then(r=>r.json()).then(s=>{setOwner(s.owner===true);
  if(s.owner===true)fetch('/api/classroom',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(d=>d&&setTurns(d.turns||[]));}).catch(()=>setOwner(false));},[]);
 async function send(e:React.FormEvent){
  e.preventDefault();if(!text.trim()||busy)return;setBusy(true);setError('');
  const body:Record<string,string>={text};if(topic.trim())body.topic=topic.trim();if(target.trim())body.target=target.trim();if(drill)body.drill=drill;
  try{const r=await fetch('/api/classroom',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
   const d=await r.json();if(!r.ok){setError(d.error||'Something went wrong');return;}
   setTurns(t=>[...t,{from:'teacher',text},{from:'zeref',text:d.reply,lookup:Array.isArray(d.lookup?.used)?d.lookup.used:[]}].slice(-40));setConfused(d.confused_state);setText('');setDrill('');}
  catch{setError('The brain did not answer this time.');}finally{setBusy(false);}
 }
 const box:React.CSSProperties={maxWidth:760,margin:'40px auto',padding:20,color:'#e8e6ff',fontFamily:'system-ui,sans-serif'};
 if(owner===null)return <main style={box}><p>Checking the owner session…</p></main>;
 if(!owner)return <main style={box}><h1>Zeref&apos;s classroom</h1><p>This classroom is for Zeref&apos;s owner and his teachers only. You can still talk with him in the public chat.</p></main>;
 return <main style={box}>
  <h1>Zeref&apos;s classroom</h1>
  <p style={{opacity:.8}}>Owner-only teaching thread (kind: classroom). Same live pinned brain as the public chat, separate thread. Every exchange is saved as a text-only experience record, pending review. Knowledge-bank lookup is on: matching open-license passages are added to his prompt and shown with their source.</p>
  <div aria-live="polite" style={{border:'1px solid #444',borderRadius:8,padding:12,minHeight:160,maxHeight:420,overflowY:'auto'}}>
   {turns.length===0?<p style={{opacity:.6}}>No lessons in this thread yet.</p>:turns.map((t,i)=><div key={i}><p><b>{t.from==='zeref'?'Zeref':'Teacher'}:</b> {t.text}</p>{(t.lookup||[]).map((u,j)=><p key={j} data-class-lookup style={{opacity:.7,fontSize:12,margin:'0 0 6px 12px'}}>Looked up (knowledge bank, word for word): {u.provenance}</p>)}</div>)}
  </div>
  <p data-testid="confused-line" title={confused&&confused.active?'Why: '+confused.why.join('; ')+' (a missed drill or a missing target word)':undefined}><b data-testid="confused-chip">{confused?(confused.active?'Confused · DERIVED':'Not confused · DERIVED'):'Not derived yet'}</b>{confused&&confused.active?<> · Zeref feels confused. That&apos;s okay.</>:null}</p>
  <form onSubmit={send} style={{display:'grid',gap:8}}>
   <textarea value={text} onChange={e=>setText(e.target.value)} maxLength={1200} rows={3} placeholder="Teacher line" required/>
   <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
    <input value={topic} onChange={e=>setTopic(e.target.value)} maxLength={60} placeholder="Topic (optional)"/>
    <input value={target} onChange={e=>setTarget(e.target.value)} maxLength={40} placeholder="Target word (optional)"/>
    <select value={drill} onChange={e=>setDrill(e.target.value as ''|'hit'|'miss')}><option value="">No drill mark</option><option value="hit">Drill hit</option><option value="miss">Drill miss</option></select>
    <button type="submit" disabled={busy}>{busy?'Waiting for Zeref…':'Send'}</button>
   </div>
   {error&&<p role="alert">{error}</p>}
  </form>
 </main>;
}
