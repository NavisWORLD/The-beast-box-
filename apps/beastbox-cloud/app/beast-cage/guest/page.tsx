import type {Metadata} from 'next';
import JourneyLinks from '@/components/journey-links';
import GuestGbaLab from '@/components/gba-guest-lab';
export const metadata:Metadata={title:'Guest Beast Cage • GBA Companion Export',description:'Try the original cosmic creature, preview real GBA 4bpp pixel art, and download a safe, importable game module.'};
export default function GuestGamePortal(){return <><div className="room-strip room-strip-top"><JourneyLinks current="cage" label="Beast Box rooms"/></div><GuestGbaLab/></>;}
