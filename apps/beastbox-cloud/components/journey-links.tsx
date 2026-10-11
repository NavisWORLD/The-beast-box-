import Link from 'next/link';
import RoomLink from './room-link';
import { ROOMS } from '@/lib/rooms';

type Extra = { label: string; href: string };
/**
 * The public journey nav used by Home, Privacy, Coming soon and the Lab pages.
 * Every page offers all seven rooms; `skip` hides rooms a header already
 * shows elsewhere (for example the brand link already goes Home).
 */
export default function JourneyLinks({ current, skip = [], extra = [], label = 'Beast Box journey' }:
  { current?: string; skip?: string[]; extra?: Extra[]; label?: string }) {
  return <nav className="public-journey-links" aria-label={label}>
    {ROOMS.filter(room => !skip.includes(room.key)).map(room =>
      <RoomLink key={room.key} href={room.href} prefetch={false} aria-current={room.key === current ? 'page' : undefined}>
        <span className="journey-icon" aria-hidden="true">{room.icon}</span>{room.label}
      </RoomLink>)}
    {extra.map(item => <Link key={item.href} href={item.href} prefetch={false} className="journey-extra">{item.label}</Link>)}
  </nav>;
}
