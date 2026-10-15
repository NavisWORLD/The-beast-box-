import type { Metadata } from 'next';
import JourneyLinks from '@/components/journey-links';
import BeastCageTalk from '@/components/beast-cage-talk';
import UniverseRoomShell from '@/components/universe-room-shell';
export const metadata: Metadata = { title: 'Talk to the Beast · BEAST BOX', description: 'A real guest chat with your Beast and an animated cosmic companion. Guest sessions do not access owner memory.' };
export default function TalkPage() {
  return <UniverseRoomShell current="/beast-cage/talk" label="Talk to your Beast">
    <div className="room-strip"><JourneyLinks current="cage" label="Beast Box rooms"/></div>
    <BeastCageTalk />
  </UniverseRoomShell>;
}
