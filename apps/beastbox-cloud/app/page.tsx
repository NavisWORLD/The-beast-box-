import Link from 'next/link';
import { ArrowUpRight, BrainCircuit, DatabaseZap, Fingerprint, Orbit, Sparkles, ShieldCheck, Stars } from 'lucide-react';
const P=[{icon:BrainCircuit,title:'SWAP THE BRAIN',copy:'Change inference providers without surrendering the history stored by Beast Box.'},{icon:DatabaseZap,title:'KEEP THE STORY',copy:'Memory and checkpoints belong to the substrate. Verify what actually persisted.'},{icon:ShieldCheck,title:'AUTHORITY STAYS HERE',copy:'Models do not inherit tools, credentials, or your workspace permissions.'}];
export default function Home(){
 return <main className="landing">
 <div className="starscape" aria-hidden="true"><span/><span/><span/><span/><span/><span/></div>
 <header className="public-header"><div className="brand"><span className="brand-mark">✺</span><span>BEAST BOX <small>BY CORY DAVIS</small></span></div><span className="pill"><span className="pulse"/> COSMIC CHAOS / PRIVATE PREVIEW</span><Link className="header-enter" href="/workspace">Enter workstation <ArrowUpRight size={16}/></Link></header>
 <section className="hero">
 <div className="hero-copy"><div className="eyebrow"><Sparkles size={15}/> A universe of your own intelligence</div><h1>Your AI.<br/><em>Your universe.</em><br/>Your story.</h1><p>Meet the cosmic workstation where models can change, memory belongs to you, and every important action leaves a trail. Strange, powerful, and built to be yours.</p>
 <div className="hero-cta"><Link href="/workspace" className="primary-link">Enter Cosmic Chaos <ArrowUpRight size={19}/></Link><a className="secondary-link" href="https://github.com/NavisWORLD/The-beast-box-" rel="noreferrer" target="_blank">Explore the source <ArrowUpRight size={17}/></a></div>
 <div className="hero-foot"><span>✹ OWNER-CONTROLLED</span><span>◇ REAL EVIDENCE</span><span>◌ LOCAL-FIRST CORE</span></div></div>
 <div className="planet-scene" aria-label="Decorative abstract violet planet with luminous orbit"><div className="orbital outer-orbit"/><div className="orbital inner-orbit"/><div className="planet"><div className="planet-shine"/></div><div className="satellite sat-one">✦</div><div className="satellite sat-two">✺</div><div className="planet-card mini-top"><small>✺ ACTIVE SUBSTRATE</small><b>YOUR STORY</b><span>Outside the model</span></div><div className="planet-card mini-bottom"><small>◇ POLICY BOUNDARY</small><b>AUTHORITY: DENIED</b><span>Until you say otherwise</span></div></div>
 </section>
 <section className="value-strip"><span>MODEL ≠ MEMORY</span><span>MODEL ≠ STATE</span><span>MODEL ≠ AUTHORITY</span></section>
 <section className="feature-section"><div><p className="eyebrow">ENGINEERING + A LITTLE MAGIC</p><h2>Make space for<br/><em>the extraordinary.</em></h2></div><div className="feature-grid">{P.map(x=><article key={x.title} className="feature-card"><x.icon size={27}/><h3>{x.title}</h3><p>{x.copy}</p></article>)}</div></section>
 <footer className="public-footer"><span>© CORY DAVIS · BEAST BOX</span><span>MODEL ≠ SYSTEM · CONTINUITY ≠ CONSCIOUSNESS</span><Link href="/workspace">Launch preview ↗</Link></footer>
 </main>
}