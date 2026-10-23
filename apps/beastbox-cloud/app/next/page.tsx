import type { Metadata } from 'next';
import Link from 'next/link';
import JourneyLinks from '@/components/journey-links';
import BrandCrest from '@/components/brand-crest';

export const metadata: Metadata = {
  title: 'Coming Soon · Beast Box',
  description: 'Gadget and watch plans. Not shipped. Raw body data stays on the device.',
};

export default function NextPage() {
  return (
    <main className="landing">
      <div className="starscape" aria-hidden="true"><span /><span /><span /><span /><span /><span /></div>
      <header className="public-header">
        <Link className="brand" href="/" aria-label="Beast Box home"><BrandCrest className="brand-mark" size={42}/><span>BEAST BOX <small>COMING SOON</small></span></Link>
        <JourneyLinks skip={["settings"]} extra={[{label:"Privacy",href:"/privacy"}]}/>
        <Link className="header-enter" href="/settings">Settings</Link>
      </header>
      <section className="hero" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,340px),1fr))', gap: 32, alignItems: 'start', minHeight: 'auto', paddingBottom: 80 }}>
        <div>
        <p className="eyebrow">NOT SHIPPED · BLUEPRINT</p>
        <h1 style={{ fontSize: 'clamp(40px, 6vw, 72px)' }}>Coming Soon</h1>
        <p style={{ fontSize: 20, margin: '0 0 12px', color: '#cfc3ff' }}>The gadget and the watch.</p>
        <div className="hero-copy" style={{ maxWidth: 720 }}>
          <p>The creature you can use tonight lives in the browser: My Beast, Beast Cage, Lost COSMOS, and Brain Bay. A Meta Muse gadget and a sensor watch are the next place it could be carried. They are not a product you can buy or pair from this site yet.</p>
          <p>The planned rule is on-device first. A walk, a sleep bucket, or an active-day flag could be opted in. Raw heart rate, location, and waveforms would stay on the device. Nothing here syncs those signals today.</p>
          <p>Open work, not a release: the Muse gadget bridge is PR #200, and the Android BLE experiment is PR #199. Neither is merged. A public connector still needs its own storage and review.</p>
          <p><a className="primary-link" href="/spark/index.html">Meet the beast that exists</a></p>
        </div>
        </div>
        <div data-next-plans style={{ display: 'grid', gap: 16 }}>
          {[['🎧','The gadget','A Meta Muse headband could let your beast feel calm and focus. Planned, not paired from this site.'],['⌚','The watch','A sensor watch could carry a walk, a sleep bucket or an active-day flag. Raw signals would stay on the watch.'],['🔒','The rule','On-device first. Nothing here syncs body signals today.']].map(([icon,title,text]) => <article key={title} style={{ padding: 20, borderRadius: 20, background: '#15123acc', border: '1px solid #8a6cff55' }}><p style={{ fontSize: 30, margin: 0 }} aria-hidden="true">{icon}</p><h2 style={{ margin: '6px 0', fontSize: 22 }}>{title} <small style={{ fontSize: 11, letterSpacing: '.12em', color: '#ffb86b' }}>NOT SHIPPED</small></h2><p style={{ margin: 0, color: '#c9cbe6', lineHeight: 1.6 }}>{text}</p></article>)}
        </div>
      </section>
    </main>
  );
}
