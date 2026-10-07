import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Privacy · Beast Box',
  description: 'What Beast Box stores on this device, what a recorded seed is, and what is not sent.',
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
        <p className="eyebrow">YOUR DEVICE · YOUR CHOICE</p>
        <h1 style={{ fontSize: 'clamp(40px, 6vw, 72px)' }}>What stays here.</h1>
        <div className="hero-copy" style={{ maxWidth: 720 }}>
          <p>A public Beast is game software. Its name, care, and QBEAST file stay in this browser unless you download or export them. Clearing site data for beastboxcosmos.xyz removes that local save. It does not delete a file you already downloaded.</p>
          <p>Microphone reaction, if you turn it on, uses local amplitude for animation. Raw audio is not saved and is not uploaded. A Muse connection, if you consent, keeps derived focus, calm, and spark. Raw samples are discarded. This is not a medical device and not a diagnosis.</p>
          <p>Recorded quantum seeds are fixed past measurement counts, mostly IBM job records. Rigetti entries used by the growth lab are archived simulator outputs. A seed is not a live quantum link, and a creature is not conscious.</p>
          <p>Public visitors talk through the on-device pattern companion. That is not a hosted language model. Owner Brain Bay uses a separate configured route. If that route is down, the status says backend offline. A missing model does not invent a reply or rewrite the creature.</p>
          <p>Owner memory, model weights, and tool permissions are not in the public creature file. A gadget or watch is not shipping on this page. See <Link href="/next">what is coming</Link>.</p>
          <p><Link className="primary-link" href="/spark/index.html">Back to My Beast</Link></p>
        </div>
      </section>
    </main>
  );
}
