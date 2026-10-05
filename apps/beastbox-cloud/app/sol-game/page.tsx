import type {Metadata} from 'next';
import Link from 'next/link';
import SolSparkPlayer from '../../components/sol-spark-player';
export const metadata:Metadata={title:'LOST COSMOS · Your Spark Beast',description:'Send your same QBEAST into the current native LOST COSMOS cartridge.'};
export default function SolGame(){return <main style={{minHeight:'100vh',background:'#0b1122',color:'#eef5ff',padding:'18px min(5vw,30px)'}}>
 <nav aria-label="Game navigation" style={{display:'flex',gap:20,flexWrap:'wrap',marginBottom:18}}><Link href="/spark/index.html">Spark Beasts</Link><Link href="/beast-cage">Beast Cage · care</Link><Link href="/beast-cage/play">Adventure</Link></nav>
 <h1 style={{fontSize:'clamp(24px,5vw,40px)'}}>PLAY IN LOST COSMOS 🎮</h1>
 <p>Your exact recorded-seed companion. Native art, movement, chirps, chat and battery saves.</p>
 <SolSparkPlayer/>
 <p style={{fontSize:12,color:'#9aadd4'}}>Native chat: START → PARTY → companion → CHAT. D-pad selects letters, A adds, L erases, SELECT sends, B returns. Save your journey from the emulator before loading another creature.</p>
 </main>}
