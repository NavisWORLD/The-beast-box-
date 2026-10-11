import Link from 'next/link';
import HomepageCreature from '../components/homepage-creature';
import CosmicSupportWidget from '../components/cosmic-support-widget';
import { ArrowUpRight, BrainCircuit, Orbit, Sparkles } from 'lucide-react';
import BrandCrest from '@/components/brand-crest';
import { ROOMS } from '@/lib/rooms';
import RoomLink from '@/components/room-link';

const ROOM_BLURBS:Record<string,string>={
 beast:'Hatch, name and care for your own Spark Beast.',
 cage:'Visit its habitat, talk to it and change its look.',
 game:'Take your Beast into the LOST COSMOS adventure.',
 brain:'Pick which brain your Beast thinks with.',
 lab:'See the real experiments and evidence.',
 settings:'Sound, motion and your saved Beast.'
};

const P=[
 {icon:Sparkles,title:'MEET YOUR BEAST',copy:'Create or load one companion, care for it, name it, and keep the same identity as you move through Beast Box.',href:'/spark/index.html'},
 {icon:Orbit,title:'EXPLORE + PLAY',copy:'Take your Beast into the Cage and LOST COSMOS. You can just play; the technical layers never have to get in the way.',href:'/beast-cage'},
 {icon:BrainCircuit,title:'GO DEEPER WHEN YOU WANT',copy:'Brain Bay and the Lab hold the models, experiments, sensors, evidence and advanced controls for people who want them.',href:'/brain-bay'}
];

export default function Home(){
 return <main className="landing">
 <div className="starscape" aria-hidden="true"><span/><span/><span/><span/><span/><span/></div>
 <header className="public-header">
  <Link className="brand" href="/" aria-label="Beast Box home"><BrandCrest className="brand-mark" size={42}/><span>BEAST BOX <small>BY CORY DAVIS</small></span></Link>
  <nav className="public-journey-links" aria-label="Beast Box journey">
   <a href="/spark/index.html"><span className="journey-icon" aria-hidden="true">🐣</span>My Beast</a>
   <Link href="/beast-cage" prefetch={false}><span className="journey-icon" aria-hidden="true">🏰</span>Beast Cage</Link>
   <Link href="/sol-game" prefetch={false}><span className="journey-icon" aria-hidden="true">🎮</span>Lost COSMOS</Link>
   <Link href="/brain-bay" prefetch={false}><span className="journey-icon" aria-hidden="true">🧠</span>Brain Bay</Link>
   <Link href="/research" prefetch={false}><span className="journey-icon" aria-hidden="true">🔬</span>Lab</Link>
  </nav>
  <span className="pill"><span className="pulse"/> DREAMERS · IDLERS · PLAYERS · BUILDERS</span>
  <Link className="header-enter" href="/settings">Settings <ArrowUpRight size={16}/></Link>
 </header>

 <section className="hero">
  <div className="hero-copy">
   <div className="eyebrow"><Sparkles size={15}/> A universe for every curious mind</div>
   <h1>A place for every person.<br/><em>A universe for every idea.</em></h1>
   <p>Dreamer, idler with time to wander, player, builder, researcher, artist, or just curious: start with a little Beast and go only as deep as you want. The creature comes first. The machinery is there when you are ready for it.</p>
   <div className="hero-cta">
    <a href="/spark/index.html" className="primary-link">Meet My Beast <ArrowUpRight size={19}/></a>
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
  <div className="feature-grid">{P.map(x=><RoomLink key={x.title} href={x.href} className="feature-card" data-tone={P.indexOf(x)}><x.icon size={27}/><h3>{x.title}</h3><p>{x.copy}</p><span className="secondary-link">Open →</span></RoomLink>)}</div>
 </section>

 <section className="room-map" aria-labelledby="room-map-title">
  <p className="eyebrow">YOUR WORLD MAP</p>
  <h2 id="room-map-title">Where should your Beast go next?</h2>
  <div className="room-map-grid">{ROOMS.filter(room=>room.key!=='home').map(room=><RoomLink key={room.key} href={room.href} prefetch={false} className="room-tile" data-room={room.key}>
   <span className="room-tile-icon" aria-hidden="true">{room.icon}</span>
   <strong>{room.label}</strong>
   <small>{ROOM_BLURBS[room.key]}</small>
   <span className="room-tile-go" aria-hidden="true">Go →</span>
  </RoomLink>)}</div>
 </section>

 <CosmicSupportWidget/>

 <footer className="public-footer">
  <span>© CORY DAVIS · BEAST BOX</span>
  <span>MODEL ≠ SYSTEM · CONTINUITY ≠ CONSCIOUSNESS</span>
  <Link href="/privacy">Privacy ↗</Link>
  <Link href="/next">Gadget & watch ↗</Link>
  <Link href="/try">Guest model ↗</Link>
  <Link href="/research">Research ↗</Link>
  <a href="https://github.com/NavisWORLD/The-beast-box-" rel="noreferrer" target="_blank">Source ↗</a>
 </footer>
 </main>
}
