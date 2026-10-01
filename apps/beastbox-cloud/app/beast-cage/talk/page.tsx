import type { Metadata } from 'next';
import Link from 'next/link';
import BeastCageTalk from '@/components/beast-cage-talk';
export const metadata: Metadata = { title: 'Talk to the Beast · BEAST BOX', description: 'A real guest chat with RAWRPHØS and an animated cosmic companion. Guest sessions do not access owner memory.' };
export default function TalkPage() {
  return <main style={{minHeight:'100vh',background:'#090e1b',color:'#f1edff'}}>
    <header style={{maxWidth:1100,margin:'auto',padding:'22px 20px',display:'flex',gap:20,alignItems:'center',justifyContent:'space-between'}}>
      <Link href="/beast-cage" style={{fontWeight:800,color:'#a8eef9',letterSpacing:'.14em'}}>✦ BEAST CAGE</Link>
      <Link href="/workspace" style={{fontSize:12,color:'#ddd1ff'}}>OWNER WORKSTATION ↗</Link>
    </header>
    <BeastCageTalk />
  </main>;
}
