import type {Metadata} from 'next';
import Link from 'next/link';
import BrandCrest from '@/components/brand-crest';

export const metadata:Metadata={title:'LOST COSMOS · Your Spark Beast',description:'Send your same QBEAST into the current native LOST COSMOS cartridge.'};

export default function SolGame(){return <main style={{minHeight:'100vh',background:'#0b1122',color:'#eef5ff',padding:'18px min(5vw,30px)'}}>
 {/* data-page-nav: the full-screen Lost COSMOS player starts below this bar, so the nav is never covered.
     One scrollable row keeps it short on phones. */}
 <nav data-page-nav aria-label="Beast Box journey" style={{display:'flex',alignItems:'center',gap:8,flexWrap:'nowrap',overflowX:'auto',whiteSpace:'nowrap',scrollbarWidth:'none',marginBottom:18,padding:6,border:'1px solid #314878',borderRadius:14,background:'#0e162b'}}>
  <Link href="/" aria-label="Beast Box home" style={{display:'inline-flex',padding:'2px 4px 2px 2px'}}><BrandCrest size={30} decorative/></Link>
  <Link href="/" style={{padding:'8px 10px'}}>Home</Link>
  <a href="/spark/index.html" style={{padding:'8px 10px'}}>My Beast</a>
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
 <p style={{fontSize:12,color:'#9aadd4'}}>Cartridge V11.6. New: a 3D view. Press START, open SYSTEM and choose 3D VIEW to walk the field in first person with your beast beside you. A switches to the Beast Cage camera, and SELECT goes back to the normal map. The Beast Home from V11.5 is still in Brindlemark. The file hash is 4acdc8d5 and the ROM header says COSMOS V11.6. Older saves still load.</p>
 </main>}
