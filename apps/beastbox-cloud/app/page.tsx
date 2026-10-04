import Link from 'next/link';
import HomepageCreature from '../components/homepage-creature';
import { ArrowUpRight, BrainCircuit, DatabaseZap, Fingerprint, Orbit, Sparkles, ShieldCheck, Stars } from 'lucide-react';
const P=[{icon:BrainCircuit,title:'SWAP THE BRAIN',copy:'Change inference providers without surrendering the history stored by Beast Box.'},{icon:DatabaseZap,title:'KEEP THE STORY',copy:'Memory and checkpoints belong to the substrate. Verify what actually persisted.'},{icon:ShieldCheck,title:'AUTHORITY STAYS HERE',copy:'Models do not inherit tools, credentials, or your workspace permissions.'}];
export default function Home(){
 return <main className="landing">
 <div className="starscape" aria-hidden="true"><span/><span/><span/><span/><span/><span/></div>
 <header className="public-header"><div className="brand"><span className="brand-mark">✺</span><span>BEAST BOX <small>BY CORY DAVIS</small></span></div><span className="pill"><span className="pulse"/> COSMIC CHAOS / EXPLORE THE BEAST CAGE</span><Link className="header-enter" href="/workspace">Enter workstation <ArrowUpRight size={16}/></Link></header>
 <section className="hero">
 <div className="hero-copy"><div className="eyebrow"><Sparkles size={15}/> A universe of your own intelligence</div><h1>A small companion.<br/><em>An entire universe.</em></h1><p>Welcome to a cyber-cosmic habitat for curious humans and their little digital troublemakers. Choose your look, explore real COSMOS systems, and keep model inference separate from memory and authority.</p>
 <div className="hero-cta"><Link href="/beast-cage" className="primary-link">Enter the Beast Cage <ArrowUpRight size={19}/></Link><Link href="/spark/index.html" className="secondary-link">Spark Beasts <ArrowUpRight size={17}/></Link><Link href="/try" className="secondary-link">Try RAWRPHØS · Guest <ArrowUpRight size={17}/></Link><a className="secondary-link" href="https://github.com/NavisWORLD/The-beast-box-" rel="noreferrer" target="_blank">Explore the source <ArrowUpRight size={17}/></a><Link className="secondary-link" href="/research">Latest COSMOS experiments <ArrowUpRight size={17}/></Link><Link className="secondary-link" href="/research/stage015">Stage 015 research <ArrowUpRight size={17}/></Link></div>
 <div className="hero-foot"><span>✹ OWNER-CONTROLLED</span><span>◇ REAL EVIDENCE</span><span>◌ LOCAL-FIRST CORE</span></div></div>
 <div className="beast-landing-art" aria-label="Original cosmic habitat artwork with the galaxy companion"><div className="beast-landing-habitat"/><div className="beast-landing-creature"><HomepageCreature/></div><span className="beast-landing-caption">YOUR OWN LITTLE UNIVERSE · VISUAL PREVIEW</span></div>
 </section>
 <section className="value-strip"><span>MODEL ≠ MEMORY</span><span>MODEL ≠ STATE</span><span>MODEL ≠ AUTHORITY</span></section>
 <section className="feature-section"><div><p className="eyebrow">ENGINEERING + A LITTLE MAGIC</p><h2>Make space for<br/><em>the extraordinary.</em></h2></div><div className="feature-grid">{P.map(x=><article key={x.title} className="feature-card"><x.icon size={27}/><h3>{x.title}</h3><p>{x.copy}</p></article>)}</div></section>
 <footer className="public-footer"><span>© CORY DAVIS · BEAST BOX</span><span>MODEL ≠ SYSTEM · CONTINUITY ≠ CONSCIOUSNESS</span><Link href="/workspace">Launch preview ↗</Link></footer>
 </main>
}