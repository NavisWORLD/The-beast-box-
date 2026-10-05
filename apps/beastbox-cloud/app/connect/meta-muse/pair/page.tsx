import type { Metadata } from 'next';
import MetaMusePairLanding from '@/components/meta-muse-pair-landing';
import styles from '@/components/meta-muse.module.css';

export const metadata: Metadata = { title: 'Connect Beast Box to Meta Muse', robots: { index: false, follow: false } };

/** Target of the Pair panel QR code / one-tap link. The code stays in the #fragment. */
export default function MetaMusePairPage() {
  return <main className={styles.page}><section className={styles.card}><MetaMusePairLanding /></section></main>;
}
