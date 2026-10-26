import type { Metadata } from 'next';
import Link from 'next/link';
import JourneyLinks from '@/components/journey-links';
import BrandCrest from '@/components/brand-crest';

export const metadata: Metadata = {
  title: 'Privacy and info · Beast Box',
  description: 'A local-first companion runtime. Your beast stays on this device. Recorded seeds stay labeled.',
};

export default function PrivacyPage() {
  return (
    <main className="landing">
      <div className="starscape" aria-hidden="true"><span /><span /><span /><span /><span /><span /></div>
      <header className="public-header">
        <Link className="brand" href="/" aria-label="Beast Box home"><BrandCrest className="brand-mark" size={42}/><span>BEAST BOX <small>PRIVACY AND INFO</small></span></Link>
        <JourneyLinks skip={["settings"]} extra={[{label:"Coming soon",href:"/next"}]}/>
        <Link className="header-enter" href="/settings">Settings</Link>
      </header>
      <section className="hero" style={{ display: 'block', minHeight: 'auto', paddingBottom: 80 }}>
        <p className="eyebrow">LIVE SUBSTRATE · LOCAL FIRST</p>
        <h1 style={{ fontSize: 'clamp(40px, 6vw, 72px)' }}>The record stays yours.</h1>
        <div className="hero-copy" style={{ maxWidth: 720 }}>
          <p>This is a working substrate. A local-first runtime for memory, state, and provenance. Creatures are seeded from RECORDED IBM measurements or SIMULATED Rigetti simulator counts.</p>
          <p>Your beast's name, care, and QBEAST file stay in this browser. Download or export them and they're yours to keep. Clearing site data removes the local save.</p>
          <p>Microphone reaction uses local amplitude only. Raw audio is never saved. Raw audio is never uploaded. A Muse connection keeps derived focus, calm, and spark. Raw samples are discarded. This is not a medical device. This is not a diagnosis.</p>
          <p>RECORDED seeds are the real IBM run: fixed past measurement counts from hardware job records. SIMULATED seeds are archived Rigetti simulator output. A seed is not a live quantum link. A creature is not conscious.</p>
          <p>The companion reacts to the signals you send. It does not learn from them. Public visitors get the on-device pattern companion. That is not a hosted language model.</p>
          <p>Owner Brain Bay uses a separate route. When that route is down, the status says backend offline. A missing model never invents a reply. A missing model never rewrites the creature.</p>
          <p>Owner memory, model weights, and tool permissions are not in the public file. The gadget and watch are not shipping. <Link href="/next">See what is next.</Link></p>
          <h2 id="labels-and-signals" style={{ marginTop: 36 }}>What the labels mean and how your signals are used</h2>
          <section data-privacy-labels aria-labelledby="labels-and-signals">
            <h3>What the labels mean</h3>
            <ul>
              <li><strong>RECORDED</strong>. A real run on IBM hardware, saved as it came out. Your universe grows from the IBM seed that was RECORDED this way.</li>
              <li><strong>SIMULATED</strong>. A run on a simulator, including the Rigetti-style runs and the way creatures grow. It is not live quantum hardware.</li>
              <li><strong>MEASURED</strong>. A reading that came from you, such as your light level or pulse. We only call it MEASURED when it was a real reading. No reading means no value, and we never invent one.</li>
              <li><strong>SEEDED</strong>. How your signals change your world. Your numbers tilt the four sand wells in your pocket cage. That effect is SEEDED: the same seed gives the same weights.</li>
            </ul>
            <h3>How your signals are used</h3>
            <p>Your universe can react to five signals: time of day, device motion, light level, sound level and fingertip pulse. Each one has its own switch, and every switch is off until you turn it on.</p>
            <p>Your numbers join the same IBM seed that built your universe. They scale the weights of the SIMULATED Rigetti-style receipt that moves the sand in your pocket cage. No new run happens. Nothing about your surroundings runs on quantum hardware.</p>
            <p>Your own beast has its own brain state. We do not claim more than that.</p>
            <h3>What leaves your phone</h3>
            <p>Sound level uses the microphone. Fingertip pulse and light use the camera, and one camera switch covers both. The camera does one job at a time, so while it reads your pulse, the light reading waits. Time of day uses your clock.</p>
            <p>Audio, video and the pulse waveform never leave your phone. Only numbers made from your readings are kept, such as a level or a beats-per-minute value. When you are signed in they are saved privately for your account, and no page on this site shows them to other people. If you are not signed in, nothing is stored: your numbers stay on this device.</p>
            <p>The owner-only IBM BIO page saves its own numbers packet to private owner storage and sends it to the IBM run. Stop sharing does not delete that packet.</p>
            <h3>Starting and stopping</h3>
            <p>Turning world signals on asks you to confirm first.</p>
            <p>Stop sharing ends all reading right away and deletes the numbers saved for you. It is one tap, with no confirm step.</p>
            <h3>Not covered</h3>
            <p>Weather is not used. 12D is a simulation, not a measurement of anything in your room.</p>
          </section>
          <p><a className="primary-link" href="/spark/index.html">Back to My Beast</a></p>
        </div>
      </section>
    </main>
  );
}
