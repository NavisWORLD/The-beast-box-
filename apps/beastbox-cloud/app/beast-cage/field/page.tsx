import type { Metadata } from 'next';
import OpenFieldCamera from '@/components/open-field-camera';
import Link from 'next/link';
import FieldPerception from '@/components/field-perception';
export const metadata: Metadata = { title: 'Lost Cosmos Field · BEAST BOX', description: 'Your companion and Zeref walking in your room: true AR tracking with WebXR (Android Chrome), camera overlay on iPhone, Quick Look AR.' };
export default function OpenFieldPage() {
  return <main style={{minHeight:'100dvh',padding:'12px 10px 120px',background:'#070b1c'}} data-page-nav>
    <nav aria-label="Open Field navigation" style={{display:'flex',gap:12,flexWrap:'wrap',fontSize:13}}><Link href="/">Home</Link><Link href="/beast-cage">Beast Cage</Link><Link href="/beast-cage/go">Field game</Link><Link href="/sol-game">Lost COSMOS</Link></nav>
    <h1 style={{margin:"10px 0 4px",fontSize:22,color:"#f5ecff"}}>Lost Cosmos Field</h1>
    <OpenFieldCamera />
    <FieldPerception />
  </main>;
}
