import type {Metadata} from 'next';
import BeastCagePortal from '@/components/beast-cage-portal';
export const metadata:Metadata={title:'The Beast Cage · A small companion, an entire universe',description:'A cosmic companion habitat within the Beast Box experience. Visual previews are local-only; real models and memory stay in COSMOS.'};
export default function BeastCage(){return <BeastCagePortal/>;}
