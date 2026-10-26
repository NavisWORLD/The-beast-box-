import type {Metadata} from 'next';
import Link from 'next/link';
import BrandCrest from '@/components/brand-crest';

export const metadata:Metadata={title:'LOST COSMOS · Your Beast',description:'Send your same QBEAST into the current native LOST COSMOS cartridge.'};

export default function SolGame(){return <main style={{minHeight:'100vh',background:'#0b1122',color:'#eef5ff',padding:'18px min(5vw,30px)'}}>
 {/* data-page-nav: the full-screen Lost COSMOS player starts below this bar, so the nav is never covered.
     One scrollable row keeps it short on phones. */}
 <nav data-page-nav aria-label="Beast Box journey" style={{display:'flex',alignItems:'center',gap:8,flexWrap:'nowrap',overflowX:'auto',whiteSpace:'nowrap',scrollbarWidth:'none',marginBottom:18,padding:6,border:'1px solid #314878',borderRadius:14,background:'#0e162b'}}>
  <Link href="/" aria-label="Beast Box home" style={{display:'inline-flex',padding:'2px 4px 2px 2px'}}><BrandCrest size={30} decorative/></Link>
  <Link href="/" style={{padding:'8px 10px'}}>Home</Link>
  <a href="/spark/index.html" style={{padding:'8px 10px'}}>My Beast</a>
  <Link href="/beast-cage" style={{padding:'8px 10px'}}>Beast Cage</Link>
  <span aria-current="page" style={{padding:'8px 10px',borderRadius:9,background:'#17314c',color:'#7ee7ff'}}>Lost COSMOS</span>
  <Link href="/beast-cage/field" style={{padding:'8px 10px'}}>Lost COSMOS Field</Link>
  <Link href="/brain-bay" style={{padding:'8px 10px'}}>Brain Bay</Link>
  <Link href="/research" style={{padding:'8px 10px'}}>Research Lab</Link>
  <Link href="/workspace" style={{padding:'8px 10px'}}>Workshop</Link>
  <Link href="/settings" style={{padding:'8px 10px'}}>Settings</Link>
 </nav>
 <p style={{fontSize:11,letterSpacing:'.14em',color:'#7ee7ff',fontWeight:800}}>YOUR BEAST · YOUR CARTRIDGE · SAME IDENTITY</p>
 <h1 style={{fontSize:'clamp(24px,5vw,40px)'}}>PLAY IN LOST COSMOS 🎮</h1>
 <p>Your exact recorded-seed companion. Native art, movement, chirps and battery saves. Open TALK to chat with your Beast through the available guest-safe brain and care for it while the cartridge stays open.</p>
 <p style={{fontSize:12,color:'#9aadd4'}}><Link href="/beast-cage/go">Explore the web field first →</Link></p>
 <p>The Game Boy player stays with you. Minimize it to explore Beast Box, then restore your current adventure.</p>
 <p style={{fontSize:15,color:'#dbe4ff',margin:'4px 0'}}>Tap <b>SEND BEAST</b>, then use the arrows and <b>A</b> to play with your Beast. 🐉</p><details style={{fontSize:12,color:'#9aadd4'}}><summary style={{cursor:'pointer',minHeight:36}}>About this cartridge</summary><p style={{fontSize:12,color:'#9aadd4'}}>Cartridge V12.2 · CST-12 EMERGENT. Every creature trait now grows from its own quantum seed and what it lives through. Open START, SYSTEM, LIVING WORLD to watch six creatures live on their own in a forest and a cave, with items, stats and a quest journal. Their life is a classical simulation seeded by recorded IBM quantum data. Act II is still here: Tide Memory, the Forgotten City, the Sentinel trials and Chronoheart continue your earned Act I save. Your beast remains off the leash. In the field it explores on its own, sniffs out doors and signs, greets people, and runs back to you when enemies show up. To call it back, open START, SYSTEM, CALL BEAST. LEASH in the same menu switches back to the old follower. PARTY, then your beast, then DETAILS shows its field record: the places it walked and its favorite spots. Act I, The First Heart, the 3D VIEW and the Beast Home are all still there. The verified 16 MB file hash begins 0f5c9155 and the ROM header says COSMOS V12.2. Older saves still load.</p></details>
 </main>}
