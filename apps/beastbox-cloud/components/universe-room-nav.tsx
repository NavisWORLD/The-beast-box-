import Link from 'next/link';
import styles from './universe-room-nav.module.css';
import BrandCrest from '@/components/brand-crest';
import { ROOMS } from '@/lib/rooms';

// Kept for any caller that still reads the tuple form.
export const UNIVERSE_ROOMS = ROOMS.map(room => [room.label.toUpperCase(), room.href]);
export default function UniverseRoomNav({current}:{current:string}){
 return <header className={styles.header}>
  <Link href="/" className={styles.brand} aria-label="Beast Box home"><BrandCrest className={styles.crest} size={28} decorative/> BEAST BOX <small>AWAKENS</small></Link>
  <nav className={styles.nav} aria-label="Universe rooms">{ROOMS.map(room=>
   <Link key={room.href} href={room.href} prefetch={false} aria-current={room.href===current?'page':undefined}><span aria-hidden="true">{room.icon}</span> {room.label.toUpperCase()}</Link>
  )}</nav>
 </header>;
}
