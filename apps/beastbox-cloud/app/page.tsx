import Link from 'next/link';
import HomepageCreature from '../components/homepage-creature';
import { ArrowUpRight, BrainCircuit, Orbit, Sparkles } from 'lucide-react';

const P=[
 {icon:Sparkles,title:'MEET YOUR BEAST',copy:'Create or load one companion, care for it, name it, and keep the same identity as you move through Beast Box.',href:'/spark/index.html'},
 {icon:Orbit,title:'EXPLORE + PLAY',copy:'Take your Beast into the Cage and LOST COSMOS. You can just play; the technical layers never have to get in the way.',href:'/beast-cage'},
 {icon:BrainCircuit,title:'GO DEEPER WHEN YOU WANT',copy:'Brain Bay and the Lab hold the models, experiments, sensors, evidence and advanced controls for people who want them.',href:'/workspace#brain-bay'}
];

export default function Home(){
 return <main className="landing">
 <div className="starscape" aria-hidden="true"><span/><span/><span/><span/><span/><span/></div>
 <header className="public-header">
  <Link className="brand" href="/" aria-label="Beast Box home"><span className="brand-mark">✺</span><span>BEAST BOX <small>BY CORY DAVIS</small></span></Link>
  <nav className="public-journey-links" aria-label="Beast Box journey">
   <Link href="/spark/index.html">My Beast</Link>
   <Link href="/beast-cage">Beast Cage</Link>
   <Link href="/sol-game">Lost COSMOS</Link>
   <Link href="/workspace#brain-bay">Brain Bay</Link>
   <Link href="/research">Lab</Link>
  </nav>
  <span className="pill"><span className="pulse"/> DREAMERS · IDLERS · PLAYERS · BUILDERS</span>
  <Link className="header-enter" href="/workspace#settings">Settings <ArrowUpRight size={16}/></Link>
 </header>

 <section className="hero">
  <div className="hero-copy">
   <div className="eyebrow"><Sparkles size={15}/> A universe for every curious mind</div>
   <h1>A place for every person.<br/><em>A universe for every idea.</em></h1>
   <p>Dreamer, idler with time to wander, player, builder, researcher, artist, or just curious: start with a little Beast and go only as deep as you want. The creature comes first. The machinery is there when you are ready for it.</p>
   <div className="hero-cta">
    <Link href="/spark/index.html" className="primary-link">Meet My Beast <ArrowUpRight size={19}/></Link>
    <Link href="/beast-cage" className="secondary-link">Enter the Beast Cage <ArrowUpRight size={17}/></Link>
    <Link href="/sol-game" className="secondary-link">Play LOST COSMOS <ArrowUpRight size={17}/></Link>
   </div>
   <div className="hero-foot"><span>✹ NO LOGIN TO MEET YOUR BEAST</span><span>◇ LOCAL-FIRST</span><span>◌ DEEP TOOLS WHEN YOU WANT THEM</span></div>
  </div>
  <div className="beast-landing-art" aria-label="Original cosmic habitat artwork with the galaxy companion"><div className="beast-landing-habitat"/><div className="beast-landing-creature"><HomepageCreature/></div><span className="beast-landing-caption">YOUR OWN LITTLE UNIVERSE · VISUAL PREVIEW</span></div>
 </section>

 <section className="value-strip"><span>MODEL ≠ MEMORY</span><span>MODEL ≠ STATE</span><span>MODEL ≠ AUTHORITY</span></section>
 <section className="feature-section">
  <div><p className="eyebrow">START SIMPLE · GO DEEP WHEN YOU WANT</p><h2>There is a door<br/><em>for however you think.</em></h2></div>
  <div className="feature-grid">{P.map(x=><Link key={x.title} href={x.href} className="feature-card"><x.icon size={27}/><h3>{x.title}</h3><p>{x.copy}</p><span className="secondary-link">Open →</span></Link>)}</div>
 </section>

 <footer className="public-footer">
  <span>© CORY DAVIS · BEAST BOX</span>
  <span>MODEL ≠ SYSTEM · CONTINUITY ≠ CONSCIOUSNESS</span>
  <Link href="/try">Guest model ↗</Link>
  <Link href="/research">Research ↗</Link>
  <a href="https://github.com/NavisWORLD/The-beast-box-" rel="noreferrer" target="_blank">Source ↗</a>
 </footer>
 </main>
}
