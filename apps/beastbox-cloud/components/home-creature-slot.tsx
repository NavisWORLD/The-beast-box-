'use client';
import HomepageCreature from './homepage-creature';
import {useBeastSession} from './beast-session';
/** Oct 16 declutter: guests see only the roaming living-core Zeref (no Hi! bubble / View menu over it);
 * a saved QBEAST keeps its own 3D hero + card. */
export default function HomeCreatureSlot(){
 const {session}=useBeastSession();
 if(!session?.beast?.qbeast?.profile?.id)return null;
 return <div className="beast-landing-creature"><HomepageCreature/></div>;
}
