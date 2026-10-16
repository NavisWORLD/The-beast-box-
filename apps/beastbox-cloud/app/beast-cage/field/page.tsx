import type { Metadata } from 'next';
import OpenFieldCamera from '@/components/open-field-camera';
import Link from 'next/link';
import FieldPerception from '@/components/field-perception';
export const metadata: Metadata = { title: 'Open Field · BEAST BOX', description: 'Your creature in 3D on your floor: WebXR AR where supported, motion-anchored camera overlay on iPhone, Quick Look AR.' };
export default function OpenFieldPage() {
  return <main style={{minHeight:'100dvh',padding:'12px 10px 120px',background:'#070b1c'}} data-page-nav>
    <nav aria-label="Open Field navigation" style={{display:'flex',gap:12,flexWrap:'wrap',fontSize:13}}><Link href="/">Home</Link><Link href="/beast-cage">Beast Cage</Link><Link href="/beast-cage/go">Field game</Link><Link href="/sol-game">Lost COSMOS</Link></nav>
    <OpenFieldCamera />
    <FieldPerception />
  </main>;
}
