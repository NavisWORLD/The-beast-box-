import type {Metadata} from 'next';
import BrainBayWorkshop from '../../components/brain-bay-workshop';

export const metadata:Metadata={title:'Brain Bay · BEAST BOX',description:'Choose a public brain socket while keeping the same local Beast and its story.'};
export default function BrainBayPage(){return <BrainBayWorkshop/>;}
