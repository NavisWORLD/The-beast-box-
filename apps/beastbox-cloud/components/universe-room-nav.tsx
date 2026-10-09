import Link from 'next/link';
import styles from './universe-room-nav.module.css';

export const UNIVERSE_ROOMS=[['HOME','/'],['MY BEAST','/spark/index.html'],['BEAST CAGE','/beast-cage'],['LOST COSMOS','/sol-game'],['BRAIN BAY','/brain-bay'],['LAB','/research'],['SETTINGS','/settings']];
export default function UniverseRoomNav({current}:{current:string}){
 return <header className={styles.header}>
  <Link href="/" className={styles.brand} aria-label="Beast Box home"><span aria-hidden="true">✦</span> BEAST BOX <small>AWAKENS</small></Link>
  <nav className={styles.nav} aria-label="Universe rooms">{UNIVERSE_ROOMS.map(([label,href])=>
   <Link key={href} href={href} prefetch={false} aria-current={href===current?'page':undefined}>{label}</Link>
  )}</nav>
 </header>;
}
