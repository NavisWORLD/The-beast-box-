import type {Metadata} from 'next';
export const metadata:Metadata={title:'Beach Two · Beast Box',description:'A pixel-art beach volleyball world whose randomness is seeded from recorded IBM Quantum outcomes.'};
// Fills the viewport exactly (no bottom black strip; Cosmo's audit). Beach Two is a self-contained three.js toy in /public/beach-two; the site menu stays above it.
export default function BeachTwo(){return <main data-beach-two-page style={{background:'#0b1122',position:'fixed',inset:0,zIndex:1}}>
 {/* Global floating overlays (companion card, sound dock, Zeref voice dock) are hidden here so they never cover the toy or its Synapse panel. */}
 <style>{`body:has([data-beach-two-page]) :is([data-site-sound],[data-zeref-voice-dock],[data-companion-overlay],[data-pet-dragon],[data-spark-beast],[data-lost-cosmos-player-shell],[data-zeref-heart],[data-zeref-reach-out],[aria-controls="beast-chat-overlay"]){display:none!important}`}</style>
 <iframe src="/beach-two/toy.html" title="Beach Two" data-beach-two style={{display:'block',width:'100%',height:'100%',border:0}} allow="fullscreen"/>
</main>}
