import type {Metadata} from 'next';
import UniverseSettings from '../../components/universe-settings';

export const metadata:Metadata={title:'Settings · Beast Box',description:'Shared sound and motion preferences for your Beast Box universe.'};
export default function SettingsPage(){return <UniverseSettings/>;}
