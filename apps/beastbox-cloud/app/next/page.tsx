import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Coming soon · Beast Box',
  description: 'Gadget and watch plans. Not shipped. Raw body data stays on the device.',
};

export default function NextPage() {
  return (
    <main className="landing">
      <div className="starscape" aria-hidden="true"><span /><span /><span /><span /><span /><span /></div>
      <header className="public-header">
        <Link className="brand" href="/" aria-label="Beast Box home"><span className="brand-mark">✺</span><span>BEAST BOX <small>COMING SOON</small></span></Link>
        <nav className="public-journey-links" aria-label="Beast Box journey">
          <Link href="/spark/index.html">My Beast</Link>
          <Link href="/beast-cage">Beast Cage</Link>
          <Link href="/privacy">Privacy</Link>
        </nav>
        <Link className="header-enter" href="/">Home</Link>
      </header>
      <section className="hero" style={{ display: 'block', minHeight: 'auto', paddingBottom: 80 }}>
        <p className="eyebrow">NOT SHIPPED · BLUEPRINT</p>
        <h1 style={{ fontSize: 'clamp(40px, 6vw, 72px)' }}>A body, later.</h1>
        <div className="hero-copy" style={{ maxWidth: 720 }}>
          <p>The creature you can use tonight lives in the browser: My Beast, Beast Cage, Lost COSMOS, and Brain Bay. A Meta Muse gadget and a sensor watch are the next place it could be carried. They are not a product you can buy or pair from this site yet.</p>
          <p>The planned rule is on-device first. A walk, a sleep bucket, or an active-day flag could be opted in. Raw heart rate, location, and waveforms would stay on the device. Nothing here syncs those signals today.</p>
          <p>Open work, not a release: the Muse gadget bridge is PR #200, and the Android BLE experiment is PR #199. Neither is merged. A public connector still needs its own storage and review.</p>
          <p><Link className="primary-link" href="/spark/index.html">Meet the beast that exists</Link></p>
        </div>
      </section>
    </main>
  );
}
