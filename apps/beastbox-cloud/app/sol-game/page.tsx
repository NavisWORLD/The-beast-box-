import type {Metadata} from 'next';
import Link from 'next/link';
import SolSparkPlayer from '../../components/sol-spark-player';
export const metadata:Metadata={title:'LOST COSMOS · Your Spark Beast',description:'Send your same QBEAST into the current native LOST COSMOS cartridge.'};
export default function SolGame(){return <main style={{minHeight:'100vh',background:'#0b1122',color:'#eef5ff',padding:'18px min(5vw,30px)'}}>
 <nav aria-label="Game navigation" style={{display:'flex',alignItems:'center',gap:8,flexWrap:'wrap',marginBottom:18,padding:6,border:'1px solid #314878',borderRadius:14,background:'#0e162b'}}><Link href="/" style={{padding:'8px 10px'}}>Home</Link><Link href="/spark/index.html" style={{padding:'8px 10px'}}>01 · Spark</Link><Link href="/beast-cage" style={{padding:'8px 10px'}}>02 · Cage</Link><Link href="/beast-cage/go" style={{padding:'8px 10px'}}>03 · Field</Link><span aria-current="page" style={{padding:'8px 10px',borderRadius:9,background:'#17314c',color:'#7ee7ff'}}>04 · LOST COSMOS</span></nav>
 <h1 style={{fontSize:'clamp(24px,5vw,40px)'}}>PLAY IN LOST COSMOS 🎮</h1>
 <p>Your exact recorded-seed companion. Native art, movement, chirps and battery saves. Open TALK to chat with your Beast through the guest model and care for it while the cartridge stays open.</p>
 <SolSparkPlayer/>
 <p style={{fontSize:12,color:'#9aadd4'}}>Native chat: START → PARTY → companion → CHAT. D-pad selects letters, A adds, L erases, SELECT sends, B returns. Save your journey from the emulator before loading another creature.</p>
 </main>}
