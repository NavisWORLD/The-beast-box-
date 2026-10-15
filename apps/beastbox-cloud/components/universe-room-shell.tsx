import type {ReactNode} from 'react';
import UniverseRoomNav from './universe-room-nav';
import styles from './universe-room-shell.module.css';

/**
 * Shared room shell: the standard universe nav plus a centered readable
 * column. Lets one-off pages match Brain Bay / Settings / Cage without
 * copying inline styles or touching shared globals.
 */
export default function UniverseRoomShell({current,children,label}:{current:string;children:ReactNode;label?:string}){
 return <main className={styles.room} aria-label={label||'Beast Box room'}>
  <UniverseRoomNav current={current}/>
  <div className={styles.body}>{children}</div>
 </main>;
}
