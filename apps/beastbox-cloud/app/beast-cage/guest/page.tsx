import type {Metadata} from 'next';
import GuestGbaLab from '@/components/gba-guest-lab';
export const metadata:Metadata={title:'Guest Beast Cage • GBA Companion Export',description:'Try the original cosmic creature, preview real GBA 4bpp pixel art, and download a safe, importable game module.'};
export default function GuestGamePortal(){return <GuestGbaLab/>;}
