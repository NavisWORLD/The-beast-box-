import type {Metadata} from 'next';
export const metadata:Metadata={title:'Beach Two · Beast Box',description:'A pixel-art beach volleyball world whose randomness is seeded from recorded IBM Quantum outcomes.'};
// Beach Two is a self-contained three.js toy in /public/beach-two; the site menu stays above it.
export default function BeachTwo(){return <main style={{background:'#0b1122',minHeight:'calc(100dvh - 44px)'}}>
 <iframe src="/beach-two/toy.html" title="Beach Two" data-beach-two style={{display:'block',width:'100%',height:'calc(100dvh - 44px)',border:0}} allow="fullscreen"/>
</main>}
