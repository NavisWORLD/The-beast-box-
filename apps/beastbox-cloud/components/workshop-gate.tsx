'use client';
import {useState} from 'react';
import Link from 'next/link';
import Studio from './studio';
/** Friendly locked screen for the Workshop. Owner sign-in is still reachable for Cory. */
export default function WorkshopGate({reason,configured}:{reason:string;configured:boolean}){
 const [ownerLogin,setOwnerLogin]=useState(false);
 if(ownerLogin)return <Studio initialOwner={false} configured={configured} initialBridge={false}/>;
 return <main data-workshop-gate style={{maxWidth:520,margin:'64px auto',padding:20,textAlign:'center',display:'grid',gap:14}}>
  <h1>🛠️ The Workshop is invite-only</h1>
  <p>This is Cory&apos;s workshop where Zeref gets built. Everything else in Beast Box is open to you, guests included.</p>
  <p data-workshop-message><strong>Want in? Message Cory for access.</strong>{reason==='unverified'?' (Verify your email first.)':reason==='guest'?' Then sign in with that account.':''}</p>
  <p><Link href="/">Back to Beast Box</Link> · <Link href="/account">Account</Link></p>
  <button type="button" onClick={()=>setOwnerLogin(true)} style={{opacity:.6}}>Cory? Owner sign-in</button>
 </main>;
}
