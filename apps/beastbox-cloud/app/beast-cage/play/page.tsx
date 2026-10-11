import type { Metadata } from 'next';
import JourneyLinks from '@/components/journey-links';
import BeastAdventure from '@/components/beast-adventure';

export const metadata: Metadata = {
  title: 'Adventure · BEAST BOX',
  description: 'Walk with your beast, talk with the selected brain, and keep Lost Cosmos loaded.',
};

export default function PlayPage() {
  return <><div className="room-strip room-strip-top"><JourneyLinks current="cage" label="Beast Box rooms"/></div><BeastAdventure /></>;
}
