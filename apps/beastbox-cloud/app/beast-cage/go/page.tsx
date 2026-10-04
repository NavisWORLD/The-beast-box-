import type { Metadata } from 'next';
import BeastGo from '@/components/beast-go';

export const metadata: Metadata = {
  title: 'Field · BEAST BOX',
  description: 'Lost Cosmos is the world. A floating field HUD keeps your beast, bag, and talk on the same care save.',
};

export default function GoPage() {
  return <BeastGo />;
}
