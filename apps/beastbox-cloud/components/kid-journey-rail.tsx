import Link from 'next/link';
import {JOURNEY_STEPS} from '@/lib/kid-journey-copy';
import styles from './kid-journey-rail.module.css';

/**
 * Kid journey rail: Meet → Name → Play → Talk → Rest → Explore → Save.
 * Horizontal stepper with short labels; horizontally scrollable on phones
 * so it never forces page-level horizontal overflow.
 */
export default function KidJourneyRail(){
 return <nav className={styles.rail} aria-label="Your Beast journey">
  <ol>{JOURNEY_STEPS.map((step,i)=><li key={step.key}>
   {step.href.startsWith('/')&&!step.href.endsWith('.html')
    ?<Link prefetch={false} href={step.href} className={styles.step}><span className={styles.num} aria-hidden="true">{i+1}</span><strong>{step.label}</strong><small>{step.hint}</small></Link>
    :<a href={step.href} className={styles.step}><span className={styles.num} aria-hidden="true">{i+1}</span><strong>{step.label}</strong><small>{step.hint}</small></a>}
  </li>)}</ol>
 </nav>;
}
