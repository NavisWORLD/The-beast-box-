import type {Metadata} from 'next';
import TinyUniverseView from '@/components/tiny-universe-view';
export const metadata:Metadata={title:'Tiny Universe · Beast Box',description:'A tiny universe seeded by real IBM entanglement, grown by a simulated Bell sampler.'};
export default function Page(){return <TinyUniverseView/>;}
