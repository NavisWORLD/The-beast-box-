'use client';
// Emeth's live recheck (Oct 23 2026): technical receipts (bb- IDs, ticks, job IDs, hashes, steps, gates) stay on the page,
// honest and unedited, but behind one "Details" toggle so each page leads with a single plain line.
// inline: a span + button (valid inside <p>/<strong>); block: native <details>.
import {useState,type ReactNode,type CSSProperties} from 'react';
export default function Details({children,label='Details',style,inline=false}:{children:ReactNode;label?:string;style?:CSSProperties;inline?:boolean}){
 const [open,setOpen]=useState(false);
 if(inline)return <span data-details-toggle data-open={open?'true':'false'} style={style}> <button type="button" aria-expanded={open} onClick={()=>setOpen(v=>!v)} style={{font:'inherit',fontSize:'.85em',background:'none',border:0,padding:0,color:'inherit',opacity:.75,textDecoration:'underline dotted',cursor:'pointer'}}>{open?'hide':label}</button>{open?<span> {children}</span>:null}</span>;
 return <details data-details-toggle style={{display:'block',fontSize:12,opacity:.85,...style}}><summary style={{cursor:'pointer'}}>{label}</summary><div>{children}</div></details>;
}
