import type {Metadata} from 'next';
import Link from 'next/link';

export const metadata:Metadata={title:'LOST COSMOS · Your Spark Beast',description:'Send your same QBEAST into the current native LOST COSMOS cartridge.'};

export default function SolGame(){return <main style={{minHeight:'100vh',background:'#0b1122',color:'#eef5ff',padding:'18px min(5vw,30px)'}}>
 <nav aria-label="Beast Box journey" style={{display:'flex',alignItems:'center',gap:8,flexWrap:'wrap',marginBottom:18,padding:6,border:'1px solid #314878',borderRadius:14,background:'#0e162b'}}>
  <Link href="/" style={{padding:'8px 10px'}}>Home</Link>
  <Link href="/spark/index.html" style={{padding:'8px 10px'}}>My Beast</Link>
  <Link href="/beast-cage" style={{padding:'8px 10px'}}>Beast Cage</Link>
  <span aria-current="page" style={{padding:'8px 10px',borderRadius:9,background:'#17314c',color:'#7ee7ff'}}>Lost COSMOS</span>
  <Link href="/brain-bay" style={{padding:'8px 10px'}}>Brain Bay</Link>
  <Link href="/research" style={{padding:'8px 10px'}}>Lab</Link>
  <Link href="/settings" style={{padding:'8px 10px'}}>Settings</Link>
 </nav>
 <p style={{fontSize:11,letterSpacing:'.14em',color:'#7ee7ff',fontWeight:800}}>YOUR BEAST · YOUR CARTRIDGE · SAME IDENTITY</p>
 <h1 style={{fontSize:'clamp(24px,5vw,40px)'}}>PLAY IN LOST COSMOS 🎮</h1>
 <p>Your exact recorded-seed companion. Native art, movement, chirps and battery saves. Open TALK to chat with your Beast through the available guest-safe brain and care for it while the cartridge stays open.</p>
 <p style={{fontSize:12,color:'#9aadd4'}}><Link href="/beast-cage/go">Explore the web field first →</Link></p>
 <p>The Game Boy player stays with you. Minimize it to explore Beast Box, then restore your current adventure.</p>
 <p style={{fontSize:12,color:'#9aadd4'}}>Cartridge V11.3. The file hash is 6f9c22fa. The ROM header still says COSMOS V11.2. That string is stale. The bytes are the V11.3 release, not the V11.2 file.</p>
 </main>}
