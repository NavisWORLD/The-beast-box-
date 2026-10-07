import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Privacy · Beast Box',
  description: 'A local-first companion runtime. Your beast stays on this device. Recorded seeds stay labeled.',
};

export default function PrivacyPage() {
  return (
    <main className="landing">
      <div className="starscape" aria-hidden="true"><span /><span /><span /><span /><span /><span /></div>
      <header className="public-header">
        <Link className="brand" href="/" aria-label="Beast Box home"><span className="brand-mark">✺</span><span>BEAST BOX <small>PRIVACY</small></span></Link>
        <nav className="public-journey-links" aria-label="Beast Box journey">
          <Link href="/spark/index.html">My Beast</Link>
          <Link href="/beast-cage">Beast Cage</Link>
          <Link href="/workspace#brain-bay">Brain Bay</Link>
          <Link href="/next">Coming soon</Link>
        </nav>
        <Link className="header-enter" href="/">Home</Link>
      </header>
      <section className="hero" style={{ display: 'block', minHeight: 'auto', paddingBottom: 80 }}>
        <p className="eyebrow">LIVE SUBSTRATE · LOCAL FIRST</p>
        <h1 style={{ fontSize: 'clamp(40px, 6vw, 72px)' }}>The record stays yours.</h1>
        <div className="hero-copy" style={{ maxWidth: 720 }}>
          <p>This is a working substrate. A local-first runtime for memory, state, and provenance. Creatures are born from real recorded quantum measurements.</p>
          <p>Your beast's name, care, and QBEAST file stay in this browser. Download or export them and they're yours to keep. Clearing site data removes the local save.</p>
          <p>Microphone reaction uses local amplitude only. Raw audio is never saved. Raw audio is never uploaded. A Muse connection keeps derived focus, calm, and spark. Raw samples are discarded. This is not a medical device. This is not a diagnosis.</p>
          <p>Recorded quantum seeds are fixed past measurement counts. IBM entries are hardware job records. Rigetti entries are archived simulator outputs. A seed is not a live quantum link. A creature is not conscious.</p>
          <p>The companion reacts to the signals you send. It does not learn from them. Public visitors get the on-device pattern companion. That is not a hosted language model.</p>
          <p>Owner Brain Bay uses a separate route. When that route is down, the status says backend offline. A missing model never invents a reply. A missing model never rewrites the creature.</p>
          <p>Owner memory, model weights, and tool permissions are not in the public file. The gadget and watch are not shipping. <Link href="/next">See what is next.</Link></p>
          <p><Link className="primary-link" href="/spark/index.html">Back to My Beast</Link></p>
        </div>
      </section>
    </main>
  );
}
