import type {Metadata} from 'next';
import TinyUniverseView from '@/components/tiny-universe-view';
export const metadata:Metadata={title:'Tiny Universe · Beast Box',description:'recorded IBM hardware outcomes used as seeds; no entanglement or Bell-violation claim'};
export default function Page(){return <TinyUniverseView/>;}
